from __future__ import annotations
"""
Pushover mobile push notifications.

Why Pushover and not Slack push:
  Slack mobile push depends on you having the app open + notifications
  enabled. Pushover sends a TRUE lock-screen alert that bypasses Do Not
  Disturb if you set the priority high enough — ideal for "stop just hit"
  or "huge winner closed" moments where you want to know NOW.

Setup (one-time, ~5 minutes):
  1. Buy Pushover ($5 one-time per device): https://pushover.net/
  2. Create an app token: https://pushover.net/apps/build
  3. Copy your User Key (https://pushover.net/) — looks like uHxxxXXXXxxx...
  4. Add to local .env + GitHub Actions secrets:
       PUSHOVER_USER_KEY=...
       PUSHOVER_APP_TOKEN=...

Public functions:
  send_push(title, message, priority=0, sound=None) -> bool
  send_big_winner(ticker, pl_dollar, pl_pct)        -> bool   # priority +1, "magic" sound
  send_stop_hit(ticker, pl_dollar, pl_pct)          -> bool   # priority 0,  "falling" sound
  send_partial_exit(ticker, tier, pl_dollar)        -> bool   # priority 0,  "cashregister"

Per-event opt-in: each event type checks a config flag so you can route
some events to push and leave the rest as Slack-only (avoids notification
fatigue on the routine stuff like scans).
"""
import os
import json
import urllib.request
import urllib.error


# ── Setup keys + per-event toggles ────────────────────────────────────
PUSHOVER_USER_KEY  = os.getenv("PUSHOVER_USER_KEY", "")
PUSHOVER_APP_TOKEN = os.getenv("PUSHOVER_APP_TOKEN", "")

# Each event flag defaults ON if Pushover is configured. Flip individual ones
# off in .env if you only want certain events on push.
PUSH_BIG_WINNERS    = os.getenv("PUSH_BIG_WINNERS",   "true").lower() == "true"
PUSH_STOP_HITS      = os.getenv("PUSH_STOP_HITS",     "true").lower() == "true"
PUSH_PARTIAL_EXITS  = os.getenv("PUSH_PARTIAL_EXITS", "true").lower() == "true"
PUSH_HALT           = os.getenv("PUSH_HALT",          "true").lower() == "true"

# Threshold above which a winning close counts as "big" and warrants push
BIG_WINNER_THRESHOLD_PCT = float(os.getenv("PUSH_BIG_WINNER_PCT", "10"))


# ── Core ──────────────────────────────────────────────────────────────

def _enabled() -> bool:
    return bool(PUSHOVER_USER_KEY and PUSHOVER_APP_TOKEN)


def send_push(
    title: str,
    message: str,
    priority: int = 0,
    sound: str | None = None,
    url: str | None = None,
    url_title: str | None = None,
) -> bool:
    """
    Send a Pushover notification.

    Priority levels:
      -2: silent (no notification, just in app)
      -1: quiet (no sound/vibration)
       0: normal (default)
       1: high (bypass quiet hours, persistent)
       2: emergency (requires ack, retries every 30s up to 3h)

    Sounds — see https://pushover.net/api#sounds for full list.
    Defaults to user's app default if None.
    """
    if not _enabled():
        print("[pushover] PUSHOVER_USER_KEY/APP_TOKEN not set — skipping.")
        return False

    data = {
        "token":    PUSHOVER_APP_TOKEN,
        "user":     PUSHOVER_USER_KEY,
        "title":    title[:250],
        "message":  message[:1024],
        "priority": int(priority),
    }
    if sound:     data["sound"]     = sound
    if url:       data["url"]       = url
    if url_title: data["url_title"] = url_title[:100]

    if priority == 2:
        # Emergency requires retry + expire
        data.setdefault("retry",  60)     # retry every 60s
        data.setdefault("expire", 3600)   # for up to 1 hour

    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        "https://api.pushover.net/1/messages.json",
        data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.loads(r.read().decode("utf-8"))
        if resp.get("status") == 1:
            print(f"[pushover] sent — '{title}'")
            return True
        print(f"[pushover] API error: {resp}")
        return False
    except urllib.error.HTTPError as e:
        print(f"[pushover] HTTP {e.code}: {e.read().decode()[:200]}")
        return False
    except Exception as e:
        print(f"[pushover] error: {e}")
        return False


# ── Pre-built helpers for common events ───────────────────────────────

def send_big_winner(ticker: str, pl_dollar: float, pl_pct: float) -> bool:
    """Big winner closed (≥ BIG_WINNER_THRESHOLD_PCT). Priority +1, magic sound."""
    if not PUSH_BIG_WINNERS:
        return False
    if pl_pct < BIG_WINNER_THRESHOLD_PCT:
        return False
    return send_push(
        title=f"💰 {ticker} BIG WINNER",
        message=f"Closed +${pl_dollar:,.0f} ({pl_pct:+.1f}%)",
        priority=1,
        sound="magic",
        url=f"https://illuminati-dashboard.pages.dev/",
        url_title="View dashboard",
    )


def send_stop_hit(ticker: str, pl_dollar: float, pl_pct: float) -> bool:
    """Stop loss triggered. Priority 0, falling sound."""
    if not PUSH_STOP_HITS:
        return False
    return send_push(
        title=f"🛑 {ticker} stopped out",
        message=f"Closed -${abs(pl_dollar):,.0f} ({pl_pct:+.1f}%)",
        priority=0,
        sound="falling",
    )


def send_partial_exit(ticker: str, tier: int, pl_dollar: float) -> bool:
    """Partial exit fired (T1 at +7% or T2 at +12%). Priority 0, cash register."""
    if not PUSH_PARTIAL_EXITS:
        return False
    tier_label = "T1 (+7%)" if tier == 1 else "T2 (+12%)" if tier == 2 else f"T{tier}"
    return send_push(
        title=f"🎯 {ticker} partial exit {tier_label}",
        message=f"Locked +${pl_dollar:,.0f} · remaining rides trailing stop",
        priority=0,
        sound="cashregister",
    )


def send_halt(reason: str) -> bool:
    """Trading halt (daily loss limit hit, kill switch, etc.). Priority +1."""
    if not PUSH_HALT:
        return False
    return send_push(
        title="🚨 TRADING HALTED",
        message=reason,
        priority=1,
        sound="siren",
    )


def send_test() -> bool:
    """Verify the Pushover integration works."""
    return send_push(
        title="🤖 Illuminati — push test",
        message="If you see this on your lock screen, Pushover is wired up.",
        priority=0,
        sound="pushover",
    )


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        ok = send_test()
        sys.exit(0 if ok else 1)
    print("Usage: python -m alerts.pushover test")
