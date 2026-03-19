"""
Safety guardrails checked before every order placement.

All checks return (allowed: bool, reason: str).
"""

from backend.config import get_settings
from backend.state import agent_state


def check_order(size_usdc: float, open_position_count: int) -> tuple[bool, str]:
    """
    Run all guardrail checks before placing an order.

    Returns (True, "") if allowed, or (False, reason) if blocked.
    """
    cfg = get_settings()

    # 1. Max position size
    if size_usdc > cfg.max_position_size_usd:
        return False, (
            f"Order size ${size_usdc:.2f} exceeds MAX_POSITION_SIZE_USD "
            f"${cfg.max_position_size_usd:.2f}"
        )

    # 2. Daily loss limit
    today_pnl = agent_state.today_pnl()
    if today_pnl < -cfg.daily_loss_limit_usd:
        return False, (
            f"Daily loss limit reached: today's PnL is ${today_pnl:.2f} "
            f"(limit: -${cfg.daily_loss_limit_usd:.2f}). Trading halted for today."
        )

    # 3. Max open positions
    if open_position_count >= cfg.max_open_positions:
        return False, (
            f"Max open positions reached: {open_position_count} "
            f"(limit: {cfg.max_open_positions})"
        )

    # 4. Max orders per cycle
    if agent_state.cycle_order_count >= cfg.max_orders_per_cycle:
        return False, (
            f"Max orders per cycle reached: {agent_state.cycle_order_count} "
            f"(limit: {cfg.max_orders_per_cycle})"
        )

    return True, ""
