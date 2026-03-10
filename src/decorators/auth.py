# decorators/auth.py
# ──────────────────────────────────────────────────────────────────
# TASK OWNER: Pawel Banasik (CabbageFootKerman)
# STATUS:     Placeholder — implement before using in blueprints
# REF:        workflow.md → Step 10
# ──────────────────────────────────────────────────────────────────
#
# This module should contain two decorators that replace the inline
# `get_current_user()` guard pattern currently duplicated across
# every protected route.
#
# ── 1. @login_required ──────────────────────────────────────────
#   • For PAGE routes (return HTML).
#   • If the user is NOT authenticated → redirect to auth.login.
#   • Passes `username` as the first arg to the wrapped function.
#   • Apply to:
#       - dashboard/routes.py  → home()
#       - device/routes.py     → device_page()
#
# ── 2. @api_login_required ──────────────────────────────────────
#   • For API routes (return JSON).
#   • If the user is NOT authenticated → return 401 JSON error.
#   • Passes `username` as the first arg to the wrapped function.
#   • Apply to every route that currently starts with:
#         username = get_current_user()
#         if not username:
#             return jsonify({"error": "Not logged in."}), 401
#     Affected blueprints (13 occurrences total):
#       - device/routes.py          → api_device_state, api_device_command
#       - media/routes.py           → api_device_upload_image, api_media_list, api_media_download
#       - notifications/routes.py   → all 6 notification endpoints + api_device_demo_notify
#
# ── Implementation sketch ───────────────────────────────────────
#   from functools import wraps
#   from flask import redirect, url_for, jsonify
#   from utils.auth import get_current_user
#
#   def login_required(f):
#       @wraps(f)
#       def decorated(*args, **kwargs):
#           username = get_current_user()
#           if not username:
#               return redirect(url_for("auth.login"))
#           return f(username, *args, **kwargs)
#       return decorated
#
#   def api_login_required(f):
#       @wraps(f)
#       def decorated(*args, **kwargs):
#           username = get_current_user()
#           if not username:
#               return jsonify({"error": "Not logged in."}), 401
#           return f(username, *args, **kwargs)
#       return decorated
#
# ── After implementing ──────────────────────────────────────────
#   1. Import the decorator in each blueprint's routes.py.
#   2. Add @login_required or @api_login_required below @bp.route().
#   3. Remove the inline get_current_user() check from the function body.
#   4. Update the function signature to accept `username` as the first param.
#   5. Run:  python -c "from app import app; print('OK')"
#   6. Verify all routes still appear with the url_map check from Step 8.
# ──────────────────────────────────────────────────────────────────
