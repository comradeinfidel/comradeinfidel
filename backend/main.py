"""
FastAPI application — routes and SSE endpoint.
"""

import asyncio
import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.config import get_settings
from backend.state import agent_state
from backend import agent as agent_module
from backend.tools import polymarket as pm

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Comrade Agent", version="1.0.0")

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# Serve static assets (JS, CSS)
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ------------------------------------------------------------------ #
# Frontend                                                            #
# ------------------------------------------------------------------ #

@app.get("/", response_class=HTMLResponse)
async def root():
    index = FRONTEND_DIR / "index.html"
    return FileResponse(str(index))


# ------------------------------------------------------------------ #
# Agent control                                                       #
# ------------------------------------------------------------------ #

_agent_task: asyncio.Task | None = None


@app.get("/api/status")
async def get_status():
    cfg = get_settings()
    return {
        "running": agent_state.running,
        "last_run": agent_state.last_run.isoformat() + "Z" if agent_state.last_run else None,
        "next_run": agent_state.next_run.isoformat() + "Z" if agent_state.next_run else None,
        "interval_minutes": cfg.agent_interval_minutes,
        "today_pnl": agent_state.today_pnl(),
        "total_realized_pnl": agent_state.total_realized_pnl,
        "cycle_order_count": agent_state.cycle_order_count,
    }


@app.post("/api/agent/start")
async def start_agent():
    global _agent_task
    if agent_state.running:
        raise HTTPException(status_code=400, detail="Agent is already running")
    cfg = get_settings()
    if not cfg.anthropic_api_key:
        raise HTTPException(status_code=400, detail="ANTHROPIC_API_KEY is not configured")
    if not cfg.polymarket_private_key:
        raise HTTPException(status_code=400, detail="POLYMARKET_PRIVATE_KEY is not configured")

    agent_state.running = True
    agent_state.emit("info", "Agent started by user")
    _agent_task = asyncio.create_task(agent_module.agent_scheduler())
    return {"started": True}


@app.post("/api/agent/stop")
async def stop_agent():
    global _agent_task
    if not agent_state.running:
        raise HTTPException(status_code=400, detail="Agent is not running")
    agent_state.running = False
    agent_state.emit("info", "Agent stopped by user")
    if _agent_task and not _agent_task.done():
        _agent_task.cancel()
    _agent_task = None
    return {"stopped": True}


# ------------------------------------------------------------------ #
# SSE stream                                                          #
# ------------------------------------------------------------------ #

@app.get("/api/agent/stream")
async def agent_stream(request):
    """Server-Sent Events stream of agent reasoning and trade events."""
    q = agent_state.subscribe()

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    entry = await asyncio.wait_for(q.get(), timeout=30)
                    yield {"data": json.dumps(entry)}
                except asyncio.TimeoutError:
                    # Keep-alive ping
                    yield {"data": json.dumps({"type": "ping"})}
        finally:
            agent_state.unsubscribe(q)

    return EventSourceResponse(event_generator())


# ------------------------------------------------------------------ #
# Data endpoints                                                      #
# ------------------------------------------------------------------ #

@app.get("/api/positions")
async def get_positions():
    try:
        positions = await asyncio.to_thread(pm.get_positions)
        return {"positions": positions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/balance")
async def get_balance():
    try:
        balance = await asyncio.to_thread(pm.get_balance)
        return balance
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pnl")
async def get_pnl():
    return {
        "today_pnl": agent_state.today_pnl(),
        "total_realized_pnl": agent_state.total_realized_pnl,
        "daily_history": agent_state.pnl_history(),
    }


# ------------------------------------------------------------------ #
# Config / guardrails                                                 #
# ------------------------------------------------------------------ #

class GuardrailUpdate(BaseModel):
    max_position_size_usd: float | None = None
    daily_loss_limit_usd: float | None = None
    max_open_positions: int | None = None
    max_orders_per_cycle: int | None = None
    agent_interval_minutes: int | None = None


@app.get("/api/config")
async def get_config():
    cfg = get_settings()
    return {
        "max_position_size_usd": cfg.max_position_size_usd,
        "daily_loss_limit_usd": cfg.daily_loss_limit_usd,
        "max_open_positions": cfg.max_open_positions,
        "max_orders_per_cycle": cfg.max_orders_per_cycle,
        "agent_interval_minutes": cfg.agent_interval_minutes,
    }


@app.post("/api/config")
async def update_config(update: GuardrailUpdate):
    """Update guardrail values at runtime (resets the settings cache)."""
    import os
    from backend.config import get_settings as _gs
    mapping = {
        "max_position_size_usd": "MAX_POSITION_SIZE_USD",
        "daily_loss_limit_usd": "DAILY_LOSS_LIMIT_USD",
        "max_open_positions": "MAX_OPEN_POSITIONS",
        "max_orders_per_cycle": "MAX_ORDERS_PER_CYCLE",
        "agent_interval_minutes": "AGENT_INTERVAL_MINUTES",
    }
    for field, env_key in mapping.items():
        val = getattr(update, field)
        if val is not None:
            os.environ[env_key] = str(val)

    # Clear the lru_cache so next call picks up new values
    _gs.cache_clear()
    agent_state.emit("info", f"Config updated: {update.model_dump(exclude_none=True)}")
    return {"updated": True, "config": (await get_config())}
