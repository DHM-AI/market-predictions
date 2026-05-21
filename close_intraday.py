"""
Intraday Position Closer — runs at 3:50 PM ET via GitHub Actions.

Simple rule: any position opened TODAY gets closed before market close.
Positions opened on previous days (SWING) are held overnight untouched.

This keeps things clean — intraday trades don't carry overnight risk.
"""
from datetime import datetime, timezone, timedelta
from execution.alpaca import get_positions, close_position, _get_client, is_configured


def _get_todays_entries() -> set[str]:
    """Return set of tickers where a BUY order was filled today."""
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


def run() -> list[dict]:
    if not is_configured():
        print("[close_intraday] Alpaca not configured — skipping.")
        return []

    positions      = get_positions()
    todays_entries = _get_todays_entries()

    if not positions:
        print("[close_intraday] No open positions.")
        return []

    intraday = [p for p in positions if p["ticker"] in todays_entries]
    swing    = [p for p in positions if p["ticker"] not in todays_entries]

    print(f"[close_intraday] {len(positions)} open positions:")
    print(f"  INTRADAY (opened today)     : {len(intraday)} → closing now")
    print(f"  SWING    (opened prev days) : {len(swing)} → holding overnight")

    results = []
    for p in intraday:
        ticker = p["ticker"]
        pl     = p.get("unrealized_pl", 0)
        pl_pct = p.get("unrealized_pl_pct", 0)
        print(f"  Closing {ticker:6s}  P&L: ${pl:+.2f} ({pl_pct:+.1f}%)")
        result = close_position(ticker)
        results.append({
            "ticker": ticker,
            "pl":     round(pl, 2),
            "pl_pct": round(pl_pct, 2),
            "status": result.get("status"),
        })

    if results:
        wins   = [r for r in results if r["pl"] >= 0]
        losses = [r for r in results if r["pl"] < 0]
        net    = sum(r["pl"] for r in results)

        lines = "\n".join(
            f">{'✅' if r['pl'] >= 0 else '🔴'} *{r['ticker']}*  "
            f"{'+'if r['pl'] >= 0 else ''}{r['pl']:.2f} ({r['pl_pct']:+.1f}%)"
            for r in results
        )

        try:
            from alerts.slack import _post
            _post({"text": (
                f"🔔 *Intraday Close — 3:50 PM ET*\n"
                f"Closed *{len(results)}* intraday position(s)\n"
                f"{lines}\n"
                f">Net: *{'+'if net>=0 else ''}{net:.2f}*  ·  "
                f"{len(wins)} wins  ·  {len(losses)} losses\n"
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
