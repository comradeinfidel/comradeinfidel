"""Alpaca stock trading tools for the AI assistant."""

import os
from typing import Optional
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

API_KEY = os.getenv("ALPACA_API_KEY", "")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

PAPER = "paper-api" in BASE_URL


def _trading_client():
    return TradingClient(API_KEY, SECRET_KEY, paper=PAPER)


def _data_client():
    return StockHistoricalDataClient(API_KEY, SECRET_KEY)


def get_stock_quote(symbol: str) -> dict:
    """Get the latest quote for a stock symbol."""
    try:
        client = _data_client()
        req = StockLatestQuoteRequest(symbol_or_symbols=symbol.upper())
        quotes = client.get_stock_latest_quote(req)
        q = quotes[symbol.upper()]
        return {
            "success": True,
            "symbol": symbol.upper(),
            "ask_price": float(q.ask_price),
            "bid_price": float(q.bid_price),
            "ask_size": int(q.ask_size),
            "bid_size": int(q.bid_size),
            "timestamp": q.timestamp.isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_account_info() -> dict:
    """Get Alpaca account information including portfolio value and buying power."""
    try:
        client = _trading_client()
        account = client.get_account()
        return {
            "success": True,
            "id": str(account.id),
            "portfolio_value": float(account.portfolio_value),
            "cash": float(account.cash),
            "buying_power": float(account.buying_power),
            "equity": float(account.equity),
            "day_trade_count": account.daytrade_count,
            "pattern_day_trader": account.pattern_day_trader,
            "trading_blocked": account.trading_blocked,
            "paper": PAPER,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_positions() -> dict:
    """Get all open stock positions."""
    try:
        client = _trading_client()
        positions = client.get_all_positions()
        return {
            "success": True,
            "positions": [
                {
                    "symbol": p.symbol,
                    "qty": float(p.qty),
                    "avg_entry_price": float(p.avg_entry_price),
                    "current_price": float(p.current_price),
                    "market_value": float(p.market_value),
                    "unrealized_pl": float(p.unrealized_pl),
                    "unrealized_plpc": float(p.unrealized_plpc),
                    "side": str(p.side),
                }
                for p in positions
            ],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def buy_stock(symbol: str, qty: float, order_type: str = "market", limit_price: Optional[float] = None) -> dict:
    """Buy shares of a stock."""
    try:
        client = _trading_client()
        if order_type == "limit" and limit_price:
            req = LimitOrderRequest(
                symbol=symbol.upper(),
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
                limit_price=limit_price,
            )
        else:
            req = MarketOrderRequest(
                symbol=symbol.upper(),
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
            )
        order = client.submit_order(req)
        return {
            "success": True,
            "order_id": str(order.id),
            "symbol": order.symbol,
            "qty": float(order.qty),
            "side": str(order.side),
            "type": str(order.type),
            "status": str(order.status),
            "created_at": order.created_at.isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def sell_stock(symbol: str, qty: float, order_type: str = "market", limit_price: Optional[float] = None) -> dict:
    """Sell shares of a stock."""
    try:
        client = _trading_client()
        if order_type == "limit" and limit_price:
            req = LimitOrderRequest(
                symbol=symbol.upper(),
                qty=qty,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
                limit_price=limit_price,
            )
        else:
            req = MarketOrderRequest(
                symbol=symbol.upper(),
                qty=qty,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
            )
        order = client.submit_order(req)
        return {
            "success": True,
            "order_id": str(order.id),
            "symbol": order.symbol,
            "qty": float(order.qty),
            "side": str(order.side),
            "type": str(order.type),
            "status": str(order.status),
            "created_at": order.created_at.isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_orders(status: str = "open", limit: int = 20) -> dict:
    """Get stock orders."""
    try:
        client = _trading_client()
        status_map = {
            "open": OrderStatus.OPEN,
            "filled": OrderStatus.FILLED,
            "cancelled": OrderStatus.CANCELED,
        }
        req = GetOrdersRequest(status=status_map.get(status, OrderStatus.OPEN), limit=limit)
        orders = client.get_orders(req)
        return {
            "success": True,
            "orders": [
                {
                    "order_id": str(o.id),
                    "symbol": o.symbol,
                    "qty": float(o.qty) if o.qty else None,
                    "filled_qty": float(o.filled_qty) if o.filled_qty else None,
                    "side": str(o.side),
                    "type": str(o.type),
                    "status": str(o.status),
                    "submitted_at": o.submitted_at.isoformat() if o.submitted_at else None,
                }
                for o in orders
            ],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
