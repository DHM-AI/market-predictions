"""
Ticker Deep Dive — full signal breakdown + chart + AI analysis for any symbol.
Matches the futuristic dark theme of the main Scanner dashboard.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.subplots as sp
import math

st.set_page_config(page_title="Ticker Dive", page_icon="🔍", layout="wide",
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
    font-size:13px !important; font-weight:600 !important; transition:all 0.15s !important;
}}
.stButton > button:hover {{ background:rgba(0,180,255,0.18) !important; }}
input[type="text"] {{
    background:{SURF} !important; border:1px solid rgba(0,180,255,0.2) !important;
    color:{TEXT} !important; border-radius:6px !important;
}}
.sec {{
    font-size:9px; font-weight:700; letter-spacing:3px; text-transform:uppercase; color:{TEXT3};
    display:flex; align-items:center; gap:10px; margin-bottom:12px;
}}
.sec::after {{ content:''; flex:1; height:1px; background:linear-gradient(90deg, rgba(0,180,255,0.15), transparent); }}
.kpi-grid {{ display:grid; grid-template-columns:repeat(5,1fr); gap:10px; margin-bottom:16px; }}
.kpi {{
    background:{SURF}; border:1px solid rgba(0,180,255,0.1); border-radius:8px;
    padding:14px 16px; position:relative; overflow:hidden;
}}
.kpi::before {{ content:''; position:absolute; top:0; left:0; right:0; height:2px; background:var(--kc,rgba(0,180,255,0.3)); }}
.kpi-lbl {{ font-size:9px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:{TEXT3}; margin-bottom:4px; }}
.kpi-val {{ font-family:'JetBrains Mono',monospace; font-size:24px; font-weight:700; color:{TEXT}; line-height:1.1; }}
.kpi-sub {{ font-size:10px; color:{TEXT2}; margin-top:3px; }}
.sig-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-bottom:16px; }}
@media(min-width:1200px) {{ .sig-grid {{ grid-template-columns:repeat(6,1fr); }} }}
.sig-card {{
    background:{SURF}; border:1px solid rgba(0,180,255,0.08);
    border-left:3px solid var(--sc, rgba(0,180,255,0.15));
    border-radius:8px; padding:14px; text-align:center;
}}
.sig-icon {{ font-size:18px; font-weight:700; margin-bottom:6px; }}
.sig-name {{ font-size:11px; font-weight:600; color:{TEXT}; margin-bottom:4px; }}
.sig-detail {{ font-size:10px; color:{TEXT3}; line-height:1.4; }}
.sig-pts {{ font-size:11px; font-weight:700; margin-top:6px; }}
.score-ring {{ display:flex; align-items:center; gap:20px; }}
.tag {{
    display:inline-block; font-size:11px; font-weight:600;
    padding:3px 10px; border-radius:4px; margin:3px;
    border:1px solid; letter-spacing:0.3px;
}}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">'
    f'<span style="font-size:18px;font-weight:700;color:{TEXT};">🔍 Ticker Deep Dive</span>'
    f'<span style="font-size:11px;color:{TEXT3};">Full signal breakdown · Chart · AI analysis</span>'
    f'</div>',
    unsafe_allow_html=True
)

col_in, col_btn = st.columns([4, 1])
with col_in:
    ticker_input = st.text_input("", placeholder="Enter symbol — AAPL, TSLA, NVDA, ES=F ...",
                                  label_visibility="collapsed")
with col_btn:
    analyze = st.button("Analyze →", type="primary", use_container_width=True)

if not ticker_input or not analyze:
    st.markdown(f"""
    <div style="text-align:center;padding:80px 0;">
      <div style="font-size:48px;margin-bottom:16px;opacity:0.3;">🔍</div>
      <div style="font-size:15px;font-weight:600;color:{TEXT2};margin-bottom:8px;">Enter a ticker above</div>
      <div style="font-size:12px;color:{TEXT3};">S&P 500 stocks · Futures (ES=F, NQ=F) · ETFs</div>
    </div>""", unsafe_allow_html=True)
    st.stop()

ticker = ticker_input.upper().strip()

with st.spinner(f"Analyzing {ticker}…"):
    from data.fetcher import get_ohlcv, get_earnings_days
    from signals.technicals import compute_all
    from signals.sentiment import get_sentiment_with_velocity
    from signals.scorer import score_ticker
    from signals.patterns import detect_patterns
    from signals.kelly import position_size
    from config import BANKROLL

    df         = get_ohlcv(ticker, period="1y")
    if df.empty:
        st.error(f"No price data found for **{ticker}**. Check the symbol and try again.")
        st.stop()

    sentiment  = get_sentiment_with_velocity(ticker)
    earnings   = get_earnings_days(ticker)
    technicals = compute_all(df)
    result     = score_ticker(ticker, df, sentiment, earnings)
    patterns   = detect_patterns(df)
    sizing     = position_size(win_prob=min(result.get("xgb_prob", result["score"] / 100), 0.99),
                               bankroll=BANKROLL)

# ── Score + KPI bar ───────────────────────────────────────────────────────────
score     = result.get("score", 0)
direction = result.get("direction", "mixed")
conf      = result.get("confidence", "—")
duration  = result.get("duration", "—")

sc_color  = GREEN if score >= 70 else AMBER if score >= 50 else TEXT2
dir_color = GREEN if direction == "bullish" else RED if direction == "bearish" else AMBER
conf_color= {"High": GREEN, "Medium": AMBER, "Low": TEXT3}.get(conf, TEXT3)

def ring(score, sz=72):
    r   = sz//2 - 7; cx = cy = sz//2
    circ= 2*math.pi*r; off = circ*(1-score/100)
    c   = GREEN if score >= 70 else AMBER if score >= 50 else TEXT2
    fs  = max(12, sz//5)
    return (
        f'<svg width="{sz}" height="{sz}" viewBox="0 0 {sz} {sz}">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="rgba(0,180,255,0.08)" stroke-width="5"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c}" stroke-width="5"'
        f' stroke-dasharray="{circ:.1f}" stroke-dashoffset="{off:.1f}"'
        f' stroke-linecap="round" transform="rotate(-90 {cx} {cy})"'
        f' style="filter:drop-shadow(0 0 6px {c});"/>'
        f'<text x="{cx}" y="{cy+fs//3}" text-anchor="middle" fill="{c}"'
        f' font-size="{fs}" font-weight="700" font-family="JetBrains Mono,monospace">{score:.0f}</text>'
        f'</svg>'
    )

rsi_val = technicals["rsi"]["value"] or 0
price_close = float(df["Close"].iloc[-1]) if not df.empty else 0
price_chg   = float((df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100) if len(df) >= 2 else 0
price_color = GREEN if price_chg >= 0 else RED

st.markdown(
    f'<div class="kpi-grid">'
    f'<div class="kpi" style="--kc:{sc_color}44;">'
    f'<div class="kpi-lbl">AI Score</div>'
    f'<div style="display:flex;align-items:center;gap:12px;">'
    f'{ring(score)}'
    f'<div><div class="kpi-val" style="color:{sc_color};">{score}</div>'
    f'<div class="kpi-sub">{conf} confidence</div></div>'
    f'</div></div>'
    f'<div class="kpi" style="--kc:{dir_color}44;">'
    f'<div class="kpi-lbl">Direction</div>'
    f'<div class="kpi-val" style="color:{dir_color};font-size:18px;margin-top:6px;">{"▲" if direction=="bullish" else "▼" if direction=="bearish" else "→"} {direction.upper()}</div>'
    f'<div class="kpi-sub">{duration}</div>'
    f'</div>'
    f'<div class="kpi" style="--kc:rgba(0,180,255,0.3);">'
    f'<div class="kpi-lbl">Last Price</div>'
    f'<div class="kpi-val">${price_close:,.2f}</div>'
    f'<div class="kpi-sub" style="color:{price_color};">{price_chg:+.2f}% today</div>'
    f'</div>'
    f'<div class="kpi" style="--kc:rgba(0,180,255,0.2);">'
    f'<div class="kpi-lbl">RSI (14)</div>'
    f'<div class="kpi-val" style="color:{"' + RED + '" if rsi_val > 70 else "' + GREEN + '" if rsi_val < 30 else TEXT};">{rsi_val:.1f}</div>'
    f'<div class="kpi-sub">{"Overbought" if rsi_val > 70 else "Oversold" if rsi_val < 30 else "Neutral"}</div>'
    f'</div>'
    f'<div class="kpi" style="--kc:rgba(0,255,136,0.2);">'
    f'<div class="kpi-lbl">Position Size</div>'
    f'<div class="kpi-val">${sizing["dollar_amount"]:,.0f}</div>'
    f'<div class="kpi-sub">{sizing["pct_of_bankroll"]:.1f}% bankroll · {sizing["risk_level"]}</div>'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True
)

# Signal tags
sigs = result.get("signals_triggered", [])
if isinstance(sigs, str):
    sigs = [s.strip() for s in sigs.split(";") if s.strip()]
if sigs:
    tags_html = "".join(
        f'<span class="tag" style="background:rgba(0,255,136,0.06);border-color:rgba(0,255,136,0.25);color:{GREEN};">{s}</span>'
        for s in sigs
    )
    if patterns.get("triggered"):
        tags_html += f'<span class="tag" style="background:rgba(0,212,255,0.06);border-color:rgba(0,212,255,0.25);color:{GLOW};">📊 {patterns["pattern"]}</span>'
    st.markdown(f'<div style="margin:4px 0 16px;">{tags_html}</div>', unsafe_allow_html=True)

# ── Signal breakdown ───────────────────────────────────────────────────────────
st.markdown('<div class="sec">Signal Breakdown</div>', unsafe_allow_html=True)

from config import WEIGHTS, EARNINGS_PROXIMITY_DAYS
breakdown = result.get("breakdown", {})

signals_data = [
    ("BB Squeeze",      technicals["bb"]["triggered"],
     f"Width pct: {technicals['bb']['width_percentile']}", "bb_squeeze"),
    ("ATR Compression", technicals["atr"]["triggered"],
     f"Ratio: {technicals['atr']['ratio']}", "atr_compression"),
    ("Volume Surge",    technicals["vol"]["triggered"],
     f"{technicals['vol']['ratio']}× avg", "volume_surge"),
    ("RSI Extreme",     technicals["rsi"]["extreme"],
     f"RSI {technicals['rsi']['value']:.1f} ({technicals['rsi']['side']})", "rsi_extreme"),
    ("Sentiment Spike", sentiment.get("spike", False),
     f"Score {sentiment.get('score',0):.3f} Δ{sentiment.get('velocity',0):+.3f}", "sentiment_spike"),
]
if earnings is not None:
    signals_data.append((
        "Earnings", 0 <= earnings <= EARNINGS_PROXIMITY_DAYS,
        f"{earnings}d away", "earnings_proximity"
    ))
if patterns.get("triggered"):
    signals_data.append((
        "Pattern", True,
        f"{patterns['pattern']} (str {patterns['strength']:.2f})", "candlestick"
    ))

sig_html = ""
for name, triggered, detail, key in signals_data:
    pts    = breakdown.get(key, WEIGHTS.get(key, 0) if triggered else 0)
    color  = GREEN if triggered else TEXT3
    border = f"rgba(0,255,136,0.5)" if triggered else "rgba(0,180,255,0.08)"
    icon   = "✓" if triggered else "○"
    sig_html += (
        f'<div class="sig-card" style="--sc:{border};">'
        f'<div class="sig-icon" style="color:{color};">{icon}</div>'
        f'<div class="sig-name">{name}</div>'
        f'<div class="sig-detail">{detail}</div>'
        f'<div class="sig-pts" style="color:{color};">+{pts} pts</div>'
        f'</div>'
    )

st.markdown(f'<div class="sig-grid">{sig_html}</div>', unsafe_allow_html=True)

# ── Chart ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="sec">Price Chart · RSI · ATR</div>', unsafe_allow_html=True)

try:
    from ta.volatility import BollingerBands as TaBB, AverageTrueRange as TaATR
    from ta.momentum import RSIIndicator as TaRSI
    rsi_s    = TaRSI(df["Close"], window=14).rsi()
    atr_s    = TaATR(df["High"], df["Low"], df["Close"], window=14).average_true_range()
    _bb      = TaBB(df["Close"], window=20, window_dev=2)
    bb_upper = _bb.bollinger_hband()
    bb_lower = _bb.bollinger_lband()
except Exception:
    from signals.technicals import _rsi_pandas, _atr_pandas, _bollinger_pandas
    rsi_s    = _rsi_pandas(df["Close"])
    atr_s    = _atr_pandas(df["High"], df["Low"], df["Close"])
    bb_upper = bb_lower = None

fig = sp.make_subplots(rows=3, cols=1, shared_xaxes=True,
                       row_heights=[0.55, 0.25, 0.20], vertical_spacing=0.02)

# Candlestick
fig.add_trace(go.Candlestick(
    x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
    name=ticker,
    increasing=dict(line=dict(color=GREEN, width=1), fillcolor="rgba(0,255,136,0.12)"),
    decreasing=dict(line=dict(color=RED,   width=1), fillcolor="rgba(255,45,120,0.12)"),
), row=1, col=1)

# BB bands
if bb_upper is not None:
    fig.add_trace(go.Scatter(x=df.index, y=bb_upper,
        line=dict(color="rgba(0,180,255,0.3)", width=1), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=bb_lower,
        line=dict(color="rgba(0,180,255,0.3)", width=1),
        fill="tonexty", fillcolor="rgba(0,180,255,0.03)", showlegend=False), row=1, col=1)

# 50 EMA
ema50 = df["Close"].ewm(span=50).mean()
fig.add_trace(go.Scatter(x=df.index, y=ema50,
    line=dict(color=AMBER, width=1, dash="dot"), name="EMA50"), row=1, col=1)

# RSI
if rsi_s is not None:
    fig.add_trace(go.Scatter(x=df.index, y=rsi_s,
        line=dict(color=GLOW, width=1.5), name="RSI", showlegend=False), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color=f"{RED}66", line_width=1, row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color=f"{GREEN}66", line_width=1, row=2, col=1)
    fig.add_hrect(y0=70, y1=100, fillcolor=f"{RED}08", line_width=0, row=2, col=1)
    fig.add_hrect(y0=0,  y1=30,  fillcolor=f"{GREEN}08", line_width=0, row=2, col=1)

# ATR
if atr_s is not None:
    fig.add_trace(go.Scatter(x=df.index, y=atr_s,
        line=dict(color=AMBER, width=1.5),
        fill="tozeroy", fillcolor="rgba(255,170,0,0.05)", name="ATR"), row=3, col=1)

gc = "rgba(0,180,255,0.06)"
fig.update_layout(
    height=560, template="plotly_dark",
    paper_bgcolor=SURF, plot_bgcolor=BG,
    xaxis_rangeslider_visible=False,
    margin=dict(l=0, r=0, t=8, b=0),
    legend=dict(x=0.01, y=0.99, font=dict(color=TEXT3, size=10)),
    yaxis=dict(gridcolor=gc, title="Price"),
    yaxis2=dict(gridcolor=gc, title="RSI", range=[0, 100]),
    yaxis3=dict(gridcolor=gc, title="ATR"),
    xaxis3=dict(gridcolor=gc),
)
st.plotly_chart(fig, use_container_width=True)

# ── AI Analysis ────────────────────────────────────────────────────────────────
st.markdown('<div class="sec">AI Analysis</div>', unsafe_allow_html=True)

if st.button("✦  Generate Claude Analysis", type="primary"):
    try:
        from analyst.claude_analyst import stream_explanation
        with st.container():
            st.markdown(
                f'<div style="background:{SURF};border:1px solid rgba(0,180,255,0.12);'
                f'border-radius:8px;padding:18px;margin-top:8px;color:{TEXT};">',
                unsafe_allow_html=True
            )
            st.write_stream(stream_explanation(result))
            st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Analysis unavailable: {e}")
