"""
Intraday Position Closer — runs at 3:50 PM ET via GitHub Actions.

Any position that was opened TODAY and hasn't hit its SL or TP by
3:50 PM gets closed at market price before the session ends.

Logic:
  1. Get all open positions
  2. Cross-reference with today's Alpaca buy orders to find which
     positions were opened today (intraday)
  3. Close them at market price
  4. Send a Slack summary

This runs BEFORE the 4 PM scan so the account is clean for after-hours.
"""
import sys
from datetime import datetime, timezone, date

from execution.alpaca import (get_positions, close_position,
                               _get_client, is_configured)


def _get_todays_entries() -> set[str]:
    """Return set of tickers where a BUY order was filled today."""
    try:
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus
        today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z")
        client    = _get_client()
        orders    = client.get_orders(GetOrdersRequest(
            status=QueryOrderStatus.ALL, after=today_utc, limit=200))
        return {
            o.symbol for o in orders
            if "buy" in str(getattr(o, "side", "")).lower()
            and str(getattr(o, "status", "")) in ("filled", "partially_filled")
        }
    except Exception as e:
        print(f"[close_intraday] Could not fetch today's orders: {e}")
        return set()


def _get_intraday_tickers_from_db(tickers: set[str]) -> set[str]:
    """
    Cross-reference predictions DB to find tickers whose duration is
    explicitly 1-day (true intraday). Swing trades opened today are
    NOT included — they should be held overnight.

    Duration strings that mean intraday: "1d", "intraday", "same-day"
    Everything else ("1-3d", "5-7d", "2-3w", etc.) = swing → hold.
    """
    intraday_keywords = ("1d", "intraday", "same-day", "same day")
    try:
        import db
        if db.db_available():
            today_str = date.today().isoformat()
            rows = db.load_predictions_for_date(today_str)
            return {
                r["ticker"] for r in rows
                if r.get("ticker") in tickers
                and any(kw in str(r.get("duration", "")).lower()
                        for kw in intraday_keywords)
            }
    except Exception as e:
        print(f"[close_intraday] DB lookup failed ({e}) — using date-only filter")
    # Fallback: if DB unavailable, return empty set (never close anything blindly)
    return set()


def run() -> list[dict]:
    if not is_configured():
        print("[close_intraday] Alpaca not configured — skipping.")
        return []

    positions      = get_positions()
    todays_entries = _get_todays_entries()

    if not positions:
        print("[close_intraday] No open positions.")
        return []

    # Among positions opened today, only close those explicitly flagged
    # as intraday in the predictions DB.
    # Swing trades opened today are held overnight — do NOT close them.
    opened_today   = {p["ticker"] for p in positions if p["ticker"] in todays_entries}
    intraday_ticks = _get_intraday_tickers_from_db(opened_today)

    intraday = [p for p in positions if p["ticker"] in intraday_ticks]
    swing    = [p for p in positions if p["ticker"] not in intraday_ticks]

    print(f"[close_intraday] {len(positions)} open positions:")
    print(f"  TRUE INTRADAY (1d duration, opened today): {len(intraday)} → will close")
    print(f"  SWING (multi-day OR opened today as swing): {len(swing)} → will hold overnight")

    results = []
    for p in intraday:
        ticker = p["ticker"]
        pl     = p.get("unrealized_pl", 0)
        pl_pct = p.get("unrealized_pl_pct", 0)
        print(f"  Closing {ticker:6s}  P&L: ${pl:+.2f} ({pl_pct:+.1f}%)")
        result = close_position(ticker)
        results.append({
            "ticker":  ticker,
            "pl":      round(pl, 2),
            "pl_pct":  round(pl_pct, 2),
            "status":  result.get("status"),
        })

    if results:
        wins   = [r for r in results if r["pl"] >= 0]
        losses = [r for r in results if r["pl"] < 0]
        net    = sum(r["pl"] for r in results)

        summary_lines = "\n".join(
            f">{'✅' if r['pl'] >= 0 else '🔴'} *{r['ticker']}*  "
            f"{'+'if r['pl']>=0 else ''}{r['pl']:.2f} ({r['pl_pct']:+.1f}%)"
            for r in results
        )

        try:
            from alerts.slack import _post
            _post({"text": (
                f"🔔 *Intraday Close — 3:50 PM ET*\n"
                f"Closed *{len(results)}* intraday position(s) before market close\n"
                f"{summary_lines}\n"
                f">Net: *{'+'if net>=0 else ''}{net:.2f}* · "
                f"{len(wins)} wins · {len(losses)} losses\n"
                f">{len(swing)} swing trade(s) held overnight"
            )})
        except Exception:
            pass

    return results


if __name__ == "__main__":
    print(f"Intraday Closer — {datetime.now().strftime('%Y-%m-%d %H:%M ET')}")
    print("=" * 50)
    results = run()
    print("=" * 50)
    if not results:
        print("No intraday positions to close.")
    else:
        print(f"Closed {len(results)} position(s).")
