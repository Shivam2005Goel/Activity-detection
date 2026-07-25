import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
# Load .env file automatically if present
load_dotenv(BASE_DIR / ".env")

# File paths
DATA_PATH = str(BASE_DIR / "data" / "sample_transactions.csv")
AUDIT_LOG_PATH = str(BASE_DIR / "audit_log.jsonl")
BACKTEST_RESULTS_PATH = str(BASE_DIR / "backtest_results.json")

# Structuring detection
STRUCTURING_AMOUNT_THRESHOLD = 10000.0
STRUCTURING_AMOUNT_LOWER_BOUND = 9000.0     # "just under" range
STRUCTURING_MIN_TXN_COUNT = 5
STRUCTURING_WINDOW_DAYS = 5

# Risk classification thresholds (0-100 scale)
RISK_LOW_MAX = 30.0
RISK_MEDIUM_MAX = 70.0
RISK_HIGH_MAX = 90.0
# >90 = Critical

# ML anomaly detection
ML_CONTAMINATION = 0.05          # expected proportion of anomalies
ML_ANOMALY_SCORE_THRESHOLD = 0.6 # normalized 0-1

# Consensus engine
MIN_TRUST_SCORE_FOR_HIGH_RISK = 60.0   # below this, downgrade or route to Verifier

# Agent loop safety
MAX_PLANNER_STEPS = 10

# LLM & OpenRouter API Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", os.getenv("OPENAI_API_KEY", os.getenv("ANTHROPIC_API_KEY", "")))
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
LLM_MAX_RETRIES = 2
LLM_TIMEOUT_SECONDS = 20.0

# Default fallback filter window if no date range detected in query
DEFAULT_LOOKBACK_DAYS = 90
