from pathlib import Path
import re


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATASET_DIR = BASE_DIR / "datasets"
MODELS_DIR = BASE_DIR / "models"
LOGS_DIR = BASE_DIR / "logs"

DB_PATH = DATA_DIR / "access_control.db"
MODEL_PATH = MODELS_DIR / "lbph_model.yml"
LOG_FILE = LOGS_DIR / "access_control.log"

CAMERA_INDEX = 0
CAPTURE_SAMPLES = 30
FACE_SIZE = (200, 200)
RECOGNITION_THRESHOLD = 58.0
REQUIRED_BLINKS = 1
LIVENESS_TIMEOUT_SECONDS = 18
LAPLACIAN_SHARPNESS_THRESHOLD = 35.0
MIN_OPEN_EYE_FRAMES = 2
MIN_CLOSED_EYE_FRAMES = 2
WINDOW_NAME_CAPTURE = "Dataset Capture"
WINDOW_NAME_ACCESS = "Face Access Point"


def ensure_directories() -> None:
    for directory in (DATA_DIR, DATASET_DIR, MODELS_DIR, LOGS_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def staff_id_storage_key(staff_id: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_-]+", "_", staff_id.strip())
    sanitized = sanitized.strip("._")
    return sanitized or "user"
