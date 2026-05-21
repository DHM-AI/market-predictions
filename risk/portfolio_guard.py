from __future__ import annotations
"""
Portfolio-level risk guard — prevents dangerous concentration before any new order.

Checks (in order):
  1. Max concurrent positions (default 10) — don't overload
  2. Sector concentration — max 35% of portfolio in any one GICS sector
  3. Direction balance — if > 80% of open positions are one-directional,
     warn before adding more of the same
  4. Daily trade count — max 5 new orders per day (avoid churning)

Usage in agent.py:
    from risk.portfolio_guard import check_trade
    ok, reason = check_trade(ticker, dollar_amount, direction, positions)
    if not ok:
        print(f"Blocked: {reason}")
        continue
"""

import yfinance as yf

# ── Config ────────────────────────────────────────────────────────────────────
MAX_OPEN_POSITIONS  = 15     # max concurrent holdings
MAX_SECTOR_PCT      = 0.35   # max 35% portfolio in one sector
MAX_DAILY_TRADES    = 10     # max new auto-executions per day
MAX_DIRECTION_PCT   = 0.80   # warn if >80% of positions same direction

_sector_cache: dict[str, str] = {}  # ticker → sector (cached across calls)
_daily_trade_count: int = 0
_daily_trade_date:  str = ""


def _get_sector(ticker: str) -> str:
    """Return GICS sector string for a ticker, using cache."""
    if ticker in _sector_cache:
        return _sector_cache[ticker]
    try:
        info   = yf.Ticker(ticker).info
        sector = info.get("sector", "Unknown") or "Unknown"
        _sector_cache[ticker] = sector
        return sector
    except Exception:
        _sector_cache[ticker] = "Unknown"
        return "Unknown"


def check_trade(
    ticker:       str,
    dollar_amount: float,
    direction:    str,
    open_positions: list[dict],
    portfolio_value: float | None = None,
) -> tuple[bool, str]:
    """
    Run all portfolio-level checks before placing an order.

    Args:
        ticker:          e.g. "NVDA"
        dollar_amount:   proposed position size in dollars
        direction:       "bullish" | "bearish"
        open_positions:  list of position dicts from alpaca.get_positions()
        portfolio_value: total account value (optional, for % calculations)

    Returns:
        (True, "ok") if trade is allowed
        (False, reason_str) if trade should be blocked
    """
    from datetime import datetime, timezone

    # ── Check 1: Already in this position ─────────────────────────────────────
    tickers_held = [p.get("ticker", "") for p in open_positions]
    if ticker in tickers_held:
        return False, f"Already holding {ticker} — no duplicate positions"

    # ── Check 2: Max concurrent positions ─────────────────────────────────────
    if len(open_positions) >= MAX_OPEN_POSITIONS:
        return False, f"Max {MAX_OPEN_POSITIONS} concurrent positions reached ({len(open_positions)} open)"

    # ── Check 3: Daily trade count — read from Alpaca (persists across runs) ──
    trades_today = 0
    try:
        from execution.alpaca import _get_client, is_configured
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus
        if is_configured():
            today_utc    = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z")
            client       = _get_client()
            orders       = client.get_orders(GetOrdersRequest(
                status=QueryOrderStatus.ALL, after=today_utc, limit=100))
            trades_today = sum(1 for o in orders
                               if "buy" in str(getattr(o, "side", "")).lower()
                               and str(getattr(o, "status", "")) in
                               ("filled", "partially_filled", "new", "accepted", "pending_new"))
    except Exception as e:
        print(f"[guard] Could not fetch daily trade count from Alpaca ({e}) — using in-memory fallback")
        trades_today = _daily_trade_count  # fall back to in-memory counter

    if trades_today >= MAX_DAILY_TRADES:
        return False, f"Daily trade limit reached ({trades_today}/{MAX_DAILY_TRADES} trades placed today)"

    # ── Check 4: Sector concentration ─────────────────────────────────────────
    if open_positions and portfolio_value and portfolio_value > 0:
        new_sector = _get_sector(ticker)

        if new_sector != "Unknown":
            # Calculate current sector exposure
            sector_value = 0.0
            for pos in open_positions:
                pos_ticker = pos.get("ticker", "")
                pos_value  = abs(float(pos.get("market_value", 0)))
                pos_sector = _get_sector(pos_ticker)
                if pos_sector == new_sector:
                    sector_value += pos_value

            # Include the proposed new position
            proposed_sector_pct = (sector_value + dollar_amount) / portfolio_value

            if proposed_sector_pct > MAX_SECTOR_PCT:
                return False, (
                    f"Sector concentration: adding {ticker} ({new_sector}) would put "
                    f"{proposed_sector_pct:.0%} of portfolio in one sector "
                    f"(max {MAX_SECTOR_PCT:.0%})"
                )

    # ── Check 5: Direction balance ─────────────────────────────────────────────
    if len(open_positions) >= 3:
        bull_count = sum(1 for p in open_positions if "long" in str(p.get("side","")).lower() or "buy" in str(p.get("side","")).lower())
        bear_count = sum(1 for p in open_positions if "short" in str(p.get("side","")).lower() or "sell" in str(p.get("side","")).lower())
        total      = len(open_positions)

        new_is_bull = direction == "bullish"
        dominant_pct = max(bull_count, bear_count) / total

        if dominant_pct >= MAX_DIRECTION_PCT:
            dominant_dir = "bullish" if bull_count > bear_count else "bearish"
            if (new_is_bull and dominant_dir == "bullish") or (not new_is_bull and dominant_dir == "bearish"):
                return True, f"WARN: {dominant_pct:.0%} of positions are {dominant_dir} — diversify direction when possible"

    # ── All checks passed ─────────────────────────────────────────────────────
    return True, "ok"


def increment_daily_count():
    """Call this after a trade is successfully placed."""
    global _daily_trade_count, _daily_trade_date
    from datetime import datetime
    today = datetime.today().strftime("%Y-%m-%d")
    if _daily_trade_date != today:
        _daily_trade_count = 0
        _daily_trade_date  = today
    _daily_trade_count += 1


def get_sector_breakdown(positions: list[dict]) -> dict[str, float]:
    """
    Returns {sector: total_market_value} for all open positions.
    Useful for dashboard display.
    """
    breakdown: dict[str, float] = {}
    for pos in positions:
        ticker = pos.get("ticker", "")
        value  = abs(float(pos.get("market_value", 0)))
        sector = _get_sector(ticker)
        breakdown[sector] = breakdown.get(sector, 0.0) + value
    return dict(sorted(breakdown.items(), key=lambda x: x[1], reverse=True))
