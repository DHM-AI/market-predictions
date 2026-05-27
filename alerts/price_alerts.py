from __future__ import annotations
"""
Slack price alerts — "ping me when X hits $Y".

Supabase table contract (add once):

    CREATE TABLE IF NOT EXISTS price_alerts (
      id          BIGSERIAL PRIMARY KEY,
      ticker      TEXT NOT NULL,
      target      NUMERIC NOT NULL,
      direction   TEXT NOT NULL CHECK (direction IN ('above','below')),
      note        TEXT,
      created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      fired       BOOLEAN NOT NULL DEFAULT FALSE,
      fired_at    TIMESTAMPTZ,
      fired_price NUMERIC
    );

Public API:
    create_alert(ticker, target, direction='above', note='')
    list_alerts(active_only=True) -> list[dict]
    cancel_alert(alert_id)
    check_and_fire_alerts() -> int   # number of alerts fired

CLI usage (used by the alert-checker workflow):
    python -m alerts.price_alerts check
    python -m alerts.price_alerts add NVDA 200 above "tactical entry"
    python -m alerts.price_alerts list
    python -m alerts.price_alerts cancel 42
"""
import sys
from datetime import datetime, timezone

import yfinance as yf

from alerts.slack import _post


def _client():
    """Lazy-import Supabase client so the module can be imported without it."""
    from db import _client as supa
    return supa()


# ── CRUD ──────────────────────────────────────────────────────────────────

def create_alert(ticker: str, target: float | None = None,
                 direction: str | None = "above", note: str = "") -> dict:
    """
    Create a new price alert OR a watch-only entry.
    - target=None → watch-only: ticker is added to scan universe but no
      price-cross ping ever fires. direction is ignored.
    - target=float → full price alert with direction=above/below.
    """
    ticker = ticker.upper().strip()
    if target is None:
        row = {"ticker": ticker, "target": None, "direction": None,
               "note": note or "", "fired": False}
        res = _client().table("price_alerts").insert(row).execute()
        inserted = res.data[0] if res.data else row
        print(f"[price-alerts] Created watch-only: {inserted['ticker']}")
        return inserted

    direction = (direction or "above").lower().strip()
    if direction not in ("above", "below"):
        raise ValueError("direction must be 'above' or 'below'")
    row = {
        "ticker":    ticker,
        "target":    float(target),
        "direction": direction,
        "note":      note or "",
        "fired":     False,
    }
    res = _client().table("price_alerts").insert(row).execute()
    inserted = res.data[0] if res.data else row
    print(f"[price-alerts] Created: {inserted['ticker']} {direction} ${target}")
    return inserted


def list_alerts(active_only: bool = True) -> list[dict]:
    """Return all alerts (active=not yet fired, by default)."""
    q = _client().table("price_alerts").select("*").order("id", desc=True)
    if active_only:
        q = q.eq("fired", False)
    res = q.execute()
    return res.data or []


def cancel_alert(alert_id: int) -> bool:
    """Hard-delete an alert by ID."""
    _client().table("price_alerts").delete().eq("id", alert_id).execute()
    print(f"[price-alerts] Cancelled alert {alert_id}")
    return True


# ── Trigger logic ─────────────────────────────────────────────────────────

def _current_price(ticker: str) -> float | None:
    """Fast single-ticker last price via yfinance fast_info."""
    try:
        t = yf.Ticker(ticker)
        # fast_info is much faster than .history; falls back if unavailable
        last = getattr(t.fast_info, "last_price", None)
        if last is None:
            hist = t.history(period="1d", interval="1m")
            last = float(hist["Close"].iloc[-1]) if not hist.empty else None
        return float(last) if last is not None else None
    except Exception as e:
        print(f"[price-alerts] price fetch failed for {ticker}: {e}")
        return None


def _fire_slack(alert: dict, current_price: float) -> bool:
    """Post the alert to Slack."""
    direction = alert["direction"]
    arrow = "📈" if direction == "above" else "📉"
    target = float(alert["target"])
    diff_pct = (current_price - target) / target * 100

    note = alert.get("note") or ""
    note_line = f"\n>_{note}_" if note else ""

    payload = {
        "attachments": [
            {
                "color":     "#00d4ff",
                "pretext":   f"*🔔 Price Alert — {alert['ticker']}*",
                "title":     f"{arrow} {alert['ticker']} crossed ${target:.2f} ({direction.upper()})",
                "title_link": f"https://finance.yahoo.com/quote/{alert['ticker']}",
                "fields": [
                    {"title": "Now",     "value": f"${current_price:.2f}",         "short": True},
                    {"title": "Target",  "value": f"${target:.2f}",                "short": True},
                    {"title": "Diff",    "value": f"{diff_pct:+.2f}%",             "short": True},
                    {"title": "Set on",  "value": str(alert.get("created_at",""))[:10], "short": True},
                ],
                "text":      note_line if note_line else None,
                "mrkdwn_in": ["pretext", "text"],
                "footer":    "Illuminati · Price Alert",
                "ts":        int(datetime.now().timestamp()),
            }
        ]
    }
    # Strip None values Slack rejects
    payload["attachments"][0] = {k: v for k, v in payload["attachments"][0].items() if v is not None}
    return _post(payload)


def _mark_fired(alert_id: int, fired_price: float) -> None:
    _client().table("price_alerts").update({
        "fired":       True,
        "fired_at":    datetime.now(timezone.utc).isoformat(),
        "fired_price": fired_price,
    }).eq("id", alert_id).execute()


def check_and_fire_alerts() -> int:
    """
    Iterate active alerts, fetch current price per unique ticker (once),
    fire Slack for any that triggered, mark fired in DB.
    Returns count of alerts fired.
    """
    active = list_alerts(active_only=True)
    if not active:
        print("[price-alerts] No active alerts.")
        return 0

    # Group by ticker so we only hit yfinance once per unique symbol
    unique_tickers = sorted({a["ticker"] for a in active})
    price_map: dict[str, float] = {}
    for tk in unique_tickers:
        p = _current_price(tk)
        if p is not None:
            price_map[tk] = p

    fired = 0
    for a in active:
        tk = a["ticker"]
        price = price_map.get(tk)
        if price is None:
            continue
        # Watch-only entries: target/direction NULL → in scan universe but
        # never fires a price-cross alert
        if a.get("target") is None or a.get("direction") is None:
            continue
        target = float(a["target"])
        triggered = (
            (a["direction"] == "above" and price >= target)
            or (a["direction"] == "below" and price <= target)
        )
        if triggered:
            ok = _fire_slack(a, price)
            if ok:
                _mark_fired(a["id"], price)
                fired += 1
                print(f"[price-alerts] FIRED #{a['id']} {tk} {a['direction']} ${target} @ ${price:.2f}")
    print(f"[price-alerts] Checked {len(active)} alerts across {len(price_map)} tickers — {fired} fired.")
    return fired


# ── CLI ───────────────────────────────────────────────────────────────────

def _cli():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m alerts.price_alerts check")
        print("  python -m alerts.price_alerts add TICKER PRICE [above|below] [note...]")
        print("  python -m alerts.price_alerts list")
        print("  python -m alerts.price_alerts cancel ALERT_ID")
        return 1

    cmd = sys.argv[1].lower()

    if cmd == "check":
        n = check_and_fire_alerts()
        return 0 if n >= 0 else 1

    if cmd == "list":
        rows = list_alerts(active_only=False)
        if not rows:
            print("No alerts.")
            return 0
        print(f"{'ID':<5} {'TICKER':<8} {'DIR':<6} {'TARGET':<10} {'STATUS':<10} NOTE")
        for r in rows:
            status = "FIRED" if r.get("fired") else "ACTIVE"
            print(f"{r['id']:<5} {r['ticker']:<8} {r['direction']:<6} "
                  f"${float(r['target']):<9.2f} {status:<10} {r.get('note','')}")
        return 0

    if cmd == "add":
        if len(sys.argv) < 3:
            print("add requires: TICKER [PRICE [above|below] [note]]")
            print("  - TICKER alone → watch-only (added to scan universe)")
            print("  - TICKER PRICE [above|below] → full price alert")
            return 1
        ticker = sys.argv[2]
        if len(sys.argv) < 4:
            # Watch-only — just ticker, no target
            create_alert(ticker)
            return 0
        price = float(sys.argv[3])
        direction = sys.argv[4] if len(sys.argv) > 4 else "above"
        note = " ".join(sys.argv[5:]) if len(sys.argv) > 5 else ""
        create_alert(ticker, price, direction, note)
        return 0

    if cmd == "cancel":
        if len(sys.argv) < 3:
            print("cancel requires: ALERT_ID")
            return 1
        cancel_alert(int(sys.argv[2]))
        return 0

    print(f"Unknown command: {cmd}")
    return 1


if __name__ == "__main__":
    sys.exit(_cli())
