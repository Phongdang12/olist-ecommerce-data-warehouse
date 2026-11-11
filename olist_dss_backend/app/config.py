import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_MODE = os.getenv("DSS_DATA_MODE", "demo").strip().lower()
DATABASE_URL = os.getenv("DSS_DATABASE_URL", "").strip()
MODEL_PATH = Path(os.getenv("DSS_MODEL_PATH", str(BASE_DIR / "artifacts" / "customer_kmeans.joblib")))
RANDOM_SEED = int(os.getenv("DSS_RANDOM_SEED", "42"))
