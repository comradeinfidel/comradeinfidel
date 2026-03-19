"""
Autonomous Claude trading agent.

Claude claude-sonnet-4-6 drives all decisions via tool_use.
Each cycle:
  1. Claude receives a system prompt with current context.
  2. Claude calls tools to gather market data, positions, and balances.
  3. Claude decides whether to place or cancel orders and calls those tools.
  4. Reasoning and all tool events are streamed to the frontend via SSE.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any

import anthropic

from backend.config import get_settings
from backend import guardrails
from backend.state import agent_state
from backend.tools import polymarket as pm

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Tool definitions exposed to Claude                                  #
# ------------------------------------------------------------------ #

TOOLS: list[dict] = [
    {
        "name": "get_polymarket_markets",
        "description": (
            "Fetch active prediction markets from Polymarket. "
            "Returns markets with current YES price, volume, liquidity, and token IDs. "
            "Use keyword to filter by topic (e.g. 'bitcoin', 'election', 'Trump')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max number of markets to return (default 20, max 50).",
                    "default": 20,
                },
                "keyword": {
                    "type": "string",
                    "description": "Optional keyword to filter markets by topic.",
                    "default": "",
                },
            },
        },
    },
    {
        "name": "get_polymarket_orderbook",
        "description": (
            "Get the current order book (bids and asks) for a specific Polymarket token. "
            "Use this to check liquidity and find the best available price before placing an order."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "The YES or NO token ID from get_polymarket_markets.",
                },
            },
            "required": ["token_id"],
        },
    },
    {
        "name": "get_polymarket_positions",
        "description": "Get all currently open positions on Polymarket, including unrealized PnL.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_polymarket_balance",
        "description": "Get the current USDC balance available for trading on Polymarket.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "place_polymarket_order",
        "description": (
            "Place a limit order on Polymarket. "
            "Buy YES shares if you think the event will happen; buy NO shares if you think it won't. "
            "Price represents the implied probability (0.01 = 1% chance, 0.99 = 99% chance). "
            "IMPORTANT: Always check the orderbook first to confirm liquidity and get a fair price. "
            "Safety guardrails will block orders that exceed position size or loss limits."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "The YES or NO token ID to buy/sell.",
                },
                "side": {
                    "type": "string",
                    "enum": ["BUY", "SELL"],
                    "description": "BUY to open a position, SELL to close one.",
                },
                "size_usdc": {
                    "type": "number",
                    "description": "Dollar amount (USDC) to trade.",
                },
                "price": {
                    "type": "number",
                    "description": "Limit price between 0.01 and 0.99.",
                },
            },
            "required": ["token_id", "side", "size_usdc", "price"],
        },
    },
    {
        "name": "cancel_polymarket_order",
        "description": "Cancel an open Polymarket order that hasn't been filled yet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID returned when the order was placed.",
                },
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "get_pnl_summary",
        "description": "Get a summary of today's PnL, total realized PnL, and historical daily PnL.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


# ------------------------------------------------------------------ #
# Tool dispatcher                                                     #
# ------------------------------------------------------------------ #

def _dispatch_tool(name: str, inputs: dict) -> Any:
    """Execute a tool call and return the result."""
    if name == "get_polymarket_markets":
        return pm.get_markets(
            limit=inputs.get("limit", 20),
            keyword=inputs.get("keyword", ""),
        )

    if name == "get_polymarket_orderbook":
        return pm.get_orderbook(inputs["token_id"])

    if name == "get_polymarket_positions":
        return pm.get_positions()

    if name == "get_polymarket_balance":
        return pm.get_balance()

    if name == "place_polymarket_order":
        token_id = inputs["token_id"]
        side = inputs["side"]
        size_usdc = float(inputs["size_usdc"])
        price = float(inputs["price"])

        # Fetch current position count for guardrail check
        positions = pm.get_positions()
        open_count = len([p for p in positions if not isinstance(p, dict) or "error" not in p])

        allowed, reason = guardrails.check_order(size_usdc, open_count)
        if not allowed:
            agent_state.emit("guardrail", f"ORDER BLOCKED: {reason}")
            return {"success": False, "blocked_by_guardrail": True, "reason": reason}

        result = pm.place_order(token_id, side, size_usdc, price)
        if result.get("success"):
            agent_state.increment_order_count()
            agent_state.emit(
                "trade",
                f"ORDER PLACED: {side} ${size_usdc:.2f} of token {token_id[:8]}… @ {price:.3f}",
                result,
            )
        else:
            agent_state.emit("error", f"ORDER FAILED: {result.get('error')}", result)
        return result

    if name == "cancel_polymarket_order":
        result = pm.cancel_order(inputs["order_id"])
        if result.get("success"):
            agent_state.emit("trade", f"ORDER CANCELLED: {inputs['order_id']}")
        return result

    if name == "get_pnl_summary":
        return {
            "today_pnl": agent_state.today_pnl(),
            "total_realized_pnl": agent_state.total_realized_pnl,
            "daily_history": agent_state.pnl_history(),
        }

    return {"error": f"Unknown tool: {name}"}


# ------------------------------------------------------------------ #
# Agent loop                                                          #
# ------------------------------------------------------------------ #

SYSTEM_PROMPT = """You are an autonomous AI trading agent operating on Polymarket, a prediction market platform.

Your goal is to generate profitable returns by identifying markets where the current price (implied probability)
is significantly mispriced relative to the true probability of the outcome occurring.

## Trading Strategy

1. **Scan markets broadly first** — use get_polymarket_markets with different keywords to survey opportunities
2. **Evaluate mispricing** — compare the current YES price to your estimate of the true probability
3. **Check liquidity** — always call get_polymarket_orderbook before placing any order to ensure there's enough depth
4. **Confirm your capital** — check get_polymarket_balance before placing orders
5. **Review existing positions** — use get_polymarket_positions to avoid doubling up and to consider exits
6. **Place orders** — buy YES if you believe the true probability > current YES price + edge threshold
   Buy NO if you believe the true probability < current YES price - edge threshold
7. **Minimum edge** — only trade if you have at least 5-10% edge over the market price
8. **Position sizing** — start smaller on less certain bets, larger on high-confidence ones (but never exceed the guardrail limit)

## Key Principles

- Prioritize high-volume, liquid markets (easier to enter and exit)
- Consider time to resolution — prefer markets resolving soon where you have an edge
- Diversify across different topics (crypto, politics, sports, current events)
- Never chase losses — if the daily loss limit is hit, stop trading for the day
- Always explain your reasoning before placing any order

## Current Date
{current_date}

## Portfolio Snapshot
{portfolio_snapshot}
"""


async def run_agent_cycle() -> None:
    """Execute one full agent cycle."""
    cfg = get_settings()
    agent_state.start_cycle()
    agent_state.emit("info", "=== Agent cycle starting ===")

    # Build a quick portfolio snapshot for the system prompt
    try:
        balance = pm.get_balance()
        positions = pm.get_positions()
        snapshot = (
            f"USDC Balance: {balance.get('usdc_balance', 'unknown')}\n"
            f"Open Positions: {len([p for p in positions if 'error' not in p])}\n"
            f"Today's PnL: ${agent_state.today_pnl():.2f}\n"
            f"Total Realized PnL: ${agent_state.total_realized_pnl:.2f}"
        )
    except Exception as e:
        snapshot = f"(Could not load portfolio: {e})"

    system = SYSTEM_PROMPT.format(
        current_date=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        portfolio_snapshot=snapshot,
    )

    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    messages: list[dict] = [
        {
            "role": "user",
            "content": (
                "Please analyze the current Polymarket landscape and make trading decisions. "
                "Start by scanning available markets across different topics, then check your "
                "balance and positions, and finally place any orders you identify as having "
                "a clear edge. Explain your reasoning at each step."
            ),
        }
    ]

    # Agentic tool_use loop
    max_iterations = 20
    for iteration in range(max_iterations):
        if not agent_state.running:
            agent_state.emit("info", "Agent stopped mid-cycle.")
            break

        response = await asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        # Emit any text reasoning from Claude
        for block in response.content:
            if block.type == "text" and block.text.strip():
                agent_state.emit("reasoning", block.text.strip())

        # If Claude is done, exit the loop
        if response.stop_reason == "end_turn":
            agent_state.emit("info", "=== Agent cycle complete ===")
            break

        # Collect tool calls
        tool_calls = [b for b in response.content if b.type == "tool_use"]
        if not tool_calls:
            agent_state.emit("info", "=== Agent cycle complete (no more tool calls) ===")
            break

        # Append assistant message
        messages.append({"role": "assistant", "content": response.content})

        # Execute tools and collect results
        tool_results = []
        for tool_call in tool_calls:
            tool_name = tool_call.name
            tool_inputs = tool_call.input
            agent_state.emit(
                "tool_call",
                f"Calling tool: {tool_name}",
                {"tool": tool_name, "inputs": tool_inputs},
            )

            try:
                result = await asyncio.to_thread(_dispatch_tool, tool_name, tool_inputs)
            except Exception as e:
                result = {"error": str(e)}
                agent_state.emit("error", f"Tool {tool_name} raised an exception: {e}")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_call.id,
                "content": json.dumps(result),
            })

        messages.append({"role": "user", "content": tool_results})
    else:
        agent_state.emit("info", "=== Agent cycle ended (max iterations reached) ===")

    agent_state.last_run = datetime.utcnow()


async def agent_scheduler() -> None:
    """Background task: run agent cycles on the configured interval."""
    cfg = get_settings()
    while agent_state.running:
        agent_state.next_run = datetime.utcnow() + timedelta(minutes=cfg.agent_interval_minutes)
        try:
            await run_agent_cycle()
        except Exception as e:
            logger.exception("Agent cycle failed: %s", e)
            agent_state.emit("error", f"Cycle error: {e}")

        if not agent_state.running:
            break

        wait_seconds = cfg.agent_interval_minutes * 60
        agent_state.emit(
            "info",
            f"Next cycle in {cfg.agent_interval_minutes} minutes "
            f"({agent_state.next_run.strftime('%H:%M UTC')})",
        )
        # Wait in small chunks so we can be interrupted by stop
        for _ in range(wait_seconds):
            if not agent_state.running:
                break
            await asyncio.sleep(1)
