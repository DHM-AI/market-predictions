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
*, body, html, [class*="css"] {{
    font-family: 'Inter', sans-serif !important;
    -webkit-font-smoothing: antialiased;
}}
.stApp {{
    background: {BG} !important;
    background-image:
        linear-gradient(rgba(0,180,255,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,180,255,0.025) 1px, transparent 1px),
        radial-gradient(ellipse at 50% 0%, rgba(0,80,180,0.10) 0%, transparent 60%) !important;
    background-size: 48px 48px, 48px 48px, 100% 100% !important;
}}
/* Hide everything Streamlit */
header[data-testid="stHeader"] {{ display:none !important; }}
.stAppHeader {{ display:none !important; }}
#stDecoration {{ display:none !important; }}
section[data-testid="stSidebar"] {{ display:none !important; }}
[data-testid="collapsedControl"] {{ display:none !important; }}
.block-container {{ padding: 20px 28px !important; max-width: 100% !important; }}
div[data-testid="stSelectbox"] div {{ background:{SURF} !important; border-color:rgba(0,180,255,0.15) !important; color:{TEXT} !important; }}
hr {{ border-color: rgba(0,180,255,0.08) !important; margin: 18px 0 !important; }}

/* ── Portfolio bar ── */
.port-bar {{
    display:flex; align-items:center; justify-content:space-between;
    background:rgba(7,17,31,0.95); border:1px solid rgba(0,180,255,0.12);
    border-radius:8px; padding:10px 20px; margin-bottom:20px;
}}
.port-item {{ display:flex; flex-direction:column; gap:2px; }}
.port-label {{ font-size:9px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:{TEXT3}; }}
.port-value {{ font-family:'JetBrains Mono',monospace; font-size:18px; font-weight:700; color:{TEXT}; }}
.port-sub   {{ font-size:10px; color:{TEXT2}; }}
.divider-v  {{ width:1px; height:36px; background:rgba(0,180,255,0.1); }}

/* ── Section header ── */
.sec-hdr {{
    font-size:9px; font-weight:700; letter-spacing:3px; text-transform:uppercase; color:{TEXT3};
    display:flex; align-items:center; gap:12px; margin-bottom:14px; margin-top:4px;
}}
.sec-hdr::after {{ content:''; flex:1; height:1px; background:linear-gradient(90deg, rgba(0,180,255,0.15), transparent); }}
.sec-badge {{
    font-family:'JetBrains Mono',monospace; font-size:11px; color:{TEXT2};
    background:rgba(0,180,255,0.06); border:1px solid rgba(0,180,255,0.12);
    padding:1px 8px; border-radius:20px;
}}

/* ── Trade recommendation card ── */
.trade-card {{
    position:relative; padding:18px;
    background:linear-gradient(135deg, rgba(10,26,44,0.97) 0%, rgba(5,12,22,0.97) 100%);
    border-radius:8px; overflow:hidden;
}}
.trade-card::before {{
    content:''; position:absolute; top:0; left:0; right:0; height:2px;
    background:linear-gradient(90deg, transparent, var(--acc), transparent); opacity:0.7;
}}
.c {{ position:absolute; width:11px; height:11px; }}
.c-tl {{ top:0; left:0; border-top:2px solid var(--acc); border-left:2px solid var(--acc); border-radius:2px 0 0 0; }}
.c-tr {{ top:0; right:0; border-top:2px solid var(--acc); border-right:2px solid var(--acc); border-radius:0 2px 0 0; }}
.c-bl {{ bottom:0; left:0; border-bottom:2px solid var(--acc); border-left:2px solid var(--acc); border-radius:0 0 0 2px; }}
.c-br {{ bottom:0; right:0; border-bottom:2px solid var(--acc); border-right:2px solid var(--acc); border-radius:0 0 2px 0; }}
.card-top {{ display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px; }}
.card-ticker {{ font-family:'JetBrains Mono',monospace; font-size:24px; font-weight:700; line-height:1; }}
.card-action {{
    font-size:11px; font-weight:800; letter-spacing:2px;
    padding:5px 12px; border-radius:4px; margin-top:6px; display:inline-block;
}}
.card-window {{ font-size:11px; color:{TEXT2}; margin-top:4px; }}
.card-divider {{ height:1px; background:rgba(0,180,255,0.08); margin:12px 0; }}
.stars {{ font-size:16px; letter-spacing:2px; margin-bottom:6px; }}
.card-reason {{
    font-size:12px; color:{TEXT}; line-height:1.5;
    background:rgba(0,0,0,0.2); border-radius:4px; padding:8px 10px;
    border-left:2px solid var(--acc); margin-bottom:12px;
}}
.card-row {{ display:flex; justify-content:space-between; align-items:center; }}
.card-position {{
    font-family:'JetBrains Mono',monospace; font-size:20px; font-weight:700;
}}
.auto-yes {{
    display:inline-flex; align-items:center; gap:5px;
    background:rgba(0,255,136,0.1); border:1px solid rgba(0,255,136,0.3);
    color:{GREEN}; font-size:10px; font-weight:700; letter-spacing:1px;
    padding:4px 10px; border-radius:4px;
}}
.auto-no {{
    display:inline-flex; align-items:center; gap:5px;
    background:rgba(0,0,0,0.2); border:1px solid rgba(0,180,255,0.1);
    color:{TEXT2}; font-size:10px; font-weight:600;
    padding:4px 10px; border-radius:4px;
}}

/* ── Open position row ── */
.pos-card {{
    background:{SURF}; border:1px solid rgba(0,180,255,0.1); border-radius:8px;
    padding:14px 18px; margin-bottom:8px;
    display:grid; grid-template-columns:80px 80px 1fr 1fr 1fr 1fr;
    align-items:center; gap:12px;
}}
.pos-ticker {{ font-family:'JetBrains Mono',monospace; font-size:16px; font-weight:700; }}
.pos-side-long  {{ background:rgba(0,255,136,0.1); border:1px solid rgba(0,255,136,0.3); color:{GREEN}; font-size:9px; font-weight:800; letter-spacing:1px; padding:2px 8px; border-radius:3px; }}
.pos-side-short {{ background:rgba(255,45,120,0.1); border:1px solid rgba(255,45,120,0.3); color:{RED};   font-size:9px; font-weight:800; letter-spacing:1px; padding:2px 8px; border-radius:3px; }}
.pos-col {{ display:flex; flex-direction:column; gap:2px; }}
.pos-lbl {{ font-size:9px; font-weight:600; letter-spacing:1px; text-transform:uppercase; color:{TEXT3}; }}
.pos-val {{ font-family:'JetBrains Mono',monospace; font-size:14px; font-weight:600; color:{TEXT}; }}

/* ── No data ── */
.waiting {{
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    padding:60px 20px; text-align:center; gap:14px;
}}
.wait-ring {{
    width:80px; height:80px;
    border:2px solid rgba(0,180,255,0.1); border-top:2px solid {GLOW};
    border-radius:50%; animation:spin 1.4s linear infinite;
}}
@keyframes spin {{ to {{ transform:rotate(360deg); }} }}
@keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0.25}} }}
</style>
""", unsafe_allow_html=True)

# ── DATA ──────────────────────────────────────────────────────────────────────
picks_df   = None
last_scan  = ""
acct       = {}
positions  = []
alpaca_ok  = False
is_live    = False

try:
    from db import load_predictions_for_date, db_available
    if db_available():
        rows = load_predictions_for_date(datetime.today().strftime("%Y-%m-%d"))
        if rows:
            picks_df = pd.DataFrame(rows)
            if "created_at" in picks_df.columns:
                ts = pd.to_datetime(picks_df["created_at"].iloc[0])
                last_scan = ts.strftime("%H:%M")
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

# ── PORTFOLIO BAR ─────────────────────────────────────────────────────────────
portfolio   = acct.get("portfolio_value", 0)
buying_power= acct.get("buying_power", 0)
mode_label  = ("🔴 LIVE" if is_live else "PAPER") if alpaca_ok else "NOT CONNECTED"
mode_color  = RED if is_live else AMBER if alpaca_ok else TEXT3

agent_dot   = GREEN if last_scan else TEXT3

st.markdown(f"""
<div class="port-bar">
  <div style="display:flex;align-items:center;gap:28px;">
    <div class="port-item">
      <span class="port-label">Portfolio</span>
      <span class="port-value">${portfolio:,.2f}</span>
      <span class="port-sub">Total equity</span>
    </div>
    <div class="divider-v"></div>
    <div class="port-item">
      <span class="port-label">Buying Power</span>
      <span class="port-value">${buying_power:,.2f}</span>
      <span class="port-sub">Available</span>
    </div>
    <div class="divider-v"></div>
    <div class="port-item">
      <span class="port-label">Open Positions</span>
      <span class="port-value" style="color:{GREEN if positions else TEXT2};">{len(positions)}</span>
      <span class="port-sub">Active trades</span>
    </div>
    <div class="divider-v"></div>
    <div class="port-item">
      <span class="port-label">Alpaca</span>
      <span class="port-value" style="font-size:14px;color:{mode_color};">{mode_label}</span>
      <span class="port-sub">Trading mode</span>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:16px;">
    <div style="display:flex;align-items:center;gap:7px;">
      <div style="width:7px;height:7px;border-radius:50%;background:{agent_dot};animation:blink 2s infinite;box-shadow:0 0 6px {agent_dot};"></div>
      <span style="font-size:11px;color:{TEXT2};">Last scan {last_scan if last_scan else 'pending'}</span>
    </div>
    <span style="font-size:11px;color:{TEXT3};">{datetime.today().strftime('%b %d %Y')}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────────────────────────
def stars(score):
    filled = round(score / 20)
    return "★" * filled + "☆" * (5 - filled)

def plain_reason(row):
    sigs = row.get("signals_triggered", [])
    if isinstance(sigs, str):
        sigs = [s.strip() for s in sigs.split(";") if s.strip()]
    direct = row.get("direction", "mixed")
    conf   = row.get("confidence", "Low")
    vol    = row.get("volume_ratio", 0) or 0
    rsi    = row.get("rsi", 50) or 50
    score  = float(row.get("score", 0))
    parts  = []
    if vol and float(vol) >= 1.5:
        parts.append(f"volume is {float(vol):.1f}× above average")
    if rsi and float(rsi) < 35:
        parts.append(f"RSI at {float(rsi):.0f} — oversold territory")
    elif rsi and float(rsi) > 65:
        parts.append(f"RSI at {float(rsi):.0f} — overbought territory")
    if "BB" in str(sigs) or "bb" in str(sigs):
        parts.append("Bollinger Band squeeze detected")
    if score >= 70 and direct == "bullish":
        parts.append("XGBoost model strongly favors upside")
    elif score >= 70 and direct == "bearish":
        parts.append("XGBoost model strongly favors downside")
    if not parts:
        parts.append(f"Multiple signals align for a {direct} setup")
    return ". ".join(p.capitalize() for p in parts[:3]) + "."

def score_ring_svg(score, accent, size=64):
    r    = size // 2 - 7
    cx   = cy = size // 2
    circ = 2 * math.pi * r
    off  = circ * (1 - score / 100)
    c    = GREEN if score >= 70 else AMBER if score >= 50 else TEXT2
    fs   = max(11, size // 5)
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="rgba(0,180,255,0.08)" stroke-width="5"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c}" stroke-width="5"'
        f' stroke-dasharray="{circ:.1f}" stroke-dashoffset="{off:.1f}"'
        f' stroke-linecap="round" transform="rotate(-90 {cx} {cy})"'
        f' style="filter:drop-shadow(0 0 5px {c});"/>'
        f'<text x="{cx}" y="{cy + fs//3}" text-anchor="middle" fill="{c}"'
        f' font-size="{fs}" font-weight="700" font-family="JetBrains Mono,monospace">{score:.0f}</text>'
        f'</svg>'
    )

# ── TODAY'S TRADE RECOMMENDATIONS ────────────────────────────────────────────
st.markdown(
    f'<div class="sec-hdr">Today\'s Trade Recommendations'
    f'<span class="sec-badge">{n_picks} found</span></div>',
    unsafe_allow_html=True)

if picks_df is not None and not picks_df.empty:
    sorted_df = picks_df.sort_values("score", ascending=False)
    chunks = [sorted_df.iloc[i:i+3] for i in range(0, len(sorted_df), 3)]
    for chunk in chunks:
        cols = st.columns(3)
        for ci, (_, row) in enumerate(chunk.iterrows()):
            ticker = row.get("ticker", "")
            score  = float(row.get("score", 0))
            direct = row.get("direction", "mixed")
            dur    = row.get("duration", "—")
            kelly  = row.get("dollar_amount", 0) or 0
            auto   = score >= 70 and alpaca_ok

            if direct == "bullish":
                acc   = GREEN
                action_label = "BUY LONG"
                action_bg    = "rgba(0,255,136,0.12)"
                action_border= "rgba(0,255,136,0.35)"
            elif direct == "bearish":
                acc   = RED
                action_label = "SELL SHORT"
                action_bg    = "rgba(255,45,120,0.12)"
                action_border= "rgba(255,45,120,0.35)"
            else:
                acc   = AMBER
                action_label = "WATCH"
                action_bg    = "rgba(255,170,0,0.10)"
                action_border= "rgba(255,170,0,0.30)"

            reason = plain_reason(row)
            ring   = score_ring_svg(score, acc)
            ks     = f"${kelly:,.0f}" if kelly else "—"
            star_html = f'<div class="stars" style="color:{acc};">{stars(score)}</div>'
            auto_html = (
                f'<span class="auto-yes">⚡ AUTO-EXECUTING</span>'
                if auto else
                f'<span class="auto-no">Manual — score &lt; 70</span>'
            )

            card = f"""
<div class="trade-card" style="--acc:{acc};border:1px solid {acc}22;">
  <span class="c c-tl"></span><span class="c c-tr"></span>
  <span class="c c-bl"></span><span class="c c-br"></span>
  <div class="card-top">
    <div>
      <div class="card-ticker" style="color:{acc};text-shadow:0 0 18px {acc}55;">{ticker}</div>
      <div class="card-action" style="background:{action_bg};border:1px solid {action_border};color:{acc};">{action_label}</div>
      <div class="card-window">{dur}</div>
    </div>
    {ring}
  </div>
  <div class="card-divider"></div>
  {star_html}
  <div class="card-reason">{reason}</div>
  <div class="card-row">
    <div>
      <div style="font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:{TEXT3};margin-bottom:3px;">Position Size</div>
      <div class="card-position" style="color:{acc};">{ks}</div>
    </div>
    {auto_html}
  </div>
</div>"""
            with cols[ci]:
                st.markdown(card, unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="waiting">
      <div class="wait-ring"></div>
      <div style="font-size:16px;font-weight:600;color:{TEXT};">Waiting for today's scan</div>
      <div style="font-size:13px;color:{TEXT2};line-height:1.8;">
        The AI agent runs automatically every weekday at <strong style="color:{GLOW};">8:00 AM ET</strong>.<br>
        Results appear here automatically. First run was triggered today — check back shortly.
      </div>
    </div>""", unsafe_allow_html=True)

# ── OPEN POSITIONS ────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    f'<div class="sec-hdr">Open Positions'
    f'<span class="sec-badge">{len(positions)}</span></div>',
    unsafe_allow_html=True)

if positions:
    total_pl = sum(p.get("unrealized_pl", 0) for p in positions)
    total_color = GREEN if total_pl >= 0 else RED
    st.markdown(
        f'<div style="font-family:JetBrains Mono,monospace;font-size:13px;'
        f'color:{total_color};margin-bottom:12px;">'
        f'Total unrealized P&amp;L: {"+" if total_pl >= 0 else ""}{total_pl:,.2f}</div>',
        unsafe_allow_html=True)
    for p in positions:
        pl     = p.get("unrealized_pl", 0)
        pl_pct = p.get("unrealized_pl_pct", 0)
        pc     = GREEN if pl >= 0 else RED
        arrow  = "▲" if pl >= 0 else "▼"
        side   = str(p.get("side", "long")).upper()
        side_cls = "pos-side-long" if side == "LONG" else "pos-side-short"
        st.markdown(f"""
<div class="pos-card">
  <div class="pos-ticker" style="color:{GLOW};">{p['ticker']}</div>
  <div><span class="{side_cls}">{side}</span></div>
  <div class="pos-col"><span class="pos-lbl">Qty</span><span class="pos-val">{p['qty']:.0f}</span></div>
  <div class="pos-col"><span class="pos-lbl">Market Value</span><span class="pos-val">${p['market_value']:,.2f}</span></div>
  <div class="pos-col">
    <span class="pos-lbl">P&amp;L</span>
    <span class="pos-val" style="color:{pc};">{arrow} ${abs(pl):,.2f}</span>
  </div>
  <div class="pos-col">
    <span class="pos-lbl">Return</span>
    <span class="pos-val" style="color:{pc};">{arrow} {abs(pl_pct):.2f}%</span>
  </div>
</div>""", unsafe_allow_html=True)
elif alpaca_ok:
    st.markdown(
        f'<div style="color:{TEXT3};font-size:13px;padding:16px 0;">No open positions right now.</div>',
        unsafe_allow_html=True)
else:
    st.markdown(
        f'<div style="color:{TEXT3};font-size:13px;padding:16px 0;">Alpaca not connected — add API keys to see positions.</div>',
        unsafe_allow_html=True)

# ── CHART ─────────────────────────────────────────────────────────────────────
if picks_df is not None and not picks_df.empty:
    st.divider()
    st.markdown(f'<div class="sec-hdr">Price Chart</div>', unsafe_allow_html=True)
    sorted_df = picks_df.sort_values("score", ascending=False)
    sel = st.selectbox("", sorted_df["ticker"].tolist(), label_visibility="collapsed")
    if sel:
        try:
            from data.fetcher import get_ohlcv
            from ta.volatility import BollingerBands as BB
            df_c = get_ohlcv(sel, period="6mo")
            if not df_c.empty:
                _bb  = BB(df_c["Close"], window=20, window_dev=2)
                fig  = go.Figure()
                try:
                    fig.add_trace(go.Scatter(x=df_c.index, y=_bb.bollinger_hband(),
                        line=dict(color=f"rgba(0,212,255,0.2)", width=1), showlegend=False))
                    fig.add_trace(go.Scatter(x=df_c.index, y=_bb.bollinger_lband(),
                        line=dict(color=f"rgba(0,212,255,0.2)", width=1),
                        fill="tonexty", fillcolor="rgba(0,212,255,0.04)", showlegend=False))
                except Exception:
                    pass
                fig.add_trace(go.Candlestick(
                    x=df_c.index, open=df_c["Open"], high=df_c["High"],
                    low=df_c["Low"], close=df_c["Close"], name=sel,
                    increasing=dict(line=dict(color=GREEN, width=1.2), fillcolor="rgba(0,255,136,0.2)"),
                    decreasing=dict(line=dict(color=RED,   width=1.2), fillcolor="rgba(255,45,120,0.2)")))
                row_d  = sorted_df[sorted_df["ticker"] == sel].iloc[0]
                direct = row_d.get("direction","mixed")
                acc2   = GREEN if direct == "bullish" else RED if direct == "bearish" else AMBER
                fig.update_layout(
                    xaxis_rangeslider_visible=False, height=360,
                    paper_bgcolor=SURF, plot_bgcolor=SURF,
                    xaxis=dict(gridcolor="rgba(0,180,255,0.06)", tickfont=dict(color=TEXT2, size=10)),
                    yaxis=dict(gridcolor="rgba(0,180,255,0.06)", tickfont=dict(color=TEXT2, size=10), side="right"),
                    margin=dict(l=0, r=52, t=28, b=0),
                    title=dict(
                        text=f"<b style='color:{acc2}'>{sel}</b>"
                             f"<span style='color:{TEXT2};font-size:12px;'>  ·  6-Month  ·  Bollinger Bands</span>",
                        font=dict(color=TEXT, size=13), x=0.01))
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.markdown(f'<div style="color:{TEXT2};padding:20px;text-align:center;font-size:12px;">Chart unavailable: {e}</div>', unsafe_allow_html=True)
