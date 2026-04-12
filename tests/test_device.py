"""
Tests for device endpoints and API key authentication.

Covers:
- require_device_api_key decorator (via telemetry and command/next endpoints)
- GET /api/device/<device_id>/state (session auth)
- POST /api/device/<device_id>/telemetry (device API key auth)
- POST /api/device/<device_id>/command (session auth)
- GET /api/device/<device_id>/command/next (device API key auth)
"""
import pytest
from unittest.mock import patch
import importlib

DEVICE_ID = "test-device-001"
API_KEY = "test-sensor-key"


# ---------------------------------------------------------------------------
# Helper: inject a logged-in session directly (no JWT needed)
# ---------------------------------------------------------------------------

def set_logged_in(client):
    """Push a valid session into the test client so api_login_required passes."""
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "test_user_123"


def device_headers():
    """Device API key headers."""
    return {"X-API-Key": API_KEY}


@pytest.fixture(autouse=True)
def clear_device_route_state():
    routes = importlib.import_module("blueprints.device.routes")

    with routes.DEVICE_LOCK:
        routes.DEVICE_STATE.clear()
        routes.DEVICE_COMMANDS.clear()

    yield

    with routes.DEVICE_LOCK:
        routes.DEVICE_STATE.clear()
        routes.DEVICE_COMMANDS.clear()

# ---------------------------------------------------------------------------
# require_device_api_key decorator — missing / wrong / valid key
# ---------------------------------------------------------------------------

def test_telemetry_no_api_key(client):
    """Missing X-API-Key returns 401."""
    response = client.post(
        f"/api/device/{DEVICE_ID}/telemetry",
        json={"door_state": "closed", "weight_g": 0.0},
    )
    assert response.status_code == 401


def test_telemetry_wrong_api_key(client):
    """Wrong X-API-Key returns 401."""
    response = client.post(
        f"/api/device/{DEVICE_ID}/telemetry",
        json={"door_state": "closed", "weight_g": 0.0},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


def test_telemetry_valid_api_key(client):
    """Valid API key + valid JSON returns 200."""
    response = client.post(
        f"/api/device/{DEVICE_ID}/telemetry",
        json={"door_state": "closed", "weight_g": 1.5},
        headers=device_headers(),
    )
    assert response.status_code == 200
    assert response.get_json()["message"] == "Telemetry received."


# ---------------------------------------------------------------------------
# Telemetry — payload validation
# ---------------------------------------------------------------------------

def test_telemetry_invalid_content_type(client):
    """Non-JSON content type returns 415."""
    response = client.post(
        f"/api/device/{DEVICE_ID}/telemetry",
        data="door_state=closed",
        headers=device_headers(),
    )
    assert response.status_code == 415


def test_telemetry_invalid_weight(client):
    """Non-numeric weight_g returns 400."""
    response = client.post(
        f"/api/device/{DEVICE_ID}/telemetry",
        json={"door_state": "closed", "weight_g": "heavy"},
        headers=device_headers(),
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/device/<device_id>/state — session auth
# ---------------------------------------------------------------------------

def test_device_state_no_auth(client):
    """Missing session returns 401."""
    response = client.get(f"/api/device/{DEVICE_ID}/state")
    assert response.status_code == 401


def test_device_state_success(client):
    """Authenticated user with device access gets state."""
    set_logged_in(client)
    with patch("blueprints.device.routes.user_can_access_device", return_value=True):
        response = client.get(f"/api/device/{DEVICE_ID}/state")
    assert response.status_code == 200
    data = response.get_json()
    assert data["device_id"] == DEVICE_ID
    assert "door_state" in data


def test_device_state_forbidden(client):
    """Authenticated user without device access gets 403."""
    set_logged_in(client)
    with patch("blueprints.device.routes.user_can_access_device", return_value=False):
        response = client.get(f"/api/device/{DEVICE_ID}/state")
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/device/<device_id>/command — session auth
# ---------------------------------------------------------------------------

def test_command_no_auth(client):
    """Missing session returns 401."""
    response = client.post(
        f"/api/device/{DEVICE_ID}/command",
        json={"command": "open"},
    )
    assert response.status_code == 401


def test_command_invalid_payload(client):
    """Invalid command value returns 400."""
    set_logged_in(client)
    with patch("blueprints.device.routes.user_can_access_device", return_value=True):
        response = client.post(
            f"/api/device/{DEVICE_ID}/command",
            json={"command": "explode"},
        )
    assert response.status_code == 400


def test_command_open_success(client):
    """Valid 'open' command returns 200."""
    set_logged_in(client)
    with patch("blueprints.device.routes.user_can_access_device", return_value=True), \
         patch("blueprints.device.routes.publish_device_notification", return_value=None):
        response = client.post(
            f"/api/device/{DEVICE_ID}/command",
            json={"command": "open"},
        )
    assert response.status_code == 200
    assert "open" in response.get_json()["message"]


def test_command_close_success(client):
    """Valid 'close' command returns 200."""
    set_logged_in(client)
    with patch("blueprints.device.routes.user_can_access_device", return_value=True), \
         patch("blueprints.device.routes.publish_device_notification", return_value=None):
        response = client.post(
            f"/api/device/{DEVICE_ID}/command",
            json={"command": "close"},
        )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/device/<device_id>/command/next — device API key auth
# ---------------------------------------------------------------------------

def test_command_next_no_api_key(client):
    """Missing X-API-Key returns 401."""
    response = client.get(f"/api/device/{DEVICE_ID}/command/next")
    assert response.status_code == 401


def test_command_next_wrong_api_key(client):
    """Wrong X-API-Key returns 401."""
    response = client.get(
        f"/api/device/{DEVICE_ID}/command/next",
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


def test_command_next_valid_key_empty_queue(client):
    """Valid key returns 200 with null command once queue is drained."""
    # Drain any commands left in the queue from previous tests
    # (DEVICE_COMMANDS is module-level state that persists across tests)
    for _ in range(10):
        r = client.get(
            f"/api/device/{DEVICE_ID}/command/next",
            headers=device_headers(),
        )
        if r.get_json().get("command") is None:
            break

    response = client.get(
        f"/api/device/{DEVICE_ID}/command/next",
        headers=device_headers(),
    )
    assert response.status_code == 200
    assert response.get_json()["command"] is None


def test_device_state_defaults_when_no_telemetry(client):
    set_logged_in(client)
    with patch("blueprints.device.routes.user_can_access_device", return_value=True):
        response = client.get(f"/api/device/{DEVICE_ID}/state")

    assert response.status_code == 200
    data = response.get_json()
    assert data["device_id"] == DEVICE_ID
    assert data["door_state"] == "unknown"
    assert data["weight_g"] == 0.0
    assert data["servo_state"] == "unknown"
    assert data["solenoid_state"] == "unknown"
    assert data["actuator_state"] == "unknown"
    assert data["last_update_iso"] is None
    assert data["cameras"]["cam0"].endswith("/camera/0/latest.jpg")


def test_telemetry_updates_state_and_state_endpoint_returns_it(client):
    telemetry = {
        "door_state": "closed",
        "weight_g": 12.5,
        "servo_state": "idle",
        "solenoid_state": "off",
        "actuator_state": "ready",
    }

    post_response = client.post(
        f"/api/device/{DEVICE_ID}/telemetry",
        json=telemetry,
        headers=device_headers(),
    )
    assert post_response.status_code == 200

    set_logged_in(client)
    with patch("blueprints.device.routes.user_can_access_device", return_value=True):
        get_response = client.get(f"/api/device/{DEVICE_ID}/state")

    assert get_response.status_code == 200
    data = get_response.get_json()
    assert data["device_id"] == DEVICE_ID
    assert data["door_state"] == "closed"
    assert data["weight_g"] == 12.5
    assert data["servo_state"] == "idle"
    assert data["solenoid_state"] == "off"
    assert data["actuator_state"] == "ready"
    assert data["last_update_iso"] is not None


def test_command_forbidden_without_device_access(client):
    set_logged_in(client)
    with patch("blueprints.device.routes.user_can_access_device", return_value=False):
        response = client.post(
            f"/api/device/{DEVICE_ID}/command",
            json={"command": "open"},
        )

    assert response.status_code == 403
    assert response.get_json()["error"] == "Forbidden"


def test_command_invalid_content_type(client):
    set_logged_in(client)
    with patch("blueprints.device.routes.user_can_access_device", return_value=True):
        response = client.post(
            f"/api/device/{DEVICE_ID}/command",
            data="command=open",
        )

    assert response.status_code == 415
    assert response.get_json()["error"] == "Content-Type must be application/json."


def test_command_capture_requires_integer_camera_id(client):
    set_logged_in(client)
    with patch("blueprints.device.routes.user_can_access_device", return_value=True):
        response = client.post(
            f"/api/device/{DEVICE_ID}/command",
            json={"command": "capture", "camera_id": "abc"},
        )

    assert response.status_code == 400
    assert response.get_json()["error"] == "camera_id must be an integer."


def test_command_capture_requires_camera_id_in_range(client):
    set_logged_in(client)
    with patch("blueprints.device.routes.user_can_access_device", return_value=True):
        response = client.post(
            f"/api/device/{DEVICE_ID}/command",
            json={"command": "capture", "camera_id": 99},
        )

    assert response.status_code == 400
    assert response.get_json()["error"] == "camera_id must be 0, 1, or 2."


def test_command_capture_success_is_queued_and_returned_by_command_next(client):
    set_logged_in(client)
    with patch("blueprints.device.routes.user_can_access_device", return_value=True), \
         patch("blueprints.device.routes.publish_device_notification", return_value=None):
        response = client.post(
            f"/api/device/{DEVICE_ID}/command",
            json={"command": "capture", "camera_id": 2},
        )

    assert response.status_code == 200

    next_response = client.get(
        f"/api/device/{DEVICE_ID}/command/next",
        headers=device_headers(),
    )
    assert next_response.status_code == 200
    payload = next_response.get_json()
    assert payload["command"] == "capture"
    assert payload["camera_id"] == 2
    assert payload["created_by"] == "test_user_123"
    assert payload["created_at"]


def test_command_next_returns_queued_open_command_then_empty(client):
    set_logged_in(client)
    with patch("blueprints.device.routes.user_can_access_device", return_value=True), \
         patch("blueprints.device.routes.publish_device_notification", return_value=None):
        post_response = client.post(
            f"/api/device/{DEVICE_ID}/command",
            json={"command": "open"},
        )

    assert post_response.status_code == 200

    first_get = client.get(
        f"/api/device/{DEVICE_ID}/command/next",
        headers=device_headers(),
    )
    assert first_get.status_code == 200
    assert first_get.get_json()["command"] == "open"

    second_get = client.get(
        f"/api/device/{DEVICE_ID}/command/next",
        headers=device_headers(),
    )
    assert second_get.status_code == 200
    assert second_get.get_json()["command"] is None


def test_command_close_success_publishes_two_notifications(client):
    set_logged_in(client)
    with patch("blueprints.device.routes.user_can_access_device", return_value=True), \
         patch("blueprints.device.routes.publish_device_notification", return_value=None) as mock_publish:
        response = client.post(
            f"/api/device/{DEVICE_ID}/command",
            json={"command": "close"},
        )

    assert response.status_code == 200
    assert mock_publish.call_count == 2

    first_call = mock_publish.call_args_list[0].kwargs
    second_call = mock_publish.call_args_list[1].kwargs

    assert first_call["notif_type"] == "device_command"
    assert second_call["notif_type"] == "door_close_requested"


def test_command_notification_failure_still_returns_200(client):
    set_logged_in(client)
    with patch("blueprints.device.routes.user_can_access_device", return_value=True), \
         patch(
             "blueprints.device.routes.publish_device_notification",
             side_effect=Exception("notification failed"),
         ):
        response = client.post(
            f"/api/device/{DEVICE_ID}/command",
            json={"command": "open"},
        )

    assert response.status_code == 200
    assert "open" in response.get_json()["message"]