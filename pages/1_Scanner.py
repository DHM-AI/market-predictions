import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from ui_style import (
    inject_css, live_badge, signal_tags, score_chip, direction_html,
    BG, CARD, CARD2, BORDER, BORDER2, TEXT, TEXT2, TEXT3,
    GREEN, RED, AMBER, BLUE, CYAN,
)

st.set_page_config(page_title="AI Market Scanner", page_icon="⚡", layout="wide")
inject_css()

st.markdown(f"""
<style>
/* ── Header ──────────────────────────────────────────── */
.top-bar {{
    background:{CARD}; border:1px solid {BORDER}; border-radius:8px;
    padding:11px 18px; margin-bottom:16px;
    display:flex; justify-content:space-between; align-items:center;
}}
.top-title  {{ font-size:16px; font-weight:700; color:{TEXT}; display:flex; align-items:center; gap:8px; }}
.top-sub    {{ font-size:11px; color:{TEXT3}; margin-top:3px; }}

/* ── Stat strip ──────────────────────────────────────── */
.stat-strip {{
    display:grid; grid-template-columns:repeat(6,1fr); gap:10px; margin-bottom:16px;
}}
.stat-box {{
    background:{CARD}; border:1px solid {BORDER}; border-radius:8px;
    padding:12px 14px;
}}
.stat-label {{ font-size:9px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:{TEXT3}; }}
.stat-val   {{ font-family:'JetBrains Mono',monospace; font-size:22px; font-weight:700; color:{TEXT}; margin:4px 0 2px; line-height:1.1; }}
.stat-sub   {{ font-size:10px; color:{TEXT3}; }}

/* ── Agent card (right panel top) ───────────────────── */
.agent-box {{
    background:{CARD}; border:1px solid {BORDER}; border-radius:8px;
    padding:12px 16px; margin-bottom:10px;
    display:flex; justify-content:space-between; align-items:center;
}}
.agent-left  {{ display:flex; flex-direction:column; gap:3px; }}
.agent-name  {{ font-size:13px; font-weight:600; color:{TEXT}; display:flex; align-items:center; gap:8px; }}
.agent-sub   {{ font-size:11px; color:{TEXT3}; margin-left:15px; }}
.agent-count {{ font-family:'JetBrains Mono',monospace; font-size:26px; font-weight:700; }}

/* ── Pipeline ────────────────────────────────────────── */
.pipe-wrap {{
    background:{CARD}; border:1px solid {BORDER}; border-radius:8px;
    overflow:hidden; margin-bottom:10px;
}}
.pipe-top {{
    display:flex; justify-content:space-between; align-items:center;
    padding:8px 14px; background:{CARD2}; border-bottom:1px solid {BORDER};
}}
.pipe-lbl {{ font-size:9px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:{TEXT3}; }}
.pipe-row {{
    display:flex; align-items:center;
    padding:9px 14px; border-bottom:1px solid rgba(255,255,255,0.03); gap:9px;
}}
.pipe-row:last-child {{ border-bottom:none; }}
.dot-on  {{ width:7px;height:7px;border-radius:50%;background:{GREEN};flex-shrink:0;box-shadow:0 0 7px {GREEN}88; }}
.dot-off {{ width:7px;height:7px;border-radius:50%;background:transparent;border:1.5px solid {TEXT3};flex-shrink:0; }}
.pipe-name {{ font-size:12px;font-weight:600;color:{TEXT};width:72px;flex-shrink:0; }}
.pipe-desc {{ font-size:10px;color:{TEXT3};flex:1; }}
.pipe-bar  {{ width:52px;height:3px;background:{BORDER2};border-radius:2px;flex-shrink:0; }}
.pipe-fill {{ height:3px;background:{GREEN};border-radius:2px; }}
.pipe-num-on  {{ font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:700;color:{GREEN};min-width:30px;text-align:right; }}
.pipe-num-off {{ font-family:'JetBrains Mono',monospace;font-size:12px;color:{TEXT3};min-width:30px;text-align:right; }}

/* ── Ticker tape ─────────────────────────────────────── */
.tape-wrap {{
    background:{CARD}; border:1px solid {BORDER}; border-radius:8px; overflow:hidden;
}}
.tape-top {{
    display:flex; justify-content:space-between; align-items:center;
    padding:8px 14px; background:{CARD2}; border-bottom:1px solid {BORDER};
}}
.tape-row {{
    display:flex; align-items:center; padding:6px 14px;
    border-bottom:1px solid rgba(255,255,255,0.025);
}}
.tape-row:last-child {{ border-bottom:none; }}
.tape-row:hover {{ background:rgba(255,255,255,0.015); }}
.t-sym {{ font-family:'JetBrains Mono',monospace;font-weight:700;color:{GREEN};font-size:12px;width:54px; }}
.t-px  {{ font-family:'JetBrains Mono',monospace;font-size:11px;color:{TEXT3};flex:1;text-align:right;padding-right:8px; }}
.t-up  {{ font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600;color:{GREEN};min-width:44px;text-align:right; }}
.t-dn  {{ font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600;color:{RED};min-width:44px;text-align:right; }}

/* ── Picks table ─────────────────────────────────────── */
.picks-outer {{
    background:{CARD}; border:1px solid {BORDER}; border-radius:8px; overflow:hidden;
}}
.picks-top {{
    display:flex; justify-content:space-between; align-items:center;
    padding:8px 14px; background:{CARD2}; border-bottom:1px solid {BORDER};
}}
.picks-table {{ border-collapse:collapse; width:100%; }}
.picks-th {{
    padding:8px 12px; text-align:left;
    font-size:9px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:{TEXT3};
    background:{CARD2}; border-bottom:1px solid {BORDER}; white-space:nowrap;
}}
.picks-td {{ padding:10px 12px; border-bottom:1px solid rgba(255,255,255,0.03); vertical-align:middle; }}
.picks-tr:last-child td {{ border-bottom:none; }}
.picks-tr:hover td {{ background:rgba(255,255,255,0.02) !important; }}
.t-ticker {{ font-family:'JetBrains Mono',monospace;font-size:15px;font-weight:700;color:{GREEN}; }}
.t-conf-hi  {{ color:{GREEN};font-size:12px;font-weight:600; }}
.t-conf-med {{ color:{AMBER};font-size:12px;font-weight:600; }}
.t-conf-lo  {{ color:{TEXT3};font-size:12px;font-weight:600; }}
.t-mono {{ font-family:'JetBrains Mono',monospace;font-size:12px;color:{TEXT2}; }}
.t-kelly {{ font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:700;color:{GREEN}; }}

/* ── Empty state ─────────────────────────────────────── */
.empty {{ padding:52px 20px;text-align:center; }}
.empty-icon  {{ font-size:32px;opacity:0.35;margin-bottom:10px; }}
.empty-title {{ font-size:14px;font-weight:600;color:{TEXT2};margin-bottom:5px; }}
.empty-body  {{ font-size:12px;color:{TEXT3};line-height:1.6; }}

/* ── Qualified bar ───────────────────────────────────── */
.qual {{
    background:rgba(0,255,136,0.05); border:1px solid rgba(0,255,136,0.18);
    border-radius:8px; padding:12px 16px; margin-top:10px;
    display:flex; justify-content:space-between; align-items:center;
}}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [("pipeline_counts", {}), ("last_picks", None),
              ("ticker_tape", []), ("scan_time", "")]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Pre-load from Supabase ────────────────────────────────────────────────────
picks_df  = st.session_state["last_picks"]
counts    = st.session_state["pipeline_counts"]
scan_time = st.session_state["scan_time"]

if picks_df is None:
    try:
        from db import load_predictions_for_date, db_available
        if db_available():
            rows = load_predictions_for_date(datetime.today().strftime("%Y-%m-%d"))
            if rows:
                picks_df = pd.DataFrame(rows)
    except Exception:
        pass

n     = len(picks_df) if picks_df is not None and not picks_df.empty else 0
n_hi  = int((picks_df["score"] >= 70).sum())       if picks_df is not None and not picks_df.empty and "score"     in picks_df.columns else 0
n_b   = int((picks_df["direction"] == "bullish").sum()) if picks_df is not None and not picks_df.empty and "direction" in picks_df.columns else 0
n_s   = int((picks_df["direction"] == "bearish").sum()) if picks_df is not None and not picks_df.empty and "direction" in picks_df.columns else 0
univ  = counts.get("universe", 0)

# ── Header ────────────────────────────────────────────────────────────────────
hL, hR = st.columns([5, 1])
with hL:
    updated = f"Last scan {scan_time} · {datetime.today().strftime('%b %d %Y')}" if scan_time else f"Not yet scanned · {datetime.today().strftime('%b %d %Y')}"
    st.markdown(
        f'<div class="top-bar">'
        f'<div><div class="top-title">⚡ AI Market Scanner {live_badge()}</div>'
        f'<div class="top-sub">S&P 500 + Futures &nbsp;·&nbsp; 5-Agent Pipeline &nbsp;·&nbsp; 5–10% Move Detection &nbsp;·&nbsp; {updated}</div></div>'
        f'</div>', unsafe_allow_html=True)
with hR:
    run_clicked = st.button("▶  Run Scan", type="primary", use_container_width=True)

# ── Stat strip ────────────────────────────────────────────────────────────────
def stat(col, label, val, sub, accent=TEXT3):
    col.markdown(
        f'<div class="stat-box">'
        f'<div class="stat-label">{label}</div>'
        f'<div class="stat-val" style="color:{accent};">{val}</div>'
        f'<div class="stat-sub">{sub}</div>'
        f'</div>', unsafe_allow_html=True)

c1,c2,c3,c4,c5,c6 = st.columns(6)
stat(c1, "Universe",        f"{univ:,}" if univ else "—",     "S&P 500 + Futures",  TEXT3)
stat(c2, "Qualified",       str(n)    if n    else "—",        "Score ≥ 50",         GREEN if n    else TEXT3)
stat(c3, "High Conviction", str(n_hi) if n_hi else "—",       "Score ≥ 70",         GREEN if n_hi else TEXT3)
stat(c4, "Long",            str(n_b)  if n_b  else "—",       "Bullish setups",     GREEN if n_b  else TEXT3)
stat(c5, "Short",           str(n_s)  if n_s  else "—",       "Bearish setups",     RED   if n_s  else TEXT3)
stat(c6, "Scanned At",      scan_time if scan_time else "—",  datetime.today().strftime("%b %d"),  GREEN if scan_time else TEXT3)

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

left, right = st.columns([5, 2], gap="medium")

# ══════════════════════ RIGHT PANEL ══════════════════════
with right:
    agent_ph    = st.empty()
    pipeline_ph = st.empty()
    tape_ph     = st.empty()

    def render_agent(name, sub, count, state="idle"):
        c = GREEN if state in ("done","running") else TEXT3
        pulse = "animation:blink 0.8s infinite;" if state == "running" else ""
        agent_ph.markdown(
            f'<div class="agent-box">'
            f'<div class="agent-left">'
            f'<div class="agent-name">'
            f'<span style="width:7px;height:7px;border-radius:50%;background:{c};display:inline-block;{pulse}"></span>'
            f'{name}</div>'
            f'<div class="agent-sub">{sub}</div>'
            f'</div>'
            f'<div class="agent-count" style="color:{c};">{count}</div>'
            f'</div>', unsafe_allow_html=True)

    def render_pipeline(counts, N=509):
        steps = [
            ("Scan",     "OHLCV · yfinance",       counts.get("universe")),
            ("Research", "Reddit · RSS · news",     counts.get("research")),
            ("Predict",  "XGBoost + sentiment",     counts.get("scored")),
            ("Risk",     "Kelly · $50k bankroll",   counts.get("risk")),
            ("Learn",    "Backfill · analysis",     counts.get("learn")),
        ]
        n_done = sum(1 for _, _, c in steps if c is not None)
        done_c = GREEN if n_done == 5 else (AMBER if n_done > 0 else TEXT3)
        rows = ""
        for name, desc, cnt in steps:
            done = cnt is not None
            dot  = "dot-on" if done else "dot-off"
            ncls = "pipe-num-on" if done else "pipe-num-off"
            cs   = str(cnt) if done else "—"
            bw   = int((cnt / N) * 100) if (done and N) else 0
            rows += (
                f'<div class="pipe-row">'
                f'<div class="{dot}"></div>'
                f'<div class="pipe-name">{name}</div>'
                f'<div class="pipe-desc">{desc}</div>'
                f'<div class="pipe-bar"><div class="pipe-fill" style="width:{bw}%;"></div></div>'
                f'<div class="{ncls}">{cs}</div>'
                f'</div>')
        pipeline_ph.markdown(
            f'<div class="pipe-wrap">'
            f'<div class="pipe-top"><span class="pipe-lbl">Filter Pipeline</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;color:{done_c};">{n_done}/5</span></div>'
            f'{rows}</div>', unsafe_allow_html=True)

    def render_tape(data):
        if not data:
            tape_ph.markdown(
                f'<div class="tape-wrap">'
                f'<div class="tape-top"><span class="pipe-lbl">Universe</span><span style="font-family:JetBrains Mono,monospace;font-size:11px;color:{TEXT3};">—</span></div>'
                f'<div class="empty" style="padding:28px 14px;">'
                f'<div class="empty-icon">📡</div>'
                f'<div class="empty-body">Populates after scan</div>'
                f'</div></div>', unsafe_allow_html=True)
            return
        rows = ""
        for t in data[:30]:
            chg  = t.get("chg_pct", 0)
            cls  = "t-up" if chg >= 0 else "t-dn"
            sign = "+" if chg >= 0 else ""
            px   = f'${t["price"]:,.2f}' if t.get("price") else "—"
            rows += (f'<div class="tape-row">'
                     f'<span class="t-sym">{t["ticker"]}</span>'
                     f'<span class="t-px">{px}</span>'
                     f'<span class="{cls}">{sign}{chg:.1f}%</span>'
                     f'</div>')
        tape_ph.markdown(
            f'<div class="tape-wrap">'
            f'<div class="tape-top"><span class="pipe-lbl">Universe</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;color:{TEXT3};">{len(data)}</span></div>'
            f'<div style="overflow-y:auto;max-height:310px;">{rows}</div></div>',
            unsafe_allow_html=True)

    is_done = bool(scan_time)
    render_agent(
        "Market Scan Agent",
        f"Completed at {scan_time}" if is_done else "Ready — press ▶ Run Scan",
        str(n) if n else "—",
        state="done" if is_done else "idle")
    render_pipeline(counts)
    render_tape(st.session_state["ticker_tape"])

# ══════════════════════ LEFT PANEL ═══════════════════════
with left:
    picks_ph = st.empty()

    def render_picks(df):
        if df is None or df.empty:
            picks_ph.markdown(
                f'<div class="picks-outer">'
                f'<div class="picks-top"><span class="pipe-lbl">Today\'s Setups</span>'
                f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;'
                f'background:{CARD2};border:1px solid {BORDER};color:{TEXT3};'
                f'padding:1px 8px;border-radius:20px;">0</span></div>'
                f'<div class="empty"><div class="empty-icon">🔍</div>'
                f'<div class="empty-title">No setups yet</div>'
                f'<div class="empty-body">Press ▶ Run Scan to analyze the full S&amp;P 500 + Futures universe<br>'
                f'and surface high-conviction 5–10% move opportunities.</div>'
                f'</div></div>', unsafe_allow_html=True)
            return

        hdrs = ["SYMBOL","DIR","SCORE","CONFIDENCE","WINDOW","RSI","VOLUME","KELLY $","SIGNALS"]
        th = "".join(f'<th class="picks-th">{h}</th>' for h in hdrs)
        rows_html = ""
        for _, row in df.sort_values("score", ascending=False).iterrows():
            ticker = row.get("ticker","")
            score  = row.get("score", 0)
            direct = row.get("direction","mixed")
            dur    = row.get("duration","—")
            conf   = row.get("confidence","—")
            rsi    = row.get("rsi","—")
            vol    = row.get("volume_ratio","—")
            kelly  = row.get("dollar_amount", 0)
            sigs   = row.get("signals_triggered",[])
            if isinstance(sigs, str):
                sigs = [s.strip() for s in sigs.split(";") if s.strip()]

            lborder = GREEN if direct=="bullish" else (RED if direct=="bearish" else AMBER)
            cc      = {"High":f"color:{GREEN};","Medium":f"color:{AMBER};","Low":f"color:{TEXT3};"}.get(conf,f"color:{TEXT3};")
            ks  = f'${kelly:,.0f}' if kelly else "—"
            rs  = f"{rsi:.1f}"    if isinstance(rsi, float) else str(rsi)
            vs  = f"{vol:.1f}×"   if isinstance(vol, float) else str(vol)
            sh  = " ".join(
                f'<span style="background:{CARD2};border:1px solid {BORDER2};'
                f'color:{TEXT2};font-size:10px;padding:2px 7px;border-radius:3px;">{s}</span>'
                for s in sigs[:3])
            rows_html += (
                f'<tr class="picks-tr" style="border-left:2px solid {lborder};">'
                f'<td class="picks-td"><span class="t-ticker">{ticker}</span></td>'
                f'<td class="picks-td">{direction_html(direct)}</td>'
                f'<td class="picks-td">{score_chip(score)}</td>'
                f'<td class="picks-td" style="font-size:12px;font-weight:600;{cc}">{conf}</td>'
                f'<td class="picks-td" style="font-size:12px;color:{TEXT2};">{dur}</td>'
                f'<td class="picks-td t-mono">{rs}</td>'
                f'<td class="picks-td t-mono">{vs}</td>'
                f'<td class="picks-td t-kelly">{ks}</td>'
                f'<td class="picks-td">{sh}</td>'
                f'</tr>')

        badge = (f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;'
                 f'background:{CARD2};border:1px solid {BORDER};color:{TEXT3};'
                 f'padding:1px 8px;border-radius:20px;">{len(df)}</span>')
        picks_ph.markdown(
            f'<div class="picks-outer">'
            f'<div class="picks-top"><span class="pipe-lbl">Today\'s Setups</span>{badge}</div>'
            f'<div style="overflow-x:auto;overflow-y:auto;max-height:480px;">'
            f'<table class="picks-table"><thead><tr>{th}</tr></thead>'
            f'<tbody>{rows_html}</tbody></table>'
            f'</div></div>', unsafe_allow_html=True)

    render_picks(picks_df)

    # ── Chart ──────────────────────────────────────────────────────
    if picks_df is not None and not picks_df.empty:
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        selected = st.selectbox(
            "Chart", picks_df.sort_values("score", ascending=False)["ticker"].tolist(),
            label_visibility="collapsed")
        if selected:
            from data.fetcher import get_ohlcv
            from ta.volatility import BollingerBands as BB
            df_c = get_ohlcv(selected, period="6mo")
            if not df_c.empty:
                _bb = BB(df_c["Close"], window=20, window_dev=2)
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=df_c.index, open=df_c["Open"], high=df_c["High"],
                    low=df_c["Low"], close=df_c["Close"], name=selected,
                    increasing=dict(line=dict(color=GREEN, width=1.2),
                                    fillcolor="rgba(0,255,136,0.18)"),
                    decreasing=dict(line=dict(color=RED,   width=1.2),
                                    fillcolor="rgba(255,59,92,0.18)")))
                try:
                    fig.add_trace(go.Scatter(x=df_c.index, y=_bb.bollinger_hband(),
                        line=dict(color="rgba(0,255,136,0.25)", width=1), showlegend=False))
                    fig.add_trace(go.Scatter(x=df_c.index, y=_bb.bollinger_lband(),
                        line=dict(color="rgba(0,255,136,0.25)", width=1),
                        fill="tonexty", fillcolor="rgba(0,255,136,0.04)", showlegend=False))
                except Exception:
                    pass
                fig.update_layout(
                    xaxis_rangeslider_visible=False, height=280,
                    paper_bgcolor=CARD, plot_bgcolor=CARD,
                    xaxis=dict(gridcolor=BORDER, tickfont=dict(color=TEXT3, size=10)),
                    yaxis=dict(gridcolor=BORDER, tickfont=dict(color=TEXT3, size=10), side="right"),
                    margin=dict(l=0, r=48, t=22, b=0),
                    title=dict(text=f"<b>{selected}</b>  ·  6M",
                               font=dict(color=TEXT, size=12), x=0.01))
                st.plotly_chart(fig, use_container_width=True)
                row  = picks_df[picks_df["ticker"] == selected].iloc[0]
                sigs = row.get("signals_triggered", [])
                if isinstance(sigs, str):
                    sigs = [s.strip() for s in sigs.split(";") if s.strip()]
                if sigs:
                    st.markdown(signal_tags(sigs), unsafe_allow_html=True)

# ══════════════════════ SCAN LOGIC ════════════════════════
if run_clicked:
    from data.universe   import get_universe
    from data.fetcher    import get_ohlcv_batch, get_earnings_days
    from data.research   import research_universe
    from signals.sentiment import get_sentiment_with_velocity
    from signals.kelly   import annotate_picks
    from model.predictor import predict_universe
    import db

    tickers = get_universe()
    N = len(tickers)

    with right:
        render_agent("Scan Agent", f"Fetching {N} tickers…", str(N), state="running")
        render_pipeline({})
    with st.spinner(""):
        ohlcv_map = get_ohlcv_batch(tickers, period="1y", chunk_size=50)

    tape = sorted([
        {"ticker": t, "price": float(df["Close"].iloc[-1]),
         "chg_pct": (float(df["Close"].iloc[-1]) - float(df["Close"].iloc[-2])) /
                    float(df["Close"].iloc[-2]) * 100}
        for t, df in ohlcv_map.items() if not df.empty and len(df) >= 2
    ], key=lambda x: abs(x["chg_pct"]), reverse=True)
    st.session_state["ticker_tape"] = tape

    with right:
        render_tape(tape)
        render_agent("Research Agent", "Reddit · RSS · Alpha Vantage…", str(N), state="running")
        render_pipeline({"universe": N})
    with st.spinner(""):
        blended = research_universe(tickers)
        sentiment_map = {
            t: {**blended.get(t, {}),
                "score":    round(get_sentiment_with_velocity(t).get("score",0)*0.4 +
                                  blended.get(t,{}).get("score",0)*0.6, 4),
                "velocity": get_sentiment_with_velocity(t).get("velocity", 0),
                "spike":   (abs(get_sentiment_with_velocity(t).get("velocity",0)) >= 0.3 or
                            blended.get(t,{}).get("score",0) > 0.4)}
            for t in tickers}

    with right:
        render_agent("Predict Agent", "XGBoost + blended sentiment…", str(N), state="running")
        render_pipeline({"universe": N, "research": N})
    with st.spinner(""):
        earnings_map = {t: get_earnings_days(t) for t in tickers[:100]}
        picks_df     = predict_universe(tickers, ohlcv_map, sentiment_map, earnings_map)

    scored = len(picks_df) if picks_df is not None and not picks_df.empty else 0

    with right:
        render_agent("Risk Agent", "Kelly Criterion sizing…", str(scored), state="running")
        render_pipeline({"universe": N, "research": N, "scored": scored})
    if picks_df is not None and not picks_df.empty:
        picks_df = annotate_picks(picks_df)

    with right:
        render_agent("Learn Agent", "Writing to Supabase…", str(scored), state="running")
        render_pipeline({"universe": N, "research": N, "scored": scored, "risk": scored})
    with st.spinner(""):
        if picks_df is not None and not picks_df.empty and db.db_available():
            out = picks_df.copy()
            out["date"] = datetime.today().strftime("%Y-%m-%d")
            out["actual_move_5d"] = None
            db.append_predictions(out.to_dict(orient="records"))

    scan_time    = datetime.now().strftime("%H:%M")
    final_counts = {"universe": N, "research": N, "scored": scored, "risk": scored, "learn": scored}
    st.session_state.update({"last_picks": picks_df, "scan_time": scan_time, "pipeline_counts": final_counts})

    with right:
        render_agent("Market Scan Agent", f"Completed at {scan_time}", str(scored), state="done")
        render_pipeline(final_counts)
    with left:
        render_picks(picks_df)
    st.rerun()
