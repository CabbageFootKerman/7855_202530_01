import json
import threading
from pathlib import Path

from flask import session
from werkzeug.security import generate_password_hash


# ---------------------------
# User persistence (users.json)
# ---------------------------

# USERS_FILE is resolved relative to the src/ directory (where app.py lives)
USERS_FILE = Path(__file__).resolve().parents[1] / "users.json"
_users_lock = threading.Lock()


def load_users() -> dict:
    """Load users from users.json. Returns {} if missing/invalid."""
    if not USERS_FILE.exists():
        return {}
    try:
        with USERS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_users(users: dict) -> None:
    """Persist users to users.json (safe write via temp file)."""
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = USERS_FILE.with_suffix(".tmp")
    with _users_lock:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, sort_keys=True)
        tmp.replace(USERS_FILE)


def looks_like_hash(value: str) -> bool:
    """Werkzeug hashes usually look like: 'scrypt:...' or 'pbkdf2:...'"""
    return isinstance(value, str) and (value.startswith("scrypt:") or value.startswith("pbkdf2:"))


def get_current_user():
    return session.get("username")


# ---------------------------
# Bootstrap: load users + ensure demo user
# ---------------------------

USERS = load_users()

if "student" not in USERS:
    USERS["student"] = generate_password_hash("secret")
    save_users(USERS)
elif not looks_like_hash(USERS["student"]):
    USERS["student"] = generate_password_hash(USERS["student"])
    save_users(USERS)
