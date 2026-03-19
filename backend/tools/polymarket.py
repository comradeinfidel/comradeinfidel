"""
Polymarket API wrappers.

Two APIs are used:
  - CLOB API (clob.polymarket.com)  — authenticated order execution
  - Gamma API (gamma-api.polymarket.com) — unauthenticated market data

Authentication for CLOB:
  L1: Ethereum private key on Polygon (chain 137)
  L2: HMAC-SHA256 derived API key/secret/passphrase
  Run backend/scripts/setup_polymarket.py once to generate L2 credentials.
"""

import logging
import math
import time
from typing import Any

import httpx
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

CLOB_HOST = "https://clob.polymarket.com"
GAMMA_HOST = "https://gamma-api.polymarket.com"

_client: ClobClient | None = None
_http = httpx.Client(timeout=15, headers={"User-Agent": "comrade-agent/1.0"})


# ------------------------------------------------------------------ #
# CLOB client (authenticated)                                         #
# ------------------------------------------------------------------ #

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
            host=CLOB_HOST,
            chain_id=POLYGON,
            key=cfg.polymarket_private_key,
            creds=creds,
            signature_type=0,
            funder=cfg.polymarket_funder_address or None,
        )
    return _client


# ------------------------------------------------------------------ #
# Market discovery — Gamma API (no auth required)                     #
# ------------------------------------------------------------------ #

def get_top_markets(limit: int = 30, sort_by: str = "volume") -> list[dict[str, Any]]:
    """
    Fetch active markets from the Gamma API sorted by volume or liquidity.
    Returns richer data than the CLOB API: categories, tags, 24h volume, price change.
    sort_by: 'volume' | 'liquidity' | 'volume24hr'
    """
    try:
        resp = _http.get(
            f"{GAMMA_HOST}/markets",
            params={
                "limit": limit,
                "order": sort_by,
                "ascending": "false",
                "active": "true",
                "closed": "false",
                "archived": "false",
            },
        )
        resp.raise_for_status()
        markets = resp.json()
        if isinstance(markets, dict):
            markets = markets.get("data", markets.get("markets", []))

        result = []
        for m in markets:
            tokens = m.get("tokens") or m.get("clobTokenIds") or []
            # Gamma returns token IDs as a list or as clob_token_ids
            yes_token_id = None
            no_token_id = None
            if isinstance(tokens, list) and len(tokens) >= 2:
                yes_token_id = tokens[0] if isinstance(tokens[0], str) else None
                no_token_id = tokens[1] if isinstance(tokens[1], str) else None

            # Price from bestAsk / outcomePrices
            outcome_prices = m.get("outcomePrices") or []
            yes_price = None
            if outcome_prices and len(outcome_prices) >= 1:
                try:
                    yes_price = float(outcome_prices[0])
                except (ValueError, TypeError):
                    pass

            result.append({
                "condition_id": m.get("conditionId") or m.get("condition_id"),
                "question": m.get("question"),
                "description": m.get("description", "")[:300],
                "category": m.get("category") or m.get("groupItemTitle", ""),
                "tags": [t.get("label", t) if isinstance(t, dict) else t
                         for t in (m.get("tags") or [])[:5]],
                "end_date": m.get("endDate") or m.get("end_date_iso"),
                "yes_price": yes_price,
                "yes_token_id": yes_token_id or m.get("clobTokenIds", [None])[0],
                "no_token_id": no_token_id,
                "volume": m.get("volume"),
                "volume24hr": m.get("volume24hr"),
                "liquidity": m.get("liquidity"),
                "spread": m.get("spread"),
                "active": m.get("active", True),
            })
        return result
    except Exception as e:
        logger.error("get_top_markets failed: %s", e)
        return [{"error": str(e)}]


def get_markets(limit: int = 20, keyword: str = "") -> list[dict[str, Any]]:
    """Return active prediction markets from CLOB API, optionally filtered by keyword."""
    client = _get_client()
    try:
        resp = client.get_markets()
        markets = resp.get("data", []) if isinstance(resp, dict) else []
        if keyword:
            kl = keyword.lower()
            markets = [
                m for m in markets
                if kl in m.get("question", "").lower()
                or kl in m.get("description", "").lower()
            ]
        result = []
        for m in markets[:limit]:
            tokens = m.get("tokens", [])
            yes_price = yes_token_id = no_token_id = None
            for t in tokens:
                if t.get("outcome", "").upper() == "YES":
                    yes_price = t.get("price")
                    yes_token_id = t.get("token_id")
                elif t.get("outcome", "").upper() == "NO":
                    no_token_id = t.get("token_id")
            result.append({
                "condition_id": m.get("condition_id"),
                "question": m.get("question"),
                "description": m.get("description", "")[:200],
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


def get_market_price_history(
    condition_id: str,
    interval: str = "1d",
) -> dict[str, Any]:
    """
    Get historical price data for a market token to analyse trend direction.

    interval: '1d' | '1w' | '1m' | 'all'
    Returns list of {t: timestamp, p: price} data points.
    This reveals whether the market is trending up, down, or stable.
    """
    try:
        resp = _http.get(
            f"{CLOB_HOST}/prices-history",
            params={"market": condition_id, "interval": interval, "fidelity": 60},
        )
        resp.raise_for_status()
        data = resp.json()
        history = data.get("history", [])

        if not history:
            return {"condition_id": condition_id, "history": [], "trend": "unknown"}

        prices = [float(h["p"]) for h in history if "p" in h]
        if len(prices) < 2:
            return {"condition_id": condition_id, "history": history, "trend": "insufficient_data"}

        first_price = prices[0]
        last_price = prices[-1]
        price_change = last_price - first_price
        pct_change = price_change / first_price if first_price else 0

        # Simple trend: last 5 vs first 5 data points
        recent = prices[-min(5, len(prices)):]
        early = prices[:min(5, len(prices))]
        trend = "rising" if sum(recent) / len(recent) > sum(early) / len(early) else "falling"

        return {
            "condition_id": condition_id,
            "interval": interval,
            "start_price": round(first_price, 4),
            "end_price": round(last_price, 4),
            "price_change": round(price_change, 4),
            "pct_change": round(pct_change * 100, 2),
            "trend": trend,
            "data_points": len(history),
            "history": history[-20:],  # last 20 points
        }
    except Exception as e:
        logger.error("get_market_price_history failed: %s", e)
        return {"error": str(e)}


def get_market_trades(condition_id: str, limit: int = 20) -> dict[str, Any]:
    """
    Get recent confirmed trades for a market.
    Useful for gauging momentum: who is buying/selling and at what price.

    Tries the authenticated CLOB client first (more reliable), then falls
    back to a direct HTTP request to the CLOB trades endpoint.
    """
    raw_trades: list[dict] = []

    # Attempt 1: use authenticated py-clob-client
    try:
        client = _get_client()
        from py_clob_client.clob_types import TradeParams
        resp = client.get_trades(TradeParams(market=condition_id, limit=limit))
        if isinstance(resp, dict):
            raw_trades = resp.get("data", [])
        elif isinstance(resp, list):
            raw_trades = resp
    except Exception as e1:
        logger.debug("CLOB client get_trades failed (%s), trying HTTP fallback", e1)
        # Attempt 2: direct HTTP — Polymarket CLOB /trades endpoint
        try:
            resp = _http.get(
                f"{CLOB_HOST}/trades",
                params={"market": condition_id, "limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()
            raw_trades = data if isinstance(data, list) else data.get("data", [])
        except Exception as e2:
            logger.error("get_market_trades HTTP fallback failed: %s", e2)
            return {"error": str(e2), "trades": [], "flow_bias": "unknown"}

    result = []
    for t in raw_trades[:limit]:
        # Field names vary: handle both CLOB and Gamma response shapes
        size = (
            t.get("size")
            or t.get("takerAmount")
            or t.get("makerAmount")
            or 0
        )
        side = t.get("side") or t.get("takerSide") or ""
        result.append({
            "trade_id": t.get("id") or t.get("tradeId"),
            "side": side.upper() if side else "UNKNOWN",
            "price": t.get("price"),
            "size": size,
            "outcome": t.get("outcome"),
            "timestamp": t.get("timestamp") or t.get("createdAt") or t.get("created_at"),
        })

    buys = [t for t in result if t["side"] == "BUY"]
    sells = [t for t in result if t["side"] == "SELL"]
    buy_vol = sum(float(t["size"] or 0) for t in buys)
    sell_vol = sum(float(t["size"] or 0) for t in sells)
    pressure = (
        "buy_pressure" if buy_vol > sell_vol
        else "sell_pressure" if sell_vol > buy_vol
        else "neutral"
    )
    return {
        "trades": result,
        "buy_volume": round(buy_vol, 2),
        "sell_volume": round(sell_vol, 2),
        "flow_bias": pressure,
    }


# ------------------------------------------------------------------ #
# Order book                                                          #
# ------------------------------------------------------------------ #

def get_orderbook(token_id: str) -> dict[str, Any]:
    """Return current orderbook with spread, best bid/ask, and total liquidity."""
    client = _get_client()
    try:
        book = client.get_order_book(token_id)
        bids = [{"price": float(b.price), "size": float(b.size)} for b in (book.bids or [])]
        asks = [{"price": float(a.price), "size": float(a.size)} for a in (book.asks or [])]

        best_bid = max((b["price"] for b in bids), default=None)
        best_ask = min((a["price"] for a in asks), default=None)
        spread = round(best_ask - best_bid, 4) if best_bid and best_ask else None
        mid = round((best_bid + best_ask) / 2, 4) if best_bid and best_ask else None

        bid_liquidity = sum(b["price"] * b["size"] for b in bids)
        ask_liquidity = sum(a["price"] * a["size"] for a in asks)

        return {
            "token_id": token_id,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": spread,
            "mid_price": mid,
            "bid_liquidity_usdc": round(bid_liquidity, 2),
            "ask_liquidity_usdc": round(ask_liquidity, 2),
            "bids": bids[:10],
            "asks": asks[:10],
        }
    except Exception as e:
        logger.error("get_orderbook failed: %s", e)
        return {"error": str(e)}


# ------------------------------------------------------------------ #
# Position & balance                                                  #
# ------------------------------------------------------------------ #

def get_positions() -> list[dict[str, Any]]:
    """Return all open positions with PnL."""
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
    """Return USDC balance available for trading."""
    client = _get_client()
    try:
        from py_clob_client.clob_types import BalanceAllowanceParams, AssetType
        params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        balance = client.get_balance_allowance(params=params)
        raw = balance.get("balance") or balance.get("asset", {}).get("balance", 0)
        return {
            "usdc_balance": float(raw) if raw else 0.0,
            "allowance": balance.get("allowance", 0),
        }
    except Exception as e:
        logger.error("get_balance failed: %s", e)
        return {"error": str(e)}


# ------------------------------------------------------------------ #
# Order execution                                                     #
# ------------------------------------------------------------------ #

def place_order(
    token_id: str,
    side: str,
    size_usdc: float,
    price: float,
) -> dict[str, Any]:
    """
    Place a GTC limit order on Polymarket.

    token_id : YES or NO token ID
    side     : 'BUY' or 'SELL'
    size_usdc: dollar amount in USDC
    price    : limit price 0.01–0.99 (implied probability)
    """
    client = _get_client()
    try:
        order_side = BUY if side.upper() == "BUY" else SELL
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
    """Cancel an open order by ID."""
    client = _get_client()
    try:
        resp = client.cancel(order_id)
        return {"success": True, "order_id": order_id, "response": resp}
    except Exception as e:
        logger.error("cancel_order failed: %s", e)
        return {"success": False, "error": str(e)}


# ------------------------------------------------------------------ #
# Helpers (used internally by the agent layer)                        #
# ------------------------------------------------------------------ #

def kelly_fraction(estimated_prob: float, market_price: float) -> float:
    """
    Full Kelly criterion for binary prediction markets (YES bet).

    f* = (p - q) / (1 - q)

    where p = your estimated probability of YES
          q = market price (implied probability)

    Returns a fraction of bankroll. Use half-Kelly in practice.
    Negative = no edge, do not bet.
    """
    if market_price <= 0 or market_price >= 1:
        return 0.0
    f = (estimated_prob - market_price) / (1.0 - market_price)
    return round(f, 4)


def expected_value_pct(estimated_prob: float, market_price: float) -> float:
    """
    Expected value of a YES bet as a percentage of stake.

    EV% = (p / q) - 1

    Positive = profitable edge, negative = expected loss.
    """
    if market_price <= 0:
        return -1.0
    return round((estimated_prob / market_price) - 1.0, 4)
