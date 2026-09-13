"""
Tests for JWT Authorization & Protected Routes.
Verifies the @require_auth decorator, token extraction, claim requirements,
error responses, security guarantees, and the protected GET /api/auth/me endpoint.
"""
import time
import pytest
import jwt
from flask import g
from werkzeug.security import generate_password_hash
from backend.database.models import User
from backend.database.db import db
from backend.utils.auth import require_auth
from backend.utils.response import api_response
from backend.services.auth_service import AuthService

@pytest.fixture(autouse=True)
def clean_users(app):
    """Ensures a clean user table for each test."""
    db.session.rollback()
    db.session.query(User).delete()
    db.session.commit()
    db.session.remove()
    yield
    db.session.rollback()
    db.session.query(User).delete()
    db.session.commit()
    db.session.remove()

@pytest.fixture
def auth_user(app):
    """Creates an active test user in the database."""
    password = "ValidUserPassword123!"
    with app.app_context():
        user = User(
            name="Alice Auth",
            email="alice.auth@example.com",
            password_hash=generate_password_hash(password),
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return {"id": user_id, "name": "Alice Auth", "email": "alice.auth@example.com", "password": password}

@pytest.fixture
def valid_token(client, auth_user):
    """Generates a valid JWT access token via the standard login route."""
    response = client.post("/api/auth/login", json={
        "email": auth_user["email"],
        "password": auth_user["password"]
    })
    return response.get_json()["data"]["access_token"]


# ===========================================================================
# A. Valid Authorization Tests
# ===========================================================================

def test_valid_bearer_token_returns_http_200(client, valid_token):
    """1. Valid Bearer token returns HTTP 200."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 200
    assert response.is_json
    body = response.get_json()
    assert body["success"] is True
    assert body["message"] == "Authenticated user."
    assert body["error_code"] is None

def test_correct_user_id_extracted_from_sub(client, valid_token, auth_user):
    """2. Correct user_id is extracted from token 'sub' claim."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    body = response.get_json()
    assert "user_id" in body["data"]
    assert body["data"]["user_id"] == auth_user["id"]

def test_g_current_user_id_available_to_route(valid_token, auth_user):
    """3. g.current_user_id and g.current_user are available to the decorated route."""
    from backend.app import create_app
    from tests.conftest import TestConfig

    test_app = create_app(TestConfig)
    with test_app.app_context():
        db.create_all()
        user = User(
            id=auth_user["id"],
            name=auth_user["name"],
            email=auth_user["email"],
            password_hash="dummy_hash",
            is_active=True
        )
        db.session.add(user)
        db.session.commit()

    captured_context = {}

    @test_app.route("/api/test-context-route", methods=["GET"])
    @require_auth
    def test_context_endpoint():
        captured_context["user_id"] = g.current_user_id
        captured_context["user"] = g.current_user
        return api_response(True, "Context verified.", {"captured_id": g.current_user_id})

    test_client = test_app.test_client()
    response = test_client.get(
        "/api/test-context-route",
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 200
    assert captured_context["user_id"] == auth_user["id"]
    assert captured_context["user"].id == auth_user["id"]


# ===========================================================================
# B. Missing / Invalid Authorization Header Tests
# ===========================================================================

def test_missing_authorization_header_returns_401(client):
    """4. Missing Authorization header returns HTTP 401 AUTHENTICATION_REQUIRED."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error_code"] == "AUTHENTICATION_REQUIRED"
    assert body["data"] is None

def test_empty_authorization_header_returns_401(client):
    """5. Empty Authorization header returns HTTP 401 AUTHENTICATION_REQUIRED."""
    response = client.get("/api/auth/me", headers={"Authorization": ""})
    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error_code"] == "AUTHENTICATION_REQUIRED"

def test_whitespace_authorization_header_returns_401(client):
    """5b. Whitespace-only Authorization header returns HTTP 401 AUTHENTICATION_REQUIRED."""
    response = client.get("/api/auth/me", headers={"Authorization": "   "})
    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error_code"] == "AUTHENTICATION_REQUIRED"

def test_wrong_scheme_basic_returns_401(client):
    """6. 'Basic ...' scheme instead of Bearer returns HTTP 401 AUTHENTICATION_REQUIRED."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Basic dXNlcjpwYXNzd29yZA=="}
    )
    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error_code"] == "AUTHENTICATION_REQUIRED"

def test_bearer_without_token_returns_401(client):
    """7. 'Bearer' without token returns HTTP 401 AUTHENTICATION_REQUIRED."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer"}
    )
    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error_code"] == "AUTHENTICATION_REQUIRED"

def test_bearer_with_trailing_space_only_returns_401(client):
    """8. 'Bearer ' with empty token returns HTTP 401 AUTHENTICATION_REQUIRED."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer "}
    )
    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error_code"] == "AUTHENTICATION_REQUIRED"


# ===========================================================================
# C. Invalid Token Integrity, Signature, & Claims Tests
# ===========================================================================

def test_malformed_jwt_returns_401(client):
    """9. Malformed JWT returns HTTP 401 INVALID_TOKEN."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer this.is.not.a.valid.jwt.string"}
    )
    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error_code"] == "INVALID_TOKEN"

def test_invalid_signature_returns_401(client, app, auth_user):
    """10. Token signed with wrong secret returns HTTP 401 INVALID_TOKEN."""
    with app.app_context():
        wrong_secret = "completely-different-wrong-secret-key"
        now = int(time.time())
        payload = {
            "sub": str(auth_user["id"]),
            "iat": now,
            "exp": now + 3600
        }
        tampered_token = jwt.encode(payload, wrong_secret, algorithm="HS256")

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"}
    )
    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error_code"] == "INVALID_TOKEN"

def test_expired_token_returns_401(client, app, auth_user):
    """11. Expired token returns HTTP 401 TOKEN_EXPIRED."""
    with app.app_context():
        secret_key = app.config.get("JWT_SECRET_KEY")
        now = int(time.time())
        expired_payload = {
            "sub": str(auth_user["id"]),
            "iat": now - 3600,
            "exp": now - 60  # Expired 60s ago
        }
        expired_token = jwt.encode(expired_payload, secret_key, algorithm="HS256")

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error_code"] == "TOKEN_EXPIRED"
    assert "expired" in body["message"].lower()

def test_missing_sub_claim_returns_401(client, app):
    """12. Token missing 'sub' claim returns HTTP 401 INVALID_TOKEN."""
    with app.app_context():
        secret_key = app.config.get("JWT_SECRET_KEY")
        now = int(time.time())
        payload = {
            "iat": now,
            "exp": now + 3600
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error_code"] == "INVALID_TOKEN"

def test_missing_exp_claim_returns_401(client, app, auth_user):
    """13. Token missing 'exp' claim returns HTTP 401 INVALID_TOKEN."""
    with app.app_context():
        secret_key = app.config.get("JWT_SECRET_KEY")
        now = int(time.time())
        payload = {
            "sub": str(auth_user["id"]),
            "iat": now
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error_code"] == "INVALID_TOKEN"

def test_missing_iat_claim_returns_401(client, app, auth_user):
    """14. Token missing 'iat' claim returns HTTP 401 INVALID_TOKEN."""
    with app.app_context():
        secret_key = app.config.get("JWT_SECRET_KEY")
        now = int(time.time())
        payload = {
            "sub": str(auth_user["id"]),
            "exp": now + 3600
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error_code"] == "INVALID_TOKEN"

def test_non_integer_sub_claim_returns_401(client, app):
    """14b. Token with non-numeric 'sub' claim returns HTTP 401 INVALID_TOKEN."""
    with app.app_context():
        secret_key = app.config.get("JWT_SECRET_KEY")
        now = int(time.time())
        payload = {
            "sub": "not-a-number",
            "iat": now,
            "exp": now + 3600
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error_code"] == "INVALID_TOKEN"


# ===========================================================================
# D. Security, Privacy, & Error Envelope Tests
# ===========================================================================

def test_authorization_errors_use_standard_envelope(client):
    """15. Authorization errors adhere strictly to the standard JSON envelope."""
    response = client.get("/api/auth/me")
    body = response.get_json()
    assert set(body.keys()) == {"success", "message", "data", "error_code"}
    assert body["success"] is False
    assert isinstance(body["message"], str)
    assert body["data"] is None
    assert isinstance(body["error_code"], str)

def test_error_responses_do_not_expose_secret_key(client, app):
    """16. Authorization error responses do not leak the configured JWT secret key."""
    secret = app.config.get("JWT_SECRET_KEY")
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer bad.token.value"}
    )
    raw_text = response.get_data(as_text=True)
    assert secret not in raw_text

def test_error_responses_do_not_expose_raw_exception_text(client):
    """17. Error responses do not leak raw PyJWT or Python exception text."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid"}
    )
    raw_text = response.get_data(as_text=True)
    assert "Traceback" not in raw_text
    assert "jwt.exceptions" not in raw_text
    assert "DecodeError" not in raw_text

def test_auth_me_does_not_expose_password_hash(client, valid_token):
    """18. /api/auth/me does not expose password_hash."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    raw_text = response.get_data(as_text=True)
    assert "password_hash" not in raw_text
    assert "scrypt:" not in raw_text

def test_auth_me_does_not_expose_password(client, valid_token, auth_user):
    """19. /api/auth/me does not expose plaintext password."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    raw_text = response.get_data(as_text=True)
    assert "password" not in raw_text
    assert auth_user["password"] not in raw_text

def test_jwt_remains_signed_using_existing_configuration(client, app, valid_token):
    """20. JWT remains signed using HS256 and the configured JWT_SECRET_KEY."""
    secret_key = app.config.get("JWT_SECRET_KEY")
    decoded = jwt.decode(valid_token, secret_key, algorithms=["HS256"])
    assert decoded is not None
    assert "sub" in decoded
    assert "iat" in decoded
    assert "exp" in decoded

def test_unexpected_server_exception_returns_500_not_masked_as_401(valid_token, auth_user):
    """
    User Correction Test: Unexpected runtime/server exceptions in protected routes
    must NOT be caught by @require_auth and disguised as 401. They must reach Flask's
    centralized error handlers and return HTTP 500 INTERNAL_SERVER_ERROR.
    """
    from backend.app import create_app
    from tests.conftest import TestConfig

    test_app = create_app(TestConfig)
    with test_app.app_context():
        db.create_all()
        user = User(
            id=auth_user["id"],
            name=auth_user["name"],
            email=auth_user["email"],
            password_hash="dummy_hash",
            is_active=True
        )
        db.session.add(user)
        db.session.commit()

    @test_app.route("/api/test-server-error-route", methods=["GET"])
    @require_auth
    def failing_endpoint():
        raise RuntimeError("Simulated internal route calculation failure.")

    test_client = test_app.test_client()
    response = test_client.get(
        "/api/test-server-error-route",
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 500
    body = response.get_json()
    assert body["success"] is False
    assert body["error_code"] == "INTERNAL_SERVER_ERROR"
    assert "Traceback" not in response.get_data(as_text=True)


# ===========================================================================
# E. Active User & Database Verification Tests (SEC-09)
# ===========================================================================

def test_inactive_user_token_rejected_with_401(client, app):
    """21. Token for an inactive user is rejected with HTTP 401 INVALID_TOKEN."""
    with app.app_context():
        inactive_user = User(
            name="Inactive Person",
            email="inactive@example.com",
            password_hash=generate_password_hash("ValidPassword123!"),
            is_active=False
        )
        db.session.add(inactive_user)
        db.session.commit()
        user_id = inactive_user.id

        secret_key = app.config.get("JWT_SECRET_KEY")
        now = int(time.time())
        token = jwt.encode({
            "sub": str(user_id),
            "iat": now,
            "exp": now + 3600
        }, secret_key, algorithm="HS256")

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error_code"] == "INVALID_TOKEN"
    assert body["message"] == "Invalid authentication token."

def test_nonexistent_user_token_rejected_with_401(client, app):
    """22. Token with valid crypto/claims but nonexistent user_id is rejected with HTTP 401."""
    with app.app_context():
        secret_key = app.config.get("JWT_SECRET_KEY")
        now = int(time.time())
        # Use an ID guaranteed not to exist in clean_users
        token = jwt.encode({
            "sub": "999999",
            "iat": now,
            "exp": now + 3600
        }, secret_key, algorithm="HS256")

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error_code"] == "INVALID_TOKEN"
    assert body["message"] == "Invalid authentication token."

def test_user_deactivated_after_token_issuance_rejected(client, app, auth_user, valid_token):
    """23. Validly issued token is immediately rejected if user is subsequently deactivated."""
    # First verify token works
    res_before = client.get("/api/auth/me", headers={"Authorization": f"Bearer {valid_token}"})
    assert res_before.status_code == 200

    # Deactivate the user in database
    with app.app_context():
        user = db.session.get(User, auth_user["id"])
        user.is_active = False
        db.session.commit()
        db.session.expire_all()

    # Subsequent request must be rejected
    res_after = client.get("/api/auth/me", headers={"Authorization": f"Bearer {valid_token}"})
    assert res_after.status_code == 401
    body = res_after.get_json()
    assert body["success"] is False
    assert body["error_code"] == "INVALID_TOKEN"

def test_user_deleted_after_token_issuance_rejected(client, app, auth_user, valid_token):
    """24. Validly issued token is immediately rejected if user record is deleted."""
    # First verify token works
    res_before = client.get("/api/auth/me", headers={"Authorization": f"Bearer {valid_token}"})
    assert res_before.status_code == 200

    # Delete user from database
    with app.app_context():
        user = db.session.get(User, auth_user["id"])
        db.session.delete(user)
        db.session.commit()
        db.session.expire_all()

    # Subsequent request must be rejected
    res_after = client.get("/api/auth/me", headers={"Authorization": f"Bearer {valid_token}"})
    assert res_after.status_code == 401
    body = res_after.get_json()
    assert body["success"] is False
    assert body["error_code"] == "INVALID_TOKEN"

def test_auth_service_verify_token_does_not_access_database(app):
    """25. AuthService.verify_token remains pure cryptographic verification (no DB queries)."""
    with app.app_context():
        secret_key = app.config.get("JWT_SECRET_KEY")
        now = int(time.time())
        token = jwt.encode({
            "sub": "888888",
            "iat": now,
            "exp": now + 3600
        }, secret_key, algorithm="HS256")

        # Must succeed and return payload without requiring user 888888 in DB
        claims = AuthService.verify_token(token)
        assert claims["sub"] == "888888"
        assert claims["iat"] == now

def test_generic_authentication_error_prevents_user_enumeration(client, app, auth_user):
    """26. Nonexistent and inactive user tokens return identical generic error to prevent enumeration."""
    with app.app_context():
        secret_key = app.config.get("JWT_SECRET_KEY")
        now = int(time.time())

        # Token for nonexistent user
        token_nonexistent = jwt.encode({
            "sub": "777777",
            "iat": now,
            "exp": now + 3600
        }, secret_key, algorithm="HS256")

        # Inactive user
        inactive = User(
            name="Inactive Enum",
            email="inactive_enum@example.com",
            password_hash=generate_password_hash("ValidPassword123!"),
            is_active=False
        )
        db.session.add(inactive)
        db.session.commit()
        token_inactive = jwt.encode({
            "sub": str(inactive.id),
            "iat": now,
            "exp": now + 3600
        }, secret_key, algorithm="HS256")

    res_nonexistent = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_nonexistent}"})
    res_inactive = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_inactive}"})

    assert res_nonexistent.status_code == 401
    assert res_inactive.status_code == 401
    assert res_nonexistent.get_json() == res_inactive.get_json()
    assert res_nonexistent.get_json()["error_code"] == "INVALID_TOKEN"
    assert res_nonexistent.get_json()["message"] == "Invalid authentication token."
