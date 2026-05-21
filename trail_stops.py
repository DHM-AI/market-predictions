"""
Trailing stop manager — runs every 30 minutes during market hours via GitHub Actions.

Logic:
  - Any position up ≥ 3% gets its fixed SL cancelled and replaced with
    an Alpaca native trailing stop at 3% below the running peak price.
  - The take-profit target (+7%) is left untouched.
  - Already-trailing positions are skipped (idempotent).
  - A Slack ping fires when a stop is upgraded.

Config (config.py):
  TRAIL_TRIGGER_PCT = 0.03   (activate when up 3%)
  TRAIL_PCT         = 0.03   (trail 3% below peak)
"""
import sys
from execution.alpaca import trail_positions, is_configured

if not is_configured():
    print("Alpaca not configured — skipping trail check.")
    sys.exit(0)

print("Checking positions for trailing stop upgrades...")
results = trail_positions()

if not results:
    print("No positions ready for trailing yet.")
else:
    print(f"\n{len(results)} position(s) upgraded to trailing stop:")
    for r in results:
        print(f"  ✓ {r['ticker']:6s}  +{r['pct_gain']:.1f}%  →  "
              f"trailing {r['trail_pct']*100:.0f}% below peak  "
              f"[{r['order_id'][:8]}...]")

print("\nDone.")
