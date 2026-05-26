"""
AEGIS — Trailing Stop & Partial Exit Manager
Runs every 30 minutes during market hours via GitHub Actions.

Two things happen in every run:

1. PARTIAL EXIT (scale-out) — fires ONCE per position at +7% gain:
   - Closes 50% of the position at market
   - Moves remaining stop to breakeven (entry price)
   - Logs to Supabase so it never fires twice
   - Next run applies trailing stop to the remaining half

2. TRAILING STOP — fires when position is up ≥ 3%:
   - Cancels fixed bracket SL, places Alpaca native trailing stop
   - Tightens as gains grow: +3%→3% trail, +7%→2%, +10%→1.5%, +15%→1%
   - Fractional positions use simulated trailing (fixed stop moved up)

Toggle ENABLE_PARTIAL_EXIT = False in config.py to revert to
single-exit mode instantly.
"""
import sys
from execution.alpaca import trail_positions, is_configured

if not is_configured():
    print("Alpaca not configured — skipping AEGIS check.")
    sys.exit(0)

print("[AEGIS] Running partial exit + trailing stop check...")
results = trail_positions()

if not results:
    print("[AEGIS] Nothing to act on — all positions below trigger thresholds.")
else:
    partial_exits = [r for r in results if r.get("action") == "partial_exit"]
    trail_upgrades = [r for r in results if r.get("action") != "partial_exit"]

    if partial_exits:
        print(f"\n✂️  {len(partial_exits)} partial exit(s) fired:")
        # Fire Pushover lock-screen alerts for each (no-op if PUSHOVER_* unset)
        try:
            from alerts.pushover import send_partial_exit, send_big_winner
            for r in partial_exits:
                tier = 2 if r.get("pct_gain", 0) >= 12 else 1
                send_partial_exit(r["ticker"], tier, r["pnl_locked"])
                # Also fire big-winner if gain ≥ threshold (default 10%)
                if r.get("pct_gain", 0) >= 10:
                    send_big_winner(r["ticker"], r["pnl_locked"], r["pct_gain"])
        except Exception as e:
            print(f"[trail_stops] pushover dispatch failed: {e}")

        for r in partial_exits:
            print(f"  ✂️  {r['ticker']:6s}  +{r['pct_gain']:.1f}%  →  "
                  f"closed {r['qty_closed']} shares  "
                  f"locked ${r['pnl_locked']:+.2f}  "
                  f"remaining {r['qty_remaining']} @ breakeven  "
                  f"[{r['order_id'][:8]}...]")

    if trail_upgrades:
        print(f"\n🔒  {len(trail_upgrades)} trailing stop upgrade(s):")
        for r in trail_upgrades:
            mode = "simulated" if r.get("status") == "simulated_trailing" else "native"
            print(f"  🔒  {r['ticker']:6s}  +{r['pct_gain']:.1f}%  →  "
                  f"trail {r['trail_pct']*100:.0f}% [{mode}]  "
                  f"[{r['order_id'][:8]}...]")

print("\n[AEGIS] Done.")
