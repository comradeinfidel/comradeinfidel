"""
Polymarket CLOB API wrappers using py-clob-client.

Authentication:
  L1: Ethereum private key on Polygon (chain 137)
  L2: HMAC-SHA256 derived API key/secret/passphrase

Run backend/scripts/setup_polymarket.py once to generate L2 credentials.
"""

import logging
from typing import Any

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import (
    ApiCreds,
    OrderArgs,
    OrderType,
    BUY,
    SELL,
)
from py_clob_client.constants import POLYGON

from backend.config import get_settings

logger = logging.getLogger(__name__)

_client: ClobClient | None = None

POLYMARKET_HOST = "https://clob.polymarket.com"


def _get_client() -> ClobClient:
    global _client
    if _client is None:
        cfg = get_settings()
        creds = ApiCreds(
            api_key=cfg.polymarket_api_key,
            api_secret=cfg.polymarket_api_secret,
            api_passphrase=cfg.polymarket_api_passphrase,
        )
        _client = ClobClient(
            host=POLYMARKET_HOST,
            chain_id=POLYGON,
            key=cfg.polymarket_private_key,
            creds=creds,
            signature_type=0,
            funder=cfg.polymarket_funder_address or None,
        )
    return _client


def get_markets(limit: int = 20, keyword: str = "") -> list[dict[str, Any]]:
    """Return active prediction markets, optionally filtered by keyword."""
    client = _get_client()
    try:
        resp = client.get_markets()
        markets = resp.get("data", []) if isinstance(resp, dict) else []
        if keyword:
            keyword_lower = keyword.lower()
            markets = [
                m for m in markets
                if keyword_lower in m.get("question", "").lower()
                or keyword_lower in m.get("description", "").lower()
            ]
        result = []
        for m in markets[:limit]:
            tokens = m.get("tokens", [])
            yes_price = None
            yes_token_id = None
            no_token_id = None
            for t in tokens:
                if t.get("outcome", "").upper() == "YES":
                    yes_price = t.get("price")
                    yes_token_id = t.get("token_id")
                elif t.get("outcome", "").upper() == "NO":
                    no_token_id = t.get("token_id")
            result.append({
                "condition_id": m.get("condition_id"),
                "question": m.get("question"),
                "description": m.get("description", ""),
                "end_date": m.get("end_date_iso"),
                "yes_price": yes_price,
                "yes_token_id": yes_token_id,
                "no_token_id": no_token_id,
                "volume": m.get("volume"),
                "liquidity": m.get("liquidity"),
                "active": m.get("active", True),
                "closed": m.get("closed", False),
            })
        return result
    except Exception as e:
        logger.error("get_markets failed: %s", e)
        return [{"error": str(e)}]


def get_orderbook(token_id: str) -> dict[str, Any]:
    """Return current orderbook (bids and asks) for a token."""
    client = _get_client()
    try:
        book = client.get_order_book(token_id)
        return {
            "token_id": token_id,
            "bids": [{"price": b.price, "size": b.size} for b in (book.bids or [])],
            "asks": [{"price": a.price, "size": a.size} for a in (book.asks or [])],
        }
    except Exception as e:
        logger.error("get_orderbook failed: %s", e)
        return {"error": str(e)}


def get_positions() -> list[dict[str, Any]]:
    """Return all open positions on Polymarket."""
    client = _get_client()
    try:
        positions = client.get_positions()
        if not isinstance(positions, list):
            positions = positions.get("data", []) if isinstance(positions, dict) else []
        result = []
        for p in positions:
            result.append({
                "condition_id": p.get("conditionId") or p.get("condition_id"),
                "token_id": p.get("tokenId") or p.get("token_id"),
                "outcome": p.get("outcome"),
                "size": p.get("size"),
                "avg_price": p.get("avgPrice") or p.get("avg_price"),
                "current_price": p.get("currentPrice") or p.get("current_price"),
                "realized_pnl": p.get("realizedPnl") or p.get("realized_pnl", 0),
                "unrealized_pnl": p.get("unrealizedPnl") or p.get("unrealized_pnl", 0),
            })
        return result
    except Exception as e:
        logger.error("get_positions failed: %s", e)
        return [{"error": str(e)}]


def get_balance() -> dict[str, Any]:
    """Return USDC balance available for trading on Polymarket."""
    client = _get_client()
    try:
        from py_clob_client.clob_types import BalanceAllowanceParams, AssetType
        params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        balance = client.get_balance_allowance(params=params)
        return {
            "usdc_balance": balance.get("balance") or balance.get("asset", {}).get("balance", 0),
            "allowance": balance.get("allowance", 0),
        }
    except Exception as e:
        logger.error("get_balance failed: %s", e)
        return {"error": str(e)}


def place_order(
    token_id: str,
    side: str,
    size_usdc: float,
    price: float,
) -> dict[str, Any]:
    """
    Place a limit order on Polymarket.

    Args:
        token_id: The YES or NO token ID for the market
        side: "BUY" or "SELL"
        size_usdc: Dollar amount to trade
        price: Limit price between 0.01 and 0.99 (represents probability %)
    """
    client = _get_client()
    try:
        order_side = BUY if side.upper() == "BUY" else SELL
        # size in shares = size_usdc / price for BUY
        size_shares = round(size_usdc / price, 2) if side.upper() == "BUY" else round(size_usdc, 2)
        order_args = OrderArgs(
            token_id=token_id,
            price=price,
            size=size_shares,
            side=order_side,
        )
        signed_order = client.create_order(order_args)
        resp = client.post_order(signed_order, OrderType.GTC)
        return {
            "success": True,
            "order_id": resp.get("orderID") or resp.get("id"),
            "token_id": token_id,
            "side": side,
            "price": price,
            "size_usdc": size_usdc,
            "size_shares": size_shares,
            "status": resp.get("status"),
        }
    except Exception as e:
        logger.error("place_order failed: %s", e)
        return {"success": False, "error": str(e)}


def cancel_order(order_id: str) -> dict[str, Any]:
    """Cancel an open Polymarket order by ID."""
    client = _get_client()
    try:
        resp = client.cancel(order_id)
        return {"success": True, "order_id": order_id, "response": resp}
    except Exception as e:
        logger.error("cancel_order failed: %s", e)
        return {"success": False, "error": str(e)}
