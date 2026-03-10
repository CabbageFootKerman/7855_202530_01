from datetime import datetime, timezone

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app

from utils.auth import get_current_user
from utils.notifications import publish_device_notification

device_bp = Blueprint("device", __name__)


@device_bp.route("/device/<device_id>")
def device_page(device_id):
    if not get_current_user():
        return redirect(url_for("auth.login"))
    return render_template("device.html", device_id=device_id)


@device_bp.route("/api/device/<device_id>/state", methods=["GET"])
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


@device_bp.route("/api/device/<device_id>/command", methods=["POST"])
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
        current_app.logger.exception("Notification publish failed: %s", e)

    return jsonify({
        "message": f"Command '{cmd}' received for {device_id}.",
        "notification": notif_result,
    }), 200
