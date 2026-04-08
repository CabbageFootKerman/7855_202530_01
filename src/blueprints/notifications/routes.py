from flask import Blueprint, request, jsonify
from firebase_admin import firestore
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

from firebase import db
from utils.firestore import _serialize_doc
from utils.notifications import publish_device_notification
from decorators.auth import api_login_required
from utils.device_access import user_can_access_device
from utils.notification_cache import (
    get_cached_notification_list, set_notification_list_cache,
    get_cached_unread_count, set_unread_count_cache,
    invalidate_notification_cache,
    get_cached_chart, set_chart_cache,
)

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/api/notifications", methods=["GET"])
@api_login_required
def api_notifications_list(username):
    try:
        limit_raw = request.args.get("limit", "20")
        limit = int(limit_raw)
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400

    limit = max(1, min(limit, 100))
    unread_only = request.args.get("unread_only", "false").lower() in ("1", "true", "yes")

    # Serve from cache when available.  The cache always holds up to 100 items
    # so both paginated and filtered variants can be satisfied without Firestore.
    cached_items = get_cached_notification_list(username)
    if cached_items is not None:
        if unread_only:
            items = [n for n in cached_items if not n.get("read")][:limit]
        else:
            items = cached_items[:limit]
        return jsonify({"username": username, "count": len(items), "items": items}), 200

    # Cache miss: fetch the maximum allowed number of items from Firestore so
    # the cached list covers all realistic pagination/filter needs.
    q = (
        db.collection("users")
        .document(username)
        .collection("notifications")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(100)
    )

    all_items = [_serialize_doc(doc) for doc in q.stream()]

    set_notification_list_cache(username, all_items)

    if unread_only:
        items = [n for n in all_items if not n.get("read")][:limit]
    else:
        items = all_items[:limit]

    return jsonify({
        "username": username,
        "count": len(items),
        "items": items,
    }), 200


@notifications_bp.route("/api/notifications/unread-count", methods=["GET"])
@api_login_required
def api_notifications_unread_count(username):
    cached = get_cached_unread_count(username)
    if cached is not None:
        return jsonify({"username": username, "unread_count": cached}), 200

    q = (
        db.collection("users")
        .document(username)
        .collection("notifications")
        .where("read", "==", False)
    )

    # Use server-side count aggregation to avoid streaming every document.
    result = q.count().get()
    count = result[0][0].value

    set_unread_count_cache(username, count)

    return jsonify({
        "username": username,
        "unread_count": count,
    }), 200


@notifications_bp.route("/api/notifications/<notification_id>/read", methods=["POST"])
@api_login_required
def api_notifications_mark_read(username, notification_id):
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

    invalidate_notification_cache(username)

    return jsonify({
        "message": "Marked as read",
        "notification_id": notification_id,
    }), 200


@notifications_bp.route("/api/notifications/read-all", methods=["POST"])
@api_login_required
def api_notifications_mark_all_read(username):
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

    invalidate_notification_cache(username)

    return jsonify({
        "message": "Marked all as read",
        "updated_count": len(docs),
    }), 200


@notifications_bp.route("/api/notifications/clear", methods=["POST"])
@api_login_required
def api_notifications_clear(username):
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

    total_deleted = 0
    BATCH_SIZE = 450

    for i in range(0, len(docs), BATCH_SIZE):
        batch = db.batch()
        chunk = docs[i:i + BATCH_SIZE]
        for doc in chunk:
            batch.delete(doc.reference)
        batch.commit()
        total_deleted += len(chunk)

    invalidate_notification_cache(username)

    return jsonify({
        "message": "Notifications cleared",
        "cleared_count": total_deleted,
        "mode": mode
    }), 200


@notifications_bp.route("/api/device/<device_id>/demo-notify", methods=["POST"])
@api_login_required
def api_device_demo_notify(username, device_id):
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


def _parse_iso_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


@notifications_bp.route("/api/device/<device_id>/door-close-chart", methods=["GET"])
@api_login_required
def api_device_door_close_chart(username, device_id):
    if not user_can_access_device(username, device_id):
        return jsonify({"error": "Forbidden"}), 403

    try:
        hours = int(request.args.get("hours", "24"))
    except ValueError:
        return jsonify({"error": "hours must be an integer"}), 400

    hours = max(1, min(hours, 168))

    # Serve from cache – chart data changes at most once per hour so a 5-minute
    # TTL is negligible staleness compared to the 60-second browser refresh.
    cached = get_cached_chart(device_id, hours)
    if cached is not None:
        return jsonify(cached), 200

    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(hours=hours - 1)

    buckets = OrderedDict()
    current = start
    while current <= now:
        label = current.strftime("%m-%d %H:00")
        buckets[label] = 0
        current += timedelta(hours=1)

    q = (
        db.collection("notification_events")
        .where("device_id", "==", device_id)
        .where("logged_at", ">=", start)
    )
    docs = list(q.stream())

    for doc in docs:
        item = doc.to_dict() or {}
        event_type = item.get("type")

        if event_type not in ("door_closed", "door_close_requested"):
            continue

        dt = item.get("logged_at")
        if dt is None:
            dt = _parse_iso_datetime(item.get("created_at_client_iso"))

        if dt is None:
            continue

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        if dt < start or dt > now + timedelta(hours=1):
            continue

        bucket_dt = dt.replace(minute=0, second=0, microsecond=0)
        label = bucket_dt.strftime("%m-%d %H:00")

        if label in buckets:
            buckets[label] += 1

    result = {
        "device_id": device_id,
        "labels": list(buckets.keys()),
        "values": list(buckets.values()),
        "total": sum(buckets.values()),
    }
    set_chart_cache(device_id, hours, result)
    return jsonify(result), 200