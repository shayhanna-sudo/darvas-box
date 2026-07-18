"""Non-secret configuration for Darvas-Bot. Secrets live in secrets_conf.py (gitignored)."""

# Darvas box engine
CONFIRM_DAYS = 3           # consecutive days to confirm a ceiling / floor
HIGH_LOOKBACK = 252        # window for new-high detection (~52 weeks)
BREAKOUT_BUFFER = 0.001    # 0.1% above top (buy-stop) / below bottom (stop-loss)

# Volume trigger (institutional fingerprint)
VOL_WINDOW = 50            # average volume window
VOL_MULT = 2.0             # current volume must exceed VOL_MULT * avg

# Technical pre-filters
SMA_TREND = 200            # price must be above this SMA
MIN_PRICE = 5.0            # skip sub-$5 names
MIN_AVG_DOLLAR_VOL = 5_000_000  # liquidity floor

# Fundamental gate (deterministic, pre-AI)
MIN_EPS_YOY_GROWTH = 0.05  # 10% YoY EPS growth
MIN_REV_YOY_GROWTH = 0.05  # 10% YoY revenue growth

# Risk management
MAX_TRADES_PER_DAY = 20
RISK_PER_TRADE = 0.01      # 1% of equity risked per position
MAX_OPEN_POSITIONS = 10
KILL_SWITCH = False        # True = detect & alert only, never send orders

# Scheduling
SCAN_HOUR_UTC = 21
SCAN_MINUTE_UTC = 15

# Paths
DB_PATH = "data/darvas.db"

# P3 filters
MAX_BOX_WIDTH = 0.12       # reject boxes wider than 12% (stop distance = risk)
NEAR_HIGH_PCT = 0.05       # box top must be within 5% of the 52-week high

# AI layer (Gemini)
GEMINI_MODEL = "gemini-2.5-flash"

# Position sizing
MAX_POSITION_PCT = 0.25    # one position never exceeds 25% of equity
ACCOUNT_EQUITY = 100000    # paper default; P6 pulls real equity from Alpaca
