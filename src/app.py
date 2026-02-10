import os
import json
import threading
from pathlib import Path
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

# ---------------------------
# User persistence (users.json)
# ---------------------------

USERS_FILE = Path(app.root_path) / "users.json"
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
    # Werkzeug hashes usually look like: "scrypt:..." or "pbkdf2:..."
    return isinstance(value, str) and (value.startswith("scrypt:") or value.startswith("pbkdf2:"))

# Load users from disk
USERS = load_users()

# Ensure demo user exists; migrate plaintext if needed
if "student" not in USERS:
    USERS["student"] = generate_password_hash("secret")
    save_users(USERS)
elif not looks_like_hash(USERS["student"]):
    # Migrate plaintext -> hash
    USERS["student"] = generate_password_hash(USERS["student"])
    save_users(USERS)

def get_current_user():
    return session.get("username")

# ---------------------------
# Routes
# ---------------------------

@app.route("/")
def home():
    # If not logged in, show landing page with Login + Sign Up buttons
    if not get_current_user():
        return render_template(
            "landing.html",
            project_name="Smart Post"
        )

    # If logged in, send them to a demo device page
    return redirect(url_for("device_page", device_id="demo123"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", error=None)

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    stored = USERS.get(username)

    # Supports hashed passwords; also supports legacy plaintext once (auto-migrates)
    if stored and looks_like_hash(stored) and check_password_hash(stored, password):
        session["username"] = username
        return redirect(url_for("home"))

    if stored and (not looks_like_hash(stored)) and stored == password:
        # Legacy plaintext login succeeds, then migrate to hash
        USERS[username] = generate_password_hash(password)
        save_users(USERS)
        session["username"] = username
        return redirect(url_for("home"))

    return render_template("login.html", error="Invalid credentials.")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html", error=None)

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        return render_template("signup.html", error="Username and password are required.")

    if username in USERS:
        return render_template("signup.html", error="Username already exists.")

    USERS[username] = generate_password_hash(password)
    save_users(USERS)

    session["username"] = username
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/device/<device_id>")
def device_page(device_id):
    if not get_current_user():
        return redirect(url_for("login"))
    return render_template("device.html", device_id=device_id)

# ----- Stub APIs so UI can load -----

@app.route("/api/device/<device_id>/state", methods=["GET"])
def api_device_state(device_id):
    if not get_current_user():
        return jsonify({"error": "Not logged in."}), 401

    return jsonify({
        "device_id": device_id,
        "door_state": "closed",
        "weight_g": 0,
        "last_update_iso": datetime.now(timezone.utc).isoformat(),
        "cameras": {
            "cam1": "/static/placeholder.jpg",
            "cam2": "/static/placeholder.jpg",
            "cam3": "/static/placeholder.jpg"
        }
    }), 200

@app.route("/api/device/<device_id>/command", methods=["POST"])
def api_device_command(device_id):
    username = get_current_user()
    if not username:
        return jsonify({"error": "Not logged in."}), 401

    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json."}), 415

    data = request.get_json(silent=True) or {}
    cmd = data.get("command")

    if cmd not in ("open", "close"):
        return jsonify({"error": "command must be 'open' or 'close'."}), 400

    print(f"COMMAND RECEIVED user={username} device={device_id} command={cmd}", flush=True)
    return jsonify({"message": f"Command '{cmd}' received for {device_id}."}), 200

if __name__ == "__main__":
    app.run(debug=True, port=5000)
