from pathlib import Path

from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename

from config import BASE_DIR, UPLOAD_ROOT, ALLOWED_IMAGE_EXTS
from utils.auth import require_device_api_key
from utils.device_access import user_can_access_device
from decorators.auth import login_required

media_bp = Blueprint("media", __name__)


@media_bp.route("/api/device/<device_id>/camera/<int:camera_id>/snapshot", methods=["POST"])
def api_device_camera_snapshot(device_id, camera_id):
    auth_error = require_device_api_key(device_id)
    if auth_error:
        return auth_error

    if camera_id not in (0, 1, 2):
        return jsonify({"error": "camera_id must be 0, 1, or 2."}), 400

    if "image" not in request.files:
        return jsonify({"error": "Missing file field 'image' (multipart/form-data)."}), 400

    f = request.files["image"]
    if not f or not f.filename:
        return jsonify({"error": "No file selected."}), 400

    original_name = secure_filename(f.filename)
    ext = Path(original_name).suffix.lower()

    if ext not in ALLOWED_IMAGE_EXTS:
        return jsonify({
            "error": f"Unsupported file type {ext}. Allowed: {sorted(ALLOWED_IMAGE_EXTS)}"
        }), 400

    device_dir = UPLOAD_ROOT / f"device_{device_id}" / "latest"
    device_dir.mkdir(parents=True, exist_ok=True)

    stored_path = device_dir / f"cam{camera_id}.jpg"
    f.save(stored_path)

    size_bytes = stored_path.stat().st_size

    print(f"Snapshot received: device={device_id}, camera={camera_id}", flush=True)

    return jsonify({
        "message": "Latest snapshot updated.",
        "device_id": device_id,
        "camera_id": camera_id,
        "size_bytes": int(size_bytes),
        "path": str(stored_path.relative_to(BASE_DIR)).replace("\\", "/"),
    }), 200


@media_bp.route("/media/device/<device_id>/camera/<int:camera_id>/latest.jpg", methods=["GET"])
@login_required
def media_device_camera_latest(username, device_id, camera_id):
    if not user_can_access_device(username, device_id):
        return jsonify({"error": "Forbidden"}), 403

    if camera_id not in (0, 1, 2):
        return jsonify({"error": "camera_id must be 0, 1, or 2."}), 400

    image_path = UPLOAD_ROOT / f"device_{device_id}" / "latest" / f"cam{camera_id}.jpg"

    if not image_path.exists():
        return jsonify({"error": "Snapshot not found."}), 404

    return send_file(image_path, mimetype="image/jpeg")
