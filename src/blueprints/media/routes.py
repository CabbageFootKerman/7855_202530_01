from pathlib import Path
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from firebase_admin import firestore
import uuid

from config import BASE_DIR, UPLOAD_ROOT, ALLOWED_IMAGE_EXTS, MEDIA_TTL_SECONDS
from firebase import db
from utils.auth import get_current_user
from utils.firestore import _utc_now_dt, _normalize_fs_dt, _serialize_firestore_value
from utils.notifications import publish_device_notification

media_bp = Blueprint("media", __name__)


@media_bp.route("/api/device/<device_id>/upload-image", methods=["POST"])
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


@media_bp.route("/api/media", methods=["GET"])
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


@media_bp.route("/api/media/<upload_id>/download", methods=["GET"])
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
