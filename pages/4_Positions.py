import streamlit as st
import pandas as pd

st.set_page_config(page_title="Positions & Trades", page_icon="💼", layout="wide")
st.title("Positions & Trades")
st.caption("Live Alpaca positions and execution log.")

from execution.alpaca import is_configured, is_live_mode, get_account, get_positions
from config import BANKROLL

if not is_configured():
    st.warning("Alpaca not configured. Add `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` to your `.env`.")
    st.stop()

mode_label = "🔴 LIVE TRADING" if is_live_mode() else "📄 PAPER TRADING"
if is_live_mode():
    st.error(f"**{mode_label}** — real money at risk")
else:
    st.info(f"**{mode_label}** — no real money")

# ── Account summary ───────────────────────────────────────────────────────────
st.divider()
try:
    acct = get_account()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio Value", f"${acct['portfolio_value']:,.2f}")
    c2.metric("Buying Power",    f"${acct['buying_power']:,.2f}")
    c3.metric("Cash",            f"${acct['cash']:,.2f}")
    c4.metric("Configured Bankroll", f"${BANKROLL:,.0f}")
except Exception as e:
    st.error(f"Could not connect to Alpaca: {e}")
    st.stop()

# ── Open positions ────────────────────────────────────────────────────────────
st.divider()
st.subheader("Open Positions")
positions = get_positions()
if not positions:
    st.info("No open positions.")
else:
    pos_df = pd.DataFrame(positions)
    def color_pl(val):
        if isinstance(val, (int, float)):
            return "color: #16a34a" if val >= 0 else "color: #dc2626"
        return ""
    styled = pos_df.style.map(color_pl, subset=["unrealized_pl", "unrealized_pl_pct"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    if st.button("Close All Positions", type="secondary"):
        st.warning("This will close all open positions. Are you sure?")
        if st.button("Yes, close all", type="primary"):
            from execution.alpaca import close_position
            for p in positions:
                close_position(p["ticker"])
            st.success("All positions closed.")

# ── Trade log ─────────────────────────────────────────────────────────────────
st.divider()
st.subheader("Execution Log")
try:
    import db
    if db.db_available():
        trades = db.load_trades()
        if trades:
            trades_df = pd.DataFrame(trades)
            st.dataframe(trades_df, use_container_width=True, hide_index=True, height=400)
        else:
            st.info("No trades executed yet.")
    else:
        st.warning("Supabase not connected — trade log unavailable.")
except Exception as e:
    st.error(f"Could not load trade log: {e}")

# ── Weekly insights ───────────────────────────────────────────────────────────
st.divider()
st.subheader("Weekly Learnings")
try:
    import db
    if db.db_available():
        learnings = db.load_learnings()
        if learnings:
            for l in learnings[:3]:
                with st.expander(f"Week of {l.get('week_of')} — hit rate {float(l.get('hit_rate',0))*100:.1f}%"):
                    st.markdown(l.get("claude_analysis", "No analysis available."))
                    cols = st.columns(3)
                    cols[0].metric("Predictions", l.get("total_predictions", 0))
                    cols[1].metric("Hit Rate", f"{float(l.get('hit_rate',0))*100:.1f}%")
                    cols[2].metric("Top Hit Signals", l.get("top_hit_signals", "—"))
        else:
            st.info("No weekly learnings yet. The system generates these every Sunday.")
except Exception:
    pass
