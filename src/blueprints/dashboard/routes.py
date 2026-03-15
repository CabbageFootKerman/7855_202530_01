from flask import Blueprint, render_template, redirect, url_for

from utils.auth import get_current_user
from utils.device_access import get_user_devices

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def home():
    username = get_current_user()

    if not username:
        return render_template(
            "landing.html",
            project_name="Smart Post"
        )

    return redirect(url_for("dashboard.devices_page"))


@dashboard_bp.route("/devices")
def devices_page():
    username = get_current_user()

    if not username:
        return redirect(url_for("auth.login"))

    devices = get_user_devices(username)
    return render_template("devices.html", devices=devices, username=username)
