from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from utils.auth import USERS, save_users, looks_like_hash

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", error=None)

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    stored = USERS.get(username)

    # Supports hashed passwords; also supports legacy plaintext once (auto-migrates)
    if stored and looks_like_hash(stored) and check_password_hash(stored, password):
        session["username"] = username
        return redirect(url_for("dashboard.home"))

    if stored and (not looks_like_hash(stored)) and stored == password:
        # Legacy plaintext login succeeds, then migrate to hash
        USERS[username] = generate_password_hash(password)
        save_users(USERS)
        session["username"] = username
        return redirect(url_for("dashboard.home"))

    return render_template("login.html", error="Invalid credentials.")


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html", error=None)

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        return render_template("signup.html", error="Username and password are required.")

    if username in USERS:
        return render_template("signup.html", error="Username already exists.")

    USERS[username] = generate_password_hash(password)
    save_users(USERS)

    session["username"] = username
    return redirect(url_for("dashboard.home"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("dashboard.home"))
