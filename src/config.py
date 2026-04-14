import os
from pathlib import Path
from dotenv import load_dotenv

# Project root directory (parent of src/)
BASE_DIR = Path(__file__).resolve().parents[1]

# Load .env from src/ directory before reading any env vars
load_dotenv(BASE_DIR / "src" / ".env", override=True)

# Redis (for Flask-Limiter)
RATELIMIT_STORAGE_URL = os.getenv("RATELIMIT_STORAGE_URL", "redis://localhost:6379")

# Flask
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

# Firestore
FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", str(BASE_DIR / "serviceAccountKey.json"))

# Firebase Auth (REST API login)
FIREBASE_WEB_API_KEY = os.getenv("FIREBASE_WEB_API_KEY", "")

# Sensor / device API key (SmartPost hardware)
SENSOR_API_KEY = os.getenv("SENSOR_API_KEY", "")

# Uploads (local disk)
UPLOAD_ROOT = BASE_DIR / "src" / "uploads"
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MEDIA_TTL_SECONDS = 180  # 3 minutes

# Notifications
NOTIFICATION_SCHEMA_VERSION = 1
