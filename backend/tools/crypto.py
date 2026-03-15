"""Coinbase Advanced Trade crypto tools for the AI assistant."""

import os
import json
import time
import hmac
import hashlib
import httpx
from typing import Optional

COINBASE_API_KEY = os.getenv("COINBASE_API_KEY", "")
COINBASE_API_SECRET = os.getenv("COINBASE_API_SECRET", "")
BASE_URL = "https://api.coinbase.com"


def _get_headers(method: str, path: str, body: str = "") -> dict:
    """Generate Coinbase Advanced Trade API auth headers."""
    timestamp = str(int(time.time()))
    message = timestamp + method.upper() + path + body
    signature = hmac.new(
        COINBASE_API_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return {
        "CB-ACCESS-KEY": COINBASE_API_KEY,
        "CB-ACCESS-SIGN": signature,
        "CB-ACCESS-TIMESTAMP": timestamp,
        "Content-Type": "application/json",
    }


def get_crypto_price(product_id: str) -> dict:
    """Get the current price of a crypto product (e.g., BTC-USD, ETH-USD)."""
    try:
        product_id = product_id.upper()
        path = f"/api/v3/brokerage/products/{product_id}"
        with httpx.Client() as client:
            resp = client.get(
                BASE_URL + path,
                headers=_get_headers("GET", path),
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "success": True,
                "product_id": data.get("product_id"),
                "price": data.get("price"),
                "volume_24h": data.get("volume_24h"),
                "price_percentage_change_24h": data.get("price_percentage_change_24h"),
                "status": data.get("status"),
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_crypto_accounts() -> dict:
    """Get all Coinbase crypto accounts and balances."""
    try:
        path = "/api/v3/brokerage/accounts"
        with httpx.Client() as client:
            resp = client.get(
                BASE_URL + path,
                headers=_get_headers("GET", path),
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            accounts = [
                {
                    "uuid": a.get("uuid"),
                    "name": a.get("name"),
                    "currency": a.get("currency"),
                    "available_balance": a.get("available_balance", {}).get("value"),
                    "hold": a.get("hold", {}).get("value"),
                }
                for a in data.get("accounts", [])
                if float(a.get("available_balance", {}).get("value", 0)) > 0
                or float(a.get("hold", {}).get("value", 0)) > 0
            ]
            return {"success": True, "accounts": accounts}
    except Exception as e:
        return {"success": False, "error": str(e)}


def buy_crypto(product_id: str, quote_size: float) -> dict:
    """Buy crypto using a USD amount (quote size). E.g., buy $100 of BTC."""
    try:
        product_id = product_id.upper()
        path = "/api/v3/brokerage/orders"
        body = json.dumps({
            "client_order_id": f"order_{int(time.time())}",
            "product_id": product_id,
            "side": "BUY",
            "order_configuration": {
                "market_market_ioc": {
                    "quote_size": str(quote_size),
                }
            },
        })
        with httpx.Client() as client:
            resp = client.post(
                BASE_URL + path,
                headers=_get_headers("POST", path, body),
                content=body,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            order = data.get("order", {})
            return {
                "success": data.get("success", False),
                "order_id": order.get("order_id"),
                "product_id": order.get("product_id"),
                "side": order.get("side"),
                "status": order.get("status"),
                "quote_size": quote_size,
                "error": data.get("error_response", {}).get("message") if not data.get("success") else None,
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def sell_crypto(product_id: str, base_size: float) -> dict:
    """Sell crypto by specifying the crypto amount (base size). E.g., sell 0.001 BTC."""
    try:
        product_id = product_id.upper()
        path = "/api/v3/brokerage/orders"
        body = json.dumps({
            "client_order_id": f"order_{int(time.time())}",
            "product_id": product_id,
            "side": "SELL",
            "order_configuration": {
                "market_market_ioc": {
                    "base_size": str(base_size),
                }
            },
        })
        with httpx.Client() as client:
            resp = client.post(
                BASE_URL + path,
                headers=_get_headers("POST", path, body),
                content=body,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            order = data.get("order", {})
            return {
                "success": data.get("success", False),
                "order_id": order.get("order_id"),
                "product_id": order.get("product_id"),
                "side": order.get("side"),
                "status": order.get("status"),
                "base_size": base_size,
                "error": data.get("error_response", {}).get("message") if not data.get("success") else None,
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_crypto_orders(limit: int = 20) -> dict:
    """List recent crypto orders."""
    try:
        path = f"/api/v3/brokerage/orders/historical/batch?limit={limit}"
        with httpx.Client() as client:
            resp = client.get(
                BASE_URL + path,
                headers=_get_headers("GET", path),
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            orders = [
                {
                    "order_id": o.get("order_id"),
                    "product_id": o.get("product_id"),
                    "side": o.get("side"),
                    "status": o.get("status"),
                    "filled_size": o.get("filled_size"),
                    "filled_value": o.get("filled_value"),
                    "created_time": o.get("created_time"),
                }
                for o in data.get("orders", [])
            ]
            return {"success": True, "orders": orders}
    except Exception as e:
        return {"success": False, "error": str(e)}
