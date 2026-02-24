import os
import json
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
from typing import Any, Dict, List, Optional


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

# --- Firestore setup ---
BASE_DIR = Path(__file__).resolve().parents[1]  # goes from /src/app.py up to project root
KEY_PATH = os.getenv("FIREBASE_KEY_PATH", str(BASE_DIR / "serviceAccountKey.json"))

if not Path(KEY_PATH).exists():
    raise FileNotFoundError(f"Firestore key not found at: {KEY_PATH}")

cred = credentials.Certificate(KEY_PATH)

# Avoid "already initialized" errors when Flask auto-reloads
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()
# --- end Firestore setup ---

# --- Uploads (local disk) ---
UPLOAD_ROOT = BASE_DIR / "src" / "uploads"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MEDIA_TTL_SECONDS = 180  # 3 minutes
# --- end uploads ---


# ---------------------------
# Notification scaffold (extensible)
# ---------------------------

NOTIFICATION_SCHEMA_VERSION = 1


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize_firestore_value(value):
    """Convert Firestore/python values into JSON-safe forms for API responses."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _serialize_firestore_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize_firestore_value(v) for v in value]
    return value


def _serialize_doc(doc) -> dict:
    data = doc.to_dict() or {}
    data = _serialize_firestore_value(data)
    data["id"] = doc.id
    return data


class NotificationChannel:
    """
    Base channel interface.
    Teammates can add WebPushChannel / MobilePushChannel later and register them.
    """
    name = "base"

    def deliver(self, payload: dict, recipients: List[str]) -> dict:
        raise NotImplementedError


class FirestoreEventLogChannel(NotificationChannel):
    """
    Writes a global event log:
      notification_events/{event_id}
    Useful for debugging, auditing, and demoing.
    """
    name = "firestore_event_log"

    def __init__(self, db_client):
        self.db = db_client

    def deliver(self, payload: dict, recipients: List[str]) -> dict:
        event_id = payload["event_id"]
        event_doc = {
            **payload,
            "recipient_usernames": recipients,
            "logged_at": firestore.SERVER_TIMESTAMP,
        }
        self.db.collection("notification_events").document(event_id).set(event_doc)
        return {"channel": self.name, "status": "ok", "logged_event_id": event_id}


class FirestoreUserInboxChannel(NotificationChannel):
    """
    Writes per-user inbox entries:
      users/{username}/notifications/{event_id}
    This is the actual in-app notification store.
    """
    name = "firestore_user_inbox"

    def __init__(self, db_client):
        self.db = db_client

    def deliver(self, payload: dict, recipients: List[str]) -> dict:
        event_id = payload["event_id"]
        writes = 0

        for username in recipients:
            doc_ref = (
                self.db.collection("users")
                .document(username)
                .collection("notifications")
                .document(event_id)
            )

            doc_ref.set({
                **payload,
                "username": username,  # recipient
                "read": False,
                "read_at": None,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
                "delivery": {
                    "in_app": {"status": "delivered", "at_client_iso": _utc_now_iso()},
                    # placeholders for future channels
                    "web_push": {"status": "not_attempted"},
                    "mobile_push": {"status": "not_attempted"},
                },
            }, merge=True)

            writes += 1

        return {"channel": self.name, "status": "ok", "writes": writes}


class StubWebPushChannel(NotificationChannel):
    """
    Placeholder only. Teammates can replace internals with FCM/web push later.
    """
    name = "web_push_stub"

    def deliver(self, payload: dict, recipients: List[str]) -> dict:
        return {
            "channel": self.name,
            "status": "skipped",
            "reason": "stub_not_implemented",
            "recipient_count": len(recipients),
        }


class StubMobilePushChannel(NotificationChannel):
    """
    Placeholder only. Teammates can replace internals with FCM APNs/Android later.
    """
    name = "mobile_push_stub"

    def deliver(self, payload: dict, recipients: List[str]) -> dict:
        return {
            "channel": self.name,
            "status": "skipped",
            "reason": "stub_not_implemented",
            "recipient_count": len(recipients),
        }


class NotificationService:
    """
    Notification orchestration layer.
    This is the key structural piece: one publish() call fans out to channels.
    """
    def __init__(self, db_client, channels: Optional[List[NotificationChannel]] = None):
        self.db = db_client
        self.channels = channels or []

    def publish(
        self,
        *,
        recipients: List[str],
        notif_type: str,
        title: str,
        body: str,
        severity: str = "info",
        actor_username: Optional[str] = None,
        device_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> dict:
        recipients = [r for r in recipients if r]
        if not recipients:
            return {
                "status": "skipped",
                "reason": "no_recipients",
                "deliveries": [],
            }

        event_id = str(uuid.uuid4())

        payload = {
            "schema_version": NOTIFICATION_SCHEMA_VERSION,
            "event_id": event_id,
            "type": notif_type,
            "title": title,
            "body": body,
            "severity": severity,  # info | warning | error | success
            "actor_username": actor_username,
            "device_id": device_id,
            "data": data or {},
            # client-visible creation time (immediate); Firestore server timestamp is written by channel
            "created_at_client_iso": _utc_now_iso(),
        }

        deliveries = []
        for channel in self.channels:
            try:
                result = channel.deliver(payload, recipients)
                deliveries.append(result)
            except Exception as e:
                deliveries.append({
                    "channel": getattr(channel, "name", "unknown"),
                    "status": "error",
                    "error": str(e),
                })

        return {
            "status": "ok",
            "event_id": event_id,
            "recipient_count": len(recipients),
            "deliveries": deliveries,
        }


def resolve_notification_recipients_for_device(
    *,
    device_id: Optional[str],
    actor_username: Optional[str],
) -> List[str]:
    """
    DEMO/TEMP recipient resolver.

    Current behavior:
    - sends notifications to the current logged-in user only.

    Future teammates can replace this with:
    - device owner lookup
    - shared users
    - team roles
    - user preferences / muting
    """
    recipients = []
    if actor_username:
        recipients.append(actor_username)

    # Deduplicate while preserving order
    deduped = []
    seen = set()
    for r in recipients:
        if r not in seen:
            seen.add(r)
            deduped.append(r)
    return deduped


notification_service = NotificationService(
    db_client=db,
    channels=[
        FirestoreEventLogChannel(db),
        FirestoreUserInboxChannel(db),
        StubWebPushChannel(),    # placeholder
        StubMobilePushChannel(), # placeholder
    ],
)


def publish_device_notification(
    *,
    actor_username: str,
    device_id: str,
    notif_type: str,
    title: str,
    body: str,
    severity: str = "info",
    data: Optional[Dict[str, Any]] = None,
) -> dict:
    recipients = resolve_notification_recipients_for_device(
        device_id=device_id,
        actor_username=actor_username,
    )
    return notification_service.publish(
        recipients=recipients,
        notif_type=notif_type,
        title=title,
        body=body,
        severity=severity,
        actor_username=actor_username,
        device_id=device_id,
        data=data,
    )

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

    notif_result = None
    try:
        notif_result = publish_device_notification(
            actor_username=username,
            device_id=device_id,
            notif_type="device_command",
            title=f"Command sent: {cmd}",
            body=f"{username} sent '{cmd}' to device {device_id}.",
            severity="info",
            data={"command": cmd, "source": "api_device_command"},
        )
    except Exception as e:
        # Do not fail the command API if notification scaffolding has an issue
        app.logger.exception("Notification publish failed: %s", e)

    return jsonify({
        "message": f"Command '{cmd}' received for {device_id}.",
        "notification": notif_result,
    }), 200

def _utc_now_dt() -> datetime:
    return datetime.now(timezone.utc)

def _normalize_fs_dt(dt: datetime) -> datetime:
    # Firestore timestamps sometimes come back naive; treat naive as UTC.
    if isinstance(dt, datetime) and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

@app.route("/api/device/<device_id>/upload-image", methods=["POST"])
def api_device_upload_image(device_id):
    username = get_current_user()
    if not username:
        return jsonify({"error": "Not logged in."}), 401

    if "image" not in request.files:
        return jsonify({"error": "Missing file field 'image' (multipart/form-data)."}), 400

    f = request.files["image"]
    if not f or not f.filename:
        return jsonify({"error": "No file selected."}), 400

    original_name = secure_filename(f.filename)
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        return jsonify({"error": f"Unsupported file type {ext}. Allowed: {sorted(ALLOWED_IMAGE_EXTS)}"}), 400

    upload_id = str(uuid.uuid4())
    stored_filename = f"{upload_id}{ext}"

    device_dir = UPLOAD_ROOT / f"device_{device_id}"
    device_dir.mkdir(parents=True, exist_ok=True)

    stored_path = device_dir / stored_filename

    # Save to disk
    f.save(stored_path)

    size_bytes = stored_path.stat().st_size
    content_type = f.mimetype or "application/octet-stream"

    now = _utc_now_dt()
    expires_at = now.replace()  # copy
    expires_at = expires_at + timedelta(seconds=MEDIA_TTL_SECONDS)

    # Store metadata in Firestore
    doc = {
        "device_id": device_id,
        "uploaded_by": username,
        "original_filename": original_name,
        "stored_filename": stored_filename,
        # store a repo-relative path so teammates on different machines don't leak absolute paths
        "relative_path": str(stored_path.relative_to(BASE_DIR)).replace("\\", "/"),
        "content_type": content_type,
        "size_bytes": int(size_bytes),
        "created_at": firestore.SERVER_TIMESTAMP,
        "expires_at": expires_at,  # Firestore will store as timestamp
        "ttl_seconds": MEDIA_TTL_SECONDS,
    }

    db.collection("media_uploads").document(upload_id).set(doc)

    # generate a notification
    try:
        publish_device_notification(
            actor_username=username,
            device_id=device_id,
            notif_type="image_uploaded",
            title="Image uploaded",
            body=f"{username} uploaded {original_name}",
            severity="info",
            data={"upload_id": upload_id, "filename": original_name},
        )
    except Exception:
        pass

    return jsonify({
        "message": "Uploaded",
        "upload_id": upload_id,
        "device_id": device_id,
        "original_filename": original_name,
        "size_bytes": int(size_bytes),
        "content_type": content_type,
        "expires_in_seconds": MEDIA_TTL_SECONDS,
    }), 201


@app.route("/api/media", methods=["GET"])
def api_media_list():
    username = get_current_user()
    if not username:
        return jsonify({"error": "Not logged in."}), 401

    device_id = (request.args.get("device_id") or "").strip()
    if not device_id:
        return jsonify({"error": "device_id query param is required"}), 400

    # Query by device_id, then filter TTL in Python to avoid requiring extra Firestore indexes.
    q = (
        db.collection("media_uploads")
        .where("device_id", "==", device_id)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(50)
    )

    now = _utc_now_dt()
    items = []
    for doc in q.stream():
        d = doc.to_dict() or {}
        exp = d.get("expires_at")
        if isinstance(exp, datetime):
            exp = _normalize_fs_dt(exp)
            if exp <= now:
                continue

        d = _serialize_firestore_value(d)
        d["id"] = doc.id
        items.append(d)

    return jsonify({
        "device_id": device_id,
        "count": len(items),
        "items": items
    }), 200


@app.route("/api/media/<upload_id>/download", methods=["GET"])
def api_media_download(upload_id):
    username = get_current_user()
    if not username:
        return jsonify({"error": "Not logged in."}), 401

    doc = db.collection("media_uploads").document(upload_id).get()
    if not doc.exists:
        return jsonify({"error": "Not found"}), 404

    data = doc.to_dict() or {}

    exp = data.get("expires_at")
    if isinstance(exp, datetime):
        exp = _normalize_fs_dt(exp)
        if exp <= _utc_now_dt():
            return jsonify({"error": "File expired"}), 410

    rel = data.get("relative_path")
    if not rel:
        return jsonify({"error": "Missing relative_path in metadata"}), 500

    # Resolve path safely and ensure it stays within UPLOAD_ROOT
    abs_path = (BASE_DIR / rel).resolve()
    if not str(abs_path).startswith(str(UPLOAD_ROOT.resolve())):
        return jsonify({"error": "Invalid path"}), 400

    if not abs_path.exists():
        return jsonify({"error": "File missing on server"}), 410

    download_name = data.get("original_filename") or abs_path.name
    return send_file(abs_path, as_attachment=True, download_name=download_name)

# firestore routes
@app.route("/api/profile", methods=["POST"])
def create_profile():
    data = request.get_json() or {}
    username = data.get("username")
    if not username:
        return jsonify({"error": "username is required"}), 400

    # Save the whole JSON as the document
    db.collection("profiles").document(username).set(data)
    return jsonify({"message": "Created", "username": username}), 201


@app.route("/api/profile/<username>", methods=["GET"])
def get_profile(username):
    doc = db.collection("profiles").document(username).get()
    if not doc.exists:
        return jsonify({"error": "Not found"}), 404

    return jsonify({"username": doc.id, **doc.to_dict()}), 200

#update route  
@app.route("/api/profile/<username>", methods=["PUT"])
def update_profile(username):
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json."}), 415

    data = request.get_json(silent=True) or {}

    #  update only the provided fields (partial update)
    doc_ref = db.collection("profiles").document(username)
    doc = doc_ref.get()
    if not doc.exists:
        return jsonify({"error": "Not found"}), 404

    # Firestore update fails if data is empty
    if not data:
        return jsonify({"error": "No fields to update"}), 400

    doc_ref.update(data)
    return jsonify({"message": "Updated", "username": username}), 200

#delete route
@app.route("/api/profile/<username>", methods=["DELETE"])
def delete_profile(username):
    doc_ref = db.collection("profiles").document(username)
    doc = doc_ref.get()
    if not doc.exists:
        return jsonify({"error": "Not found"}), 404

    doc_ref.delete()
    return jsonify({"message": "Deleted", "username": username}), 200

# ---------------------------
# Notification APIs (scaffold demo + inbox)
# ---------------------------

@app.route("/api/notifications", methods=["GET"])
def api_notifications_list():
    username = get_current_user()
    if not username:
        return jsonify({"error": "Not logged in."}), 401

    try:
        limit_raw = request.args.get("limit", "20")
        limit = int(limit_raw)
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400

    # clamp limit for safety
    limit = max(1, min(limit, 100))

    unread_only = request.args.get("unread_only", "false").lower() in ("1", "true", "yes")

    q = (
        db.collection("users")
        .document(username)
        .collection("notifications")
    )

    if unread_only:
        q = q.where("read", "==", False)

    # Order newest first. Firestore may require indexes as this grows.
    q = q.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)

    docs = list(q.stream())
    items = [_serialize_doc(doc) for doc in docs]

    return jsonify({
        "username": username,
        "count": len(items),
        "items": items,
    }), 200


@app.route("/api/notifications/unread-count", methods=["GET"])
def api_notifications_unread_count():
    username = get_current_user()
    if not username:
        return jsonify({"error": "Not logged in."}), 401

    q = (
        db.collection("users")
        .document(username)
        .collection("notifications")
        .where("read", "==", False)
    )

    # Simple scaffold implementation (fine for demo/small volume).
    # Teammates can replace with aggregated counters later.
    count = sum(1 for _ in q.stream())

    return jsonify({
        "username": username,
        "unread_count": count,
    }), 200


@app.route("/api/notifications/<notification_id>/read", methods=["POST"])
def api_notifications_mark_read(notification_id):
    username = get_current_user()
    if not username:
        return jsonify({"error": "Not logged in."}), 401

    doc_ref = (
        db.collection("users")
        .document(username)
        .collection("notifications")
        .document(notification_id)
    )
    doc = doc_ref.get()
    if not doc.exists:
        return jsonify({"error": "Notification not found"}), 404

    doc_ref.update({
        "read": True,
        "read_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP,
    })

    return jsonify({
        "message": "Marked as read",
        "notification_id": notification_id,
    }), 200


@app.route("/api/notifications/read-all", methods=["POST"])
def api_notifications_mark_all_read():
    username = get_current_user()
    if not username:
        return jsonify({"error": "Not logged in."}), 401

    q = (
        db.collection("users")
        .document(username)
        .collection("notifications")
        .where("read", "==", False)
    )

    docs = list(q.stream())
    batch = db.batch()
    for doc in docs:
        batch.update(doc.reference, {
            "read": True,
            "read_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
    if docs:
        batch.commit()

    return jsonify({
        "message": "Marked all as read",
        "updated_count": len(docs),
    }), 200

@app.route("/api/notifications/clear", methods=["POST"])
def api_notifications_clear():
    """
    Clear notifications from the logged-in user's inbox.

    Optional JSON body:
      {
        "mode": "all" | "read"
      }

    Default mode is "read" (safer).
    """
    username = get_current_user()
    if not username:
        return jsonify({"error": "Not logged in."}), 401

    data = request.get_json(silent=True) or {}
    mode = (data.get("mode") or "read").strip().lower()

    if mode not in ("all", "read"):
        return jsonify({"error": "mode must be 'all' or 'read'"}), 400

    q = (
        db.collection("users")
        .document(username)
        .collection("notifications")
    )

    if mode == "read":
        q = q.where("read", "==", True)

    docs = list(q.stream())

    if not docs:
        return jsonify({
            "message": "Nothing to clear",
            "cleared_count": 0,
            "mode": mode
        }), 200

    # Firestore batched writes support up to 500 ops per batch.
    # This scaffold handles that safely by chunking.
    total_deleted = 0
    BATCH_SIZE = 450  # leave headroom

    for i in range(0, len(docs), BATCH_SIZE):
        batch = db.batch()
        chunk = docs[i:i + BATCH_SIZE]
        for doc in chunk:
            batch.delete(doc.reference)
        batch.commit()
        total_deleted += len(chunk)

    return jsonify({
        "message": "Notifications cleared",
        "cleared_count": total_deleted,
        "mode": mode
    }), 200

@app.route("/api/device/<device_id>/demo-notify", methods=["POST"])
def api_device_demo_notify(device_id):
    """
    Demo route to generate notifications without real hardware events.
    Integrates with your existing device-centric API style.
    """
    username = get_current_user()
    if not username:
        return jsonify({"error": "Not logged in."}), 401

    data = request.get_json(silent=True) or {}
    preset = (data.get("preset") or "package_detected").strip()

    presets = {
        "package_detected": {
            "notif_type": "package_detected",
            "title": "Package detected",
            "body": f"Device {device_id} detected a package.",
            "severity": "success",
            "data": {"source": "demo", "event": "package_detected"},
        },
        "door_left_open": {
            "notif_type": "door_alert",
            "title": "Door left open",
            "body": f"Device {device_id} door appears to be open.",
            "severity": "warning",
            "data": {"source": "demo", "event": "door_left_open"},
        },
        "device_offline": {
            "notif_type": "device_status",
            "title": "Device offline",
            "body": f"Device {device_id} stopped reporting status.",
            "severity": "error",
            "data": {"source": "demo", "event": "device_offline"},
        },
        "video_recorded": {
            "notif_type": "video_recorded",
            "title": "Video recorded",
            "body": f"Device {device_id} recorded a new video clip.",
            "severity": "info",
            "data": {"source": "demo", "event": "video_recorded"},
        },
    }

    if preset not in presets:
        return jsonify({
            "error": "Invalid preset",
            "valid_presets": sorted(presets.keys())
        }), 400

    p = presets[preset]
    result = publish_device_notification(
        actor_username=username,
        device_id=device_id,
        notif_type=p["notif_type"],
        title=p["title"],
        body=p["body"],
        severity=p["severity"],
        data=p["data"],
    )

    return jsonify({
        "message": "Demo notification generated",
        "preset": preset,
        "notification": result,
    }), 200


#end of firestore routes

if __name__ == "__main__":
    app.run(debug=True, port=5000)
