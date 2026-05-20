import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from ui_style import (inject_css, section_header, page_title,
                      score_chip, direction_html, signal_tags, status_bar)

st.set_page_config(page_title="MKTPRED | SCAN", page_icon="📡", layout="wide")
inject_css()

page_title("AI Market Scanner", "S&P 500 + Futures · 5-Agent Pipeline · 5-10% Move Detection")
st.markdown('<p style="color:#555;font-size:10px;letter-spacing:1px;margin-top:2px;">S&P 500 + FUTURES  ·  5-AGENT PIPELINE  ·  5-10% MOVE DETECTION</p>', unsafe_allow_html=True)

# ── Run button ─────────────────────────────────────────────────────────────────
c_btn, c_model, c_time = st.columns([1, 2, 1])
with c_btn:
    run_clicked = st.button("▶  RUN SCAN", type="primary", use_container_width=True)
with c_model:
    from model.predictor import model_available
    dot   = "●" if model_available() else "○"
    color = "#00ff88" if model_available() else "#555"
    label = "XGBOOST MODEL LOADED" if model_available() else "NO MODEL — RULE-BASED FALLBACK"
    st.markdown(f'<span style="color:{color};font-size:10px;letter-spacing:1px;">{dot} {label}</span>', unsafe_allow_html=True)
with c_time:
    st.markdown(f'<span style="color:#333;font-size:10px;float:right;">{datetime.now().strftime("%H:%M:%S")}</span>', unsafe_allow_html=True)

st.markdown("<hr/>", unsafe_allow_html=True)

# ══ SESSION STATE ══════════════════════════════════════════════════════════════
for k, v in [("pipeline_counts", {}), ("last_picks", None),
             ("ticker_tape", []), ("scan_time", "")]:
    if k not in st.session_state:
        st.session_state[k] = v

# ══ TWO-COLUMN LAYOUT ══════════════════════════════════════════════════════════
left_col, right_col = st.columns([1, 2], gap="small")

# ── LEFT: Ticker tape ──────────────────────────────────────────────────────────
with left_col:
    section_header("ACTIVE UNIVERSE", "SORTED BY MOVE")
    tape_ph = st.empty()

    def render_tape(data: list):
        if not data:
            tape_ph.markdown(
                '<div style="color:#222;padding:30px 10px;font-size:10px;'
                'letter-spacing:1px;">NO DATA — RUN SCAN</div>',
                unsafe_allow_html=True
            )
            return
        rows = ""
        for t in data[:45]:
            chg  = t.get("chg_pct", 0)
            cls  = "tape-up" if chg >= 0 else "tape-dn"
            sign = "+" if chg >= 0 else ""
            px   = f'${t["price"]:>8,.2f}' if t.get("price") else "      —"
            rows += (f'<div class="tape-row">'
                     f'<span class="tape-sym">{t["ticker"]:<6}</span>'
                     f'<span class="tape-price">{px}</span>'
                     f'<span class="{cls}">{sign}{chg:.1f}%</span>'
                     f'</div>')
        tape_ph.markdown(
            f'<div style="border:1px solid #1a1a1a;overflow-y:auto;max-height:580px;">{rows}</div>',
            unsafe_allow_html=True
        )

    render_tape(st.session_state["ticker_tape"])

# ── RIGHT: Pipeline panel ──────────────────────────────────────────────────────
with right_col:
    agent_ph    = st.empty()
    pipeline_ph = st.empty()
    qual_ph     = st.empty()

    def render_agent(title, sub, count, running=False):
        dot_color = "#00ff88" if running else ("#00ff88" if count != "—" else "#222")
        pulse_css = "animation:pulse 0.8s infinite;" if running else ""
        agent_ph.markdown(f"""
        <div style="border:1px solid #1a1a1a;border-top:2px solid #00ff88;
             background:#000;padding:12px 14px;display:flex;
             justify-content:space-between;align-items:center;margin-bottom:8px;">
          <div>
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="display:inline-block;width:8px;height:8px;border-radius:50%;
                background:{dot_color};{pulse_css}"></span>
              <span style="color:#00ff88;font-size:11px;font-weight:700;letter-spacing:1px;">{title}</span>
            </div>
            <div style="color:#444;font-size:10px;margin-top:3px;margin-left:16px;">{sub}</div>
          </div>
          <div style="font-size:28px;font-weight:700;color:#00ff88;letter-spacing:1px;">{count}</div>
        </div>
        """, unsafe_allow_html=True)

    def render_pipeline(counts: dict, n: int = 509):
        steps = [
            ("1",  "SCAN",     "FETCH OHLCV · YFINANCE",                 counts.get("universe", n),    n,  True),
            ("2",  "RESEARCH", "REDDIT · RSS · ALPHA VANTAGE · YFINANCE", counts.get("research", None), n,  "research" in counts),
            ("3",  "PREDICT",  "XGBOOST + BLENDED SENTIMENT",             counts.get("scored", None),   n,  "scored" in counts),
            ("4",  "RISK",     "KELLY CRITERION · $50K BANKROLL",         counts.get("risk", None),     n,  "risk" in counts),
            ("5",  "LEARN",    "BACKFILL ACTUALS · POST-MORTEM LOOP",     counts.get("learn", None),    n,  "learn" in counts),
        ]
        html = '<div style="border:1px solid #1a1a1a;">'
        html += ('<div style="background:#0a0a0a;padding:5px 10px;'
                 'color:#555;font-size:9px;letter-spacing:2px;'
                 'border-bottom:1px solid #1a1a1a;">FILTER PIPELINE</div>')
        for num, label, sub, cnt, total, done in steps:
            dot_cls = "pip-dot-ok" if done else "pip-dot-off"
            num_cls = "pip-num-ok" if done else "pip-num-off"
            cnt_str = str(cnt) if cnt is not None else "—"
            bar_pct = int((cnt / total) * 100) if (cnt and total) else 0
            html += f"""
            <div class="pip-row">
              <div class="{dot_cls}"></div>
              <div style="flex:1;">
                <div style="color:#ccc;font-size:10px;letter-spacing:0.5px;">
                  <span style="color:#00ff88;">{num}</span> · {label}
                </div>
                <div style="color:#333;font-size:9px;">{sub}</div>
              </div>
              <div class="pip-bar">
                <div class="pip-bar-fill" style="width:{bar_pct}%;"></div>
              </div>
              <div class="{num_cls}">{cnt_str}</div>
            </div>"""
        html += "</div>"
        pipeline_ph.markdown(html, unsafe_allow_html=True)

    def render_qualified(n: int):
        if n > 0:
            qual_ph.markdown(f"""
            <div style="border:1px solid #00ff88;border-top:2px solid #00ff88;
                 background:#0a1f14;padding:14px 16px;
                 display:flex;justify-content:space-between;align-items:center;margin-top:8px;">
              <div>
                <div style="color:#555;font-size:9px;letter-spacing:2px;">QUALIFIED SETUPS</div>
                <div style="color:#00ff88;font-size:10px;margin-top:2px;letter-spacing:1px;">SCORE ≥ 50 · MOVE TARGET 5%+</div>
              </div>
              <div style="font-size:36px;font-weight:700;color:#00ff88;letter-spacing:2px;">
                {n} <span style="font-size:14px;letter-spacing:3px;">FOUND</span>
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            qual_ph.markdown("""
            <div style="border:1px solid #1a1a1a;padding:14px 16px;
                 display:flex;justify-content:space-between;align-items:center;margin-top:8px;">
              <div style="color:#222;font-size:9px;letter-spacing:2px;">QUALIFIED SETUPS</div>
              <div style="color:#222;font-size:24px;font-weight:700;">— NONE</div>
            </div>""", unsafe_allow_html=True)

    # Initial render
    picks_df  = st.session_state["last_picks"]
    counts    = st.session_state["pipeline_counts"]
    scan_time = st.session_state["scan_time"]
    n_picks   = len(picks_df) if picks_df is not None and not picks_df.empty else 0

    render_agent("MARKET SCAN AGENT",
                 f"LAST SCAN: {scan_time}" if scan_time else "READY · PRESS F8 TO START",
                 str(n_picks) if n_picks else "—", running=False)
    render_pipeline(counts)
    render_qualified(n_picks)


# ══ RUN SCAN ════════════════════════════════════════════════════════════════════
if run_clicked:
    import time as _time
    from data.universe import get_universe
    from data.fetcher import get_ohlcv_batch, get_earnings_days
    from data.research import research_universe
    from signals.sentiment import get_sentiment_with_velocity
    from signals.kelly import annotate_picks
    from model.predictor import predict_universe
    import db

    tickers = get_universe()
    N = len(tickers)

    # Stage 1 ─────────────────────────────────────────────────────
    render_agent("1 · SCAN AGENT", f"FETCHING OHLCV FOR {N} TICKERS...", str(N), running=True)
    render_pipeline({})
    render_qualified(0)
    with st.spinner(""):
        ohlcv_map = get_ohlcv_batch(tickers, period="1y", chunk_size=50)

    # Build ticker tape from biggest movers
    tape = []
    for t, df in ohlcv_map.items():
        if df.empty or len(df) < 2:
            continue
        price = float(df["Close"].iloc[-1])
        prev  = float(df["Close"].iloc[-2])
        tape.append({"ticker": t, "price": price, "chg_pct": (price - prev) / prev * 100})
    tape.sort(key=lambda x: abs(x["chg_pct"]), reverse=True)
    st.session_state["ticker_tape"] = tape
    render_tape(tape)

    # Stage 2 ─────────────────────────────────────────────────────
    render_agent("2 · RESEARCH AGENT", "REDDIT · RSS · ALPHA VANTAGE · YFINANCE", str(N), running=True)
    render_pipeline({"universe": N})
    with st.spinner(""):
        blended = research_universe(tickers)
        sentiment_map = {}
        for t in tickers:
            cached   = get_sentiment_with_velocity(t)
            bl       = blended.get(t, {})
            combined = cached.get("score", 0) * 0.4 + bl.get("score", 0) * 0.6
            sentiment_map[t] = {**bl, "score": round(combined, 4),
                                 "velocity": cached.get("velocity", 0),
                                 "spike": abs(cached.get("velocity", 0)) >= 0.3 or bl.get("score", 0) > 0.4}

    # Stage 3 ─────────────────────────────────────────────────────
    render_agent("3 · PREDICT AGENT", "XGBOOST + BLENDED SENTIMENT → PROBABILITY", str(N), running=True)
    render_pipeline({"universe": N, "research": N})
    with st.spinner(""):
        earnings_map = {t: get_earnings_days(t) for t in tickers[:100]}
        picks_df     = predict_universe(tickers, ohlcv_map, sentiment_map, earnings_map)
    scored = len(picks_df) if picks_df is not None and not picks_df.empty else 0

    # Stage 4 ─────────────────────────────────────────────────────
    render_agent("4 · RISK AGENT", "KELLY CRITERION · $50K BANKROLL", str(scored), running=True)
    render_pipeline({"universe": N, "research": N, "scored": scored})
    if picks_df is not None and not picks_df.empty:
        picks_df = annotate_picks(picks_df)

    # Stage 5 ─────────────────────────────────────────────────────
    render_agent("5 · LEARN AGENT", "BACKFILLING ACTUALS · PERSISTING TO SUPABASE", str(scored), running=True)
    render_pipeline({"universe": N, "research": N, "scored": scored, "risk": scored})
    with st.spinner(""):
        if picks_df is not None and not picks_df.empty and db.db_available():
            rows = picks_df.copy()
            rows["date"] = datetime.today().strftime("%Y-%m-%d")
            rows["actual_move_5d"] = None
            db.append_predictions(rows.to_dict(orient="records"))

    # Done ────────────────────────────────────────────────────────
    scan_time = datetime.now().strftime("%H:%M:%S")
    st.session_state.update({
        "last_picks": picks_df, "scan_time": scan_time,
        "pipeline_counts": {"universe": N, "research": N,
                            "scored": scored, "risk": scored, "learn": scored}
    })
    final_counts = st.session_state["pipeline_counts"]
    render_agent("MARKET SCAN AGENT", f"COMPLETED · {scan_time}", str(scored), running=False)
    render_pipeline(final_counts)
    render_qualified(scored)


# ══ LOAD FROM DB IF NO SESSION SCAN ════════════════════════════════════════════
if picks_df is None:
    try:
        from db import load_predictions_for_date, db_available
        if db_available():
            rows = load_predictions_for_date(datetime.today().strftime("%Y-%m-%d"))
            if rows:
                picks_df = pd.DataFrame(rows)
                render_qualified(len(picks_df))
    except Exception:
        pass


# ══ RESULTS TABLE ═══════════════════════════════════════════════════════════════
if picks_df is not None and not picks_df.empty:
    st.markdown("<hr/>", unsafe_allow_html=True)
    section_header("QUALIFIED SETUPS", f"{len(picks_df)} RESULTS · SORTED BY SCORE")

    rows_html = ""
    for _, row in picks_df.iterrows():
        ticker  = row.get("ticker", "")
        score   = row.get("score", 0)
        direct  = row.get("direction", "mixed")
        dur     = row.get("duration", "—")
        conf    = row.get("confidence", "—")
        rsi     = row.get("rsi", "—")
        vol     = row.get("volume_ratio", "—")
        kelly   = row.get("dollar_amount", 0)
        risk_lv = row.get("risk_level", "—")
        sigs    = row.get("signals_triggered", [])
        if isinstance(sigs, str):
            sigs = [s.strip() for s in sigs.split(";") if s.strip()]

        conf_color  = {"High": "#00ff88", "Medium": "#F0B82A", "Low": "#333"}.get(conf, "#333")
        risk_color  = {"aggressive": "#FF3333", "moderate": "#F0B82A",
                       "conservative": "#00ff88", "skip": "#333"}.get(risk_lv, "#555")
        kelly_str   = f"${kelly:,.0f}" if kelly else "—"
        rsi_str     = f"{rsi:.1f}" if isinstance(rsi, float) else str(rsi)
        vol_str     = f"{vol:.1f}x" if isinstance(vol, float) else str(vol)
        sig_html    = signal_tags(sigs[:3])

        rows_html += f"""
        <tr>
          <td style="color:#00ff88;font-weight:700;font-size:13px;padding:9px 10px;">{ticker}</td>
          <td style="padding:9px 10px;">{score_chip(score)}</td>
          <td style="padding:9px 10px;">{direction_html(direct)}</td>
          <td style="color:#555;font-size:10px;padding:9px 10px;">{dur}</td>
          <td style="color:{conf_color};font-size:10px;font-weight:700;padding:9px 10px;">{conf.upper()}</td>
          <td style="color:#888;padding:9px 10px;">{rsi_str}</td>
          <td style="color:#888;padding:9px 10px;">{vol_str}</td>
          <td style="color:#00ff88;font-weight:700;padding:9px 10px;">{kelly_str}</td>
          <td style="color:{risk_color};font-size:10px;font-weight:700;padding:9px 10px;">{risk_lv.upper()}</td>
          <td style="padding:9px 10px;">{sig_html}</td>
        </tr>"""

    hdrs = ["TICKER", "SCORE", "SIGNAL", "WINDOW", "CONF", "RSI", "VOL", "KELLY $", "RISK", "TRIGGERS"]
    th = "".join(f'<th>{h}</th>' for h in hdrs)

    st.markdown(f"""
    <div style="border:1px solid #1a1a1a;overflow-x:auto;">
    <table class="bbg-table"><thead><tr>{th}</tr></thead>
    <tbody>{rows_html}</tbody></table>
    </div>""", unsafe_allow_html=True)

    # ── Chart ──────────────────────────────────────────────────────────────────
    st.markdown("<hr/>", unsafe_allow_html=True)
    section_header("PRICE CHART", "6M CANDLESTICK + BB BANDS")

    selected = st.selectbox("", picks_df["ticker"].tolist(), label_visibility="collapsed")

    if selected:
        from data.fetcher import get_ohlcv
        from ta.volatility import BollingerBands as BB

        df = get_ohlcv(selected, period="6mo")
        if not df.empty:
            _bb = BB(df["Close"], window=20, window_dev=2)
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df.index, open=df["Open"], high=df["High"],
                low=df["Low"], close=df["Close"], name=selected,
                increasing=dict(line=dict(color="#00ff88"), fillcolor="#00280522"),
                decreasing=dict(line=dict(color="#FF3333"), fillcolor="#28000522"),
            ))
            try:
                _upper = _bb.bollinger_hband()
                _lower = _bb.bollinger_lband()
                u = [_upper]; l = [_lower]
            except Exception:
                u = []; l = []
            if u and l:
                fig.add_trace(go.Scatter(x=df.index, y=u[0],
                    line=dict(color="#00ff88", width=1, dash="dot"),
                    name="BB Upper", showlegend=False))
                fig.add_trace(go.Scatter(x=df.index, y=l[0],
                    line=dict(color="#00ff88", width=1, dash="dot"),
                    fill="tonexty", fillcolor="rgba(240,125,42,0.04)",
                    name="BB Lower", showlegend=False))

            fig.update_layout(
                xaxis_rangeslider_visible=False, height=360,
                paper_bgcolor="#000", plot_bgcolor="#000",
                xaxis=dict(gridcolor="#0a0a0a", showgrid=True,
                           tickfont=dict(color="#444", size=9, family="IBM Plex Mono"),
                           linecolor="#1a1a1a"),
                yaxis=dict(gridcolor="#0a0a0a", showgrid=True,
                           tickfont=dict(color="#444", size=9, family="IBM Plex Mono"),
                           linecolor="#1a1a1a"),
                margin=dict(l=0, r=0, t=20, b=0),
                title=dict(text=f"{selected}  ·  6M",
                           font=dict(color="#00ff88", size=11, family="IBM Plex Mono"), x=0.01),
            )
            st.plotly_chart(fig, use_container_width=True)

            row  = picks_df[picks_df["ticker"] == selected].iloc[0]
            sigs = row.get("signals_triggered", [])
            if isinstance(sigs, str):
                sigs = [s.strip() for s in sigs.split(";") if s.strip()]
            if sigs:
                st.markdown(signal_tags(sigs), unsafe_allow_html=True)

scan_time = st.session_state.get("scan_time", "")
status_bar(f"MKTPRED TERMINAL  ·  SCAN ENGINE v2.0  ·  "
           f"{'LAST UPDATE: ' + scan_time if scan_time else 'AWAITING SCAN'}  ·  "
           f"UNIVERSE: S&P 500 + FUTURES")
