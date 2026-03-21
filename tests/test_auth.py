from unittest.mock import patch


def test_login_success(client):
    fake_decoded = {
        "uid": "firebase-uid-123",
        "email": "user@example.com",
    }

    with patch("blueprints.auth.routes.firebase_auth.verify_id_token", return_value=fake_decoded) as mock_verify:
        response = client.post("/login", json={"idToken": "valid-token"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["message"] == "Login successful"
    assert body["username"] == "firebase-uid-123"
    assert body["email"] == "user@example.com"
    mock_verify.assert_called_once_with("valid-token")


def test_login_missing_token_returns_401(client):
    response = client.post("/login", json={})

    assert response.status_code == 401
    assert response.get_json()["error"] == "Unauthorized"


def test_login_invalid_token_returns_401(client):
    with patch(
        "blueprints.auth.routes.firebase_auth.verify_id_token",
        side_effect=Exception("bad token"),
    ) as mock_verify:
        response = client.post("/login", json={"idToken": "invalid-token"})

    assert response.status_code == 401
    assert response.get_json()["error"] == "Unauthorized"
    mock_verify.assert_called_once_with("invalid-token")

def test_login_success_with_bearer_header(client):
    fake_decoded = {
        "uid": "firebase-uid-456",
        "email": "header@example.com",
    }

    with patch(
        "blueprints.auth.routes.firebase_auth.verify_id_token",
        return_value=fake_decoded,
    ) as mock_verify:
        response = client.post(
            "/login",
            headers={"Authorization": "Bearer header-token"},
            json={},
        )

    assert response.status_code == 200
    assert response.get_json()["username"] == "firebase-uid-456"
    mock_verify.assert_called_once_with("header-token")