"""
CLEANUP — cancel stale pending limit orders before market open.

Limit orders submitted with TimeInForce.DAY after market close don't expire —
they queue for the NEXT trading session's open. If the signal that produced
the order is hours old, the market may have moved enough that the trade no
longer makes sense.

This script cancels any LIMIT order older than STALE_HOURS (default 8h).
Stop / trailing-stop / bracket-child orders are NEVER touched — they're
protective and should persist.

Scheduled via .github/workflows/cleanup_stale_orders.yml to run at 9:25 AM ET
weekdays, 5 minutes before the open.

Run manually anytime:
    python -m cleanup_stale_orders
"""
import os
import sys
from datetime import datetime, timezone


STALE_HOURS = float(os.getenv("CLEANUP_STALE_HOURS", "8"))


def cleanup_stale_orders(stale_hours: float = STALE_HOURS,
                         notify_slack: bool = True) -> list[dict]:
    """
    Cancel any LIMIT pending order older than stale_hours.
    Returns list of cancelled order details.
    """
    try:
        from execution.alpaca import _get_client, is_configured
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus
    except Exception as e:
        print(f"[CLEANUP] Could not import alpaca: {e}")
        return []

    if not is_configured():
        print("[CLEANUP] Alpaca not configured — skipping.")
        return []

    client = _get_client()
    orders = client.get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN, limit=200))
    now = datetime.now(timezone.utc)

    cancelled = []
    for o in orders:
        otype = str(getattr(o, "type", "")).lower()
        # Only target LIMIT entry orders. Never cancel stops, trailing stops,
        # or bracket children (protective orders).
        if "limit" not in otype or "stop" in otype:
            continue
        # Skip bracket children (have parent_order_id) — those are TP legs
        # of an active bracket and shouldn't be killed independently
        if getattr(o, "parent_order_id", None):
            continue
        if not getattr(o, "created_at", None):
            continue
        age_hrs = (now - o.created_at).total_seconds() / 3600
        if age_hrs < stale_hours:
            continue
        try:
            client.cancel_order_by_id(str(o.id))
            cancelled.append({
                "symbol":  o.symbol,
                "side":    str(o.side),
                "qty":     float(o.qty),
                "limit":   float(o.limit_price) if o.limit_price else None,
                "age_hrs": round(age_hrs, 1),
            })
            print(f"[CLEANUP] ✕ {o.symbol:6s} {o.side} qty={o.qty} "
                  f"@ ${float(o.limit_price):.2f} (age {age_hrs:.1f}h)")
        except Exception as e:
            print(f"[CLEANUP] Failed to cancel {o.symbol}: {e}")

    # Slack summary
    if notify_slack and cancelled:
        try:
            from alerts.slack import _post
            lines = [
                f"• `{c['symbol']:6s}` {c['side']} {c['qty']:g} @ ${c['limit']:.2f}  ({c['age_hrs']}h old)"
                for c in cancelled
            ]
            _post({
                "attachments": [{
                    "color":   "warning",
                    "pretext": f"*🧹 Stale orders cancelled before open*",
                    "text":    f"_Older than {stale_hours}h — signals decayed, won't fire at next open._\n"
                               + "\n".join(lines),
                    "mrkdwn_in": ["pretext", "text"],
                    "footer":  f"Illuminati · CLEANUP",
                    "ts":      int(datetime.now().timestamp()),
                }]
            })
        except Exception as e:
            print(f"[CLEANUP] Slack notify failed: {e}")
    elif notify_slack:
        print("[CLEANUP] No stale orders to cancel.")

    return cancelled


if __name__ == "__main__":
    print(f"[CLEANUP] Scanning for limit orders older than {STALE_HOURS}h...")
    result = cleanup_stale_orders()
    print(f"[CLEANUP] Done — {len(result)} order(s) cancelled.")
    sys.exit(0)
