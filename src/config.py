import os
from pathlib import Path

# Project root directory (parent of src/)
BASE_DIR = Path(__file__).resolve().parents[1]

# Flask
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

# Firestore
FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", str(BASE_DIR / "serviceAccountKey.json"))

# Uploads (local disk)
UPLOAD_ROOT = BASE_DIR / "src" / "uploads"
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MEDIA_TTL_SECONDS = 180  # 3 minutes

# Notifications
NOTIFICATION_SCHEMA_VERSION = 1
