import streamlit as st
import pandas as pd
from ui_style import inject_css, section_header, live_badge, agent_card
from config import BANKROLL

st.set_page_config(page_title="Positions & Trades", page_icon="💼", layout="wide")
inject_css()

from execution.alpaca import is_configured, is_live_mode

mode_label = "🔴 LIVE TRADING" if (is_configured() and is_live_mode()) else "📄 PAPER TRADING"
mode_color = "#ef4444" if is_live_mode() else "#f59e0b"

st.markdown(
    f'<h2 style="color:#e8e8e8;font-weight:700;">Positions & Trades</h2>'
    f'<p style="color:{mode_color};font-size:13px;margin-top:-8px;font-weight:600;">{mode_label}</p>',
    unsafe_allow_html=True
)

if not is_configured():
    st.markdown(
        '<div style="background:#161616;border:1px solid #f59e0b;border-radius:6px;padding:16px;color:#f59e0b;">'
        '⚠ Alpaca not configured. Add ALPACA_API_KEY and ALPACA_SECRET_KEY to your .env</div>',
        unsafe_allow_html=True
    )
    st.stop()

# ── Account ────────────────────────────────────────────────────────────────────
from execution.alpaca import get_account, get_positions, close_position
try:
    acct = get_account()
    st.divider()
    section_header("ACCOUNT SUMMARY")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio Value", f"${acct['portfolio_value']:,.2f}")
    c2.metric("Buying Power",    f"${acct['buying_power']:,.2f}")
    c3.metric("Cash",            f"${acct['cash']:,.2f}")
    c4.metric("Configured Bankroll", f"${BANKROLL:,.0f}")
except Exception as e:
    st.error(f"Alpaca connection error: {e}")
    st.stop()

# ── Open positions ─────────────────────────────────────────────────────────────
st.divider()
section_header("OPEN POSITIONS")
positions = get_positions()
if not positions:
    st.markdown('<div style="color:#333;padding:20px 0;">No open positions</div>', unsafe_allow_html=True)
else:
    rows_html = ""
    for p in positions:
        pl = p.get("unrealized_pl", 0)
        pl_pct = p.get("unrealized_pl_pct", 0)
        color = "#00ff88" if pl >= 0 else "#ef4444"
        arrow = "▲" if pl >= 0 else "▼"
        rows_html += f"""<tr style="border-bottom:1px solid #1a1a1a;">
          <td style="padding:10px 12px;font-family:JetBrains Mono,monospace;font-weight:700;color:#e8e8e8;">{p['ticker']}</td>
          <td style="padding:10px 12px;font-family:JetBrains Mono,monospace;color:#e8e8e8;">{p['qty']}</td>
          <td style="padding:10px 12px;font-family:JetBrains Mono,monospace;color:#e8e8e8;">${p['market_value']:,.2f}</td>
          <td style="padding:10px 12px;font-family:JetBrains Mono,monospace;color:{color};">{arrow} ${abs(pl):,.2f}</td>
          <td style="padding:10px 12px;font-family:JetBrains Mono,monospace;color:{color};">{arrow} {abs(pl_pct):.2f}%</td>
          <td style="padding:10px 12px;color:#555;font-size:12px;">{p.get('side','')}</td>
        </tr>"""

    st.markdown(f"""
    <table width="100%" cellpadding="0" cellspacing="0"
           style="border-collapse:collapse;background:#0d0d0d;border:1px solid #1e1e1e;border-radius:6px;overflow:hidden;">
      <thead><tr style="background:#111;">
        {"".join(f'<th style="padding:10px 12px;text-align:left;color:#444;font-size:11px;letter-spacing:1px;text-transform:uppercase;">{h}</th>' for h in ["Ticker","Qty","Value","P&L","P&L %","Side"])}
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table>""", unsafe_allow_html=True)

# ── Trade log ──────────────────────────────────────────────────────────────────
st.divider()
section_header("EXECUTION LOG")
try:
    import db
    if db.db_available():
        trades = db.load_trades()
        if trades:
            tdf = pd.DataFrame(trades)
            rows_html = ""
            for _, t in tdf.iterrows():
                side  = t.get("side","")
                color = "#00ff88" if side == "buy" else "#ef4444"
                rows_html += f"""<tr style="border-bottom:1px solid #1a1a1a;">
                  <td style="padding:8px 12px;color:#555;font-size:12px;">{str(t.get('timestamp',''))[:16]}</td>
                  <td style="padding:8px 12px;font-family:JetBrains Mono,monospace;font-weight:700;color:#e8e8e8;">{t.get('ticker','')}</td>
                  <td style="padding:8px 12px;color:{color};font-weight:600;">{side.upper()}</td>
                  <td style="padding:8px 12px;font-family:JetBrains Mono,monospace;color:#00ff88;">${float(t.get('dollar_amount',0)):,.2f}</td>
                  <td style="padding:8px 12px;color:#555;font-size:12px;">{t.get('mode','')}</td>
                  <td style="padding:8px 12px;color:#555;font-size:11px;">{str(t.get('reason',''))[:50]}</td>
                </tr>"""
            st.markdown(f"""
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="border-collapse:collapse;background:#0d0d0d;border:1px solid #1e1e1e;border-radius:6px;overflow:hidden;">
              <thead><tr style="background:#111;">
                {"".join(f'<th style="padding:10px 12px;text-align:left;color:#444;font-size:11px;letter-spacing:1px;text-transform:uppercase;">{h}</th>' for h in ["Time","Ticker","Side","Amount","Mode","Reason"])}
              </tr></thead>
              <tbody>{rows_html}</tbody>
            </table>""", unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#333;padding:20px 0;">No trades executed yet</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#555;padding:20px 0;">Supabase not connected — trade log unavailable</div>', unsafe_allow_html=True)
except Exception as e:
    st.error(str(e))

# ── Weekly learnings ───────────────────────────────────────────────────────────
st.divider()
section_header("WEEKLY LEARNINGS")
try:
    import db
    if db.db_available():
        learnings = db.load_learnings()
        if learnings:
            for l in learnings[:3]:
                hit_rate_pct = float(l.get("hit_rate", 0)) * 100
                color = "#00ff88" if hit_rate_pct >= 60 else "#f59e0b" if hit_rate_pct >= 45 else "#ef4444"
                with st.expander(f"Week of {l.get('week_of')} — hit rate {hit_rate_pct:.1f}%"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Predictions", l.get("total_predictions", 0))
                    c2.metric("Hit Rate", f"{hit_rate_pct:.1f}%")
                    c3.metric("Top Signal", l.get("top_hit_signals", "—"))
                    st.markdown(
                        f'<div style="background:#161616;border:1px solid #1e1e1e;border-radius:6px;padding:16px;'
                        f'color:#e8e8e8;font-size:13px;line-height:1.6;margin-top:8px;">'
                        f'{l.get("claude_analysis","No analysis available.").replace(chr(10),"<br>")}'
                        f'</div>', unsafe_allow_html=True
                    )
        else:
            st.markdown('<div style="color:#333;padding:20px 0;">No weekly learnings yet — generated every Sunday automatically</div>', unsafe_allow_html=True)
except Exception:
    pass
