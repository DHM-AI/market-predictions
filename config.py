from dotenv import load_dotenv
import os

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
ALPHA_VANTAGE_KEY  = os.getenv("ALPHA_VANTAGE_KEY", "")
GMAIL_USER         = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASS     = os.getenv("GMAIL_APP_PASS", "")
ALERT_EMAIL        = os.getenv("ALERT_EMAIL", "renato@deltahubmedia.com")

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

# ── Signal thresholds ─────────────────────────────────────────────────────────
BB_SQUEEZE_PERCENTILE  = 10
ATR_COMPRESSION_RATIO  = 0.75
VOLUME_SURGE_RATIO     = 2.0
RSI_OVERBOUGHT         = 72
RSI_OVERSOLD           = 28
EARNINGS_PROXIMITY_DAYS = 10

# ── Scoring weights (must sum to 100) ─────────────────────────────────────────
WEIGHTS = {
    "bb_squeeze":         25,
    "atr_compression":    15,
    "volume_surge":       20,
    "sentiment_spike":    20,
    "rsi_extreme":        10,
    "earnings_proximity": 10,
}

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
