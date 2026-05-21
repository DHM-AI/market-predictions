"""
Positions & Trades — live open positions, execution log, weekly learnings.
Matches the futuristic dark theme of the main Scanner dashboard.
"""
import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Positions & Trades", page_icon="💼", layout="wide",
                   initial_sidebar_state="collapsed")

BG    = "#03060d"
SURF  = "#07111f"
SURF2 = "#0c1d30"
GLOW  = "#00d4ff"
GREEN = "#00ff88"
RED   = "#ff2d78"
AMBER = "#ffaa00"
TEXT  = "#e8f4ff"
TEXT2 = "#8ab8d4"
TEXT3 = "#5a8a9f"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
*, body, html, [class*="css"] {{ font-family:'Inter',sans-serif !important; }}
.stApp {{
    background:{BG} !important;
    background-image:
        linear-gradient(rgba(0,180,255,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,180,255,0.025) 1px, transparent 1px),
        radial-gradient(ellipse at 50% 0%, rgba(0,80,180,0.10) 0%, transparent 60%) !important;
    background-size:48px 48px, 48px 48px, 100% 100% !important;
}}
header[data-testid="stHeader"],
.stAppHeader, #stDecoration, footer,
[data-testid="stBottom"], #MainMenu,
section[data-testid="stSidebar"],
[data-testid="collapsedControl"] {{ display:none !important; }}
.block-container {{ padding:16px 24px !important; max-width:100% !important; }}
hr {{ border-color:rgba(0,180,255,0.08) !important; margin:16px 0 !important; }}
.stButton > button {{
    background:rgba(0,180,255,0.08) !important; color:{GLOW} !important;
    border:1px solid rgba(0,180,255,0.25) !important; border-radius:6px !important;
    font-size:12px !important; font-weight:600 !important; transition:all 0.15s !important;
}}
.stButton > button:hover {{ background:rgba(0,180,255,0.18) !important; }}
.sec {{
    font-size:9px; font-weight:700; letter-spacing:3px; text-transform:uppercase; color:{TEXT3};
    display:flex; align-items:center; gap:10px; margin:16px 0 12px;
}}
.sec::after {{ content:''; flex:1; height:1px; background:linear-gradient(90deg, rgba(0,180,255,0.15), transparent); }}
.metrics-row {{ display:grid; grid-template-columns:repeat(5,1fr); gap:10px; margin-bottom:16px; }}
.metric-card {{
    background:{SURF}; border:1px solid rgba(0,180,255,0.1); border-radius:8px;
    padding:12px 14px; position:relative; overflow:hidden;
}}
.metric-card::before {{
    content:''; position:absolute; top:0; left:0; right:0; height:2px;
    background:var(--mc, rgba(0,180,255,0.3));
}}
.metric-lbl {{ font-size:9px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:{TEXT3}; margin-bottom:4px; }}
.metric-val {{ font-family:'JetBrains Mono',monospace; font-size:22px; font-weight:700; color:{TEXT}; line-height:1.1; }}
.metric-sub {{ font-size:10px; color:{TEXT2}; margin-top:3px; }}
.pos-card {{
    background:{SURF}; border:1px solid rgba(0,180,255,0.1); border-radius:8px;
    padding:14px 18px; margin-bottom:8px;
    display:grid; grid-template-columns:80px 70px 1fr 1fr 1fr 1fr 1fr 90px;
    align-items:center; gap:12px; transition:border-color 0.15s;
}}
.pos-card:hover {{ border-color:rgba(0,180,255,0.3); }}
.pos-ticker {{ font-family:'JetBrains Mono',monospace; font-size:16px; font-weight:700; color:{GLOW}; }}
.pos-badge-l {{ background:rgba(0,255,136,0.1); border:1px solid rgba(0,255,136,0.3); color:{GREEN}; font-size:9px; font-weight:800; letter-spacing:1px; padding:2px 7px; border-radius:3px; }}
.pos-badge-s {{ background:rgba(255,45,120,0.1); border:1px solid rgba(255,45,120,0.3); color:{RED}; font-size:9px; font-weight:800; letter-spacing:1px; padding:2px 7px; border-radius:3px; }}
.pos-col {{ display:flex; flex-direction:column; gap:2px; }}
.pos-lbl {{ font-size:9px; font-weight:700; letter-spacing:1px; text-transform:uppercase; color:{TEXT3}; }}
.pos-val {{ font-family:'JetBrains Mono',monospace; font-size:13px; font-weight:600; color:{TEXT}; }}
.tbl-hdr {{ display:grid; gap:10px; padding:8px 16px; background:rgba(0,180,255,0.04); border-radius:6px 6px 0 0; }}
.tbl-row {{ display:grid; gap:10px; padding:10px 16px; border-bottom:1px solid rgba(0,180,255,0.05); transition:background 0.1s; }}
.tbl-row:hover {{ background:rgba(0,180,255,0.03); }}
.tbl-row:last-child {{ border-bottom:none; }}
.tbl-lbl {{ font-size:9px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:{TEXT3}; }}
.learn-card {{
    background:{SURF}; border:1px solid rgba(0,180,255,0.1);
    border-radius:8px; padding:18px; margin-bottom:10px;
}}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
try:
    from execution.alpaca import is_configured, is_live_mode
except ImportError:
    def is_configured(): return False
    def is_live_mode():  return False

mode_label = "🔴 LIVE TRADING" if (is_configured() and is_live_mode()) else "📄 PAPER TRADING"
mode_color = RED if (is_configured() and is_live_mode()) else AMBER

st.markdown(
    f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">'
    f'<span style="font-size:18px;font-weight:700;color:{TEXT};">💼 Positions & Trades</span>'
    f'<span style="font-size:11px;font-weight:700;color:{mode_color};">{mode_label}</span>'
    f'</div>',
    unsafe_allow_html=True
)

if not is_configured():
    st.markdown(
        f'<div style="background:{SURF};border:1px solid rgba(255,170,0,0.3);border-radius:8px;'
        f'padding:20px;color:{AMBER};">'
        f'⚠ Alpaca not configured. Add ALPACA_API_KEY and ALPACA_SECRET_KEY to your .env</div>',
        unsafe_allow_html=True
    )
    st.stop()

# ── Account metrics ────────────────────────────────────────────────────────────
from execution.alpaca import get_account, get_positions, close_position
from config import BANKROLL

try:
    acct      = get_account()
    positions = get_positions()
except Exception as e:
    st.error(f"Alpaca connection error: {e}")
    st.stop()

portfolio    = acct.get("portfolio_value", 0)
buying_power = acct.get("buying_power", 0)
cash         = acct.get("cash", 0)
total_pl     = sum(p.get("unrealized_pl", 0) for p in positions)
pl_color     = GREEN if total_pl >= 0 else RED
pl_sign      = "+" if total_pl >= 0 else ""

def mc(label, val, sub, color=TEXT3):
    return (
        f'<div class="metric-card" style="--mc:{color}44;">'
        f'<div class="metric-lbl">{label}</div>'
        f'<div class="metric-val" style="color:{color};">{val}</div>'
        f'<div class="metric-sub">{sub}</div>'
        f'</div>'
    )

st.markdown(
    f'<div class="metrics-row">'
    + mc("Portfolio Value",  f"${portfolio:,.0f}",          "Total equity", GLOW)
    + mc("Unrealized P&L",  f"{pl_sign}${abs(total_pl):,.2f}", f"{len(positions)} open", pl_color)
    + mc("Buying Power",    f"${buying_power:,.0f}",         "Available", TEXT)
    + mc("Cash",            f"${cash:,.0f}",                 "Uninvested", TEXT2)
    + mc("Bankroll Config", f"${BANKROLL:,.0f}",             "Max deployment", TEXT3)
    + f'</div>',
    unsafe_allow_html=True
)

# ── Sector breakdown ───────────────────────────────────────────────────────────
if positions:
    try:
        from risk.portfolio_guard import get_sector_breakdown
        sectors = get_sector_breakdown(positions)
        if sectors:
            total_val = sum(sectors.values()) or 1
            sector_pills = "".join(
                f'<span style="display:inline-flex;align-items:center;gap:6px;'
                f'background:{SURF2};border:1px solid rgba(0,180,255,0.12);'
                f'border-radius:20px;padding:4px 12px;font-size:11px;margin:3px;">'
                f'<span style="color:{TEXT2};">{sec}</span>'
                f'<span style="font-family:JetBrains Mono,monospace;color:{GLOW};font-weight:700;">'
                f'${val:,.0f}</span>'
                f'<span style="color:{TEXT3};">({val/total_val:.0%})</span>'
                f'</span>'
                for sec, val in sectors.items()
            )
            st.markdown(
                f'<div style="margin-bottom:16px;">'
                f'<div class="sec">Sector Exposure</div>'
                f'<div>{sector_pills}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
    except Exception:
        pass

# ── Open positions ────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="sec">Open Positions <span style="font-family:JetBrains Mono,monospace;'
    f'font-size:11px;color:{TEXT2};background:rgba(0,180,255,0.06);border:1px solid rgba(0,180,255,0.12);'
    f'padding:1px 8px;border-radius:20px;">{len(positions)}</span>'
    f'<span style="font-size:9px;color:{TEXT3};margin-left:8px;">updates every page load</span></div>',
    unsafe_allow_html=True
)

if "confirm_close" not in st.session_state:
    st.session_state["confirm_close"] = None

if st.session_state["confirm_close"]:
    tkr = st.session_state["confirm_close"]
    st.markdown(
        f'<div style="background:rgba(255,45,120,0.06);border:1px solid rgba(255,45,120,0.25);'
        f'border-radius:8px;padding:14px 18px;margin-bottom:12px;">'
        f'<span style="color:{TEXT};font-size:13px;">⚠ Close <strong style="color:{RED};">{tkr}</strong> at market price?</span>'
        f'</div>',
        unsafe_allow_html=True
    )
    c1, c2, c3 = st.columns([4, 1, 1])
    with c2:
        if st.button("✓ Confirm", type="primary", use_container_width=True):
            result = close_position(tkr)
            if result.get("status") == "closed":
                st.success(f"{tkr} closed.")
            else:
                st.error(result.get("reason", "Error"))
            st.session_state["confirm_close"] = None
            st.rerun()
    with c3:
        if st.button("✗ Cancel", use_container_width=True):
            st.session_state["confirm_close"] = None
            st.rerun()

if not positions:
    st.markdown(
        f'<div style="background:{SURF};border:1px solid rgba(0,180,255,0.08);'
        f'border-radius:8px;padding:40px;text-align:center;color:{TEXT3};">'
        f'No open positions right now</div>',
        unsafe_allow_html=True
    )
else:
    # Column headers
    _hdr_cells = "".join(f'<div class="tbl-lbl">{h}</div>' for h in ["Ticker","Side","Value","Entry","Current","P&L","SL / TP","Close"])
    st.markdown(
        f'<div class="pos-card" style="background:rgba(0,180,255,0.03);border-color:rgba(0,180,255,0.06);">'
        f'{_hdr_cells}'
        f'</div>',
        unsafe_allow_html=True
    )
    for p in positions:
        tkr      = p.get("ticker", "")
        side     = str(p.get("side", "")).lower()
        qty      = p.get("qty", 0)
        mkt_val  = p.get("market_value", 0)
        pl       = p.get("unrealized_pl", 0)
        pl_pct   = p.get("unrealized_pl_pct", 0)
        entry    = p.get("avg_entry_price", 0)
        current  = p.get("current_price", 0)
        sl       = p.get("stop_loss")
        tp       = p.get("take_profit")
        is_long  = side in ("long", "buy")
        pl_c     = GREEN if pl >= 0 else RED
        arrow    = "▲" if pl >= 0 else "▼"

        badge = (f'<span class="pos-badge-l">LONG</span>' if is_long
                 else f'<span class="pos-badge-s">SHORT</span>')

        sl_tp = "—"
        if sl and tp:
            sl_tp = f'<span style="color:{RED};font-family:JetBrains Mono,monospace;font-size:11px;">${sl:.2f}</span> / <span style="color:{GREEN};font-family:JetBrains Mono,monospace;font-size:11px;">${tp:.2f}</span>'
        elif sl:
            sl_tp = f'<span style="color:{RED};font-family:JetBrains Mono,monospace;font-size:11px;">SL ${sl:.2f}</span>'

        close_key = f"close_{tkr}"

        col_pos, col_btn_close = st.columns([10, 1])
        with col_pos:
            st.markdown(
                f'<div class="pos-card">'
                f'<div class="pos-ticker">{tkr}</div>'
                f'<div>{badge}<br><span style="font-size:10px;color:{TEXT3};">{qty:.0f} shares</span></div>'
                f'<div class="pos-col"><div class="pos-lbl">Market Value</div><div class="pos-val">${mkt_val:,.2f}</div></div>'
                f'<div class="pos-col"><div class="pos-lbl">Entry</div><div class="pos-val">${entry:.2f}</div></div>'
                f'<div class="pos-col"><div class="pos-lbl">Current</div><div class="pos-val">${current:.2f}</div></div>'
                f'<div class="pos-col"><div class="pos-lbl">P&L</div>'
                f'<div class="pos-val" style="color:{pl_c};">{arrow} ${abs(pl):,.2f}</div>'
                f'<div style="font-size:10px;color:{pl_c};">{pl_pct:+.2f}%</div></div>'
                f'<div class="pos-col"><div class="pos-lbl">SL / TP</div><div style="margin-top:2px;">{sl_tp}</div></div>'
                f'<div></div>'
                f'</div>',
                unsafe_allow_html=True
            )
        with col_btn_close:
            if st.button("✗ Close", key=close_key, use_container_width=True):
                st.session_state["confirm_close"] = tkr
                st.rerun()

# ── Execution log ──────────────────────────────────────────────────────────────
st.markdown('<div class="sec">Execution Log</div>', unsafe_allow_html=True)

try:
    import db
    if db.db_available():
        trades = db.load_trades()
        if trades:
            tdf = pd.DataFrame(trades).head(50)

            headers = ["Time", "Ticker", "Side", "Amount", "Entry", "SL", "TP", "Mode", "Reason"]
            cols_w  = "120px 80px 70px 100px 80px 80px 80px 60px 1fr"

            # Build lookup maps: open positions and closed trade P&L
            open_pl_map = {p["ticker"]: p for p in positions}   # live unrealized P&L
            closed_pnl_map = {}
            try:
                from execution.alpaca import get_closed_trade_pnl
                for cp in get_closed_trade_pnl(days=90):
                    closed_pnl_map[cp["ticker"]] = cp
            except Exception:
                pass

            headers = ["Time", "Ticker", "Side", "Invested", "Entry", "SL", "TP", "P&L", "Status"]
            cols_w  = "110px 70px 60px 90px 80px 80px 80px 110px 1fr"

            hdr_html = f'<div class="tbl-hdr" style="grid-template-columns:{cols_w};">' + \
                       "".join(f'<div class="tbl-lbl">{h}</div>' for h in headers) + "</div>"

            rows_html = ""
            for _, t in tdf.iterrows():
                side_   = t.get("side", "")
                sc      = GREEN if side_ == "buy" else RED
                ts      = str(t.get("timestamp", ""))[:16].replace("T", " ")
                ticker_ = t.get("ticker", "")
                entry_  = t.get("entry_price")
                sl_     = t.get("stop_loss")
                tp_     = t.get("take_profit")
                entry_s = f'${float(entry_):,.2f}' if entry_ else "—"
                sl_s    = f'${float(sl_):,.2f}'    if sl_    else "—"
                tp_s    = f'${float(tp_):,.2f}'    if tp_    else "—"

                # P&L column — live if open, realized if closed
                if ticker_ in open_pl_map:
                    upl   = open_pl_map[ticker_]["unrealized_pl"]
                    upct  = open_pl_map[ticker_]["unrealized_pl_pct"]
                    pc    = GREEN if upl >= 0 else RED
                    arrow = "▲" if upl >= 0 else "▼"
                    pnl_s = (f'<span style="color:{pc};font-family:JetBrains Mono,monospace;font-weight:700;">'
                             f'{arrow} ${abs(upl):,.2f} ({upct:+.1f}%)</span>')
                    status_s = f'<span style="color:{GLOW};font-size:10px;font-weight:700;">● OPEN</span>'
                elif ticker_ in closed_pnl_map:
                    cp    = closed_pnl_map[ticker_]
                    rpl   = cp["realized_pnl"]
                    rpct  = cp["realized_pnl_pct"]
                    pc    = GREEN if rpl >= 0 else RED
                    arrow = "▲" if rpl >= 0 else "▼"
                    pnl_s = (f'<span style="color:{pc};font-family:JetBrains Mono,monospace;font-weight:700;">'
                             f'{arrow} ${abs(rpl):,.2f} ({rpct:+.1f}%)</span>')
                    outcome_map = {"tp_hit": f"🎯 TP HIT", "sl_hit": f"🛑 SL HIT", "closed": "CLOSED"}
                    outcome_label = outcome_map.get(cp.get("outcome","closed"), "CLOSED")
                    oc = GREEN if cp.get("outcome") == "tp_hit" else RED if cp.get("outcome") == "sl_hit" else TEXT3
                    status_s = f'<span style="color:{oc};font-size:10px;font-weight:700;">{outcome_label}</span>'
                else:
                    pnl_s    = f'<span style="color:{TEXT3};">Pending</span>'
                    status_s = f'<span style="color:{TEXT3};font-size:10px;">PENDING</span>'

                rows_html += (
                    f'<div class="tbl-row" style="grid-template-columns:{cols_w};">'
                    f'<div style="font-family:JetBrains Mono,monospace;font-size:11px;color:{TEXT3};">{ts}</div>'
                    f'<div style="font-family:JetBrains Mono,monospace;font-weight:700;color:{TEXT};">{ticker_}</div>'
                    f'<div style="color:{sc};font-weight:700;font-size:12px;">{side_.upper()}</div>'
                    f'<div style="font-family:JetBrains Mono,monospace;color:{GLOW};">${float(t.get("dollar_amount",0)):,.0f}</div>'
                    f'<div style="font-family:JetBrains Mono,monospace;font-size:12px;color:{TEXT2};">{entry_s}</div>'
                    f'<div style="font-family:JetBrains Mono,monospace;font-size:12px;color:{RED};">{sl_s}</div>'
                    f'<div style="font-family:JetBrains Mono,monospace;font-size:12px;color:{GREEN};">{tp_s}</div>'
                    f'<div>{pnl_s}</div>'
                    f'<div>{status_s}</div>'
                    f'</div>'
                )

            st.markdown(
                f'<div style="background:{SURF};border:1px solid rgba(0,180,255,0.08);border-radius:8px;overflow:hidden;">'
                f'{hdr_html}'
                f'<div style="max-height:400px;overflow-y:auto;">{rows_html}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div style="background:{SURF};border:1px solid rgba(0,180,255,0.08);border-radius:8px;'
                f'padding:30px;text-align:center;color:{TEXT3};">No trades executed yet</div>',
                unsafe_allow_html=True
            )
except Exception as e:
    st.markdown(f'<div style="color:{AMBER};padding:12px;">Trade log unavailable: {e}</div>',
                unsafe_allow_html=True)

# ── Weekly learnings ───────────────────────────────────────────────────────────
st.markdown('<div class="sec">Weekly Learnings</div>', unsafe_allow_html=True)

try:
    import db
    if db.db_available():
        learnings = db.load_learnings()
        if learnings:
            for l in learnings[:3]:
                hr = float(l.get("hit_rate", 0)) * 100
                hr_color = GREEN if hr >= 60 else AMBER if hr >= 45 else RED
                week = l.get("week_of", "")
                analysis = l.get("claude_analysis", "No analysis available.").replace("\n", "<br>")
                with st.expander(f"Week of {week}  ·  Hit rate {hr:.1f}%"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Predictions", l.get("total_predictions", 0))
                    c2.metric("Hit Rate", f"{hr:.1f}%")
                    c3.metric("Top Signal", l.get("top_hit_signals", "—"))
                    st.markdown(
                        f'<div style="background:{SURF2};border:1px solid rgba(0,180,255,0.08);'
                        f'border-radius:6px;padding:14px;color:{TEXT2};font-size:13px;line-height:1.7;margin-top:8px;">'
                        f'{analysis}</div>',
                        unsafe_allow_html=True
                    )
        else:
            st.markdown(
                f'<div style="background:{SURF};border:1px solid rgba(0,180,255,0.08);border-radius:8px;'
                f'padding:30px;text-align:center;color:{TEXT3};">'
                f'No weekly learnings yet — generated every Sunday automatically</div>',
                unsafe_allow_html=True
            )
except Exception:
    pass
