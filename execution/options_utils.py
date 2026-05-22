from __future__ import annotations
"""
Options utilities — symbol building, strike selection, expiry finding.
Used by APEX when placing iron butterfly orders on earnings plays.
"""
from datetime import datetime, timedelta
import math


def get_atm_strike(price: float, increment: float | None = None) -> float:
    """Round price to nearest standard strike increment."""
    if increment is None:
        if price >= 500:   increment = 5.0
        elif price >= 100: increment = 2.5
        elif price >= 25:  increment = 1.0
        else:              increment = 0.5
    return round(round(price / increment) * increment, 2)


def build_option_symbol(ticker: str, expiry_yymmdd: str,
                        call_or_put: str, strike: float) -> str:
    """
    Build OCC option symbol.
    Example: SPY 2025-05-30 Call $600 → SPY250530C00600000
    """
    cp     = "C" if call_or_put.upper().startswith("C") else "P"
    strike_int = int(round(strike * 1000))
    return f"{ticker.upper()}{expiry_yymmdd}{cp}{strike_int:08d}"


def get_next_expiry(target_date: datetime | None = None,
                    prefer_weekly: bool = True) -> str:
    """
    Return nearest weekly (Friday) expiry on or after target_date, as YYMMDD.
    Falls back to the next Friday from today if target_date is None.
    """
    base = target_date if target_date else datetime.today()
    # Find next Friday (weekday 4)
    days_ahead = (4 - base.weekday()) % 7
    if days_ahead == 0 and base.hour >= 15:
        days_ahead = 7   # too late today — use next week
    expiry = base + timedelta(days=days_ahead)
    return expiry.strftime("%y%m%d")


def get_wing_increment(price: float, wing_pct: float = 0.05) -> float:
    """Calculate wing width for iron butterfly (default 5% OTM)."""
    raw   = price * wing_pct
    incr  = get_atm_strike(price) - get_atm_strike(price - 0.01)  # step size
    step  = max(incr, 1.0)
    return round(round(raw / step) * step, 2)
