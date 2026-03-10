# decorators/api_key.py
# ──────────────────────────────────────────────────────────────────
# TASK OWNER: Pawel Banasik (CabbageFootKerman)
# STATUS:     Not started
# ESTIMATE:   ~1.5 hr implementation + ~1 hr testing
# ──────────────────────────────────────────────────────────────────
#
# GOAL:  Create an @api_key_required decorator that verifies an API
#        key on protected endpoints — scoped per USER and per DEVICE
#        (SmartPost unit).
#
# ── Background ──────────────────────────────────────────────────
#   Currently every API route checks `get_current_user()` which
#   relies on Flask session cookies.  That works for the browser
#   but NOT for headless / IoT / third-party callers.
#
#   This decorator adds a second auth path:
#     • Caller sends an API key in the request header
#       (e.g. `X-API-Key: <key>` or `Authorization: Bearer <key>`)
#     • The decorator validates the key against Firestore.
#     • If valid → inject `username` and `device_id` into the route.
#     • If invalid / missing → return 401 or 403 JSON.
#
# ── Suggested Firestore schema ──────────────────────────────────
#   Collection: api_keys
#   Document ID: <the key itself or a hash of it>
#   Fields:
#     - username    (str)   owner of the key
#     - device_id   (str)   SmartPost unit this key can access
#     - created_at  (timestamp)
#     - revoked     (bool, default False)
#
# ── Decorator behaviour ─────────────────────────────────────────
#   1. Read header  →  key = request.headers.get("X-API-Key")
#   2. If missing   →  return 401  {"error": "API key required"}
#   3. Look up key doc in Firestore.
#   4. If not found or revoked  →  return 403  {"error": "Invalid API key"}
#   5. If the route includes <device_id>, verify key.device_id matches.
#   6. Inject `username` (and optionally `device_id`) into kwargs.
#
# ── Implementation sketch ───────────────────────────────────────
#   from functools import wraps
#   from flask import request, jsonify
#   from firebase import db
#
#   def api_key_required(f):
#       @wraps(f)
#       def decorated(*args, **kwargs):
#           key = request.headers.get("X-API-Key")
#           if not key:
#               return jsonify({"error": "API key required"}), 401
#
#           doc = db.collection("api_keys").document(key).get()
#           if not doc.exists:
#               return jsonify({"error": "Invalid API key"}), 403
#
#           data = doc.to_dict()
#           if data.get("revoked"):
#               return jsonify({"error": "API key has been revoked"}), 403
#
#           # Scope check: if route has device_id, it must match
#           route_device = kwargs.get("device_id")
#           if route_device and data.get("device_id") != route_device:
#               return jsonify({"error": "API key not authorised for this device"}), 403
#
#           kwargs["username"] = data["username"]
#           return f(*args, **kwargs)
#       return decorated
#
# ── Where to apply ──────────────────────────────────────────────
#   Device endpoints that an IoT unit or external caller would hit:
#     - device/routes.py          → api_device_state, api_device_command
#     - media/routes.py           → api_device_upload_image
#     - notifications/routes.py   → api_device_demo_notify (optional)
#
#   You can layer it alongside @api_login_required so that EITHER
#   a valid session OR a valid API key grants access:
#
#       @device_bp.route("/api/device/<device_id>/state")
#       @session_or_api_key          # ← a combined decorator, or
#       @api_key_required            # ← standalone if session not needed
#       def api_device_state(device_id, username=None):
#           ...
#
# ── Testing (unit tests) ────────────────────────────────────────
#   File: tests/test_api_key.py
#
#   Suggested test cases:
#     1. Request with no X-API-Key header        → assert 401
#     2. Request with unknown key                 → assert 403
#     3. Request with revoked key                 → assert 403
#     4. Request with valid key, wrong device_id  → assert 403
#     5. Request with valid key, correct device   → assert 200 + correct data
#     6. Key grants access only to its own device (isolation test)
#
#   Use Flask's test client:
#       with app.test_client() as c:
#           resp = c.get("/api/device/demo123/state",
#                        headers={"X-API-Key": test_key})
#           assert resp.status_code == 200
#
#   For Firestore in tests, either:
#     a. Use the Firestore emulator, or
#     b. Mock `db.collection("api_keys").document(...).get()`
#        with unittest.mock.patch.
#
# ── After both tasks are done ───────────────────────────────────
#   1. Run the full test suite to confirm nothing is broken.
#   2. Update workflow.md Step 10 checklist to mark completion.
#   3. Verify with:  python -c "from app import app; print('OK')"
# ──────────────────────────────────────────────────────────────────
