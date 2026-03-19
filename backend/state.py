"""
Shared in-memory state for the trading agent.

Holds the agent's running status, event log (streamed via SSE),
daily PnL tracking, and a count of orders placed in the current cycle.
"""

import asyncio
from datetime import date, datetime
from typing import Any


class AgentState:
    def __init__(self) -> None:
        self.running: bool = False
        self.last_run: datetime | None = None
        self.next_run: datetime | None = None

        # SSE subscribers: list of asyncio.Queue
        self._subscribers: list[asyncio.Queue[dict]] = []

        # Ring buffer of recent log entries (for new clients joining mid-session)
        self._log_buffer: list[dict] = []
        self._log_buffer_max = 200

        # Daily PnL: { "2026-03-19": float }
        self.daily_pnl: dict[str, float] = {}
        self.total_realized_pnl: float = 0.0

        # Orders placed in the current agent cycle
        self.cycle_order_count: int = 0

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
        """Record realized PnL (positive = profit, negative = loss)."""
        today = date.today().isoformat()
        self.daily_pnl[today] = self.daily_pnl.get(today, 0.0) + amount
        self.total_realized_pnl += amount

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
