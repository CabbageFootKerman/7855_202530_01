import requests as http_requests
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from firebase_admin import auth as firebase_auth

from config import FIREBASE_WEB_API_KEY
from extensions import limiter
from firebase import db

auth_bp = Blueprint("auth", __name__)

FIREBASE_SIGN_IN_URL = (
    "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
    f"?key={FIREBASE_WEB_API_KEY}"
)

# Friendly error mapping 
_ERROR_MAP = {
    "INVALID_LOGIN_CREDENTIALS": "Invalid email or password",
    "EMAIL_NOT_FOUND": "Invalid email or password",
    "INVALID_PASSWORD": "Invalid email or password",
    "USER_DISABLED": "This account has been disabled",
    "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts: please try again later",
    "EMAIL_EXISTS": "An account with this email already exists",
    "WEAK_PASSWORD": "Password is too weak. Use at least 6 characters",
    "INVALID_EMAIL": "Invalid email address",
}


def _friendly_error(raw_message, fallback="Something went wrong."):
    for key, friendly in _ERROR_MAP.items():
        if key in raw_message:
            return friendly
    return fallback


def _extract_id_token_from_request(data: dict) -> str:
    id_token = (data.get("idToken") or "").strip()
    if id_token:
        return id_token

    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ").strip()

    return ""


def _start_user_session_from_id_token(id_token: str) -> dict:
    decoded = firebase_auth.verify_id_token(id_token)

    uid = decoded.get("uid") or decoded.get("user_id") or decoded.get("sub")
    if not uid:
        raise ValueError("Verified token did not contain a user id")

    session.clear()
    session["logged_in"] = True
    session["username"] = uid
    session["email"] = decoded.get("email")
    session["id_token"] = id_token

    return decoded

# --------------------------------------------------
# Web form routes
# --------------------------------------------------

@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if request.method == "GET":
        return render_template("login.html", error=None)

    # JSON callers get the API path
    if request.is_json:
        return api_login()

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template("login.html", error="Email and password are required.")

    try:
        resp = http_requests.post(FIREBASE_SIGN_IN_URL, json={
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }, timeout=10)
    except http_requests.RequestException:
        return render_template("login.html", error="Authentication service unavailable.")

    if resp.status_code != 200:
        raw = resp.json().get("error", {}).get("message", "Invalid credentials.")
        return render_template("login.html", error=_friendly_error(raw, "Invalid credentials."))

    data = resp.json()
    
    try:
        _start_user_session_from_id_token(data["idToken"])
    except Exception:
        return render_template("login.html", error="Authentication failed.")

    return redirect(url_for("dashboard.home"))



@auth_bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def signup():
    if request.method == "GET":
        return render_template("signup.html", error=None)

    if request.is_json:
        return api_signup()

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    if not email or not password:
        return render_template("signup.html", error="Email and password are required.")

    try:
        user = firebase_auth.create_user(email=email, password=password)

        # Create Firestore profile for the new user
        db.collection("profiles").document(user.uid).set({
            "email": email,
            "role": "user",
        })

        return redirect(url_for("auth.login"))
    except Exception as e:
        return render_template("signup.html", error=_friendly_error(str(e), "Signup failed."))


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


# --------------------------------------------------
# JSON API endpoints (for SmartPost / programmatic callers)
# --------------------------------------------------

def api_login():
    data = request.get_json(silent=True) or {}
    id_token = _extract_id_token_from_request(data)

    # Backward-compatible path: accept email/password, sign in with Firebase,
    # then verify the returned ID token before treating the user as logged in.
    if not id_token:
        email = (data.get("email") or "").strip()
        password = data.get("password") or ""

        if email and password:
            try:
                resp = http_requests.post(
                    FIREBASE_SIGN_IN_URL,
                    json={
                        "email": email,
                        "password": password,
                        "returnSecureToken": True,
                    },
                    timeout=10,
                )
            except http_requests.RequestException:
                return jsonify({"error": "Authentication service unavailable"}), 503

            if resp.status_code != 200:
                return jsonify({"error": "Unauthorized"}), 401

            id_token = (resp.json().get("idToken") or "").strip()

    if not id_token:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        decoded = _start_user_session_from_id_token(id_token)
    except Exception:
        return jsonify({"error": "Unauthorized"}), 401

    return jsonify({
        "message": "Login successful",
        "username": session["username"],
        "email": decoded.get("email"),
        "token": id_token,
    }), 200

def api_signup():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        user = firebase_auth.create_user(email=email, password=password)

        db.collection("profiles").document(user.uid).set({
            "email": email,
            "role": "user",
        })

        return jsonify({"message": "User created successfully", "uid": user.uid}), 201
    except Exception as e:
        msg = str(e)
        if "email-already-exists" in msg:
            return jsonify({"error": "An account with this email already exists"}), 400
        if "invalid-email" in msg:
            return jsonify({"error": "Invalid email address"}), 400
        if "weak-password" in msg:
            return jsonify({"error": "Password is too weak"}), 400
        return jsonify({"error": "Failed to create user"}), 400
