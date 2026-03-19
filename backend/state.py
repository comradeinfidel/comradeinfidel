"""
Shared in-memory state for the trading agent, with disk persistence.

PnL is synced from Polymarket positions at the end of each cycle so the
chart reflects real numbers rather than always showing $0.

Persistence: state is saved to data/state.json on every write and loaded
at startup, so history survives restarts.
"""

import asyncio
import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).parent.parent / "data" / "state.json"


class AgentState:
    def __init__(self) -> None:
        self.running: bool = False
        self.last_run: datetime | None = None
        self.next_run: datetime | None = None

        # SSE subscribers
        self._subscribers: list[asyncio.Queue[dict]] = []

        # Ring buffer for late-joining SSE clients
        self._log_buffer: list[dict] = []
        self._log_buffer_max = 200

        # PnL — keyed by ISO date string "YYYY-MM-DD"
        self.daily_pnl: dict[str, float] = {}
        self.total_realized_pnl: float = 0.0

        # Last-seen realized PnL per token_id, used to detect new
        # realizations without double-counting across cycles.
        self._last_realized: dict[str, float] = {}

        # Orders placed in the current agent cycle
        self.cycle_order_count: int = 0

        self._load()

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def _load(self) -> None:
        """Load persisted state from disk (silently skip if missing)."""
        try:
            if STATE_FILE.exists():
                raw = json.loads(STATE_FILE.read_text())
                self.daily_pnl = raw.get("daily_pnl", {})
                self.total_realized_pnl = raw.get("total_realized_pnl", 0.0)
                self._last_realized = raw.get("last_realized", {})
                logger.info("State loaded from %s", STATE_FILE)
        except Exception as e:
            logger.warning("Could not load state file: %s", e)

    def _save(self) -> None:
        """Persist current state to disk."""
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            STATE_FILE.write_text(json.dumps({
                "daily_pnl": self.daily_pnl,
                "total_realized_pnl": self.total_realized_pnl,
                "last_realized": self._last_realized,
                "saved_at": datetime.utcnow().isoformat() + "Z",
            }, indent=2))
        except Exception as e:
            logger.warning("Could not save state file: %s", e)

    # ------------------------------------------------------------------ #
    # SSE pub/sub                                                          #
    # ------------------------------------------------------------------ #

    def subscribe(self) -> asyncio.Queue[dict]:
        q: asyncio.Queue[dict] = asyncio.Queue(maxsize=500)
        # Replay recent history to the new subscriber
        for entry in self._log_buffer:
            q.put_nowait(entry)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict]) -> None:
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    def emit(self, event_type: str, message: str, data: dict | None = None) -> None:
        """Broadcast an event to all SSE subscribers."""
        entry = {
            "type": event_type,
            "message": message,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        self._log_buffer.append(entry)
        if len(self._log_buffer) > self._log_buffer_max:
            self._log_buffer.pop(0)
        for q in list(self._subscribers):
            try:
                q.put_nowait(entry)
            except asyncio.QueueFull:
                pass

    # ------------------------------------------------------------------ #
    # PnL tracking                                                         #
    # ------------------------------------------------------------------ #

    def record_pnl(self, amount: float) -> None:
        """Record realized PnL directly (positive = profit, negative = loss)."""
        today = date.today().isoformat()
        self.daily_pnl[today] = self.daily_pnl.get(today, 0.0) + amount
        self.total_realized_pnl += amount
        self._save()

    def sync_pnl_from_positions(self, positions: list[dict]) -> None:
        """
        Sync realized PnL by diffing latest position data against last snapshot.
        Called at the end of every agent cycle.

        Polymarket returns realized_pnl per position as a cumulative total.
        We track deltas to avoid double-counting across cycles.
        """
        total_delta = 0.0
        for p in positions:
            if "error" in p:
                continue
            token_id = p.get("token_id") or p.get("condition_id", "")
            if not token_id:
                continue
            current_realized = float(p.get("realized_pnl") or 0)
            last_seen = self._last_realized.get(token_id, 0.0)
            delta = current_realized - last_seen
            if delta != 0:
                self._last_realized[token_id] = current_realized
                total_delta += delta

        if total_delta != 0:
            today = date.today().isoformat()
            self.daily_pnl[today] = self.daily_pnl.get(today, 0.0) + total_delta
            self.total_realized_pnl += total_delta
            self.emit(
                "info",
                f"PnL synced: ${total_delta:+.2f} realized "
                f"(all-time total: ${self.total_realized_pnl:.2f})",
            )
            self._save()

    def today_pnl(self) -> float:
        return self.daily_pnl.get(date.today().isoformat(), 0.0)

    def pnl_history(self) -> list[dict[str, Any]]:
        return [{"date": d, "pnl": v} for d, v in sorted(self.daily_pnl.items())]

    # ------------------------------------------------------------------ #
    # Cycle management                                                     #
    # ------------------------------------------------------------------ #

    def start_cycle(self) -> None:
        self.cycle_order_count = 0
        self.last_run = datetime.utcnow()

    def increment_order_count(self) -> None:
        self.cycle_order_count += 1


# Singleton
agent_state = AgentState()
