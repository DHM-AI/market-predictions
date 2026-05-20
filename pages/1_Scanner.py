import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from ui_style import (inject_css, live_badge, signal_tags,
                      score_chip, direction_html,
                      BG, CARD, CARD2, BORDER, TEXT, MUTED, SUBTLE,
                      CYAN, GREEN, RED, ORANGE, AMBER, PURPLE)

st.set_page_config(page_title="AI Market Scanner", page_icon="⚡", layout="wide")
inject_css()

st.markdown(f"""
<style>
/* ── Header ────────────────────────────────────────────── */
.dash-header {{
    display: flex; justify-content: space-between; align-items: center;
    background: {CARD}; border: 1px solid {BORDER};
    border-radius: 6px; padding: 10px 18px; margin-bottom: 16px;
}}
.dash-title {{
    font-size: 16px; font-weight: 700; color: {TEXT};
    display: flex; align-items: center; gap: 8px;
}}
.dash-sub {{ font-size: 11px; color: {MUTED}; margin-top: 2px; }}

/* ── Metric card ───────────────────────────────────────── */
.m-card {{
    background: {CARD}; border: 1px solid {BORDER};
    border-radius: 6px; padding: 12px 14px;
}}
.m-label {{ font-size: 10px; font-weight: 600; color: {MUTED}; text-transform: uppercase; letter-spacing: 1px; }}
.m-val   {{ font-family: 'JetBrains Mono', monospace; font-size: 20px; font-weight: 700; color: {TEXT}; margin-top: 2px; }}
.m-sub   {{ font-size: 11px; color: {MUTED}; margin-top: 1px; }}

/* ── Section title ─────────────────────────────────────── */
.sec-bar {{
    display: flex; justify-content: space-between; align-items: center;
    background: {CARD2}; border: 1px solid {BORDER};
    border-radius: 6px 6px 0 0; padding: 8px 14px; border-bottom: none;
}}
.sec-name {{ font-size: 11px; font-weight: 600; color: {MUTED}; letter-spacing: 1.5px; text-transform: uppercase; }}
.sec-badge {{
    font-family: 'JetBrains Mono', monospace;
    background: {CARD}; border: 1px solid {BORDER};
    color: {MUTED}; font-size: 11px; padding: 1px 8px; border-radius: 20px;
}}

/* ── Picks table ───────────────────────────────────────── */
.picks-table {{
    background: {CARD}; border: 1px solid {BORDER};
    border-radius: 0 0 6px 6px; overflow: hidden;
    border-top: 1px solid {BORDER};
}}
.picks-th {{
    font-size: 10px; font-weight: 600; color: {MUTED};
    text-transform: uppercase; letter-spacing: 1px;
    padding: 8px 12px; text-align: left;
    background: {CARD2}; border-bottom: 1px solid {BORDER};
}}
.picks-td {{ padding: 9px 12px; border-bottom: 1px solid #222; vertical-align: middle; }}
.picks-tr:last-child td {{ border-bottom: none; }}
.picks-tr:hover td {{ background: #242424 !important; }}
.t-sym {{ font-family: 'JetBrains Mono', monospace; font-weight: 700; color: {CYAN}; font-size: 14px; }}

/* ── Pipeline panel ────────────────────────────────────── */
.pipe-panel {{
    background: {CARD}; border: 1px solid {BORDER};
    border-radius: 6px; overflow: hidden;
}}
.pipe-title {{
    font-size: 10px; font-weight: 600; color: {MUTED};
    letter-spacing: 1.5px; text-transform: uppercase;
    padding: 8px 14px; border-bottom: 1px solid {BORDER};
    background: {CARD2};
    display: flex; justify-content: space-between; align-items: center;
}}
.pip-row {{
    display: flex; align-items: center; padding: 9px 14px;
    border-bottom: 1px solid #222; gap: 10px;
}}
.pip-row:last-child {{ border-bottom: none; }}
.pip-dot-on  {{ width:7px;height:7px;border-radius:50%;background:{GREEN};box-shadow:0 0 5px rgba(34,197,94,0.5);flex-shrink:0; }}
.pip-dot-off {{ width:7px;height:7px;border-radius:50%;background:#333;border:1px solid #444;flex-shrink:0; }}
.pip-name    {{ font-size:12px;color:{TEXT};font-weight:500;width:68px;flex-shrink:0; }}
.pip-sub     {{ font-size:11px;color:#555;flex:1; }}
.pip-bar     {{ width:60px;height:3px;background:#2a2a2a;border-radius:2px;flex-shrink:0; }}
.pip-fill    {{ height:3px;background:{GREEN};border-radius:2px; }}
.pip-num-on  {{ font-family:'JetBrains Mono',monospace;font-size:12px;color:{GREEN};font-weight:600;min-width:34px;text-align:right; }}
.pip-num-off {{ font-family:'JetBrains Mono',monospace;font-size:12px;color:#444;min-width:34px;text-align:right; }}

/* ── Qualified box ─────────────────────────────────────── */
.qual-box {{
    background: {CARD}; border: 1px solid {BORDER};
    border-radius: 6px; padding: 12px 14px; margin-top: 10px;
    display: flex; justify-content: space-between; align-items: center;
}}

/* ── Tape ──────────────────────────────────────────────── */
.tape-panel {{
    background: {CARD}; border: 1px solid {BORDER};
    border-radius: 6px; overflow: hidden; margin-top: 10px;
}}
.tape-row {{
    display: flex; align-items: center; padding: 6px 14px;
    border-bottom: 1px solid #1f1f1f; font-size: 12px;
}}
.tape-row:last-child {{ border-bottom: none; }}
.t-px {{ font-family:'JetBrains Mono',monospace;color:{MUTED};flex:1;text-align:right;padding-right:10px;font-size:11px; }}
.t-up {{ font-family:'JetBrains Mono',monospace;color:{GREEN};min-width:48px;text-align:right;font-size:11px;font-weight:500; }}
.t-dn {{ font-family:'JetBrains Mono',monospace;color:{RED};min-width:48px;text-align:right;font-size:11px;font-weight:500; }}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [("pipeline_counts", {}), ("last_picks", None),
              ("ticker_tape", []), ("scan_time", "")]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Header bar ────────────────────────────────────────────────────────────────
h1, h2 = st.columns([4, 1])
with h1:
    scan_time = st.session_state["scan_time"]
    updated = f"Updated: {scan_time}" if scan_time else "Not yet scanned today"
    st.markdown(
        f'<div class="dash-header">'
        f'<div><div class="dash-title">⚡ AI Trading Dashboard {live_badge()}</div>'
        f'<div class="dash-sub">S&P 500 + Futures · 5-Agent Pipeline · 5–10% Move Detection · {updated}</div></div>'
        f'</div>',
        unsafe_allow_html=True
    )
with h2:
    run_clicked = st.button("▶  Run Scan", type="primary", use_container_width=True)

# ── Top metric cards ──────────────────────────────────────────────────────────
picks_df  = st.session_state["last_picks"]
counts    = st.session_state["pipeline_counts"]
n_picks   = len(picks_df) if picks_df is not None and not picks_df.empty else 0

# Load from DB if no in-session scan
if picks_df is None:
    try:
        from db import load_predictions_for_date, db_available
        if db_available():
            rows = load_predictions_for_date(datetime.today().strftime("%Y-%m-%d"))
            if rows:
                picks_df = pd.DataFrame(rows)
                n_picks  = len(picks_df)
    except Exception:
        pass

n_high  = len(picks_df[picks_df["score"] >= 70]) if picks_df is not None and not picks_df.empty and "score" in picks_df.columns else 0
n_bull  = len(picks_df[picks_df["direction"] == "bullish"]) if picks_df is not None and not picks_df.empty and "direction" in picks_df.columns else 0
n_bear  = len(picks_df[picks_df["direction"] == "bearish"]) if picks_df is not None and not picks_df.empty and "direction" in picks_df.columns else 0
univ    = counts.get("universe", 0)

m1, m2, m3, m4, m5, m6 = st.columns(6)
def mcard(col, label, val, sub="", color=TEXT):
    col.markdown(
        f'<div class="m-card"><div class="m-label">{label}</div>'
        f'<div class="m-val" style="color:{color};">{val}</div>'
        f'<div class="m-sub">{sub}</div></div>',
        unsafe_allow_html=True
    )

mcard(m1, "Universe Scanned", f"{univ:,}" if univ else "—", "S&P 500 + Futures")
mcard(m2, "Qualified Setups", str(n_picks) if n_picks else "—", "Score ≥ 50",
      color=GREEN if n_picks > 0 else MUTED)
mcard(m3, "High Conviction", str(n_high) if n_high else "—", "Score ≥ 70",
      color=GREEN if n_high > 0 else MUTED)
mcard(m4, "Long Signals",  str(n_bull) if n_bull else "—", "Bullish setups",
      color=GREEN if n_bull > 0 else MUTED)
mcard(m5, "Short Signals", str(n_bear) if n_bear else "—", "Bearish setups",
      color=ORANGE if n_bear > 0 else MUTED)
mcard(m6, "Last Scan", scan_time if scan_time else "—", datetime.today().strftime("%b %d %Y"))

st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)

# ── Main layout ───────────────────────────────────────────────────────────────
left_col, right_col = st.columns([3, 1], gap="medium")

# ── RIGHT: pipeline + tape ────────────────────────────────────────────────────
with right_col:
    agent_ph    = st.empty()
    pipeline_ph = st.empty()
    qual_ph     = st.empty()
    tape_ph     = st.empty()

    def render_agent(name, sub, count, running=False, done=False):
        dot_color = CYAN if running else (GREEN if done else "#333")
        val_color = CYAN if running else (GREEN if done else MUTED)
        pulse = "animation:blink 0.8s infinite;" if running else ""
        agent_ph.markdown(
            f'<div style="background:{CARD};border:1px solid {BORDER};border-radius:6px;'
            f'padding:10px 14px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;">'
            f'<div>'
            f'<div style="color:{TEXT};font-size:13px;font-weight:600;display:flex;align-items:center;gap:7px;">'
            f'<span style="width:7px;height:7px;border-radius:50%;background:{dot_color};display:inline-block;{pulse}"></span>{name}</div>'
            f'<div style="color:{MUTED};font-size:11px;margin-top:2px;margin-left:14px;">{sub}</div>'
            f'</div>'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:20px;font-weight:700;color:{val_color};">{count}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    def render_pipeline(counts, universe=509):
        steps = [
            ("Scan",     "OHLCV · yfinance",        counts.get("universe")),
            ("Research", "Reddit · RSS · AV",        counts.get("research")),
            ("Predict",  "XGBoost + sentiment",      counts.get("scored")),
            ("Risk",     "Kelly · $50k bankroll",    counts.get("risk")),
            ("Learn",    "Backfill · post-mortem",   counts.get("learn")),
        ]
        rows = ""
        for name, sub, cnt in steps:
            done   = cnt is not None
            dot    = "pip-dot-on" if done else "pip-dot-off"
            ncls   = "pip-num-on" if done else "pip-num-off"
            cs     = str(cnt) if cnt is not None else "—"
            bar_w  = int((cnt / universe) * 100) if (done and universe) else 0
            rows  += (
                f'<div class="pip-row">'
                f'<div class="{dot}"></div>'
                f'<div class="pip-name">{name}</div>'
                f'<div class="pip-sub">{sub}</div>'
                f'<div class="pip-bar"><div class="pip-fill" style="width:{bar_w}%;"></div></div>'
                f'<div class="{ncls}">{cs}</div>'
                f'</div>'
            )
        n_done = sum(1 for _, _, c in steps if c is not None)
        pipeline_ph.markdown(
            f'<div class="pipe-panel">'
            f'<div class="pipe-title"><span>Filter Pipeline</span>'
            f'<span style="font-family:JetBrains Mono,monospace;color:{GREEN if n_done==5 else MUTED};">{n_done}/5</span></div>'
            f'{rows}</div>',
            unsafe_allow_html=True
        )

    def render_tape(data):
        if not data:
            tape_ph.markdown(
                f'<div class="tape-panel">'
                f'<div class="pipe-title"><span>Market Universe</span></div>'
                f'<div style="padding:30px 14px;text-align:center;color:{MUTED};font-size:12px;">'
                f'Run scan to populate</div></div>',
                unsafe_allow_html=True
            )
            return
        rows = ""
        for t in data[:30]:
            chg  = t.get("chg_pct", 0)
            cls  = "t-up" if chg >= 0 else "t-dn"
            sign = "+" if chg >= 0 else ""
            px   = f'${t["price"]:,.2f}' if t.get("price") else "—"
            rows += (
                f'<div class="tape-row">'
                f'<span style="font-family:JetBrains Mono,monospace;font-weight:700;color:{CYAN};width:58px;display:inline-block;">{t["ticker"]}</span>'
                f'<span class="t-px">{px}</span>'
                f'<span class="{cls}">{sign}{chg:.1f}%</span>'
                f'</div>'
            )
        tape_ph.markdown(
            f'<div class="tape-panel">'
            f'<div class="pipe-title"><span>Market Universe</span>'
            f'<span style="font-family:JetBrains Mono,monospace;color:{MUTED};">{len(data)}</span></div>'
            f'<div style="overflow-y:auto;max-height:320px;">{rows}</div></div>',
            unsafe_allow_html=True
        )

    # Initial render
    is_done = st.session_state["scan_time"] != ""
    render_agent(
        "Market Scan Agent",
        f"Completed at {st.session_state['scan_time']}" if is_done else "Ready — press ▶ Run Scan",
        str(n_picks) if n_picks else "—",
        done=is_done
    )
    render_pipeline(counts)
    render_tape(st.session_state["ticker_tape"])

# ── LEFT: picks table ─────────────────────────────────────────────────────────
with left_col:
    picks_ph = st.empty()

    def render_picks(df):
        if df is None or df.empty:
            picks_ph.markdown(
                f'<div class="sec-bar"><span class="sec-name">Today\'s Setups</span>'
                f'<span class="sec-badge">0</span></div>'
                f'<div class="picks-table" style="border-radius:0 0 6px 6px;">'
                f'<div style="padding:60px 20px;text-align:center;color:{MUTED};font-size:13px;">'
                f'No setups yet — run a scan to find opportunities</div></div>',
                unsafe_allow_html=True
            )
            return

        headers = ["SYMBOL", "DIR", "SCORE", "CONFIDENCE", "WINDOW", "RSI", "VOLUME", "KELLY $", "SIGNALS"]
        th = "".join(f'<th class="picks-th">{h}</th>' for h in headers)

        rows_html = ""
        for _, row in df.iterrows():
            ticker = row.get("ticker", "")
            score  = row.get("score", 0)
            direct = row.get("direction", "mixed")
            dur    = row.get("duration", "—")
            conf   = row.get("confidence", "—")
            rsi    = row.get("rsi", "—")
            vol    = row.get("volume_ratio", "—")
            kelly  = row.get("dollar_amount", 0)
            sigs   = row.get("signals_triggered", [])
            if isinstance(sigs, str):
                sigs = [s.strip() for s in sigs.split(";") if s.strip()]

            conf_color = {"High": GREEN, "Medium": AMBER, "Low": MUTED}.get(conf, MUTED)
            ks = f'${kelly:,.0f}' if kelly else "—"
            rs = f"{rsi:.1f}" if isinstance(rsi, float) else str(rsi)
            vs = f"{vol:.1f}x" if isinstance(vol, float) else str(vol)
            sh = " ".join(
                f'<span style="background:rgba(34,211,238,0.08);border:1px solid rgba(34,211,238,0.2);'
                f'color:{CYAN};font-size:10px;padding:1px 7px;border-radius:4px;">{s}</span>'
                for s in sigs[:3]
            )

            rows_html += (
                f'<tr class="picks-tr">'
                f'<td class="picks-td"><span class="t-sym">{ticker}</span></td>'
                f'<td class="picks-td">{direction_html(direct)}</td>'
                f'<td class="picks-td">{score_chip(score)}</td>'
                f'<td class="picks-td" style="color:{conf_color};font-size:12px;font-weight:600;">{conf}</td>'
                f'<td class="picks-td" style="color:{MUTED};font-size:12px;">{dur}</td>'
                f'<td class="picks-td" style="font-family:JetBrains Mono,monospace;color:{MUTED};font-size:12px;">{rs}</td>'
                f'<td class="picks-td" style="font-family:JetBrains Mono,monospace;color:{MUTED};font-size:12px;">{vs}</td>'
                f'<td class="picks-td" style="font-family:JetBrains Mono,monospace;color:{GREEN};font-weight:600;font-size:13px;">{ks}</td>'
                f'<td class="picks-td">{sh}</td>'
                f'</tr>'
            )

        picks_ph.markdown(
            f'<div class="sec-bar"><span class="sec-name">Today\'s Setups</span>'
            f'<span class="sec-badge">{len(df)}</span></div>'
            f'<div class="picks-table"><div style="overflow-y:auto;max-height:480px;">'
            f'<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">'
            f'<thead><tr>{th}</tr></thead>'
            f'<tbody>{rows_html}</tbody>'
            f'</table></div></div>',
            unsafe_allow_html=True
        )

    render_picks(picks_df)

    # ── Mini chart ──────────────────────────────────────────
    if picks_df is not None and not picks_df.empty:
        st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
        selected = st.selectbox("Quick chart", picks_df["ticker"].tolist(),
                                label_visibility="collapsed")
        if selected:
            from data.fetcher import get_ohlcv
            from ta.volatility import BollingerBands as BB
            df_chart = get_ohlcv(selected, period="6mo")
            if not df_chart.empty:
                _bb = BB(df_chart["Close"], window=20, window_dev=2)
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=df_chart.index,
                    open=df_chart["Open"], high=df_chart["High"],
                    low=df_chart["Low"],  close=df_chart["Close"],
                    name=selected,
                    increasing=dict(line=dict(color=GREEN), fillcolor="rgba(34,197,94,0.18)"),
                    decreasing=dict(line=dict(color=RED),   fillcolor="rgba(239,68,68,0.18)")
                ))
                try:
                    fig.add_trace(go.Scatter(x=df_chart.index, y=_bb.bollinger_hband(),
                        line=dict(color=f"rgba(34,211,238,0.35)", width=1), showlegend=False))
                    fig.add_trace(go.Scatter(x=df_chart.index, y=_bb.bollinger_lband(),
                        line=dict(color=f"rgba(34,211,238,0.35)", width=1),
                        fill="tonexty", fillcolor="rgba(34,211,238,0.04)", showlegend=False))
                except Exception:
                    pass
                fig.update_layout(
                    xaxis_rangeslider_visible=False, height=300,
                    paper_bgcolor=CARD, plot_bgcolor=CARD,
                    xaxis=dict(gridcolor=BORDER, tickfont=dict(color=MUTED, size=10)),
                    yaxis=dict(gridcolor=BORDER, tickfont=dict(color=MUTED, size=10)),
                    margin=dict(l=0, r=0, t=20, b=0),
                    title=dict(text=f"{selected} · 6M", font=dict(color=TEXT, size=12), x=0.01)
                )
                st.plotly_chart(fig, use_container_width=True)
                row  = picks_df[picks_df["ticker"] == selected].iloc[0]
                sigs = row.get("signals_triggered", [])
                if isinstance(sigs, str):
                    sigs = [s.strip() for s in sigs.split(";") if s.strip()]
                if sigs:
                    st.markdown(signal_tags(sigs), unsafe_allow_html=True)

# ── Run scan ──────────────────────────────────────────────────────────────────
if run_clicked:
    from data.universe import get_universe
    from data.fetcher  import get_ohlcv_batch, get_earnings_days
    from data.research import research_universe
    from signals.sentiment import get_sentiment_with_velocity
    from signals.kelly     import annotate_picks
    from model.predictor   import predict_universe
    import db

    tickers = get_universe()
    N = len(tickers)

    with right_col:
        render_agent("Market Scan Agent", f"Fetching {N} tickers…", str(N), running=True)
        render_pipeline({})

    with st.spinner(""):
        ohlcv_map = get_ohlcv_batch(tickers, period="1y", chunk_size=50)

    tape = [
        {"ticker": t,
         "price": float(df["Close"].iloc[-1]),
         "chg_pct": (float(df["Close"].iloc[-1]) - float(df["Close"].iloc[-2])) /
                    float(df["Close"].iloc[-2]) * 100}
        for t, df in ohlcv_map.items() if not df.empty and len(df) >= 2
    ]
    tape.sort(key=lambda x: abs(x["chg_pct"]), reverse=True)
    st.session_state["ticker_tape"] = tape
    with right_col:
        render_tape(tape)
        render_agent("Research Agent", "Reddit · RSS · news…", str(N), running=True)
        render_pipeline({"universe": N})

    with st.spinner(""):
        blended = research_universe(tickers)
        sentiment_map = {
            t: {
                **blended.get(t, {}),
                "score": round(
                    get_sentiment_with_velocity(t).get("score", 0) * 0.4 +
                    blended.get(t, {}).get("score", 0) * 0.6, 4),
                "velocity": get_sentiment_with_velocity(t).get("velocity", 0),
                "spike": (abs(get_sentiment_with_velocity(t).get("velocity", 0)) >= 0.3 or
                          blended.get(t, {}).get("score", 0) > 0.4),
            } for t in tickers
        }

    with right_col:
        render_agent("Predict Agent", "XGBoost + sentiment…", str(N), running=True)
        render_pipeline({"universe": N, "research": N})

    with st.spinner(""):
        earnings_map = {t: get_earnings_days(t) for t in tickers[:100]}
        picks_df     = predict_universe(tickers, ohlcv_map, sentiment_map, earnings_map)

    scored = len(picks_df) if picks_df is not None and not picks_df.empty else 0

    with right_col:
        render_agent("Risk Agent", "Kelly Criterion…", str(scored), running=True)
        render_pipeline({"universe": N, "research": N, "scored": scored})

    if picks_df is not None and not picks_df.empty:
        picks_df = annotate_picks(picks_df)

    with right_col:
        render_agent("Learn Agent", "Persisting to Supabase…", str(scored), running=True)
        render_pipeline({"universe": N, "research": N, "scored": scored, "risk": scored})

    with st.spinner(""):
        if picks_df is not None and not picks_df.empty and db.db_available():
            rows = picks_df.copy()
            rows["date"] = datetime.today().strftime("%Y-%m-%d")
            rows["actual_move_5d"] = None
            db.append_predictions(rows.to_dict(orient="records"))

    scan_time = datetime.now().strftime("%H:%M")
    final_counts = {"universe": N, "research": N, "scored": scored, "risk": scored, "learn": scored}
    st.session_state.update({
        "last_picks": picks_df, "scan_time": scan_time, "pipeline_counts": final_counts,
    })
    with right_col:
        render_agent("Market Scan Agent", f"Completed at {scan_time}", str(scored), done=True)
        render_pipeline(final_counts)

    with left_col:
        render_picks(picks_df)

    st.rerun()
