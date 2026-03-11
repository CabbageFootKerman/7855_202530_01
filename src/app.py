from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
import os

# Load .env before importing config/blueprints
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path, override=True)

print("ENV PATH:", env_path)
print("ENV EXISTS:", env_path.exists())
print("SMARTPOST_PI_API_KEY loaded?", bool(os.getenv("SMARTPOST_PI_API_KEY")))
print("SMARTPOST_PI_API_KEY value:", os.getenv("SMARTPOST_PI_API_KEY"))

from config import FLASK_SECRET_KEY, UPLOAD_ROOT

# Blueprint imports
from blueprints.dashboard.routes import dashboard_bp
from blueprints.auth.routes import auth_bp
from blueprints.device.routes import device_bp
from blueprints.media.routes import media_bp
from blueprints.profile.routes import profile_bp
from blueprints.notifications.routes import notifications_bp


app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# Ensure uploads directory exists
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

# Register blueprints
app.register_blueprint(dashboard_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(device_bp)
app.register_blueprint(media_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(notifications_bp)


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000)