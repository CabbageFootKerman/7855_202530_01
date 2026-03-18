import os

from flask import session, request, jsonify

from config import SENSOR_API_KEY


def get_current_user():
    """Return the currently logged-in username (or None).

    Uses session data set during `/login`. This keeps all login checks
    consistent in one place.
    """
    if not session.get("logged_in"):
        return None
    return session.get("username")


# ---------------------------
# Device / sensor auth (API key)
# ---------------------------

def require_device_api_key(device_id):
    """Validate the X-API-Key header against the SENSOR_API_KEY env var.
    Accepts any known device_id - no longer hardcoded to one device."""
    expected = SENSOR_API_KEY or os.getenv("SMARTPOST_PI_API_KEY", "")
    if not expected:
        return jsonify({"error": "Server device API key is not configured."}), 500

    provided = request.headers.get("X-API-Key", "").strip()
    if not provided or provided != expected:
        return jsonify({"error": "Invalid device API key."}), 401

    return None