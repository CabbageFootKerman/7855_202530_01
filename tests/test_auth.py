from unittest.mock import patch
import pytest

import importlib
import requests as http_requests

def routes_module():
    # Imported lazily so the fake firebase module from conftest is already in place.
    return importlib.import_module("blueprints.auth.routes")


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


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

# ---------------------------------------------------------------------------
# Helper function coverage
# ---------------------------------------------------------------------------

def test_friendly_error_known_mapping(client):
    auth_routes = routes_module()
    msg = auth_routes._friendly_error("INVALID_PASSWORD")
    assert msg == "Invalid email or password"


def test_friendly_error_fallback_for_unknown_code(client):
    auth_routes = routes_module()
    msg = auth_routes._friendly_error("SOMETHING_ELSE", "Fallback message")
    assert msg == "Fallback message"


def test_extract_id_token_prefers_json_token_over_header(client):
    auth_routes = routes_module()

    with client.application.test_request_context(
        "/login",
        headers={"Authorization": "Bearer header-token"},
    ):
        token = auth_routes._extract_id_token_from_request({"idToken": " body-token "})

    assert token == "body-token"


def test_extract_id_token_from_bearer_header(client):
    auth_routes = routes_module()

    with client.application.test_request_context(
        "/login",
        headers={"Authorization": "Bearer header-token"},
    ):
        token = auth_routes._extract_id_token_from_request({})

    assert token == "header-token"


def test_extract_id_token_returns_empty_for_non_bearer_header(client):
    auth_routes = routes_module()

    with client.application.test_request_context(
        "/login",
        headers={"Authorization": "Token abc123"},
    ):
        token = auth_routes._extract_id_token_from_request({})

    assert token == ""


def test_start_user_session_accepts_user_id_field(client):
    auth_routes = routes_module()

    with client.application.test_request_context("/login"):
        with patch(
            "blueprints.auth.routes.firebase_auth.verify_id_token",
            return_value={"user_id": "user-123", "email": "user@example.com"},
        ):
            decoded = auth_routes._start_user_session_from_id_token("token-123")

        assert decoded["user_id"] == "user-123"
        assert auth_routes.session["logged_in"] is True
        assert auth_routes.session["username"] == "user-123"
        assert auth_routes.session["email"] == "user@example.com"
        assert auth_routes.session["id_token"] == "token-123"


def test_start_user_session_accepts_sub_field(client):
    auth_routes = routes_module()

    with client.application.test_request_context("/login"):
        with patch(
            "blueprints.auth.routes.firebase_auth.verify_id_token",
            return_value={"sub": "sub-456", "email": "sub@example.com"},
        ):
            decoded = auth_routes._start_user_session_from_id_token("token-456")

        assert decoded["sub"] == "sub-456"
        assert auth_routes.session["username"] == "sub-456"


def test_start_user_session_raises_when_no_uid_like_field_exists(client):
    auth_routes = routes_module()

    with client.application.test_request_context("/login"):
        with patch(
            "blueprints.auth.routes.firebase_auth.verify_id_token",
            return_value={"email": "nouid@example.com"},
        ):
            with pytest.raises(ValueError, match="did not contain a user id"):
                auth_routes._start_user_session_from_id_token("token-without-uid")


# ---------------------------------------------------------------------------
# Web login route coverage
# ---------------------------------------------------------------------------

def test_login_get_returns_page(client):
    response = client.get("/login")
    assert response.status_code == 200


def test_login_form_missing_fields_shows_error(client):
    response = client.post("/login", data={"email": "", "password": ""})
    assert response.status_code == 200
    assert b"Email and password are required." in response.data


def test_login_form_service_unavailable_shows_error(client):
    with patch(
        "blueprints.auth.routes.http_requests.post",
        side_effect=http_requests.RequestException("network down"),
    ):
        response = client.post(
            "/login",
            data={"email": "user@example.com", "password": "abcdef"},
        )

    assert response.status_code == 200
    assert b"Authentication service unavailable." in response.data


def test_login_form_maps_firebase_error_to_friendly_message(client):
    with patch(
        "blueprints.auth.routes.http_requests.post",
        return_value=FakeResponse(400, {"error": {"message": "USER_DISABLED"}}),
    ):
        response = client.post(
            "/login",
            data={"email": "user@example.com", "password": "abcdef"},
        )

    assert response.status_code == 200
    assert b"This account has been disabled" in response.data


def test_login_form_authentication_failed_after_token_verification_issue(client):
    with patch(
        "blueprints.auth.routes.http_requests.post",
        return_value=FakeResponse(200, {"idToken": "good-token"}),
    ), patch(
        "blueprints.auth.routes.firebase_auth.verify_id_token",
        side_effect=Exception("verification failed"),
    ):
        response = client.post(
            "/login",
            data={"email": "user@example.com", "password": "abcdef"},
        )

    assert response.status_code == 200
    assert b"Authentication failed." in response.data


def test_login_form_success_redirects_and_sets_session(client):
    with patch(
        "blueprints.auth.routes.http_requests.post",
        return_value=FakeResponse(200, {"idToken": "web-login-token"}),
    ), patch(
        "blueprints.auth.routes.firebase_auth.verify_id_token",
        return_value={"uid": "web-user-1", "email": "user@example.com"},
    ):
        response = client.post(
            "/login",
            data={"email": "user@example.com", "password": "abcdef"},
            follow_redirects=False,
        )

    assert response.status_code == 302

    with client.session_transaction() as sess:
        assert sess["logged_in"] is True
        assert sess["username"] == "web-user-1"
        assert sess["email"] == "user@example.com"
        assert sess["id_token"] == "web-login-token"


# ---------------------------------------------------------------------------
# API login fallback coverage (email/password path)
# ---------------------------------------------------------------------------

def test_api_login_with_email_password_fallback_success(client):
    with patch(
        "blueprints.auth.routes.http_requests.post",
        return_value=FakeResponse(200, {"idToken": "fallback-token"}),
    ) as mock_post, patch(
        "blueprints.auth.routes.firebase_auth.verify_id_token",
        return_value={"uid": "fallback-user", "email": "user@example.com"},
    ) as mock_verify:
        response = client.post(
            "/login",
            json={"email": "user@example.com", "password": "abcdef"},
        )

    assert response.status_code == 200
    body = response.get_json()
    assert body["message"] == "Login successful"
    assert body["username"] == "fallback-user"
    assert body["email"] == "user@example.com"
    assert body["token"] == "fallback-token"
    mock_post.assert_called_once()
    mock_verify.assert_called_once_with("fallback-token")


def test_api_login_with_email_password_service_unavailable_returns_503(client):
    with patch(
        "blueprints.auth.routes.http_requests.post",
        side_effect=http_requests.RequestException("network down"),
    ):
        response = client.post(
            "/login",
            json={"email": "user@example.com", "password": "abcdef"},
        )

    assert response.status_code == 503
    assert response.get_json() == {"error": "Authentication service unavailable"}


def test_api_login_with_email_password_bad_firebase_status_returns_401(client):
    with patch(
        "blueprints.auth.routes.http_requests.post",
        return_value=FakeResponse(400, {"error": {"message": "INVALID_PASSWORD"}}),
    ):
        response = client.post(
            "/login",
            json={"email": "user@example.com", "password": "wrongpass"},
        )

    assert response.status_code == 401
    assert response.get_json() == {"error": "Unauthorized"}


def test_api_login_with_email_password_but_missing_returned_token_returns_401(client):
    with patch(
        "blueprints.auth.routes.http_requests.post",
        return_value=FakeResponse(200, {}),
    ):
        response = client.post(
            "/login",
            json={"email": "user@example.com", "password": "abcdef"},
        )

    assert response.status_code == 401
    assert response.get_json() == {"error": "Unauthorized"}


def test_api_login_verified_token_without_uid_returns_401(client):
    with patch(
        "blueprints.auth.routes.firebase_auth.verify_id_token",
        return_value={"email": "user@example.com"},
    ):
        response = client.post("/login", json={"idToken": "token-no-uid"})

    assert response.status_code == 401
    assert response.get_json() == {"error": "Unauthorized"}


# ---------------------------------------------------------------------------
# Web signup route coverage
# ---------------------------------------------------------------------------

def test_signup_get_returns_page(client):
    response = client.get("/signup")
    assert response.status_code == 200


def test_signup_form_validation_error_renders_template_error(client):
    response = client.post(
        "/signup",
        data={
            "email": "not-an-email",
            "password": "abcdef",
            "confirm_password": "abcdef",
        },
    )

    assert response.status_code == 200
    assert b"Invalid email" in response.data


def test_signup_form_service_unavailable_shows_error(client):
    with patch(
        "blueprints.auth.routes.http_requests.post",
        side_effect=http_requests.RequestException("network down"),
    ):
        response = client.post(
            "/signup",
            data={
                "email": "newuser@example.com",
                "password": "abcdef",
                "confirm_password": "abcdef",
            },
        )

    assert response.status_code == 200
    assert b"Authentication service unavailable." in response.data


def test_signup_form_maps_firebase_error_to_friendly_message(client):
    with patch(
        "blueprints.auth.routes.http_requests.post",
        return_value=FakeResponse(400, {"error": {"message": "WEAK_PASSWORD"}}),
    ):
        response = client.post(
            "/signup",
            data={
                "email": "newuser@example.com",
                "password": "abcdef",
                "confirm_password": "abcdef",
            },
        )

    assert response.status_code == 200
    assert b"Password is too weak. Use at least 6 characters" in response.data


def test_signup_form_authentication_failed_after_token_verification_issue(client):
    with patch(
        "blueprints.auth.routes.http_requests.post",
        return_value=FakeResponse(200, {"idToken": "signup-token"}),
    ), patch(
        "blueprints.auth.routes.firebase_auth.verify_id_token",
        side_effect=Exception("verification failed"),
    ):
        response = client.post(
            "/signup",
            data={
                "email": "newuser@example.com",
                "password": "abcdef",
                "confirm_password": "abcdef",
            },
        )

    assert response.status_code == 200
    assert b"Authentication failed." in response.data


def test_signup_form_success_redirects_and_sets_session(client):
    with patch(
        "blueprints.auth.routes.http_requests.post",
        return_value=FakeResponse(200, {"idToken": "signup-web-token"}),
    ), patch(
        "blueprints.auth.routes.firebase_auth.verify_id_token",
        return_value={"uid": "new-web-user", "email": "newuser@example.com"},
    ):
        response = client.post(
            "/signup",
            data={
                "email": "newuser@example.com",
                "password": "abcdef",
                "confirm_password": "abcdef",
            },
            follow_redirects=False,
        )

    assert response.status_code == 302

    with client.session_transaction() as sess:
        assert sess["logged_in"] is True
        assert sess["username"] == "new-web-user"
        assert sess["email"] == "newuser@example.com"
        assert sess["id_token"] == "signup-web-token"


# ---------------------------------------------------------------------------
# API signup uncovered branches
# ---------------------------------------------------------------------------

def test_api_signup_service_unavailable_returns_503(client):
    with patch(
        "blueprints.auth.routes.http_requests.post",
        side_effect=http_requests.RequestException("network down"),
    ):
        response = client.post(
            "/signup",
            json={
                "email": "newuser@example.com",
                "password": "abcdef",
                "confirm_password": "abcdef",
            },
        )

    assert response.status_code == 503
    assert response.get_json() == {"error": "Authentication service unavailable"}


def test_api_signup_authentication_failed_returns_400(client):
    with patch(
        "blueprints.auth.routes.http_requests.post",
        return_value=FakeResponse(200, {"idToken": "signup-valid-token"}),
    ), patch(
        "blueprints.auth.routes.firebase_auth.verify_id_token",
        side_effect=Exception("bad token"),
    ):
        response = client.post(
            "/signup",
            json={
                "email": "newuser@example.com",
                "password": "abcdef",
                "confirm_password": "abcdef",
            },
        )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Authentication failed"}


# ---------------------------------------------------------------------------
# Logout coverage
# ---------------------------------------------------------------------------

def test_logout_clears_session_and_redirects(client):
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "someone"
        sess["email"] = "someone@example.com"
        sess["id_token"] = "some-token"

    response = client.get("/logout", follow_redirects=False)

    assert response.status_code == 302

    with client.session_transaction() as sess:
        assert "logged_in" not in sess
        assert "username" not in sess
        assert "email" not in sess
        assert "id_token" not in sess