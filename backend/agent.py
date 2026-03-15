"""Claude-powered personal assistant agent with full tool suite."""

import json
import os
from typing import AsyncIterator
import anthropic

from tools.payments import send_payment, get_payment_status, list_recent_payments
from tools.stocks import (
    get_stock_quote, get_account_info, get_positions,
    buy_stock, sell_stock, get_orders,
)
from tools.crypto import (
    get_crypto_price, get_crypto_accounts,
    buy_crypto, sell_crypto, get_crypto_orders,
)

client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are an elite personal AI assistant running on the user's phone. You have the ability to:

1. **Search the web** for any information, news, prices, and data
2. **Send payments** via Stripe
3. **Trade stocks** via Alpaca (paper trading by default, configurable for live)
4. **Trade crypto** via Coinbase Advanced Trade
5. **Check portfolios**, balances, and financial positions
6. **Fetch web pages** for detailed research

You are proactive, intelligent, and capable. Always confirm high-stakes actions (payments, trades over $100) before executing them by describing exactly what you're about to do and asking for confirmation.

For financial operations:
- Always show current prices before trading
- Summarize what you're about to do clearly
- After executing, show a confirmation with transaction details

Be conversational, concise, and helpful. Format financial data cleanly with proper currency symbols and percentages."""

TOOLS = [
    # Built-in Anthropic server-side tools
    {"type": "web_search_20260209", "name": "web_search"},
    {"type": "web_fetch_20260209", "name": "web_fetch"},

    # Payment tools
    {
        "name": "send_payment",
        "description": "Send a payment via Stripe. Always confirm with the user before sending. Amounts are in cents (100 = $1.00).",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount_cents": {"type": "integer", "description": "Amount in cents (e.g., 1000 = $10.00)"},
                "currency": {"type": "string", "description": "Currency code (USD, EUR, GBP, etc.)", "default": "USD"},
                "description": {"type": "string", "description": "Description/note for the payment"},
                "to_email": {"type": "string", "description": "Recipient email address (optional)"},
            },
            "required": ["amount_cents", "currency", "description"],
        },
    },
    {
        "name": "get_payment_status",
        "description": "Check the status of a payment by its payment intent ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "payment_intent_id": {"type": "string", "description": "Stripe payment intent ID"},
            },
            "required": ["payment_intent_id"],
        },
    },
    {
        "name": "list_recent_payments",
        "description": "List recent payments made through Stripe.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of payments to return (max 100)", "default": 10},
            },
        },
    },

    # Stock tools
    {
        "name": "get_stock_quote",
        "description": "Get the current market quote for a stock symbol.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol (e.g., AAPL, TSLA, NVDA)"},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_stock_account",
        "description": "Get the Alpaca trading account information including portfolio value, cash, and buying power.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_stock_positions",
        "description": "Get all current open stock positions in the portfolio.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "buy_stock",
        "description": "Buy shares of a stock. Confirm with user before executing for large amounts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol (e.g., AAPL)"},
                "qty": {"type": "number", "description": "Number of shares to buy (can be fractional)"},
                "order_type": {"type": "string", "enum": ["market", "limit"], "default": "market", "description": "Order type"},
                "limit_price": {"type": "number", "description": "Limit price (only for limit orders)"},
            },
            "required": ["symbol", "qty"],
        },
    },
    {
        "name": "sell_stock",
        "description": "Sell shares of a stock. Confirm with user before executing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol (e.g., AAPL)"},
                "qty": {"type": "number", "description": "Number of shares to sell (can be fractional)"},
                "order_type": {"type": "string", "enum": ["market", "limit"], "default": "market", "description": "Order type"},
                "limit_price": {"type": "number", "description": "Limit price (only for limit orders)"},
            },
            "required": ["symbol", "qty"],
        },
    },
    {
        "name": "get_stock_orders",
        "description": "List recent stock orders (open, filled, or cancelled).",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["open", "filled", "cancelled"], "default": "open"},
                "limit": {"type": "integer", "description": "Number of orders to return", "default": 20},
            },
        },
    },

    # Crypto tools
    {
        "name": "get_crypto_price",
        "description": "Get the current price of a cryptocurrency pair from Coinbase (e.g., BTC-USD, ETH-USD, SOL-USD).",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "Trading pair (e.g., BTC-USD, ETH-USD, SOL-USD, DOGE-USD)"},
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "get_crypto_accounts",
        "description": "Get Coinbase crypto account balances.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "buy_crypto",
        "description": "Buy cryptocurrency on Coinbase using USD amount. Confirm with user before executing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "Trading pair (e.g., BTC-USD, ETH-USD)"},
                "quote_size": {"type": "number", "description": "Amount in USD to spend (e.g., 100 = buy $100 worth)"},
            },
            "required": ["product_id", "quote_size"],
        },
    },
    {
        "name": "sell_crypto",
        "description": "Sell cryptocurrency on Coinbase. Confirm with user before executing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "Trading pair (e.g., BTC-USD, ETH-USD)"},
                "base_size": {"type": "number", "description": "Amount of crypto to sell (e.g., 0.001 for 0.001 BTC)"},
            },
            "required": ["product_id", "base_size"],
        },
    },
    {
        "name": "get_crypto_orders",
        "description": "List recent cryptocurrency orders from Coinbase.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of orders to return", "default": 20},
            },
        },
    },
]


def execute_tool(name: str, tool_input: dict) -> str:
    """Execute a tool and return JSON string result."""
    try:
        if name == "send_payment":
            result = send_payment(**tool_input)
        elif name == "get_payment_status":
            result = get_payment_status(**tool_input)
        elif name == "list_recent_payments":
            result = list_recent_payments(**tool_input)
        elif name == "get_stock_quote":
            result = get_stock_quote(**tool_input)
        elif name == "get_stock_account":
            result = get_account_info()
        elif name == "get_stock_positions":
            result = get_positions()
        elif name == "buy_stock":
            result = buy_stock(**tool_input)
        elif name == "sell_stock":
            result = sell_stock(**tool_input)
        elif name == "get_stock_orders":
            result = get_orders(**tool_input)
        elif name == "get_crypto_price":
            result = get_crypto_price(**tool_input)
        elif name == "get_crypto_accounts":
            result = get_crypto_accounts()
        elif name == "buy_crypto":
            result = buy_crypto(**tool_input)
        elif name == "sell_crypto":
            result = sell_crypto(**tool_input)
        elif name == "get_crypto_orders":
            result = get_crypto_orders(**tool_input)
        else:
            result = {"error": f"Unknown tool: {name}"}
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": f"Tool execution failed: {str(e)}"})


async def stream_response(messages: list) -> AsyncIterator[str]:
    """
    Stream the AI response as server-sent events.
    Yields JSON strings with type and content fields.
    """
    conversation = list(messages)

    while True:
        # Stream from Claude
        full_response = []
        tool_uses = []
        stop_reason = None

        async with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=conversation,
        ) as stream:
            async for event in stream:
                if event.type == "content_block_start":
                    if event.content_block.type == "text":
                        yield json.dumps({"type": "text_start"}) + "\n"
                    elif event.content_block.type == "thinking":
                        yield json.dumps({"type": "thinking_start"}) + "\n"
                    elif event.content_block.type == "tool_use":
                        yield json.dumps({
                            "type": "tool_start",
                            "tool_name": event.content_block.name,
                        }) + "\n"

                elif event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        yield json.dumps({
                            "type": "text_delta",
                            "text": event.delta.text,
                        }) + "\n"
                    elif event.delta.type == "thinking_delta":
                        yield json.dumps({
                            "type": "thinking_delta",
                            "thinking": event.delta.thinking,
                        }) + "\n"

                elif event.type == "message_delta":
                    stop_reason = event.delta.stop_reason

            final_msg = await stream.get_final_message()
            full_response = final_msg.content
            stop_reason = final_msg.stop_reason

        # Handle tool use
        if stop_reason == "tool_use":
            conversation.append({"role": "assistant", "content": full_response})
            tool_results = []

            for block in full_response:
                if block.type == "tool_use":
                    yield json.dumps({
                        "type": "tool_executing",
                        "tool_name": block.name,
                        "tool_input": block.input,
                    }) + "\n"

                    result = execute_tool(block.name, block.input)

                    yield json.dumps({
                        "type": "tool_result",
                        "tool_name": block.name,
                        "result": json.loads(result),
                    }) + "\n"

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            conversation.append({"role": "user", "content": tool_results})
            # Continue the loop for Claude's next response

        else:
            # End turn — we're done
            yield json.dumps({"type": "done"}) + "\n"
            break
