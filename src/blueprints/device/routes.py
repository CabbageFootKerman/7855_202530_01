from collections import deque
from datetime import datetime, timezone
from threading import Lock

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app

from utils.auth import require_device_api_key
from utils.notifications import publish_device_notification
from utils.device_access import user_can_access_device, claim_device
from decorators.auth import login_required, api_login_required

device_bp = Blueprint("device", __name__)

DEVICE_STATE = {}
DEVICE_COMMANDS = {}
DEVICE_LOCK = Lock()


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


@device_bp.route("/pair-device", methods=["GET"])
@login_required
def pair_device_page(username):
    return render_template("pair_device.html", error=None)


@device_bp.route("/pair-device", methods=["POST"])
@login_required
def pair_device_submit(username):
    device_id = request.form.get("device_id", "").strip()
    claim_code = request.form.get("claim_code", "").strip()

    if not device_id or not claim_code:
        return render_template("pair_device.html", error="Device ID and claim code are required.")

    ok, message = claim_device(username, device_id, claim_code)
    if not ok:
        return render_template("pair_device.html", error=message)

    return redirect(url_for("device.device_page", device_id=device_id))


@device_bp.route("/device/<device_id>")
@login_required
def device_page(username, device_id):
    if not user_can_access_device(username, device_id):
        return jsonify({"error": "Forbidden"}), 403

    return render_template("device.html", device_id=device_id)


@device_bp.route("/api/device/<device_id>/state", methods=["GET"])
@api_login_required
def api_device_state(username, device_id):
    if not user_can_access_device(username, device_id):
        return jsonify({"error": "Forbidden"}), 403

    with DEVICE_LOCK:
        state = DEVICE_STATE.get(device_id, {
            "device_id": device_id,
            "door_state": "unknown",
            "weight_g": 0.0,
            "servo_state": "unknown",
            "solenoid_state": "unknown",
            "actuator_state": "unknown",
            "last_update_iso": None,
        })

    return jsonify({
        "device_id": device_id,
        "door_state": state.get("door_state", "unknown"),
        "weight_g": state.get("weight_g", 0.0),
        "servo_state": state.get("servo_state", "unknown"),
        "solenoid_state": state.get("solenoid_state", "unknown"),
        "actuator_state": state.get("actuator_state", "unknown"),
        "last_update_iso": state.get("last_update_iso"),
        "cameras": {
            "cam0": f"/media/device/{device_id}/camera/0/latest.jpg",
            "cam1": f"/media/device/{device_id}/camera/1/latest.jpg",
            "cam2": f"/media/device/{device_id}/camera/2/latest.jpg",
        }
    }), 200



@device_bp.route("/api/device/<device_id>/telemetry", methods=["POST"])
def api_device_telemetry(device_id):
    auth_error = require_device_api_key(device_id)
    if auth_error:
        return auth_error

    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json."}), 415

    data = request.get_json(silent=True) or {}

    try:
        weight_g = float(data.get("weight_g", 0.0))
    except (TypeError, ValueError):
        return jsonify({"error": "weight_g must be numeric."}), 400

    door_state = data.get("door_state", "unknown")
    servo_state = data.get("servo_state", "unknown")
    solenoid_state = data.get("solenoid_state", "unknown")
    actuator_state = data.get("actuator_state", "unknown")

    with DEVICE_LOCK:
        DEVICE_STATE[device_id] = {
            "device_id": device_id,
            "door_state": door_state,
            "weight_g": weight_g,
            "servo_state": servo_state,
            "solenoid_state": solenoid_state,
            "actuator_state": actuator_state,
            "last_update_iso": utc_now_iso(),
        }

    print(f"Telemetry received from {device_id}: {data}", flush=True)
    return jsonify({"message": "Telemetry received."}), 200


@device_bp.route("/api/device/<device_id>/command", methods=["POST"])
@api_login_required
def api_device_command(username, device_id):
    if not user_can_access_device(username, device_id):
        return jsonify({"error": "Forbidden"}), 403

    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json."}), 415

    data = request.get_json(silent=True) or {}
    cmd = data.get("command")

    if cmd not in ("open", "close"):
        return jsonify({"error": "command must be 'open' or 'close'."}), 400

    queued_item = {
        "command": cmd,
        "created_at": utc_now_iso(),
        "created_by": username,
    }

    with DEVICE_LOCK:
        if device_id not in DEVICE_COMMANDS:
            DEVICE_COMMANDS[device_id] = deque()
        DEVICE_COMMANDS[device_id].append(queued_item)

    print(f"COMMAND QUEUED user={username} device={device_id} command={cmd}", flush=True)

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
        current_app.logger.exception("Notification publish failed: %s", e)

    return jsonify({
        "message": f"Command '{cmd}' queued for {device_id}.",
        "notification": notif_result,
    }), 200


@device_bp.route("/api/device/<device_id>/command/next", methods=["GET"])
def api_device_command_next(device_id):
    auth_error = require_device_api_key(device_id)
    if auth_error:
        return auth_error

    with DEVICE_LOCK:
        queue = DEVICE_COMMANDS.get(device_id)
        if not queue or len(queue) == 0:
            return jsonify({"command": None}), 200

        next_command = queue.popleft()

    return jsonify(next_command), 200
