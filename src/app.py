from flask import Flask

from config import FLASK_SECRET_KEY, UPLOAD_ROOT, FIREBASE_WEB_API_KEY, SENSOR_API_KEY
from extensions import limiter

print("--- SmartPost Startup Check ---")
print(f"  FLASK_SECRET_KEY set?       {bool(FLASK_SECRET_KEY)}")
print(f"  FIREBASE_WEB_API_KEY set?   {bool(FIREBASE_WEB_API_KEY)}")
#print(f"  SENSOR_API_KEY set?         {bool(SENSOR_API_KEY)}")
print("-------------------------------")

# Blueprint imports
from blueprints.dashboard.routes import dashboard_bp
from blueprints.auth.routes import auth_bp
from blueprints.device.routes import device_bp
from blueprints.media.routes import media_bp
from blueprints.profile.routes import profile_bp
from blueprints.notifications.routes import notifications_bp


app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# Rate limiter (shared instance from extensions.py)
limiter.init_app(app)

# Ensure uploads directory exists
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

# Register blueprints
app.register_blueprint(dashboard_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(device_bp)
app.register_blueprint(media_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(notifications_bp)


@app.after_request
def no_cache_authenticated_pages(response):
    """Prevent browser from caching pages so back-button after logout
    forces a fresh server request instead of showing stale content."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000)