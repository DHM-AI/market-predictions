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
# These are scanned on every run regardless of index membership.
# S&P 500 stocks are included automatically — list only extras here.
WATCHLIST = [
    # ── Airlines (high volume, volatile, often not in S&P 500) ────────────────
    "AAL",   # American Airlines  — removed from S&P 500 in 2020
    "UAL",   # United Airlines    — may rotate in/out of S&P 500
    "DAL",   # Delta Air Lines    — may rotate in/out of S&P 500
    "LUV",   # Southwest Airlines — may rotate in/out of S&P 500
    "JBLU",  # JetBlue            — not in S&P 500

    # ── High-profile tech / growth not always in S&P 500 ─────────────────────
    "TSLA",  # Tesla              — in S&P 500 (deduped automatically if so)
    "RIVN",  # Rivian             — EV, not in S&P 500
    "LCID",  # Lucid Motors       — EV, not in S&P 500
    "HOOD",  # Robinhood          — fintech, not in S&P 500
    "SOFI",  # SoFi Technologies  — fintech, not in S&P 500
    "RBLX",  # Roblox             — gaming/metaverse
    "COIN",  # Coinbase           — crypto exchange
    "PLTR",  # Palantir           — AI/data (may be in S&P 500)
    "SNOW",  # Snowflake          — cloud data
    "PATH",  # UiPath             — automation/AI

    # ── Recent high-volume IPOs (auto-updated via get_recent_ipos()) ──────────
    # Dynamic IPO list is appended at runtime — see universe.py
]

# How many months back to look for recent IPOs
IPO_LOOKBACK_MONTHS = 12
# Min avg daily volume for an IPO to be worth scanning
IPO_MIN_VOLUME = 1_000_000

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

# ── Sentiment Guard ───────────────────────────────────────────────────────────
# Monitors open positions for sentiment reversal and takes protective action.
# Scores range from -1.0 (very bearish) to +1.0 (very bullish).
GUARD_WARN_THRESHOLD    = -0.15  # LONG:  alert when sentiment drops below this
GUARD_TIGHTEN_THRESHOLD = -0.35  # LONG:  tighten stop to 1.5% when below this
GUARD_CLOSE_THRESHOLD   = -0.60  # LONG:  close position when sentiment this bad
# (reversed for SHORT positions)

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

# ── Crypto ────────────────────────────────────────────────────────────────────
# Alpaca uses "BTC/USD" format; yfinance uses "BTC-USD"
ENABLE_CRYPTO = os.getenv("ENABLE_CRYPTO", "true").lower() == "true"
CRYPTO_UNIVERSE = {
    "BTC/USD":  "BTC-USD",   # Bitcoin
    "ETH/USD":  "ETH-USD",   # Ethereum
    "SOL/USD":  "SOL-USD",   # Solana
    "DOGE/USD": "DOGE-USD",  # Dogecoin
}
# Reverse map: yfinance symbol → Alpaca symbol
CRYPTO_YFINANCE_TO_ALPACA = {v: k for k, v in CRYPTO_UNIVERSE.items()}
CRYPTO_YFINANCE_TICKERS   = list(CRYPTO_UNIVERSE.values())   # ["BTC-USD", ...]
CRYPTO_ALPACA_TICKERS     = list(CRYPTO_UNIVERSE.keys())     # ["BTC/USD", ...]

# ── Options ───────────────────────────────────────────────────────────────────
# Requires Level 3 options approval on Alpaca — set ENABLE_OPTIONS=true only after
# applying and receiving approval in the Alpaca dashboard.
ENABLE_OPTIONS          = os.getenv("ENABLE_OPTIONS", "true").lower() == "true"
OPTIONS_MIN_SCORE       = 85   # only use options for very high-confidence picks
OPTIONS_EARNINGS_WINDOW = 7    # days: place iron butterfly within 7 days of earnings
