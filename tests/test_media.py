import io
from pathlib import Path
from unittest.mock import patch

import pytest


DEVICE_ID = "test-device-001"
API_KEY = "test-sensor-key"


def set_logged_in(client, username="test_user_123"):
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = username


def device_headers():
    return {"X-API-Key": API_KEY}


@pytest.fixture
def media_upload_root(tmp_path, monkeypatch):
    import blueprints.media.routes as media_routes

    monkeypatch.setattr(media_routes, "UPLOAD_ROOT", tmp_path, raising=False)
    monkeypatch.setattr(media_routes, "BASE_DIR", tmp_path, raising=False)
    monkeypatch.setattr(media_routes, "ALLOWED_IMAGE_EXTS", {".jpg", ".jpeg", ".png"}, raising=False)
    return tmp_path


def test_snapshot_no_api_key_returns_401(client, media_upload_root):
    response = client.post(
        f"/api/device/{DEVICE_ID}/camera/0/snapshot",
        data={},
        content_type="multipart/form-data",
    )

    assert response.status_code == 401


def test_snapshot_invalid_camera_id_returns_400(client, media_upload_root):
    response = client.post(
        f"/api/device/{DEVICE_ID}/camera/9/snapshot",
        headers=device_headers(),
        data={},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "camera_id must be 0, 1, or 2."}


def test_snapshot_missing_image_field_returns_400(client, media_upload_root):
    response = client.post(
        f"/api/device/{DEVICE_ID}/camera/0/snapshot",
        headers=device_headers(),
        data={},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Missing file field 'image' (multipart/form-data)."
    }


def test_snapshot_empty_filename_returns_400(client, media_upload_root):
    response = client.post(
        f"/api/device/{DEVICE_ID}/camera/0/snapshot",
        headers=device_headers(),
        data={"image": (io.BytesIO(b"fake-bytes"), "")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "No file selected."}


def test_snapshot_unsupported_extension_returns_400(client, media_upload_root):
    response = client.post(
        f"/api/device/{DEVICE_ID}/camera/0/snapshot",
        headers=device_headers(),
        data={"image": (io.BytesIO(b"fake-bytes"), "bad.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "Unsupported file type .txt" in response.get_json()["error"]


def test_snapshot_success_saves_latest_image_and_returns_metadata(client, media_upload_root):
    response = client.post(
        f"/api/device/{DEVICE_ID}/camera/1/snapshot",
        headers=device_headers(),
        data={"image": (io.BytesIO(b"abc123"), "photo.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    body = response.get_json()

    assert body["message"] == "Latest snapshot updated."
    assert body["device_id"] == DEVICE_ID
    assert body["camera_id"] == 1
    assert body["size_bytes"] == 6
    assert body["path"] == f"device_{DEVICE_ID}/latest/cam1.jpg"

    stored = media_upload_root / f"device_{DEVICE_ID}" / "latest" / "cam1.jpg"
    assert stored.exists()
    assert stored.read_bytes() == b"abc123"


def test_media_latest_requires_login(client, media_upload_root):
    response = client.get(f"/media/device/{DEVICE_ID}/camera/0/latest.jpg")
    assert response.status_code == 302


def test_media_latest_forbidden_without_device_access(client, media_upload_root):
    set_logged_in(client)

    with patch("blueprints.media.routes.user_can_access_device", return_value=False):
        response = client.get(f"/media/device/{DEVICE_ID}/camera/0/latest.jpg")

    assert response.status_code == 403
    assert response.get_json() == {"error": "Forbidden"}


def test_media_latest_invalid_camera_id_returns_400(client, media_upload_root):
    set_logged_in(client)

    with patch("blueprints.media.routes.user_can_access_device", return_value=True):
        response = client.get(f"/media/device/{DEVICE_ID}/camera/7/latest.jpg")

    assert response.status_code == 400
    assert response.get_json() == {"error": "camera_id must be 0, 1, or 2."}


def test_media_latest_not_found_returns_404(client, media_upload_root):
    set_logged_in(client)

    with patch("blueprints.media.routes.user_can_access_device", return_value=True):
        response = client.get(f"/media/device/{DEVICE_ID}/camera/2/latest.jpg")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Snapshot not found."}


def test_media_latest_success_returns_jpeg_file(client, media_upload_root):
    set_logged_in(client)

    image_path = media_upload_root / f"device_{DEVICE_ID}" / "latest"
    image_path.mkdir(parents=True, exist_ok=True)
    stored = image_path / "cam0.jpg"
    stored.write_bytes(b"jpeg-bytes")

    with patch("blueprints.media.routes.user_can_access_device", return_value=True):
        response = client.get(f"/media/device/{DEVICE_ID}/camera/0/latest.jpg")

    assert response.status_code == 200
    assert response.mimetype == "image/jpeg"
    assert response.data == b"jpeg-bytes"