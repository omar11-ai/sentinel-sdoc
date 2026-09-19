"""SENTINEL configuration — tuned to the REAL data_v2 schema (520 emails)."""
import os
from pathlib import Path

# load .env (gitignored) before reading env vars; real environment still wins
_ENV_FILE = Path(__file__).resolve().parent / ".env"
if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

ROOT = Path(__file__).resolve().parent

# ---------------- Data source ----------------
DATA_DIR = Path(os.getenv("SENTINEL_DATA", str(ROOT / "mock_data")))
MODE = os.getenv("SENTINEL_MODE", "folder")            # folder | server
SERVER_URL = os.getenv("SENTINEL_SERVER_URL", "").rstrip("/")

# ---------------- LLM backend ----------------
LLM_PROVIDER = os.getenv("SENTINEL_LLM_PROVIDER", "")  # "" = rules only
LLM_API_KEY = os.getenv("SENTINEL_LLM_KEY", "")
LLM_MODEL = os.getenv("SENTINEL_LLM_MODEL", "gemini-flash-latest")
LLM_FAST_MODEL = os.getenv("SENTINEL_LLM_FAST_MODEL", "gemini-3.1-flash-lite")
LLM_TEMPERATURE = float(os.getenv("SENTINEL_LLM_TEMP", "0"))
LLM_CACHE = os.getenv("SENTINEL_LLM_CACHE", "1") == "1"
LLM_BATCH = os.getenv("SENTINEL_LLM_BATCH", "1") == "1"  # LLM in full-batch runs (quota!)
CACHE_DIR = ROOT / ".cache" / "llm"

# ---------------- Feature flags ----------------
USE_LLM = os.getenv("SENTINEL_USE_LLM", "auto")        # auto | on | off
FLAG_COURT = os.getenv("SENTINEL_COURT", "1") == "1"
COURT_CONFIDENCE = float(os.getenv("SENTINEL_COURT_CONF", "0.60"))
FLAG_ADVERSARIAL = os.getenv("SENTINEL_ADVERSARIAL", "1") == "1"
ADVERSARIAL_MODE = os.getenv("SENTINEL_ADVERSARIAL_MODE", "advisory")
FLAG_CORPUS = os.getenv("SENTINEL_CORPUS", "1") == "1"
FLAG_SANITIZE = os.getenv("SENTINEL_SANITIZE", "1") == "1"

# ---------------- Escalation policy ----------------
MIN_COMMON_FIELDS = int(os.getenv("SENTINEL_MIN_COMMON", "5"))  # comparable fields needed

# ---------------- Self-eval scoring server ----------------
SCORING_URL = os.getenv("SENTINEL_SCORING_URL", "").rstrip("/")

# ---------------- Canonical v2 schema (from the participant guide) ----------------
FIELDS = [
    "shipper",
    "consignee",
    "notify_party",
    "port_of_loading",
    "port_of_discharge",
    "container_count",
    "gross_weight_kg",
]

CATEGORIES = ["BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM"]
STATUSES = ["OK", "MISMATCH", "NEEDS_REVIEW"]
REVIEW_REASONS = ["wrong_doc_type", "missing_attachment", "unreadable", "missing_value"]
STATUS_FOR_NON_BL = "OK"


def effective_llm_enabled() -> bool:
    if USE_LLM == "off":
        return False
    if USE_LLM == "on":
        return bool(LLM_PROVIDER and LLM_API_KEY)
    return bool(LLM_PROVIDER and LLM_API_KEY)  # auto
