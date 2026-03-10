from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore

from config import FIREBASE_KEY_PATH

if not Path(FIREBASE_KEY_PATH).exists():
    raise FileNotFoundError(f"Firestore key not found at: {FIREBASE_KEY_PATH}")

cred = credentials.Certificate(FIREBASE_KEY_PATH)

# Avoid "already initialized" errors when Flask auto-reloads
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()
