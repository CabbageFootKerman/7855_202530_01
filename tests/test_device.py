"""
Tests for device endpoints and API key authentication.

Covers:
- api_key_required decorator (via telemetry and command/next endpoints)
- GET /api/device/<device_id>/state (session auth)
- POST /api/device/<device_id>/telemetry (device API key auth)
- POST /api/device/<device_id>/command (session auth)
- GET /api/device/<device_id>/command/next (device API key auth)
"""
import pytest
from unittest.mock import patch


DEVICE_ID = "test-device-001"
API_KEY = "test-sensor-key"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def auth_headers():
    """Session-authenticated headers (uses mock_firebase_auth fixture)."""
    return {"Authorization": "Bearer validtoken"}


def device_headers():
    """Device API key headers."""
    return {"X-API-Key": API_KEY}


# ---------------------------------------------------------------------------
# API key decorator — missing / wrong / valid key
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


def test_device_state_success(client, mock_firebase_auth):
    """Authenticated user with device access gets state."""
    with patch("blueprints.device.routes.user_can_access_device", return_value=True):
        response = client.get(
            f"/api/device/{DEVICE_ID}/state",
            headers=auth_headers(),
        )
    assert response.status_code == 200
    data = response.get_json()
    assert data["device_id"] == DEVICE_ID
    assert "door_state" in data


def test_device_state_forbidden(client, mock_firebase_auth):
    """Authenticated user without device access gets 403."""
    with patch("blueprints.device.routes.user_can_access_device", return_value=False):
        response = client.get(
            f"/api/device/{DEVICE_ID}/state",
            headers=auth_headers(),
        )
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


def test_command_invalid_payload(client, mock_firebase_auth):
    """Invalid command value returns 400."""
    with patch("blueprints.device.routes.user_can_access_device", return_value=True):
        response = client.post(
            f"/api/device/{DEVICE_ID}/command",
            json={"command": "explode"},
            headers=auth_headers(),
        )
    assert response.status_code == 400


def test_command_open_success(client, mock_firebase_auth):
    """Valid 'open' command returns 200."""
    with patch("blueprints.device.routes.user_can_access_device", return_value=True), \
         patch("blueprints.device.routes.publish_device_notification", return_value=None):
        response = client.post(
            f"/api/device/{DEVICE_ID}/command",
            json={"command": "open"},
            headers=auth_headers(),
        )
    assert response.status_code == 200
    assert "open" in response.get_json()["message"]


def test_command_close_success(client, mock_firebase_auth):
    """Valid 'close' command returns 200."""
    with patch("blueprints.device.routes.user_can_access_device", return_value=True), \
         patch("blueprints.device.routes.publish_device_notification", return_value=None):
        response = client.post(
            f"/api/device/{DEVICE_ID}/command",
            json={"command": "close"},
            headers=auth_headers(),
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
    """Valid key with empty queue returns 200 with null command."""
    response = client.get(
        f"/api/device/{DEVICE_ID}/command/next",
        headers=device_headers(),
    )
    assert response.status_code == 200
    assert response.get_json()["command"] is None
