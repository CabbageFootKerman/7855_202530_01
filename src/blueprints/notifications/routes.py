from flask import Blueprint, request, jsonify
from firebase_admin import firestore

from firebase import db
from utils.auth import get_current_user
from utils.firestore import _serialize_doc
from utils.notifications import publish_device_notification

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/api/notifications", methods=["GET"])
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


@notifications_bp.route("/api/notifications/unread-count", methods=["GET"])
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


@notifications_bp.route("/api/notifications/<notification_id>/read", methods=["POST"])
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


@notifications_bp.route("/api/notifications/read-all", methods=["POST"])
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


@notifications_bp.route("/api/notifications/clear", methods=["POST"])
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


@notifications_bp.route("/api/device/<device_id>/demo-notify", methods=["POST"])
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
