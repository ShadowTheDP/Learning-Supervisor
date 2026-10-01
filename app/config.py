import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RESOURCES_DIR = DATA_DIR / "resources"
STATE_DIR = DATA_DIR / "state"
IMPORT_JOBS_DIR = STATE_DIR / "import_jobs"
DOCLING_ARTIFACTS_DIR = STATE_DIR / "docling_artifacts"
DOCLING_EASYOCR_DIR = DOCLING_ARTIFACTS_DIR / "EasyOcr"
DOCLING_PDF_BACKEND = (os.getenv("DOCLING_PDF_BACKEND", "local").strip().lower() or "local")


def _read_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() not in {"", "0", "false", "no", "off"}


DOCLING_PDF_OCR_ENABLED = _read_bool_env("DOCLING_PDF_OCR_ENABLED", False)
DOCLING_PDF_FORMULA_ENRICHMENT = _read_bool_env("DOCLING_PDF_FORMULA_ENRICHMENT", False)
DOCLING_EASYOCR_LANGS = tuple(
    part.strip()
    for part in os.getenv("DOCLING_EASYOCR_LANGS", "en").split(",")
    if part.strip()
) or ("en",)
DOCLING_SERVE_URL = os.getenv("DOCLING_SERVE_URL", "").strip()
if not DOCLING_SERVE_URL:
    DOCLING_SERVE_URL = os.getenv("DOCLING_REMOTE_URL", "").strip()
DOCLING_SERVE_API_KEY = os.getenv("DOCLING_SERVE_API_KEY", "").strip()
DOCLING_REMOTE_TIMEOUT_SECONDS = int(os.getenv("DOCLING_REMOTE_TIMEOUT_SECONDS", "180"))
OUTPUT_DIR = PROJECT_ROOT / "output"
DB_PATH = STATE_DIR / "learning_supervisor.db"
REVIEW_INTERVALS_DAYS = (1, 3, 7, 14)
DEFAULT_DAILY_CAPACITY_MINUTES = 45


def ensure_runtime_dirs() -> None:
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    IMPORT_JOBS_DIR.mkdir(parents=True, exist_ok=True)
    DOCLING_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCLING_EASYOCR_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
