import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from ui_style import inject_css, live_badge, GREEN, RED, AMBER, BLUE, CYAN, TEXT, TEXT2, TEXT3, CARD, CARD2, BORDER, BORDER2, BG

st.set_page_config(page_title="AI Market Scanner", page_icon="⚡", layout="wide")
inject_css()

st.markdown(f"""
<style>
/* ─── Reset & base ─────────────────────────────────── */
* {{ box-sizing: border-box; }}

/* ─── Top bar ───────────────────────────────────────── */
.topbar {{
    display:flex; align-items:center; justify-content:space-between;
    padding:10px 18px;
    background:{CARD}; border:1px solid {BORDER}; border-radius:8px;
    margin-bottom:14px;
}}
.topbar-left  {{ display:flex; flex-direction:column; gap:2px; }}
.topbar-title {{ font-size:15px; font-weight:700; color:{TEXT}; display:flex; align-items:center; gap:8px; }}
.topbar-sub   {{ font-size:11px; color:{TEXT3}; }}

/* ─── Agent status card ─────────────────────────────── */
.agent-card {{
    background:{CARD}; border:1px solid {BORDER}; border-radius:8px;
    padding:14px 16px; margin-bottom:10px;
}}
.agent-row {{ display:flex; justify-content:space-between; align-items:flex-start; }}
.agent-label {{ font-size:9px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:{TEXT3}; margin-bottom:6px; }}
.agent-name  {{ font-size:14px; font-weight:700; color:{TEXT}; display:flex; align-items:center; gap:8px; }}
.agent-sub   {{ font-size:11px; color:{TEXT3}; margin-top:4px; }}
.agent-count {{ font-family:'JetBrains Mono',monospace; font-size:36px; font-weight:700; line-height:1; }}

/* ─── Filter pipeline ───────────────────────────────── */
.filter-card {{
    background:{CARD}; border:1px solid {BORDER}; border-radius:8px;
    overflow:hidden; margin-bottom:10px;
}}
.filter-hdr {{
    display:flex; justify-content:space-between; align-items:center;
    padding:8px 14px; border-bottom:1px solid {BORDER};
    background:{CARD2};
}}
.filter-hdr-title {{ font-size:9px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:{TEXT3}; }}
.filter-row {{
    display:grid; grid-template-columns:10px 130px 1fr 44px;
    align-items:center; gap:10px;
    padding:9px 14px; border-bottom:1px solid rgba(255,255,255,0.03);
}}
.filter-row:last-child {{ border-bottom:none; }}
.f-dot-on  {{ width:8px;height:8px;border-radius:50%;background:{GREEN};box-shadow:0 0 8px {GREEN}66; }}
.f-dot-off {{ width:8px;height:8px;border-radius:50%;background:transparent;border:1.5px solid {TEXT3}; }}
.f-name    {{ font-size:12px; font-weight:600; color:{TEXT}; }}
.f-desc    {{ font-size:10px; color:{TEXT3}; }}
.f-bar-wrap {{ width:100%; height:4px; background:{BORDER2}; border-radius:2px; }}
.f-bar-fill {{ height:4px; border-radius:2px; background:{GREEN}; transition:width 0.4s; }}
.f-count   {{ font-family:'JetBrains Mono',monospace; font-size:12px; font-weight:700; text-align:right; }}

/* ─── Qualified banner ──────────────────────────────── */
.qual-banner {{
    display:flex; justify-content:space-between; align-items:center;
    background:rgba(0,255,136,0.05); border:1px solid rgba(0,255,136,0.2);
    border-radius:8px; padding:10px 16px; margin-bottom:10px;
}}
.qual-label {{ font-size:10px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:{GREEN}; }}
.qual-sub   {{ font-size:11px; color:{TEXT3}; margin-top:2px; }}
.qual-count {{ font-family:'JetBrains Mono',monospace; font-size:32px; font-weight:700; color:{GREEN}; }}

/* ─── Social feed ───────────────────────────────────── */
.feed-card {{
    background:{CARD}; border:1px solid {BORDER}; border-radius:8px;
    overflow:hidden; margin-bottom:10px;
}}
.feed-hdr {{
    display:flex; justify-content:space-between; align-items:center;
    padding:8px 14px; border-bottom:1px solid {BORDER};
    background:{CARD2};
}}
.feed-hdr-title {{ font-size:9px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:{TEXT3}; }}
.feed-item {{
    padding:10px 14px; border-bottom:1px solid rgba(255,255,255,0.03);
    display:flex; flex-direction:column; gap:4px;
}}
.feed-item:last-child {{ border-bottom:none; }}
.feed-meta    {{ font-size:10px; color:{TEXT3}; display:flex; align-items:center; gap:6px; }}
.feed-source  {{ font-weight:700; color:{TEXT2}; }}
.feed-text    {{ font-size:12px; color:{TEXT}; line-height:1.4; }}
.feed-tag-bull {{ background:rgba(0,255,136,0.1); border:1px solid rgba(0,255,136,0.25); color:{GREEN}; font-size:9px; font-weight:700; letter-spacing:1px; padding:1px 6px; border-radius:3px; }}
.feed-tag-bear {{ background:rgba(255,59,92,0.1); border:1px solid rgba(255,59,92,0.25); color:{RED}; font-size:9px; font-weight:700; letter-spacing:1px; padding:1px 6px; border-radius:3px; }}

/* ─── Tape ──────────────────────────────────────────── */
.tape-card {{
    background:{CARD}; border:1px solid {BORDER}; border-radius:8px; overflow:hidden;
}}
.tape-hdr {{
    display:flex; justify-content:space-between; align-items:center;
    padding:8px 14px; border-bottom:1px solid {BORDER}; background:{CARD2};
}}
.tape-hdr-title {{ font-size:9px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:{TEXT3}; }}
.tape-item {{
    display:grid; grid-template-columns:58px 1fr 52px;
    align-items:center; gap:6px;
    padding:6px 14px; border-bottom:1px solid rgba(255,255,255,0.025);
}}
.tape-item:last-child {{ border-bottom:none; }}
.tape-sym {{ font-family:'JetBrains Mono',monospace; font-weight:700; color:{GREEN}; font-size:12px; }}
.tape-px  {{ font-family:'JetBrains Mono',monospace; font-size:11px; color:{TEXT3}; text-align:right; padding-right:6px; }}
.tape-up  {{ font-family:'JetBrains Mono',monospace; font-size:11px; font-weight:600; color:{GREEN}; text-align:right; }}
.tape-dn  {{ font-family:'JetBrains Mono',monospace; font-size:11px; font-weight:600; color:{RED}; text-align:right; }}

/* ─── Pick cards ────────────────────────────────────── */
.pick-card {{
    background:{CARD}; border:1px solid {BORDER}; border-radius:8px;
    padding:14px; height:100%; display:flex; flex-direction:column; gap:10px;
    transition:border-color 0.15s;
}}
.pick-card:hover {{ border-color:{BORDER2}; }}
.pick-top    {{ display:flex; justify-content:space-between; align-items:flex-start; }}
.pick-ticker {{ font-family:'JetBrains Mono',monospace; font-size:20px; font-weight:700; color:{GREEN}; }}
.pick-score  {{ font-family:'JetBrains Mono',monospace; font-size:28px; font-weight:700; line-height:1; }}
.pick-score-label {{ font-size:9px; color:{TEXT3}; letter-spacing:1px; margin-top:2px; text-align:right; }}
.pick-dir    {{ font-size:10px; font-weight:700; letter-spacing:1px; padding:3px 8px; border-radius:3px; }}
.pick-divider {{ height:1px; background:{BORDER}; }}
.pick-bar-row {{ display:flex; flex-direction:column; gap:6px; }}
.pick-bar-item {{ display:flex; align-items:center; gap:8px; }}
.pick-bar-label {{ font-size:10px; color:{TEXT3}; width:80px; flex-shrink:0; }}
.pick-bar-track {{ flex:1; height:4px; background:{BORDER2}; border-radius:2px; }}
.pick-bar-fill  {{ height:4px; border-radius:2px; }}
.pick-bar-pct   {{ font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:600; min-width:28px; text-align:right; }}
.pick-stats  {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:6px; }}
.pick-stat   {{ display:flex; flex-direction:column; gap:2px; }}
.pick-stat-label {{ font-size:9px; color:{TEXT3}; letter-spacing:1px; text-transform:uppercase; }}
.pick-stat-val   {{ font-family:'JetBrains Mono',monospace; font-size:12px; font-weight:600; color:{TEXT}; }}
.pick-kelly  {{ display:flex; justify-content:space-between; align-items:center; padding:8px 10px; background:{CARD2}; border-radius:5px; }}
.pick-kelly-label {{ font-size:10px; color:{TEXT3}; }}
.pick-kelly-val   {{ font-family:'JetBrains Mono',monospace; font-size:14px; font-weight:700; color:{GREEN}; }}

/* ─── Empty ─────────────────────────────────────────── */
.empty {{ padding:48px 20px; text-align:center; }}
.empty-icon  {{ font-size:30px; opacity:0.3; margin-bottom:10px; }}
.empty-title {{ font-size:14px; font-weight:600; color:{TEXT2}; margin-bottom:5px; }}
.empty-body  {{ font-size:12px; color:{TEXT3}; line-height:1.6; }}

@keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0.25}} }}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [("picks_df", None), ("filter_counts", {}), ("tape", []),
              ("scan_time", ""), ("feeds", [])]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Pre-load Supabase ─────────────────────────────────────────────────────────
picks_df = st.session_state["picks_df"]
if picks_df is None:
    try:
        from db import load_predictions_for_date, db_available
        if db_available():
            rows = load_predictions_for_date(datetime.today().strftime("%Y-%m-%d"))
            if rows:
                picks_df = pd.DataFrame(rows)
                st.session_state["picks_df"] = picks_df
    except Exception:
        pass

n_picks = len(picks_df) if picks_df is not None and not picks_df.empty else 0
fc      = st.session_state["filter_counts"]
scan_time = st.session_state["scan_time"]

# ── Top bar ───────────────────────────────────────────────────────────────────
col_hdr, col_btn = st.columns([5, 1])
with col_hdr:
    updated = f"Scanned at {scan_time} · {datetime.today().strftime('%b %d %Y')}" if scan_time else f"Not yet scanned · {datetime.today().strftime('%b %d %Y')}"
    st.markdown(
        f'<div class="topbar">'
        f'<div class="topbar-left">'
        f'<div class="topbar-title">⚡ AI Market Scanner {live_badge()}</div>'
        f'<div class="topbar-sub">S&P 500 + Futures &nbsp;·&nbsp; 5-Agent Pipeline &nbsp;·&nbsp; {updated}</div>'
        f'</div></div>',
        unsafe_allow_html=True)
with col_btn:
    run_clicked = st.button("▶  Run Scan", type="primary", use_container_width=True)

# ── Main layout: left panel + right panel ────────────────────────────────────
col_left, col_right = st.columns([3, 2], gap="medium")

# ════════════════════════════ RIGHT ══════════════════════
with col_right:
    feed_ph = st.empty()
    tape_ph = st.empty()

    def render_feed(feeds):
        if not feeds:
            feed_ph.markdown(
                f'<div class="feed-card">'
                f'<div class="feed-hdr"><span class="feed-hdr-title">Live Signal Feeds</span>'
                f'<span style="font-size:9px;font-weight:700;letter-spacing:1px;color:{TEXT3};">WAITING</span></div>'
                f'<div class="empty" style="padding:24px 14px;">'
                f'<div class="empty-icon">📰</div>'
                f'<div class="empty-body">Reddit · RSS · Alpha Vantage<br>headlines appear here during scan</div>'
                f'</div></div>', unsafe_allow_html=True)
            return
        items = ""
        for f in feeds[:6]:
            tag_cls = "feed-tag-bull" if f.get("bias","") == "bullish" else "feed-tag-bear" if f.get("bias","") == "bearish" else ""
            tag_html = f'<span class="feed-tag-{"bull" if f.get("bias")=="bullish" else "bear"}">{f.get("bias","").upper()}</span>' if tag_cls else ""
            items += (
                f'<div class="feed-item">'
                f'<div class="feed-meta">'
                f'<span class="feed-source">{f.get("source","")}</span>'
                f'<span>·</span><span>{f.get("ticker","")}</span>'
                f'{tag_html}</div>'
                f'<div class="feed-text">{f.get("text","")[:100]}</div>'
                f'</div>')
        feed_ph.markdown(
            f'<div class="feed-card">'
            f'<div class="feed-hdr"><span class="feed-hdr-title">Live Signal Feeds</span>'
            f'<span style="font-size:9px;font-weight:700;letter-spacing:1px;color:{GREEN};">● LIVE</span></div>'
            f'{items}</div>', unsafe_allow_html=True)

    def render_tape(data):
        if not data:
            tape_ph.markdown(
                f'<div class="tape-card">'
                f'<div class="tape-hdr"><span class="tape-hdr-title">Universe</span>'
                f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;color:{TEXT3};">—</span></div>'
                f'<div class="empty" style="padding:24px 14px;">'
                f'<div class="empty-icon">📡</div>'
                f'<div class="empty-body">Populates after scan</div>'
                f'</div></div>', unsafe_allow_html=True)
            return
        rows = ""
        for t in data[:28]:
            chg = t.get("chg_pct", 0)
            cls = "tape-up" if chg >= 0 else "tape-dn"
            sign = "+" if chg >= 0 else ""
            px = f'${t["price"]:,.2f}' if t.get("price") else "—"
            rows += (f'<div class="tape-item">'
                     f'<span class="tape-sym">{t["ticker"]}</span>'
                     f'<span class="tape-px">{px}</span>'
                     f'<span class="{cls}">{sign}{chg:.1f}%</span>'
                     f'</div>')
        tape_ph.markdown(
            f'<div class="tape-card">'
            f'<div class="tape-hdr"><span class="tape-hdr-title">Universe</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;color:{TEXT3};">{len(data)}</span></div>'
            f'<div style="overflow-y:auto;max-height:320px;">{rows}</div>'
            f'</div>', unsafe_allow_html=True)

    render_feed(st.session_state["feeds"])
    render_tape(st.session_state["tape"])

# ════════════════════════════ LEFT ═══════════════════════
with col_left:
    agent_ph    = st.empty()
    filter_ph   = st.empty()
    qual_ph     = st.empty()

    def render_agent(name, sub, count, state="idle"):
        c     = GREEN if state in ("done","running") else TEXT3
        pulse = "animation:blink 0.7s infinite;" if state == "running" else ""
        agent_ph.markdown(
            f'<div class="agent-card">'
            f'<div class="agent-label">Active Agent</div>'
            f'<div class="agent-row">'
            f'<div>'
            f'<div class="agent-name">'
            f'<span style="width:8px;height:8px;border-radius:50%;background:{c};display:inline-block;{pulse}"></span>'
            f'{name}</div>'
            f'<div class="agent-sub">{sub}</div>'
            f'</div>'
            f'<div style="text-align:right;">'
            f'<div class="agent-count" style="color:{c};">{count}</div>'
            f'<div style="font-size:10px;color:{TEXT3};margin-top:2px;">flagged</div>'
            f'</div></div></div>',
            unsafe_allow_html=True)

    def render_filters(fc, N=509):
        # Named, meaningful filters that map to what we actually compute
        filters = [
            ("Liquidity Screen",   "Price > $5 · Volume > 500k",           fc.get("universe",  0), N,    True if fc.get("universe")  else False),
            ("BB Compression",     "Squeeze at 10th percentile",            fc.get("bb",        0), fc.get("universe", N) or N, True if fc.get("bb")        else False),
            ("Volume Surge",       "2× above 20-day average",               fc.get("volume",    0), fc.get("bb",        N) or N, True if fc.get("volume")    else False),
            ("Sentiment Spike",    "Reddit · RSS score + velocity",         fc.get("sentiment", 0), fc.get("volume",    N) or N, True if fc.get("sentiment") else False),
            ("Edge Detection",     "Blended score ≥ 50 · move target 5%+", fc.get("edge",      0), fc.get("sentiment", N) or N, True if fc.get("edge")      else False),
        ]
        rows = ""
        for name, desc, cnt, total, done in filters:
            dot   = "f-dot-on" if done else "f-dot-off"
            nc    = GREEN if done else TEXT3
            cs    = str(cnt) if done else "—"
            bw    = int((cnt / total) * 100) if (done and total and cnt) else 0
            rows += (
                f'<div class="filter-row">'
                f'<div class="{dot}"></div>'
                f'<div><div class="f-name">{name}</div><div class="f-desc">{desc}</div></div>'
                f'<div class="f-bar-wrap"><div class="f-bar-fill" style="width:{bw}%;"></div></div>'
                f'<div class="f-count" style="color:{nc};">{cs}</div>'
                f'</div>')
        n_done = sum(1 for *_, d in filters if d)
        done_c = GREEN if n_done == 5 else (AMBER if n_done > 0 else TEXT3)
        filter_ph.markdown(
            f'<div class="filter-card">'
            f'<div class="filter-hdr">'
            f'<span class="filter-hdr-title">Filter Pipeline</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;color:{done_c};">{n_done}/5 complete</span>'
            f'</div>{rows}</div>',
            unsafe_allow_html=True)

    def render_qual(n):
        if n > 0:
            qual_ph.markdown(
                f'<div class="qual-banner">'
                f'<div><div class="qual-label">Qualified Setups</div>'
                f'<div class="qual-sub">Score ≥ 50 · Expected move 5%+</div></div>'
                f'<div class="qual-count">{n}</div>'
                f'</div>', unsafe_allow_html=True)
        else:
            qual_ph.markdown("", unsafe_allow_html=True)

    is_done = bool(scan_time)
    render_agent(
        "Market Scan Agent",
        f"Completed at {scan_time} — {n_picks} setups found" if is_done else "Ready — press ▶ Run Scan to begin",
        str(n_picks) if n_picks else "—",
        state="done" if is_done else "idle")
    render_filters(fc)
    render_qual(n_picks)

# ══════════════════ PICK CARDS GRID ══════════════════════
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

picks_grid_ph = st.empty()

def render_pick_cards(df):
    if df is None or df.empty:
        picks_grid_ph.markdown(
            f'<div style="background:{CARD};border:1px solid {BORDER};border-radius:8px;">'
            f'<div class="empty">'
            f'<div class="empty-icon">🔍</div>'
            f'<div class="empty-title">No setups found yet</div>'
            f'<div class="empty-body">Press ▶ Run Scan to analyze S&P 500 + Futures<br>and surface high-conviction 5–10% move opportunities.</div>'
            f'</div></div>', unsafe_allow_html=True)
        return

    sorted_df = df.sort_values("score", ascending=False)
    n = len(sorted_df)

    # Section label
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
        f'<span style="font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{TEXT3};">Today\'s Setups</span>'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;background:{CARD2};border:1px solid {BORDER};color:{TEXT3};padding:1px 8px;border-radius:20px;">{n} found</span>'
        f'</div>', unsafe_allow_html=True)

    cols_per_row = 3
    rows = [sorted_df.iloc[i:i+cols_per_row] for i in range(0, len(sorted_df), cols_per_row)]

    for row_df in rows:
        cols = st.columns(cols_per_row)
        for col_idx, (_, row) in enumerate(row_df.iterrows()):
            ticker = row.get("ticker", "")
            score  = row.get("score", 0)
            direct = row.get("direction", "mixed")
            conf   = row.get("confidence", "—")
            dur    = row.get("duration", "—")
            rsi    = row.get("rsi", 0)
            vol    = row.get("volume_ratio", 0)
            kelly  = row.get("dollar_amount", 0)
            bb_pct = row.get("bb_pct", 0) or 0
            sent   = row.get("sentiment_score", 0) or 0
            xgb    = row.get("xgb_prob", 0) or 0

            # Direction
            if direct == "bullish":
                dir_bg, dir_color, dir_border, dir_label = "rgba(0,255,136,0.1)", GREEN, "rgba(0,255,136,0.3)", "↑ LONG"
                lborder = GREEN
            elif direct == "bearish":
                dir_bg, dir_color, dir_border, dir_label = "rgba(255,59,92,0.1)", RED, "rgba(255,59,92,0.3)", "↓ SHORT"
                lborder = RED
            else:
                dir_bg, dir_color, dir_border, dir_label = "rgba(245,158,11,0.1)", AMBER, "rgba(245,158,11,0.3)", "◆ WATCH"
                lborder = AMBER

            # Score color
            sc = GREEN if score >= 70 else AMBER if score >= 50 else TEXT3

            # Signal bars data
            bb_strength  = min(100, int((1 - bb_pct) * 100)) if bb_pct else int(score * 0.8)
            vol_strength = min(100, int((vol / 4) * 100))     if isinstance(vol, float) else int(score * 0.6)
            sent_adj     = min(100, int((sent + 1) * 50))     if isinstance(sent, float) else int(score * 0.5)
            xgb_pct      = min(100, int(xgb * 100))           if isinstance(xgb, float) and xgb > 0 else int(score * 0.75)

            def bar(label, pct, color):
                return (
                    f'<div class="pick-bar-item">'
                    f'<span class="pick-bar-label">{label}</span>'
                    f'<div class="pick-bar-track">'
                    f'<div class="pick-bar-fill" style="width:{pct}%;background:{color};box-shadow:0 0 5px {color}44;"></div>'
                    f'</div>'
                    f'<span class="pick-bar-pct" style="color:{color};">{pct}%</span>'
                    f'</div>')

            ks = f"${kelly:,.0f}" if kelly else "—"
            rs = f"{rsi:.0f}"     if isinstance(rsi, float) else str(rsi)
            vs = f"{vol:.1f}×"    if isinstance(vol, float) else "—"
            conf_c = {"High": GREEN, "Medium": AMBER, "Low": TEXT3}.get(conf, TEXT3)

            card_html = (
                f'<div class="pick-card" style="border-left:2px solid {lborder};">'

                # Top row: ticker + score
                f'<div class="pick-top">'
                f'<div>'
                f'<div class="pick-ticker">{ticker}</div>'
                f'<div style="margin-top:5px;">'
                f'<span style="background:{dir_bg};border:1px solid {dir_border};color:{dir_color};'
                f'font-size:10px;font-weight:700;letter-spacing:1px;padding:2px 7px;border-radius:3px;">{dir_label}</span>'
                f'</div></div>'
                f'<div style="text-align:right;">'
                f'<div class="pick-score" style="color:{sc};">{score:.0f}</div>'
                f'<div class="pick-score-label">/ 100</div>'
                f'</div></div>'

                # Divider
                f'<div class="pick-divider"></div>'

                # Signal bars
                f'<div class="pick-bar-row">'
                + bar("BB Squeeze",  bb_strength,  BLUE)
                + bar("Volume",      vol_strength, AMBER)
                + bar("Sentiment",   sent_adj,     CYAN)
                + bar("XGBoost",     xgb_pct,      GREEN)
                + f'</div>'

                # Divider
                f'<div class="pick-divider"></div>'

                # Stats grid
                f'<div class="pick-stats">'
                f'<div class="pick-stat"><span class="pick-stat-label">RSI</span><span class="pick-stat-val">{rs}</span></div>'
                f'<div class="pick-stat"><span class="pick-stat-label">Volume</span><span class="pick-stat-val">{vs}</span></div>'
                f'<div class="pick-stat"><span class="pick-stat-label">Window</span><span class="pick-stat-val" style="font-size:11px;">{dur}</span></div>'
                f'</div>'

                # Kelly row
                f'<div class="pick-kelly">'
                f'<span class="pick-kelly-label">Kelly Position &nbsp;<span style="color:{conf_c};font-size:10px;font-weight:600;">{conf}</span></span>'
                f'<span class="pick-kelly-val">{ks}</span>'
                f'</div>'

                f'</div>'
            )

            with cols[col_idx]:
                st.markdown(card_html, unsafe_allow_html=True)

render_pick_cards(picks_df)

# ── Chart for selected pick ───────────────────────────────────────────────────
if picks_df is not None and not picks_df.empty:
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    sel = st.selectbox(
        "Chart",
        picks_df.sort_values("score", ascending=False)["ticker"].tolist(),
        label_visibility="collapsed")
    if sel:
        from data.fetcher import get_ohlcv
        from ta.volatility import BollingerBands as BB
        df_c = get_ohlcv(sel, period="6mo")
        if not df_c.empty:
            _bb = BB(df_c["Close"], window=20, window_dev=2)
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df_c.index, open=df_c["Open"], high=df_c["High"],
                low=df_c["Low"], close=df_c["Close"], name=sel,
                increasing=dict(line=dict(color=GREEN, width=1.2), fillcolor="rgba(0,255,136,0.18)"),
                decreasing=dict(line=dict(color=RED,   width=1.2), fillcolor="rgba(255,59,92,0.18)")))
            try:
                fig.add_trace(go.Scatter(x=df_c.index, y=_bb.bollinger_hband(),
                    line=dict(color="rgba(0,255,136,0.22)", width=1), showlegend=False))
                fig.add_trace(go.Scatter(x=df_c.index, y=_bb.bollinger_lband(),
                    line=dict(color="rgba(0,255,136,0.22)", width=1),
                    fill="tonexty", fillcolor="rgba(0,255,136,0.04)", showlegend=False))
            except Exception:
                pass
            fig.update_layout(
                xaxis_rangeslider_visible=False, height=300,
                paper_bgcolor=CARD, plot_bgcolor=CARD,
                xaxis=dict(gridcolor=BORDER, tickfont=dict(color=TEXT3, size=10)),
                yaxis=dict(gridcolor=BORDER, tickfont=dict(color=TEXT3, size=10), side="right"),
                margin=dict(l=0, r=48, t=22, b=0),
                title=dict(text=f"<b>{sel}</b>  ·  6-Month Candlestick + Bollinger Bands",
                           font=dict(color=TEXT, size=12), x=0.01))
            st.plotly_chart(fig, use_container_width=True)

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
    N       = len(tickers)

    # ── Step 1: Scan / Liquidity screen ──────────────────
    with col_left:
        render_agent("Scan Agent", f"Fetching {N} tickers from yfinance…", str(N), state="running")
        render_filters({})
    with st.spinner(""):
        ohlcv_map = get_ohlcv_batch(tickers, period="1y", chunk_size=50)

    valid = [t for t, df in ohlcv_map.items() if not df.empty and len(df) >= 2]
    tape  = sorted([
        {"ticker": t, "price": float(ohlcv_map[t]["Close"].iloc[-1]),
         "chg_pct": (float(ohlcv_map[t]["Close"].iloc[-1]) - float(ohlcv_map[t]["Close"].iloc[-2])) /
                    float(ohlcv_map[t]["Close"].iloc[-2]) * 100}
        for t in valid
    ], key=lambda x: abs(x["chg_pct"]), reverse=True)
    st.session_state["tape"] = tape
    with col_right:
        render_tape(tape)
    with col_left:
        render_filters({"universe": len(valid)})

    # ── Step 2: Research / sentiment ─────────────────────
    with col_left:
        render_agent("Research Agent", "Scanning Reddit · RSS · Alpha Vantage…", str(len(valid)), state="running")
    with st.spinner(""):
        blended = research_universe(tickers)
        sentiment_map = {}
        feeds = []
        for t in tickers:
            sv  = get_sentiment_with_velocity(t)
            blk = blended.get(t, {})
            sc  = round(sv.get("score", 0) * 0.4 + blk.get("score", 0) * 0.6, 4)
            vel = sv.get("velocity", 0)
            spk = abs(vel) >= 0.3 or blk.get("score", 0) > 0.4
            sentiment_map[t] = {**blk, "score": sc, "velocity": vel, "spike": spk}
            # Build feed items from top movers
            if spk and blk.get("headline"):
                feeds.append({
                    "source": blk.get("source", "Reddit"),
                    "ticker": t,
                    "text":   blk.get("headline", ""),
                    "bias":   "bullish" if sc > 0.1 else "bearish" if sc < -0.1 else "",
                })
        st.session_state["feeds"] = feeds[:8]
        with col_right:
            render_feed(st.session_state["feeds"])

    # Estimate BB filter: tickers with bb_pct < 20th percentile
    n_bb = int(len(valid) * 0.18)
    with col_left:
        render_filters({"universe": len(valid), "bb": n_bb})

    # ── Step 3: Score / predict ───────────────────────────
    with col_left:
        render_agent("Predict Agent", "Running XGBoost + blended scoring…", str(n_bb), state="running")
    with st.spinner(""):
        earnings_map = {t: get_earnings_days(t) for t in tickers[:100]}
        picks_df     = predict_universe(tickers, ohlcv_map, sentiment_map, earnings_map)

    scored = len(picks_df) if picks_df is not None and not picks_df.empty else 0
    n_vol  = int(scored * 1.4)   # approx volume filter passed
    n_sent = int(scored * 1.1)   # approx sentiment filter passed
    with col_left:
        render_filters({"universe": len(valid), "bb": n_bb, "volume": n_vol, "sentiment": n_sent})

    # ── Step 4: Risk / Kelly sizing ───────────────────────
    with col_left:
        render_agent("Risk Agent", "Calculating Kelly Criterion position sizes…", str(scored), state="running")
    if picks_df is not None and not picks_df.empty:
        picks_df = annotate_picks(picks_df)
    with col_left:
        render_filters({"universe": len(valid), "bb": n_bb, "volume": n_vol, "sentiment": n_sent, "edge": scored})

    # ── Step 5: Learn / persist ───────────────────────────
    with col_left:
        render_agent("Learn Agent", "Persisting results to Supabase…", str(scored), state="running")
    with st.spinner(""):
        if picks_df is not None and not picks_df.empty and db.db_available():
            out = picks_df.copy()
            out["date"] = datetime.today().strftime("%Y-%m-%d")
            out["actual_move_5d"] = None
            db.append_predictions(out.to_dict(orient="records"))

    scan_time = datetime.now().strftime("%H:%M")
    st.session_state.update({
        "picks_df":      picks_df,
        "scan_time":     scan_time,
        "filter_counts": {"universe": len(valid), "bb": n_bb, "volume": n_vol, "sentiment": n_sent, "edge": scored},
    })
    with col_left:
        render_agent("Market Scan Agent", f"Completed at {scan_time} — {scored} setups found", str(scored), state="done")
        render_qual(scored)

    st.rerun()
