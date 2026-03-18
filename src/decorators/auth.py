from functools import wraps
from flask import redirect, url_for, jsonify
from utils.auth import get_current_user


def login_required(f):
    """For PAGE routes. Redirects to login if not authenticated.
    Passes `username` as the first arg to the wrapped function."""
    @wraps(f)
    def decorated(*args, **kwargs):
        username = get_current_user()
        if not username:
            return redirect(url_for("auth.login"))
        return f(username, *args, **kwargs)
    return decorated


def api_login_required(f):
    """For API routes. Returns 401 JSON if not authenticated.
    Passes `username` as the first arg to the wrapped function."""
    @wraps(f)
    def decorated(*args, **kwargs):
        username = get_current_user()
        if not username:
            return jsonify({"error": "Not logged in."}), 401
        return f(username, *args, **kwargs)
    return decorated
