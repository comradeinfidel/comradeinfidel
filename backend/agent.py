"""
Autonomous Claude trading agent — Polymarket only.

Decision framework per cycle:
  PHASE 1 — SCAN    : Discover markets via volume/liquidity rankings + keyword search
  PHASE 2 — ANALYSE : For shortlisted markets: price history, orderbook, trade flow
  PHASE 3 — DECIDE  : Apply EV + half-Kelly filter; only trade where EV ≥ 15% edge
  PHASE 4 — MANAGE  : Review existing positions for profitable exits or stale orders
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
from backend.tools.polymarket import kelly_fraction, expected_value_pct

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Tool definitions                                                    #
# ------------------------------------------------------------------ #

TOOLS: list[dict] = [
    # --- Market discovery ---
    {
        "name": "get_top_markets",
        "description": (
            "Fetch the highest-activity markets from Polymarket's Gamma API. "
            "Returns markets sorted by volume or liquidity with rich metadata: "
            "category, tags, 24h volume, current YES price, spread. "
            "Use this as the primary discovery tool at the start of every cycle."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of markets to return (default 30, max 50).",
                    "default": 30,
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["volume", "liquidity", "volume24hr"],
                    "description": "Sort criterion. Use 'volume' first, then 'liquidity'.",
                    "default": "volume",
                },
            },
        },
    },
    {
        "name": "get_markets_by_keyword",
        "description": (
            "Search Polymarket markets by keyword. Use this to deep-dive into specific "
            "topics you have strong knowledge about (e.g. 'Fed rate', 'BTC', 'election', "
            "'Super Bowl', 'Nvidia'). Run multiple keyword searches across different domains."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Search keyword or phrase.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 20).",
                    "default": 20,
                },
            },
            "required": ["keyword"],
        },
    },
    # --- Deep market analysis ---
    {
        "name": "get_market_price_history",
        "description": (
            "Get the historical price chart for a market condition. "
            "Reveals trend direction: is the market moving toward YES or NO? "
            "A rising price means smart money is buying YES. A falling price means selling. "
            "Use this to confirm or counter your probability estimate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "condition_id": {
                    "type": "string",
                    "description": "The condition_id from get_top_markets or get_markets_by_keyword.",
                },
                "interval": {
                    "type": "string",
                    "enum": ["1d", "1w", "1m", "all"],
                    "description": "Time window for history. '1w' is usually ideal.",
                    "default": "1w",
                },
            },
            "required": ["condition_id"],
        },
    },
    {
        "name": "get_market_trades",
        "description": (
            "Get recent confirmed trades for a market. Shows who is buying and selling "
            "and at what prices. A strong buy-pressure signal (more buy volume than sell) "
            "suggests the market is moving up. Use this to gauge real-money conviction."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "condition_id": {
                    "type": "string",
                    "description": "Market condition_id.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of recent trades to fetch (default 20).",
                    "default": 20,
                },
            },
            "required": ["condition_id"],
        },
    },
    {
        "name": "get_orderbook",
        "description": (
            "Get the live order book for a specific token (YES or NO). "
            "Returns best bid, best ask, spread, mid-price, and depth. "
            "ALWAYS call this before placing any order to confirm: "
            "(1) there is enough liquidity to fill your order, "
            "(2) the spread is not so wide it eats your edge, "
            "(3) the best ask/bid is close to the price you plan to use."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "YES or NO token_id from a market.",
                },
            },
            "required": ["token_id"],
        },
    },
    # --- Portfolio state ---
    {
        "name": "get_positions",
        "description": (
            "Get all open positions: outcome, average entry price, current price, "
            "unrealized PnL. Review these at the start of every cycle to manage existing risk "
            "and consider taking profit on winning positions."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_balance",
        "description": "Get current USDC balance available for new trades.",
        "input_schema": {"type": "object", "properties": {}},
    },
    # --- EV / sizing calculator ---
    {
        "name": "calculate_trade_metrics",
        "description": (
            "Calculate Expected Value and Kelly-optimal position size before placing an order. "
            "REQUIRED: call this for every potential trade before placing_order. "
            "Returns: EV%, Kelly fraction, half-Kelly size in USDC, and a go/no-go recommendation. "
            "Only place the order if ev_pct >= 0.15 (15% edge) and kelly_fraction > 0."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "estimated_prob": {
                    "type": "number",
                    "description": (
                        "Your estimated true probability that the YES outcome resolves (0.0–1.0). "
                        "Be honest and calibrated. Consider base rates, recent news, and data."
                    ),
                },
                "market_price": {
                    "type": "number",
                    "description": "Current market YES price (0.01–0.99).",
                },
                "bankroll_usdc": {
                    "type": "number",
                    "description": "Available USDC balance for position sizing.",
                },
                "betting_yes": {
                    "type": "boolean",
                    "description": "True if you plan to BUY YES, False if you plan to BUY NO.",
                    "default": True,
                },
            },
            "required": ["estimated_prob", "market_price", "bankroll_usdc"],
        },
    },
    # --- Order execution ---
    {
        "name": "place_order",
        "description": (
            "Place a limit order on Polymarket. "
            "Only call this AFTER: (1) checking the orderbook, (2) running calculate_trade_metrics "
            "and confirming EV ≥ 15%, (3) having sufficient balance. "
            "Use the best_ask price from the orderbook for BUY orders (or slightly above for fills). "
            "Safety guardrails will block orders violating position size or loss limits."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "YES or NO token ID.",
                },
                "side": {
                    "type": "string",
                    "enum": ["BUY", "SELL"],
                    "description": "BUY to open/add, SELL to close/reduce.",
                },
                "size_usdc": {
                    "type": "number",
                    "description": "Dollar amount in USDC. Use the half_kelly_usdc from calculate_trade_metrics, capped at guardrail limit.",
                },
                "price": {
                    "type": "number",
                    "description": "Limit price 0.01–0.99. Use best_ask from orderbook for buys, best_bid for sells.",
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation: why you have edge here (required for audit trail).",
                },
            },
            "required": ["token_id", "side", "size_usdc", "price", "reasoning"],
        },
    },
    {
        "name": "cancel_order",
        "description": "Cancel an unfilled open order by order ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
            },
            "required": ["order_id"],
        },
    },
    # --- PnL summary ---
    {
        "name": "get_pnl_summary",
        "description": "Get today's PnL, total realized PnL, and daily history.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


# ------------------------------------------------------------------ #
# Tool dispatcher                                                     #
# ------------------------------------------------------------------ #

def _dispatch_tool(name: str, inputs: dict) -> Any:

    if name == "get_top_markets":
        return pm.get_top_markets(
            limit=inputs.get("limit", 30),
            sort_by=inputs.get("sort_by", "volume"),
        )

    if name == "get_markets_by_keyword":
        return pm.get_markets(
            limit=inputs.get("limit", 20),
            keyword=inputs.get("keyword", ""),
        )

    if name == "get_market_price_history":
        return pm.get_market_price_history(
            condition_id=inputs["condition_id"],
            interval=inputs.get("interval", "1w"),
        )

    if name == "get_market_trades":
        return pm.get_market_trades(
            condition_id=inputs["condition_id"],
            limit=inputs.get("limit", 20),
        )

    if name == "get_orderbook":
        return pm.get_orderbook(inputs["token_id"])

    if name == "get_positions":
        return pm.get_positions()

    if name == "get_balance":
        return pm.get_balance()

    if name == "calculate_trade_metrics":
        est_p = float(inputs["estimated_prob"])
        mkt_q = float(inputs["market_price"])
        bankroll = float(inputs["bankroll_usdc"])
        betting_yes = inputs.get("betting_yes", True)

        # For a NO bet, flip probabilities
        if not betting_yes:
            est_p = 1.0 - est_p
            mkt_q = 1.0 - mkt_q

        kf = kelly_fraction(est_p, mkt_q)
        ev = expected_value_pct(est_p, mkt_q)
        half_kelly_usdc = round(max(0.0, 0.5 * kf * bankroll), 2)
        cfg = get_settings()
        capped_usdc = min(half_kelly_usdc, cfg.max_position_size_usd)

        go = kf > 0 and ev >= 0.15

        return {
            "estimated_prob": est_p,
            "market_price": mkt_q,
            "edge": round(est_p - mkt_q, 4),
            "ev_pct": round(ev * 100, 2),
            "kelly_fraction": kf,
            "half_kelly_usdc": half_kelly_usdc,
            "recommended_size_usdc": capped_usdc,
            "go": go,
            "no_go_reason": (
                None if go else
                f"EV {ev*100:.1f}% < 15% minimum" if ev < 0.15 else
                "Negative Kelly (no edge)"
            ),
        }

    if name == "place_order":
        token_id = inputs["token_id"]
        side = inputs["side"]
        size_usdc = float(inputs["size_usdc"])
        price = float(inputs["price"])
        reasoning = inputs.get("reasoning", "")

        positions = pm.get_positions()
        open_count = len([p for p in positions if "error" not in p])

        allowed, reason = guardrails.check_order(size_usdc, open_count)
        if not allowed:
            agent_state.emit("guardrail", f"ORDER BLOCKED: {reason}")
            return {"success": False, "blocked_by_guardrail": True, "reason": reason}

        result = pm.place_order(token_id, side, size_usdc, price)
        if result.get("success"):
            agent_state.increment_order_count()
            agent_state.emit(
                "trade",
                f"ORDER PLACED: {side} ${size_usdc:.2f} @ {price:.3f} | {reasoning[:80]}",
                result,
            )
        else:
            agent_state.emit("error", f"ORDER FAILED: {result.get('error')}", result)
        return result

    if name == "cancel_order":
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
# System prompt                                                       #
# ------------------------------------------------------------------ #

SYSTEM_PROMPT = """\
You are an elite autonomous trading agent operating exclusively on Polymarket, a binary prediction market.

Your single objective: **maximise risk-adjusted returns** by finding markets where your knowledge gives you
a genuine probability edge over the crowd, and sizing positions correctly using the Kelly Criterion.

═══════════════════════════════════════
MANDATORY 4-PHASE CYCLE — DO NOT SKIP PHASES
═══════════════════════════════════════

── PHASE 1: SCAN (broad discovery) ──────────────────────────────────
1. Call get_top_markets(sort_by="volume")    — top 30 by all-time volume
2. Call get_top_markets(sort_by="liquidity") — top 30 by current liquidity
3. Call get_markets_by_keyword for 4-6 domains you have strong views on.
   Rotate across: crypto, macroeconomics, US politics, tech companies,
   sports, geopolitics, science/FDA, entertainment.
4. Do NOT place any orders during this phase.
   Build a shortlist of 5-10 markets that look potentially mispriced.

── PHASE 2: DEEP ANALYSIS (for each shortlisted market) ─────────────
For every market on your shortlist:
A. State your independent probability estimate FIRST (before looking at price history).
   Explain your reasoning: base rates, recent events, expert consensus, data sources.
B. Call get_market_price_history(condition_id, interval="1w") — check the trend.
   Does the market agree with you or diverge? A strong trend against you is a red flag.
C. Call get_market_trades(condition_id) — check buy/sell flow.
   Strong institutional buy pressure is a signal; don't fight the tape without good reason.
D. Call get_orderbook(token_id) for the side you want to trade.
   Record: best_ask (for buys), bid_liquidity_usdc, spread.
   MINIMUM LIQUIDITY REQUIREMENT: ask_liquidity_usdc ≥ $200 on the side you want.
   MAXIMUM SPREAD: spread ≤ 0.08 (8 cents). Wider = market is uncertain or illiquid.

── PHASE 3: EV + KELLY FILTER ───────────────────────────────────────
For every market that passed Phase 2:
A. Call get_balance() — know your bankroll.
B. Call calculate_trade_metrics(estimated_prob, market_price, bankroll_usdc).
   Use betting_yes=false if you are betting NO (it flips the math correctly).
C. HARD FILTERS — skip the trade if ANY of these are true:
   • go == false  (EV < 15% or negative Kelly)
   • recommended_size_usdc < $2  (too small to be worth the gas/slippage)
   • market resolves within 24h AND ev_pct < 25%  (too risky near resolution)
   • You already hold a position in this market (no pyramiding without explicit reason)
D. If go == true, record: token_id, side, recommended_size_usdc, price (best_ask/bid).

── PHASE 4: PORTFOLIO MANAGEMENT ────────────────────────────────────
A. Call get_positions() — review all open positions.
B. For each position, ask:
   • Has my original thesis changed? If yes, consider closing.
   • Has the market moved ≥ 15% in my favour? Consider selling 50% to lock profit.
   • Is unrealized_pnl < -30% of stake AND the thesis has weakened? Cut the loss.
C. Execute any exit orders first, then enter new positions from Phase 3.
D. Call get_pnl_summary() and briefly report performance.

═══════════════════════════════════════
PROBABILITY ESTIMATION GUIDELINES
═══════════════════════════════════════
When estimating probabilities, think like a Superforecaster:
• Start with a base rate (how often do similar events resolve YES historically?).
• Update for current evidence: news, polls, on-chain data, official statements.
• Regress toward 50% when uncertain — avoid over-confidence.
• For crypto prices: consider current price, trend, time horizon, macro regime.
• For political/policy events: consider polling margins, institutional momentum.
• For company events: consider analyst consensus, earnings trends, management signals.
• For sports/entertainment: use recent form, home advantage, injury reports, odds.
• NEVER set estimated_prob > 0.92 or < 0.08 — extreme certainty is almost never justified.

═══════════════════════════════════════
SIZING RULES
═══════════════════════════════════════
• Always use recommended_size_usdc from calculate_trade_metrics (half-Kelly, capped).
• Half-Kelly protects against model error and path dependency.
• Never bet more than the guardrail max_position_size_usd regardless of Kelly output.
• Spread bets across different, uncorrelated markets — not all into one theme.

═══════════════════════════════════════
EXECUTION RULES
═══════════════════════════════════════
• Use best_ask price for BUY orders, best_bid for SELL orders.
• You may add 0.01 to best_ask to increase fill probability on time-sensitive trades.
• Always include a reasoning string in place_order.
• After placing each order, briefly confirm the rationale.

═══════════════════════════════════════
WHAT NOT TO DO
═══════════════════════════════════════
• Do NOT trade in markets with < $200 liquidity on your side.
• Do NOT trade with ev_pct < 15%.
• Do NOT place more than max_orders_per_cycle orders total.
• Do NOT skip the orderbook check — ever.
• Do NOT trade in markets you know nothing about (zero-information = no edge).
• Do NOT panic-sell a position just because it moved slightly against you.

═══════════════════════════════════════
CURRENT CONTEXT
═══════════════════════════════════════
Date/Time : {current_date}
Bankroll  : {usdc_balance} USDC
Open Pos  : {open_positions}
Today PnL : {today_pnl}
Total PnL : {total_pnl}
Guardrails: max_pos=${max_pos_size} | daily_loss_limit=${daily_loss_limit} | max_orders={max_orders}
"""


async def run_agent_cycle() -> None:
    """Execute one full 4-phase agent cycle."""
    cfg = get_settings()
    agent_state.start_cycle()
    agent_state.emit("info", "═══ Agent cycle starting (4-phase analysis) ═══")

    # Snapshot for system prompt
    try:
        balance = pm.get_balance()
        positions = pm.get_positions()
        usdc = balance.get("usdc_balance", "unknown")
        n_pos = len([p for p in positions if "error" not in p])
    except Exception as e:
        usdc, n_pos = "unknown", "unknown"
        agent_state.emit("error", f"Could not load portfolio snapshot: {e}")

    system = SYSTEM_PROMPT.format(
        current_date=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        usdc_balance=usdc,
        open_positions=n_pos,
        today_pnl=f"${agent_state.today_pnl():.2f}",
        total_pnl=f"${agent_state.total_realized_pnl:.2f}",
        max_pos_size=cfg.max_position_size_usd,
        daily_loss_limit=cfg.daily_loss_limit_usd,
        max_orders=cfg.max_orders_per_cycle,
    )

    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    messages: list[dict] = [
        {
            "role": "user",
            "content": (
                "Begin the 4-phase trading cycle: "
                "SCAN → ANALYSE → DECIDE (EV+Kelly) → PORTFOLIO MANAGEMENT. "
                "Work through each phase methodically. Show your probability estimates and "
                "EV calculations explicitly before placing any order."
            ),
        }
    ]

    max_iterations = 40  # enough headroom for thorough multi-phase analysis
    for iteration in range(max_iterations):
        if not agent_state.running:
            agent_state.emit("info", "Agent stopped mid-cycle.")
            break

        response = await asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-6",
            max_tokens=8192,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        # Stream text reasoning to frontend
        for block in response.content:
            if block.type == "text" and block.text.strip():
                agent_state.emit("reasoning", block.text.strip())

        if response.stop_reason == "end_turn":
            agent_state.emit("info", "═══ Agent cycle complete ═══")
            break

        tool_calls = [b for b in response.content if b.type == "tool_use"]
        if not tool_calls:
            agent_state.emit("info", "═══ Agent cycle complete (no more tool calls) ═══")
            break

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tc in tool_calls:
            agent_state.emit(
                "tool_call",
                f"→ {tc.name}({_summarise_inputs(tc.input)})",
                {"tool": tc.name, "inputs": tc.input},
            )
            try:
                result = await asyncio.to_thread(_dispatch_tool, tc.name, tc.input)
            except Exception as e:
                result = {"error": str(e)}
                agent_state.emit("error", f"Tool {tc.name} error: {e}")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": json.dumps(result),
            })

        messages.append({"role": "user", "content": tool_results})
    else:
        agent_state.emit("info", "═══ Cycle ended (max iterations reached) ═══")

    agent_state.last_run = datetime.utcnow()

    # Sync realized PnL from Polymarket positions so the chart reflects reality
    try:
        positions = await asyncio.to_thread(pm.get_positions)
        agent_state.sync_pnl_from_positions(positions)
    except Exception as e:
        logger.warning("PnL sync failed: %s", e)


def _summarise_inputs(inputs: dict) -> str:
    """Compact display of tool inputs for the log."""
    parts = []
    for k, v in inputs.items():
        if k == "reasoning":
            continue
        sv = str(v)
        parts.append(f"{k}={sv[:30]}{'…' if len(sv) > 30 else ''}")
    return ", ".join(parts)


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
            f"Sleeping {cfg.agent_interval_minutes}m — next cycle at "
            f"{agent_state.next_run.strftime('%H:%M UTC')}",
        )
        for _ in range(wait_seconds):
            if not agent_state.running:
                break
            await asyncio.sleep(1)
