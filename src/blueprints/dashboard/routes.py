from flask import Blueprint, render_template, redirect, url_for

from utils.auth import get_current_user

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def home():
    if not get_current_user():
        return render_template(
            "landing.html",
            project_name="Smart Post"
        )

    return redirect(url_for("device.device_page", device_id="smartpost-pi-01"))