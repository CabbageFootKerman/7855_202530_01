from unittest.mock import patch
import pytest


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


@pytest.mark.parametrize(
    "payload, expected_error",
    [
        (
            {"email": "", "password": "abcdef", "confirm_password": "abcdef"},
            "Email is required",
        ),
        (
            {"email": "not-an-email", "password": "abcdef", "confirm_password": "abcdef"},
            "Invalid email",
        ),
        (
            {"email": "user@example.com", "password": "", "confirm_password": ""},
            "Password is required",
        ),
        (
            {"email": "user@example.com", "password": "123", "confirm_password": "123"},
            "Password must be at least 6 characters",
        ),
        (
            {"email": "user@example.com", "password": "abcdef", "confirm_password": "abcxyz"},
            "Passwords do not match",
        ),
    ],
)
def test_signup_invalid_input_returns_400(client, payload, expected_error):
    response = client.post("/signup", json=payload)

    assert response.status_code == 400
    assert response.get_json() == {"error": expected_error}


def test_signup_success(client):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "idToken": "signup-valid-token",
                "localId": "firebase-uid-999",
                "email": "newuser@example.com",
            }

    fake_decoded = {
        "uid": "firebase-uid-999",
        "email": "newuser@example.com",
    }

    with patch("blueprints.auth.routes.http_requests.post", return_value=FakeResponse()) as mock_post, \
         patch("blueprints.auth.routes.firebase_auth.verify_id_token", return_value=fake_decoded) as mock_verify:
        response = client.post(
            "/signup",
            json={
                "email": "newuser@example.com",
                "password": "abcdef",
                "confirm_password": "abcdef",
            },
        )

    assert response.status_code == 201
    body = response.get_json()
    assert body["message"] == "Signup successful"
    assert body["username"] == "firebase-uid-999"
    assert body["email"] == "newuser@example.com"
    assert body["token"] == "signup-valid-token"

    mock_post.assert_called_once()
    mock_verify.assert_called_once_with("signup-valid-token")


def test_signup_firebase_rejection_returns_400(client):
    class FakeResponse:
        status_code = 400

        def json(self):
            return {"error": {"message": "EMAIL_EXISTS"}}

    with patch("blueprints.auth.routes.http_requests.post", return_value=FakeResponse()) as mock_post:
        response = client.post(
            "/signup",
            json={
                "email": "existing@example.com",
                "password": "abcdef",
                "confirm_password": "abcdef",
            },
        )

    assert response.status_code == 400
    assert response.get_json() == {"error": "An account with this email already exists"}
    mock_post.assert_called_once()