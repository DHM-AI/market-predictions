from dotenv import load_dotenv
import os

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
ALPHA_VANTAGE_KEY  = os.getenv("ALPHA_VANTAGE_KEY", "")
SLACK_WEBHOOK_URL  = os.getenv("SLACK_WEBHOOK_URL", "")
GMAIL_USER         = os.getenv("GMAIL_USER", "")        # legacy — kept for optional fallback
GMAIL_APP_PASS     = os.getenv("GMAIL_APP_PASS", "")    # legacy
ALERT_EMAIL        = os.getenv("ALERT_EMAIL", "renato@deltahubmedia.com")  # legacy

# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# ── Alpaca ────────────────────────────────────────────────────────────────────
ALPACA_API_KEY    = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL   = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
ALPACA_LIVE_MODE  = os.getenv("ALPACA_LIVE_MODE", "false").lower() == "true"

# ── Universe ──────────────────────────────────────────────────────────────────
FUTURES = ["ES=F", "NQ=F", "RTY=F", "CL=F", "GC=F", "ZB=F"]

# ── Watchlist — always scanned even if not in S&P 500 ─────────────────────────
# Add any ticker here to force it into every scan.
WATCHLIST = [
    "AAL",   # American Airlines — removed from S&P 500 in 2020, still high volume
]

# ── Signal thresholds ─────────────────────────────────────────────────────────
BB_SQUEEZE_PERCENTILE  = 10
ATR_COMPRESSION_RATIO  = 0.75
VOLUME_SURGE_RATIO     = 2.0
RSI_OVERBOUGHT         = 72
RSI_OVERSOLD           = 28
EARNINGS_PROXIMITY_DAYS = 10

# ── Scoring weights (must sum to 100) ─────────────────────────────────────────
WEIGHTS = {
    "bb_squeeze":         18,   # was 25 — reduced to make room for new signals
    "atr_compression":    10,   # was 15
    "volume_surge":       15,   # was 20
    "sentiment_spike":    15,   # was 20
    "rsi_extreme":        10,   # unchanged
    "earnings_proximity":  7,   # was 10
    "candlestick":         8,   # NEW — pattern detection (hammer, engulfing, pin bar)
    "options_flow":       10,   # NEW — put/call ratio institutional signal
    "short_squeeze":       7,   # NEW — high short interest + bullish momentum
}
# Total: 18+10+15+15+10+7+8+10+7 = 100

# ── Market regime ──────────────────────────────────────────────────────────────
REGIME_CACHE_MINUTES  = 30   # re-fetch regime every 30 minutes during scan
ENABLE_OPTIONS_FLOW   = True  # set False to skip options API (faster scans)

# ── Goal ──────────────────────────────────────────────────────────────────────
MONTHLY_TARGET_PCT  = 0.10   # 10% per month target return

# ── Prediction ────────────────────────────────────────────────────────────────
MIN_SCORE_TO_ALERT  = 50
TOP_N_CLAUDE_ANALYSIS = 5
MOVE_TARGET_PCT     = 0.07   # 7% move target (raised from 5% to support 10%/mo goal)

# ── Model blending weights ────────────────────────────────────────────────────
XGB_WEIGHT       = 0.70
SENTIMENT_WEIGHT = 0.30

# ── Kelly Criterion / position sizing ─────────────────────────────────────────
BANKROLL          = float(os.getenv("BANKROLL", "50000"))
KELLY_WIN_PCT     = 0.07   # expected gain on a win (7% move target — aligned with 10%/mo goal)
KELLY_LOSS_PCT    = 0.03   # expected loss if wrong (3% stop)
KELLY_FRACTION    = 0.5    # use half-Kelly for safety
MAX_POSITION_PCT  = 0.15   # max 15% of bankroll per trade (raised to support 10%/mo goal)
DAILY_LOSS_LIMIT_PCT = 0.05  # halt trading if down 5% in a day

# ── Trailing stop ──────────────────────────────────────────────────────────────
# When a position gains TRAIL_TRIGGER_PCT, cancel the fixed SL and replace
# with an Alpaca native trailing stop that follows price up automatically.
TRAIL_TRIGGER_PCT = 0.03   # activate trailing when position is up 3%
TRAIL_PCT         = 0.03   # trail 3% below the highest price since activation

# ── Auto-execution threshold ──────────────────────────────────────────────────
# Only auto-execute if score >= this AND Alpaca is configured
AUTO_EXECUTE_MIN_SCORE = 70

# ── Paths ─────────────────────────────────────────────────────────────────────
LOGS_DIR            = "logs"
PREDICTIONS_CSV     = "logs/predictions.csv"   # legacy, kept for compat
MODEL_PATH          = "model/saved/xgb_model.pkl"
FEATURE_NAMES_PATH  = "model/saved/feature_names.json"

# ── Scheduler ─────────────────────────────────────────────────────────────────
SCAN_TIME_ET = "08:00"

# ── Training ──────────────────────────────────────────────────────────────────
TRAIN_YEARS        = 3
TRAIN_TEST_SPLIT   = 0.80
