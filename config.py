"""SENTINEL configuration — tuned to the REAL data_v2 schema (520 emails)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ---------------- Data source ----------------
DATA_DIR = Path(os.getenv("SENTINEL_DATA", str(ROOT / "mock_data")))
MODE = os.getenv("SENTINEL_MODE", "folder")            # folder | server
SERVER_URL = os.getenv("SENTINEL_SERVER_URL", "").rstrip("/")

# ---------------- LLM backend ----------------
LLM_PROVIDER = os.getenv("SENTINEL_LLM_PROVIDER", "")  # "" = rules only
LLM_API_KEY = os.getenv("SENTINEL_LLM_KEY", "")
LLM_MODEL = os.getenv("SENTINEL_LLM_MODEL", "gpt-4o-mini")
LLM_FAST_MODEL = os.getenv("SENTINEL_LLM_FAST_MODEL", LLM_MODEL)
LLM_TEMPERATURE = float(os.getenv("SENTINEL_LLM_TEMP", "0"))
LLM_CACHE = os.getenv("SENTINEL_LLM_CACHE", "1") == "1"
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
