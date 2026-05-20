import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import math

st.set_page_config(page_title="Market Scanner", page_icon="⚡", layout="wide",
                   initial_sidebar_state="collapsed")

BG    = "#03060d"
SURF  = "#07111f"
SURF2 = "#0c1d30"
GLOW  = "#00d4ff"
GREEN = "#00ff88"
RED   = "#ff2d78"
AMBER = "#ffaa00"
TEXT  = "#c8e8ff"
TEXT2 = "#4a7a9b"
TEXT3 = "#1e3a50"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
*, body, html, [class*="css"] {{ font-family:'Inter',sans-serif !important; -webkit-font-smoothing:antialiased; }}
.stApp {{
    background:{BG} !important;
    background-image:
        linear-gradient(rgba(0,180,255,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,180,255,0.025) 1px, transparent 1px),
        radial-gradient(ellipse at 50% 0%, rgba(0,80,180,0.10) 0%, transparent 60%) !important;
    background-size:48px 48px, 48px 48px, 100% 100% !important;
}}
header[data-testid="stHeader"] {{ display:none !important; }}
.stAppHeader {{ display:none !important; }}
#stDecoration {{ display:none !important; }}
footer {{ display:none !important; }}
footer * {{ display:none !important; }}
[data-testid="stBottom"] {{ display:none !important; }}
[data-testid="stBottom"] * {{ display:none !important; }}
.viewerBadge_container__r5tak {{ display:none !important; }}
.viewerBadge_link__qRIco {{ display:none !important; }}
#MainMenu {{ display:none !important; }}
.st-emotion-cache-h4xjwg {{ display:none !important; }}
.st-emotion-cache-1dp5vir {{ display:none !important; }}
/* Nuclear option — hide any fixed bottom bar */
div[style*="position: fixed"][style*="bottom"] {{ display:none !important; }}
div[class*="manage"] {{ display:none !important; }}
section[data-testid="stSidebar"] {{ display:none !important; }}
[data-testid="collapsedControl"] {{ display:none !important; }}
.block-container {{ padding:16px 24px !important; max-width:100% !important; }}
hr {{ border-color:rgba(0,180,255,0.08) !important; margin:16px 0 !important; }}

/* ── Top bar ── */
.top-row {{
    display:flex; align-items:center; justify-content:space-between;
    margin-bottom:14px;
}}
.dash-title {{ font-size:18px; font-weight:700; color:{TEXT}; display:flex; align-items:center; gap:10px; }}
.live-pill {{
    display:inline-flex; align-items:center; gap:5px;
    background:rgba(0,255,136,0.08); border:1px solid rgba(0,255,136,0.25);
    color:{GREEN}; font-size:9px; font-weight:700; letter-spacing:2px;
    padding:3px 10px; border-radius:20px;
}}
.live-dot {{ width:5px; height:5px; border-radius:50%; background:{GREEN}; animation:blink 1.4s infinite; display:inline-block; }}
.top-right {{ display:flex; align-items:center; gap:10px; }}
.last-update {{ font-size:11px; color:{TEXT3}; }}

/* ── Metric cards ── */
.metrics-row {{ display:grid; grid-template-columns:repeat(6,1fr); gap:10px; margin-bottom:16px; }}
.metric-card {{
    background:{SURF}; border:1px solid rgba(0,180,255,0.1); border-radius:8px;
    padding:12px 14px; position:relative; overflow:hidden; cursor:default;
}}
.metric-card::before {{
    content:''; position:absolute; top:0; left:0; right:0; height:2px;
    background:var(--mc, rgba(0,180,255,0.3));
}}
.metric-lbl {{ font-size:9px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:{TEXT3}; margin-bottom:4px; }}
.metric-val {{ font-family:'JetBrains Mono',monospace; font-size:20px; font-weight:700; color:{TEXT}; line-height:1.1; }}
.metric-sub {{ font-size:10px; color:{TEXT2}; margin-top:3px; }}

/* ── Tooltip system ── */
.tt {{ position:relative; display:block; cursor:help; }}
.tt .tip {{
    visibility:hidden; opacity:0;
    position:fixed; z-index:99999;
    background:#071828; border:1px solid rgba(0,180,255,0.4);
    border-radius:10px; padding:14px 16px;
    font-size:11px; color:{TEXT}; line-height:1.7;
    width:260px;
    box-shadow:0 16px 48px rgba(0,0,0,0.8), 0 0 0 1px rgba(0,180,255,0.1);
    transition:opacity 0.15s; pointer-events:none;
    text-align:left; white-space:normal;
}}
.tt:hover .tip {{ visibility:visible; opacity:1; }}
/* JS positions the tip on hover to stay on-screen */

/* ── Section header ── */
.sec {{
    font-size:9px; font-weight:700; letter-spacing:3px; text-transform:uppercase; color:{TEXT3};
    display:flex; align-items:center; gap:10px; margin-bottom:12px;
}}
.sec::after {{ content:''; flex:1; height:1px; background:linear-gradient(90deg, rgba(0,180,255,0.15), transparent); }}
.sec-n {{ font-family:'JetBrains Mono',monospace; font-size:11px; color:{TEXT2}; background:rgba(0,180,255,0.06); border:1px solid rgba(0,180,255,0.12); padding:1px 8px; border-radius:20px; }}

/* ── Trade card ── */
.trade-card {{
    position:relative; padding:16px;
    background:linear-gradient(135deg, rgba(10,26,44,0.97) 0%, rgba(5,12,22,0.97) 100%);
    border:1px solid var(--acc2, rgba(0,180,255,0.15));
    border-radius:8px; overflow:visible; height:100%;
}}
.trade-card::before {{
    content:''; position:absolute; top:0; left:0; right:0; height:2px;
    background:linear-gradient(90deg, transparent, var(--acc), transparent); opacity:0.7;
    border-radius:8px 8px 0 0;
}}
.c {{ position:absolute; width:10px; height:10px; }}
.c-tl {{ top:0;left:0; border-top:2px solid var(--acc); border-left:2px solid var(--acc); border-radius:2px 0 0 0; }}
.c-tr {{ top:0;right:0; border-top:2px solid var(--acc); border-right:2px solid var(--acc); border-radius:0 2px 0 0; }}
.c-bl {{ bottom:0;left:0; border-bottom:2px solid var(--acc); border-left:2px solid var(--acc); border-radius:0 0 0 2px; }}
.c-br {{ bottom:0;right:0; border-bottom:2px solid var(--acc); border-right:2px solid var(--acc); border-radius:0 0 2px 0; }}
.card-ticker {{ font-family:'JetBrains Mono',monospace; font-size:22px; font-weight:700; line-height:1; }}
.card-action {{ font-size:10px; font-weight:800; letter-spacing:2px; padding:4px 10px; border-radius:3px; display:inline-block; margin-top:5px; }}
.card-div {{ height:1px; background:rgba(0,180,255,0.08); margin:10px 0; }}
.stars {{ font-size:15px; letter-spacing:2px; margin-bottom:5px; }}
.card-reason {{
    font-size:11px; color:{TEXT}; line-height:1.5;
    background:rgba(0,0,0,0.25); border-radius:4px; padding:8px 10px;
    border-left:2px solid var(--acc); margin-bottom:10px;
}}
.card-footer {{ display:flex; justify-content:space-between; align-items:center; }}
.card-pos {{ font-family:'JetBrains Mono',monospace; font-size:18px; font-weight:700; }}
.auto-yes {{
    background:rgba(0,255,136,0.1); border:1px solid rgba(0,255,136,0.3);
    color:{GREEN}; font-size:9px; font-weight:800; letter-spacing:1px;
    padding:4px 9px; border-radius:4px; display:inline-block;
}}
.auto-no {{
    background:rgba(0,0,0,0.2); border:1px solid rgba(0,180,255,0.1);
    color:{TEXT2}; font-size:9px; font-weight:600;
    padding:4px 9px; border-radius:4px; display:inline-block;
}}

/* ── Open positions ── */
.pos-row {{
    background:{SURF}; border:1px solid rgba(0,180,255,0.1); border-radius:8px;
    padding:12px 16px; margin-bottom:8px;
    display:grid; grid-template-columns:70px 70px 1fr 1fr 1fr 1fr;
    align-items:center; gap:10px;
    transition:border-color 0.15s;
}}
.pos-row:hover {{ border-color:rgba(0,180,255,0.3); }}
.pos-ticker {{ font-family:'JetBrains Mono',monospace; font-size:15px; font-weight:700; color:{GLOW}; }}
.pos-badge-l {{ background:rgba(0,255,136,0.1); border:1px solid rgba(0,255,136,0.3); color:{GREEN}; font-size:9px; font-weight:800; letter-spacing:1px; padding:2px 7px; border-radius:3px; }}
.pos-badge-s {{ background:rgba(255,45,120,0.1); border:1px solid rgba(255,45,120,0.3); color:{RED}; font-size:9px; font-weight:800; letter-spacing:1px; padding:2px 7px; border-radius:3px; }}
.pos-col {{ display:flex; flex-direction:column; gap:2px; }}
.pos-lbl {{ font-size:9px; font-weight:700; letter-spacing:1px; text-transform:uppercase; color:{TEXT3}; }}
.pos-val {{ font-family:'JetBrains Mono',monospace; font-size:13px; font-weight:600; color:{TEXT}; }}

/* ── Activity log ── */
.log-item {{ padding:8px 0; border-bottom:1px solid rgba(0,180,255,0.06); display:flex; gap:12px; align-items:flex-start; }}
.log-item:last-child {{ border-bottom:none; }}
.log-time {{ font-family:'JetBrains Mono',monospace; font-size:10px; color:{TEXT3}; white-space:nowrap; margin-top:1px; width:40px; flex-shrink:0; }}
.log-text {{ font-size:11px; color:{TEXT2}; line-height:1.4; }}
.log-dot {{ width:6px; height:6px; border-radius:50%; flex-shrink:0; margin-top:4px; }}

/* ── No data ── */
.waiting {{ padding:50px 20px; text-align:center; }}
.wait-ring {{ width:70px; height:70px; border:2px solid rgba(0,180,255,0.1); border-top:2px solid {GLOW}; border-radius:50%; animation:spin 1.4s linear infinite; margin:0 auto 16px; }}
@keyframes spin {{ to {{ transform:rotate(360deg); }} }}
@keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0.25}} }}

div[data-testid="stSelectbox"] div {{ background:{SURF} !important; border-color:rgba(0,180,255,0.2) !important; color:{TEXT} !important; }}

/* ── Trade history table ── */
.hist-row {{
    display:grid; grid-template-columns:90px 80px 60px 90px 100px 1fr;
    align-items:center; gap:10px;
    padding:10px 16px; border-bottom:1px solid rgba(0,180,255,0.05);
    transition:background 0.1s;
}}
.hist-row:hover {{ background:rgba(0,180,255,0.03); }}
.hist-row:last-child {{ border-bottom:none; }}
.hist-hdr {{ display:grid; grid-template-columns:90px 80px 60px 90px 100px 1fr; gap:10px; padding:8px 16px; background:rgba(0,180,255,0.04); border-radius:6px 6px 0 0; }}
.hist-lbl {{ font-size:9px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:{TEXT3}; }}
.stButton > button {{
    background:rgba(0,180,255,0.08) !important; color:{GLOW} !important;
    border:1px solid rgba(0,180,255,0.25) !important; border-radius:6px !important;
    font-size:12px !important; font-weight:600 !important; padding:6px 18px !important;
    transition:all 0.15s !important;
}}
.stButton > button:hover {{ background:rgba(0,180,255,0.18) !important; border-color:rgba(0,180,255,0.5) !important; }}
</style>
""", unsafe_allow_html=True)

# ── DATA ──────────────────────────────────────────────────────────────────────
picks_df  = None
last_scan = ""
acct      = {"portfolio_value": 0, "buying_power": 0, "cash": 0}
positions = []
trades    = []
alpaca_ok = False
is_live   = False
db_ok     = False

try:
    from db import load_predictions_for_date, load_trades, db_available
    db_ok = db_available()
    if db_ok:
        rows = load_predictions_for_date(datetime.today().strftime("%Y-%m-%d"))
        if rows:
            picks_df = pd.DataFrame(rows)
            if "created_at" in picks_df.columns:
                ts = pd.to_datetime(picks_df["created_at"].iloc[0])
                last_scan = ts.strftime("%H:%M")
        try:
            trades = load_trades()[:10]
        except Exception:
            trades = []
except Exception:
    pass

try:
    from execution.alpaca import get_account, get_positions, is_configured, is_live_mode
    alpaca_ok = is_configured()
    is_live   = is_live_mode()
    if alpaca_ok:
        acct      = get_account()
        positions = get_positions()
except Exception:
    pass

n_picks = len(picks_df) if picks_df is not None and not picks_df.empty else 0
n_auto  = int((picks_df["score"] >= 70).sum()) if picks_df is not None and not picks_df.empty and "score" in picks_df.columns else 0
portfolio    = acct.get("portfolio_value", 0)
buying_power = acct.get("buying_power", 0)
cash         = acct.get("cash", 0)
total_pl     = sum(p.get("unrealized_pl", 0) for p in positions)
pl_color     = GREEN if total_pl >= 0 else RED

# ── HELPERS ───────────────────────────────────────────────────────────────────
def stars(score):
    f = round(score / 20)
    return "★" * f + "☆" * (5 - f)

def plain_reason(row):
    sigs   = row.get("signals_triggered", [])
    direct = row.get("direction","mixed")
    vol    = float(row.get("volume_ratio", 0) or 0)
    rsi    = float(row.get("rsi", 50) or 50)
    score  = float(row.get("score", 0))
    if isinstance(sigs, str): sigs = [s.strip() for s in sigs.split(";") if s.strip()]
    parts  = []
    if vol >= 1.5:  parts.append(f"volume is {vol:.1f}× above average")
    if rsi < 35:    parts.append(f"RSI at {rsi:.0f} — oversold, potential bounce")
    elif rsi > 65:  parts.append(f"RSI at {rsi:.0f} — overbought, potential reversal")
    if any("BB" in s or "squeeze" in s.lower() for s in sigs):
        parts.append("Bollinger Band squeeze — low volatility breakout incoming")
    if score >= 70: parts.append(f"AI model has high confidence ({score:.0f}/100) in this setup")
    elif score >= 50: parts.append(f"AI model sees a moderate edge ({score:.0f}/100)")
    if not parts: parts.append(f"Multiple technical signals align for a {direct} move")
    return ". ".join(p.capitalize() for p in parts[:3]) + "."

def tooltip_content(row):
    score  = float(row.get("score", 0))
    rsi    = float(row.get("rsi", 0) or 0)
    vol    = float(row.get("volume_ratio", 0) or 0)
    bb     = float(row.get("bb_pct", 0) or 0)
    sent   = float(row.get("sentiment_score", 0) or 0)
    xgb    = float(row.get("xgb_prob", 0) or 0)
    dur    = row.get("duration", "—")
    sigs   = row.get("signals_triggered", [])
    if isinstance(sigs, str): sigs = [s.strip() for s in sigs.split(";") if s.strip()]
    lines = [
        f"<b style='color:#00d4ff;'>Technical Details</b>",
        f"Score: {score:.0f}/100",
        f"RSI: {rsi:.1f}",
        f"Volume ratio: {vol:.1f}×",
        f"BB squeeze: {bb:.2f}",
        f"Sentiment: {sent:+.3f}",
        f"XGBoost prob: {xgb:.0%}" if xgb else "",
        f"Window: {dur}",
        f"<br><b style='color:#00d4ff;'>Signals triggered:</b>",
    ] + [f"• {s}" for s in sigs[:4]]
    return "<br>".join(l for l in lines if l)

def ring(score, acc, sz=62):
    r = sz//2 - 7; cx = cy = sz//2
    circ = 2*math.pi*r; off = circ*(1-score/100)
    c = GREEN if score>=70 else AMBER if score>=50 else TEXT2
    fs = max(11, sz//5)
    return (
        f'<svg width="{sz}" height="{sz}" viewBox="0 0 {sz} {sz}">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="rgba(0,180,255,0.08)" stroke-width="5"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c}" stroke-width="5"'
        f' stroke-dasharray="{circ:.1f}" stroke-dashoffset="{off:.1f}"'
        f' stroke-linecap="round" transform="rotate(-90 {cx} {cy})"'
        f' style="filter:drop-shadow(0 0 5px {c});"/>'
        f'<text x="{cx}" y="{cy+fs//3}" text-anchor="middle" fill="{c}"'
        f' font-size="{fs}" font-weight="700" font-family="JetBrains Mono,monospace">{score:.0f}</text>'
        f'</svg>'
    )

# ── HEADER ROW ────────────────────────────────────────────────────────────────
hc1, hc2 = st.columns([4, 1])
with hc1:
    mode_badge = (
        f'<span style="background:rgba(255,45,120,0.15);border:1px solid rgba(255,45,120,0.4);color:{RED};font-size:9px;font-weight:800;letter-spacing:2px;padding:2px 8px;border-radius:3px;">🔴 LIVE TRADING</span>'
        if (alpaca_ok and is_live) else
        f'<span style="background:rgba(255,170,0,0.1);border:1px solid rgba(255,170,0,0.3);color:{AMBER};font-size:9px;font-weight:800;letter-spacing:2px;padding:2px 8px;border-radius:3px;">PAPER MODE</span>'
        if alpaca_ok else
        f'<span style="background:rgba(0,0,0,0.2);border:1px solid {TEXT3};color:{TEXT3};font-size:9px;font-weight:800;letter-spacing:2px;padding:2px 8px;border-radius:3px;">ALPACA OFF</span>'
    )
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">'
        f'<span style="font-size:18px;font-weight:700;color:{TEXT};">⚡ Market Intelligence Dashboard</span>'
        f'<span class="live-pill"><span class="live-dot"></span>LIVE</span>'
        f'{mode_badge}'
        f'<span style="font-size:11px;color:{TEXT3};">Last scan: {last_scan if last_scan else "pending"} &nbsp;·&nbsp; {datetime.today().strftime("%b %d %Y")}</span>'
        f'</div>',
        unsafe_allow_html=True)

with hc2:
    if st.button("⟳  Refresh Dashboard", use_container_width=True):
        st.rerun()

# ── METRIC STRIP ──────────────────────────────────────────────────────────────
def mc(label, val, sub, color=TEXT3, tip=""):
    tip_html = f'<div class="tip">{tip}</div>' if tip else ""
    return (
        f'<div class="metric-card tt" style="--mc:{color}44;">'
        f'<div class="metric-lbl">{label}</div>'
        f'<div class="metric-val" style="color:{color};">{val}</div>'
        f'<div class="metric-sub">{sub}</div>'
        f'{tip_html}'
        f'</div>'
    )

pl_sign = "+" if total_pl >= 0 else ""
st.markdown(
    f'<div class="metrics-row">'
    + mc("Portfolio Value",   f"${portfolio:,.0f}",     "Total equity",
         GLOW,
         "Your total Alpaca account value including all open positions and cash.")
    + mc("Unrealized P&L",   f"{pl_sign}${total_pl:,.2f}", f"{len(positions)} positions",
         pl_color if total_pl != 0 else TEXT2,
         f"Total profit/loss on your {len(positions)} currently open position(s). Not yet realized — closes when you exit the trade.")
    + mc("Buying Power",     f"${buying_power:,.0f}",   "Available to trade",
         TEXT,
         "Cash available to open new positions right now in Alpaca.")
    + mc("AI Setups Today",  str(n_picks) if n_picks else "—", "Flagged by agent",
         GREEN if n_picks else TEXT2,
         f"Tickers flagged by the AI agent today with score ≥ 50. The agent scans S&P 500 + Futures at 8 AM ET every weekday.")
    + mc("Auto-Executing",   str(n_auto) if n_auto else "0",  "Score ≥ 70",
         GREEN if n_auto else TEXT2,
         f"Setups with score ≥ 70 are automatically traded by Alpaca at market open. Score must be high enough to overcome spread + fees.")
    + mc("DB / Agent",       "Online" if db_ok else "Offline", "Supabase",
         GREEN if db_ok else RED,
         "Supabase database connection status. Predictions are stored here by the GitHub Actions agent.")
    + f'</div>',
    unsafe_allow_html=True)

# ── MAIN CONTENT ──────────────────────────────────────────────────────────────
left, right = st.columns([3, 1], gap="large")

with right:
    # ── Agent status ──────────────────────────────────────────────────────────
    st.markdown(f'<div class="sec">Agent Status</div>', unsafe_allow_html=True)
    status_items = [
        (GREEN if last_scan else TEXT3, "Scan", f"Last run {last_scan}" if last_scan else "No scan today yet"),
        (GREEN if db_ok else RED,       "DB",   "Supabase connected" if db_ok else "Database offline"),
        (GREEN if alpaca_ok else RED,   "Alpaca", "API connected" if alpaca_ok else "Not configured"),
        (AMBER, "Next scans", "8AM · 11:30AM · 3PM ET weekdays"),
    ]
    items_html = ""
    for color, label, val in status_items:
        items_html += (
            f'<div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid rgba(0,180,255,0.06);">'
            f'<div style="width:7px;height:7px;border-radius:50%;background:{color};box-shadow:0 0 6px {color};flex-shrink:0;"></div>'
            f'<div>'
            f'<div style="font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:{TEXT3};">{label}</div>'
            f'<div style="font-size:12px;color:{TEXT};font-family:JetBrains Mono,monospace;">{val}</div>'
            f'</div></div>'
        )
    st.markdown(f'<div style="background:{SURF};border:1px solid rgba(0,180,255,0.1);border-radius:8px;padding:12px 14px;">{items_html}</div>', unsafe_allow_html=True)

    # ── Recent trade log ──────────────────────────────────────────────────────
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    st.markdown(f'<div class="sec">Recent Trades</div>', unsafe_allow_html=True)
    if trades:
        log_html = ""
        for t in trades[:8]:
            side  = t.get("side","")
            c     = GREEN if side=="buy" else RED
            ts    = str(t.get("timestamp",""))[:16]
            amt   = float(t.get("dollar_amount", 0))
            log_html += (
                f'<div class="log-item">'
                f'<div class="log-dot" style="background:{c};box-shadow:0 0 5px {c};"></div>'
                f'<div class="log-time">{ts[11:16]}</div>'
                f'<div class="log-text">'
                f'<span style="color:{c};font-weight:700;font-family:JetBrains Mono,monospace;">{t.get("ticker","")}</span>'
                f' {side.upper()} ${amt:,.0f}'
                f'<div style="color:{TEXT3};font-size:10px;">{str(t.get("reason",""))[:60]}</div>'
                f'</div></div>'
            )
        st.markdown(f'<div style="background:{SURF};border:1px solid rgba(0,180,255,0.1);border-radius:8px;padding:12px 14px;max-height:320px;overflow-y:auto;">{log_html}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="background:{SURF};border:1px solid rgba(0,180,255,0.1);border-radius:8px;padding:20px 14px;text-align:center;"><div style="color:{TEXT3};font-size:12px;">No trades executed yet.<br>Trades appear here after auto-execution.</div></div>', unsafe_allow_html=True)

with left:
    st.markdown(
        f'<div class="sec">Today\'s Trade Recommendations <span class="sec-n">{n_picks} setups</span></div>',
        unsafe_allow_html=True)

    if picks_df is not None and not picks_df.empty:
        sorted_df = picks_df.sort_values("score", ascending=False)
        chunks = [sorted_df.iloc[i:i+3] for i in range(0, len(sorted_df), 3)]
        for chunk in chunks:
            cols = st.columns(3)
            for ci, (_, row) in enumerate(chunk.iterrows()):
                ticker = row.get("ticker","")
                score  = float(row.get("score",0))
                direct = row.get("direction","mixed")
                dur    = row.get("duration","—")
                kelly  = float(row.get("dollar_amount",0) or 0)
                auto   = score >= 70 and alpaca_ok

                if direct == "bullish":
                    acc, ab, abrd, alabel = GREEN, "rgba(0,255,136,0.12)", "rgba(0,255,136,0.35)", "BUY LONG"
                elif direct == "bearish":
                    acc, ab, abrd, alabel = RED,   "rgba(255,45,120,0.12)", "rgba(255,45,120,0.35)", "SELL SHORT"
                else:
                    acc, ab, abrd, alabel = AMBER, "rgba(255,170,0,0.10)",  "rgba(255,170,0,0.30)",  "WATCH"

                tip  = tooltip_content(row)
                rea  = plain_reason(row)
                ks   = f"${kelly:,.0f}" if kelly else "—"

                card = f"""
<div class="trade-card tt" style="--acc:{acc};--acc2:{acc}33;">
  <div class="tip">{tip}</div>
  <span class="c c-tl"></span><span class="c c-tr"></span>
  <span class="c c-bl"></span><span class="c c-br"></span>
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">
    <div>
      <div class="card-ticker" style="color:{acc};text-shadow:0 0 18px {acc}44;">{ticker}</div>
      <div class="card-action" style="background:{ab};border:1px solid {abrd};color:{acc};">{alabel}</div>
      <div style="font-size:10px;color:{TEXT2};margin-top:4px;">{dur}</div>
    </div>
    {ring(score, acc)}
  </div>
  <div class="card-div"></div>
  <div class="stars" style="color:{acc};">{stars(score)}</div>
  <div class="card-reason">{rea}</div>
  <div class="card-footer">
    <div>
      <div style="font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:{TEXT3};margin-bottom:2px;">Position Size</div>
      <div class="card-pos" style="color:{acc};">{ks}</div>
    </div>
    {"<span class='auto-yes'>⚡ AUTO-EXECUTING</span>" if auto else "<span class='auto-no'>Manual only (score &lt; 70)</span>"}
  </div>
</div>"""
                with cols[ci]:
                    st.markdown(card, unsafe_allow_html=True)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="waiting">
          <div class="wait-ring"></div>
          <div style="font-size:15px;font-weight:600;color:{TEXT};margin-bottom:6px;">Waiting for today's scan</div>
          <div style="font-size:12px;color:{TEXT2};line-height:1.8;">
            The AI agent runs automatically every weekday at <strong style="color:{GLOW};">8:00 AM ET</strong> via GitHub Actions.<br>
            Hit <strong style="color:{TEXT};">⟳ Refresh Dashboard</strong> to check for new results.
          </div>
        </div>""", unsafe_allow_html=True)

# ── OPEN POSITIONS ────────────────────────────────────────────────────────────
st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
st.markdown(
    f'<div class="sec">Open Positions <span class="sec-n">{len(positions)}</span></div>',
    unsafe_allow_html=True)

if positions:
    for p in positions:
        pl    = p.get("unrealized_pl", 0)
        plpct = p.get("unrealized_pl_pct", 0)
        pc    = GREEN if pl >= 0 else RED
        arrow = "▲" if pl >= 0 else "▼"
        side  = str(p.get("side","long")).upper()
        badge = "pos-badge-l" if side=="LONG" else "pos-badge-s"
        st.markdown(f"""
<div class="pos-row">
  <div class="pos-ticker">{p['ticker']}</div>
  <div><span class="{badge}">{side}</span></div>
  <div class="pos-col">
    <span class="pos-lbl">Shares</span>
    <span class="pos-val">{p['qty']:.0f}</span>
  </div>
  <div class="pos-col">
    <span class="pos-lbl">Market Value</span>
    <span class="pos-val">${p['market_value']:,.2f}</span>
  </div>
  <div class="pos-col">
    <span class="pos-lbl">Unrealized P&amp;L</span>
    <span class="pos-val" style="color:{pc};">{arrow} ${abs(pl):,.2f}</span>
  </div>
  <div class="pos-col">
    <span class="pos-lbl">Return</span>
    <span class="pos-val" style="color:{pc};">{arrow} {abs(plpct):.2f}%</span>
  </div>
</div>""", unsafe_allow_html=True)
elif alpaca_ok:
    st.markdown(f'<div style="color:{TEXT3};font-size:13px;padding:14px 0;">No open positions. Trades will appear here after auto-execution.</div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div style="color:{TEXT3};font-size:13px;padding:14px 0;">Alpaca not connected — configure API keys to see live positions.</div>', unsafe_allow_html=True)

# ── CHART ─────────────────────────────────────────────────────────────────────
if picks_df is not None and not picks_df.empty:
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    st.markdown(f'<div class="sec">Price Chart &amp; Bollinger Bands</div>', unsafe_allow_html=True)
    sorted_df = picks_df.sort_values("score", ascending=False)
    sel = st.selectbox("Select ticker to chart", sorted_df["ticker"].tolist(), label_visibility="collapsed")
    if sel:
        try:
            from data.fetcher import get_ohlcv
            from ta.volatility import BollingerBands as BB
            df_c = get_ohlcv(sel, period="6mo")
            if not df_c.empty:
                _bb = BB(df_c["Close"], window=20, window_dev=2)
                fig = go.Figure()
                try:
                    fig.add_trace(go.Scatter(x=df_c.index, y=_bb.bollinger_hband(),
                        line=dict(color="rgba(0,212,255,0.2)", width=1), showlegend=False, name="BB Upper"))
                    fig.add_trace(go.Scatter(x=df_c.index, y=_bb.bollinger_lband(),
                        line=dict(color="rgba(0,212,255,0.2)", width=1),
                        fill="tonexty", fillcolor="rgba(0,212,255,0.04)", showlegend=False, name="BB Lower"))
                except Exception:
                    pass
                row_d  = sorted_df[sorted_df["ticker"]==sel].iloc[0]
                direct = row_d.get("direction","mixed")
                acc2   = GREEN if direct=="bullish" else RED if direct=="bearish" else AMBER
                fig.add_trace(go.Candlestick(
                    x=df_c.index, open=df_c["Open"], high=df_c["High"],
                    low=df_c["Low"], close=df_c["Close"], name=sel,
                    increasing=dict(line=dict(color=GREEN, width=1.2), fillcolor="rgba(0,255,136,0.2)"),
                    decreasing=dict(line=dict(color=RED,   width=1.2), fillcolor="rgba(255,45,120,0.2)")))
                fig.update_layout(
                    xaxis_rangeslider_visible=False, height=360,
                    paper_bgcolor=SURF, plot_bgcolor=SURF,
                    xaxis=dict(gridcolor="rgba(0,180,255,0.06)", tickfont=dict(color=TEXT2, size=10)),
                    yaxis=dict(gridcolor="rgba(0,180,255,0.06)", tickfont=dict(color=TEXT2, size=10), side="right"),
                    margin=dict(l=0, r=52, t=28, b=0),
                    title=dict(
                        text=f"<b style='color:{acc2}'>{sel}</b>"
                             f"<span style='color:{TEXT2};font-size:12px;'>  ·  6-Month  ·  Bollinger Bands  ·  Score {float(row_d.get('score',0)):.0f}/100</span>",
                        font=dict(color=TEXT, size=13), x=0.01))
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.markdown(f'<div style="color:{TEXT2};padding:20px;text-align:center;font-size:12px;">Chart unavailable: {e}</div>', unsafe_allow_html=True)

# ── TRADE HISTORY ──────────────────────────────────────────────────────────────
st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
st.markdown(
    f'<div class="sec">Full Trade History <span class="sec-n">{len(trades)} records</span></div>',
    unsafe_allow_html=True)

if trades:
    hdr = (f'<div class="hist-hdr">'
           f'<span class="hist-lbl">Time</span>'
           f'<span class="hist-lbl">Ticker</span>'
           f'<span class="hist-lbl">Side</span>'
           f'<span class="hist-lbl">Amount</span>'
           f'<span class="hist-lbl">Mode</span>'
           f'<span class="hist-lbl">Reason</span>'
           f'</div>')
    rows_html = ""
    for t in trades:
        side  = t.get("side","")
        c     = GREEN if side=="buy" else RED
        ts    = str(t.get("timestamp",""))[:16].replace("T"," ")
        amt   = float(t.get("dollar_amount",0))
        mode  = t.get("mode","PAPER")
        mc    = RED if mode=="LIVE" else AMBER
        reason= str(t.get("reason","—"))[:80]
        rows_html += (
            f'<div class="hist-row">'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;color:{TEXT2};">{ts}</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:14px;font-weight:700;color:{GLOW};">{t.get("ticker","")}</span>'
            f'<span style="background:{"rgba(0,255,136,0.1)" if side=="buy" else "rgba(255,45,120,0.1)"};'
            f'border:1px solid {"rgba(0,255,136,0.3)" if side=="buy" else "rgba(255,45,120,0.3)"};'
            f'color:{c};font-size:9px;font-weight:800;letter-spacing:1px;padding:2px 7px;border-radius:3px;">'
            f'{side.upper()}</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:13px;font-weight:700;color:{c};">${amt:,.0f}</span>'
            f'<span style="font-size:10px;font-weight:700;color:{mc};">{mode}</span>'
            f'<span style="font-size:11px;color:{TEXT2};">{reason}</span>'
            f'</div>'
        )
    st.markdown(
        f'<div style="background:{SURF};border:1px solid rgba(0,180,255,0.1);border-radius:8px;overflow:hidden;">'
        f'{hdr}{rows_html}</div>',
        unsafe_allow_html=True)
else:
    st.markdown(
        f'<div style="background:{SURF};border:1px solid rgba(0,180,255,0.1);border-radius:8px;'
        f'padding:24px;text-align:center;color:{TEXT3};font-size:12px;">'
        f'No trade history yet. Auto-executed trades will appear here.</div>',
        unsafe_allow_html=True)

# ── Smart tooltip positioning ──────────────────────────────────────────────────
st.markdown("""
<script>
document.querySelectorAll('.tt').forEach(el => {
    el.addEventListener('mouseenter', function(e) {
        const tip = this.querySelector('.tip');
        if (!tip) return;
        const r = this.getBoundingClientRect();
        const tw = 260, th = 200;
        let left = r.left + r.width / 2 - tw / 2;
        let top  = r.bottom + 8;
        if (left < 8) left = 8;
        if (left + tw > window.innerWidth - 8) left = window.innerWidth - tw - 8;
        if (top + th > window.innerHeight - 8) top = r.top - th - 8;
        tip.style.left = left + 'px';
        tip.style.top  = top  + 'px';
    });
});
</script>
""", unsafe_allow_html=True)
