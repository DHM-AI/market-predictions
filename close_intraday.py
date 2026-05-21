"""
Intraday Position Closer — runs at 3:50 PM ET via GitHub Actions.

Rule:
  - Positions with SHORT duration ("1d", "1-3d earnings") → close at 3:50 PM
  - Positions with SWING duration ("5-7d", "2-3w") → hold overnight
    even if they were opened today

This means a swing trade entered this morning is NOT closed EOD —
it stays open until its SL, TP, or trailing stop is hit.
"""
from datetime import datetime, timezone
from execution.alpaca import get_positions, close_position, _get_client, is_configured


def _get_todays_entries() -> set[str]:
    """Return tickers where a BUY order was filled today."""
    try:
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus
        today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z")
        orders    = _get_client().get_orders(GetOrdersRequest(
            status=QueryOrderStatus.ALL, after=today_utc, limit=200))
        return {
            o.symbol for o in orders
            if "buy" in str(getattr(o, "side", "")).lower()
            and str(getattr(o, "status", "")) in ("filled", "partially_filled")
        }
    except Exception as e:
        print(f"[close_intraday] Could not fetch today's orders: {e}")
        return set()


# Duration strings that mean SHORT-TERM → close EOD
_SHORT_DURATIONS = ("1d", "intraday", "same-day", "1-3d")

# Duration strings that mean SWING → hold overnight
_SWING_DURATIONS = ("5-7d", "2-3w", "1w", "week", "swing")


def _is_short_term(duration: str) -> bool:
    d = duration.lower()
    return any(k in d for k in _SHORT_DURATIONS)


def _get_duration_map(tickers: set[str]) -> dict[str, str]:
    """Pull today's predicted duration for each ticker from Supabase."""
    try:
        import db
        if db.db_available():
            from datetime import date
            rows = db.load_predictions_for_date(date.today().isoformat())
            return {r["ticker"]: str(r.get("duration", "")) for r in rows
                    if r.get("ticker") in tickers}
    except Exception as e:
        print(f"[close_intraday] DB lookup failed: {e}")
    return {}


def run() -> list[dict]:
    if not is_configured():
        print("[close_intraday] Alpaca not configured — skipping.")
        return []

    positions      = get_positions()
    todays_entries = _get_todays_entries()

    if not positions:
        print("[close_intraday] No open positions.")
        return []

    opened_today  = {p["ticker"] for p in positions if p["ticker"] in todays_entries}
    duration_map  = _get_duration_map(opened_today)

    to_close = []
    to_hold  = []

    for p in positions:
        ticker   = p["ticker"]
        duration = duration_map.get(ticker, "")

        if ticker not in todays_entries:
            # Opened on a previous day — always hold
            to_hold.append((p, "swing (prev day)"))
        elif _is_short_term(duration):
            to_close.append(p)
        else:
            # Opened today but swing duration — hold overnight
            to_hold.append((p, f"swing today ({duration or 'no duration'})"))

    print(f"[close_intraday] {len(positions)} positions:")
    print(f"  Closing  : {len(to_close)}")
    print(f"  Holding  : {len(to_hold)}")
    for p, reason in to_hold:
        print(f"    → Hold {p['ticker']:6s}  ({reason})")

    results = []
    for p in to_close:
        ticker = p["ticker"]
        pl     = p.get("unrealized_pl", 0)
        pl_pct = p.get("unrealized_pl_pct", 0)
        dur    = duration_map.get(ticker, "")
        print(f"  Closing {ticker:6s}  {dur}  P&L: ${pl:+.2f} ({pl_pct:+.1f}%)")
        result = close_position(ticker)
        results.append({
            "ticker":   ticker,
            "duration": dur,
            "pl":       round(pl, 2),
            "pl_pct":   round(pl_pct, 2),
            "status":   result.get("status"),
        })

    if results:
        wins  = [r for r in results if r["pl"] >= 0]
        losses= [r for r in results if r["pl"] < 0]
        net   = sum(r["pl"] for r in results)
        lines = "\n".join(
            f">{'✅' if r['pl'] >= 0 else '🔴'} *{r['ticker']}*  "
            f"{'+'if r['pl']>=0 else ''}{r['pl']:.2f} ({r['pl_pct']:+.1f}%)  {r['duration']}"
            for r in results
        )
        try:
            from alerts.slack import _post
            _post({"text": (
                f"🔔 *Intraday Close — 3:50 PM ET*\n"
                f"Closed *{len(results)}* short-term position(s)\n"
                f"{lines}\n"
                f">Net: *{'+'if net>=0 else ''}{net:.2f}*  ·  "
                f"{len(wins)} wins  ·  {len(losses)} losses\n"
                f">{len(to_hold)} swing trade(s) held overnight"
            )})
        except Exception:
            pass

    elif opened_today:
        print("[close_intraday] All positions opened today are swing trades — holding overnight.")

    return results


if __name__ == "__main__":
    print(f"Intraday Closer — {datetime.now().strftime('%Y-%m-%d %H:%M ET')}")
    print("=" * 50)
    results = run()
    print("=" * 50)
    print(f"Closed {len(results)} position(s)." if results else "Nothing closed.")
