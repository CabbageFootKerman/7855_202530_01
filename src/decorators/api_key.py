from functools import wraps
from flask import request, jsonify
from firebase import db


def api_key_required(f):
    """Validates an API key from the X-API-Key header against Firestore.
    Injects `username` into kwargs. If the route has a `device_id` param,
    verifies the key is scoped to that device."""
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key", "").strip()
        if not key:
            return jsonify({"error": "API key required"}), 401

        doc = db.collection("api_keys").document(key).get()
        if not doc.exists:
            return jsonify({"error": "Invalid API key"}), 403

        data = doc.to_dict()
        if data.get("revoked"):
            return jsonify({"error": "API key has been revoked"}), 403

        # Scope check: if route has device_id, it must match
        route_device = kwargs.get("device_id")
        if route_device and data.get("device_id") != route_device:
            return jsonify({"error": "API key not authorised for this device"}), 403

        kwargs["username"] = data["username"]
        return f(*args, **kwargs)
    return decorated
