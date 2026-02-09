import os
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

# Simple demo login
USERS = {"student": "secret"}

def get_current_user():
    return session.get("username")

@app.route("/")
def home():
    # If not logged in, show landing page with Login + Sign Up buttons
    if not get_current_user():
        return render_template(
            "landing.html",
            project_name="Smart Post"  # change this
        )

    # If logged in, send them to a demo device page
    return redirect(url_for("device_page", device_id="demo123"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", error=None)

    username = request.form.get("username", "")
    password = request.form.get("password", "")

    if username in USERS and password == USERS[username]:
        session["username"] = username
        return redirect(url_for("home"))

    return render_template("login.html", error="Invalid credentials.")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html", error=None)

    # Minimal demo signup (in-memory only)
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        return render_template("signup.html", error="Username and password are required.")

    if username in USERS:
        return render_template("signup.html", error="Username already exists.")

    USERS[username] = password
    session["username"] = username
    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/device/<device_id>")
def device_page(device_id):
    if not get_current_user():
        return redirect(url_for("login"))
    return render_template("device.html", device_id=device_id)

# ----- Stub APIs so UI can load -----

@app.route("/api/device/<device_id>/state", methods=["GET"])
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

@app.route("/api/device/<device_id>/command", methods=["POST"])
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
    return jsonify({"message": f"Command '{cmd}' received for {device_id}."}), 200

if __name__ == "__main__":
    app.run(debug=True, port=5000)
