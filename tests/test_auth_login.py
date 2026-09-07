"""
Tests for User Login and JWT Authentication API (POST /api/auth/login).
Verifies credential validation, anti-enumeration security, and JWT issuance.
"""
import time
import pytest
import jwt
from werkzeug.security import generate_password_hash
from backend.database.models import User
from backend.database.db import db
from backend.services.auth_service import AuthService

@pytest.fixture(autouse=True)
def clean_users(app):
    """Ensures a clean user table for each test."""
    with app.app_context():
        db.session.query(User).delete()
        db.session.commit()
    yield
    with app.app_context():
        db.session.query(User).delete()
        db.session.commit()

@pytest.fixture
def active_user(app):
    """Creates and returns an active test user."""
    password = "ValidUserPassword123!"
    with app.app_context():
        user = User(
            name="Alice Login",
            email="alice.login@example.com",
            password_hash=generate_password_hash(password),
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return {"id": user_id, "email": "alice.login@example.com", "password": password}

@pytest.fixture
def inactive_user(app):
    """Creates and returns an inactive test user."""
    password = "InactivePassword123!"
    with app.app_context():
        user = User(
            name="Inactive Bob",
            email="bob.inactive@example.com",
            password_hash=generate_password_hash(password),
            is_active=False
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return {"id": user_id, "email": "bob.inactive@example.com", "password": password}

def test_login_success_http_200(client, active_user):
    """1. Successful login returns HTTP 200."""
    response = client.post("/api/auth/login", json={
        "email": active_user["email"],
        "password": active_user["password"]
    })
    assert response.status_code == 200
    assert response.is_json

def test_login_success_returns_access_token(client, active_user):
    """2. Successful login returns access_token in standard data envelope."""
    response = client.post("/api/auth/login", json={
        "email": active_user["email"],
        "password": active_user["password"]
    })
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["message"] == "Login successful."
    assert json_data["error_code"] is None
    assert "access_token" in json_data["data"]
    assert isinstance(json_data["data"]["access_token"], str)
    assert len(json_data["data"]["access_token"]) > 20

def test_login_token_type_is_bearer(client, active_user):
    """3. token_type is Bearer."""
    response = client.post("/api/auth/login", json={
        "email": active_user["email"],
        "password": active_user["password"]
    })
    json_data = response.get_json()
    assert json_data["data"]["token_type"] == "Bearer"

def test_login_expires_in_present_and_sensible(client, active_user):
    """4. expires_in is present and sensible (matches 24h = 86400s)."""
    response = client.post("/api/auth/login", json={
        "email": active_user["email"],
        "password": active_user["password"]
    })
    json_data = response.get_json()
    assert "expires_in" in json_data["data"]
    expires_in = json_data["data"]["expires_in"]
    assert isinstance(expires_in, int)
    assert expires_in == 86400  # 24 hours * 3600 seconds

def test_login_response_does_not_expose_password_hash(client, active_user):
    """5. Returned response does not contain password_hash or salt."""
    response = client.post("/api/auth/login", json={
        "email": active_user["email"],
        "password": active_user["password"]
    })
    raw_text = response.get_data(as_text=True)
    assert "password_hash" not in raw_text
    assert "scrypt:" not in raw_text
    assert "pbkdf2:" not in raw_text

def test_login_response_does_not_expose_password(client, active_user):
    """6. Returned response does not contain plaintext password."""
    response = client.post("/api/auth/login", json={
        "email": active_user["email"],
        "password": active_user["password"]
    })
    raw_text = response.get_data(as_text=True)
    assert active_user["password"] not in raw_text

def test_correct_password_succeeds(client, active_user):
    """7. Correct password succeeds."""
    response = client.post("/api/auth/login", json={
        "email": active_user["email"],
        "password": active_user["password"]
    })
    assert response.status_code == 200
    assert response.get_json()["success"] is True

def test_incorrect_password_returns_http_401(client, active_user):
    """8. Incorrect password returns HTTP 401 with INVALID_CREDENTIALS."""
    response = client.post("/api/auth/login", json={
        "email": active_user["email"],
        "password": "WrongPassword123!"
    })
    assert response.status_code == 401
    assert response.is_json
    data = response.get_json()
    assert data["success"] is False
    assert data["error_code"] == "INVALID_CREDENTIALS"
    assert data["message"] == "Invalid email or password."
    assert data["data"] is None

def test_nonexistent_email_returns_http_401(client):
    """9. Nonexistent email returns HTTP 401."""
    response = client.post("/api/auth/login", json={
        "email": "doesnotexist@example.com",
        "password": "AnyPassword123!"
    })
    assert response.status_code == 401
    assert response.is_json
    data = response.get_json()
    assert data["success"] is False
    assert data["error_code"] == "INVALID_CREDENTIALS"
    assert data["message"] == "Invalid email or password."

def test_incorrect_password_and_nonexistent_email_identical_response(client, active_user):
    """10. Incorrect password and nonexistent email use the EXACT SAME error response."""
    res_wrong_pw = client.post("/api/auth/login", json={
        "email": active_user["email"],
        "password": "WrongPassword123!"
    })
    res_no_user = client.post("/api/auth/login", json={
        "email": "nobody@example.com",
        "password": "WrongPassword123!"
    })
    assert res_wrong_pw.status_code == res_no_user.status_code == 401
    assert res_wrong_pw.get_json() == res_no_user.get_json()

def test_inactive_user_cannot_login(client, inactive_user):
    """11. Inactive user cannot log in and receives identical generic 401 response."""
    response = client.post("/api/auth/login", json={
        "email": inactive_user["email"],
        "password": inactive_user["password"]
    })
    assert response.status_code == 401
    data = response.get_json()
    assert data["success"] is False
    assert data["error_code"] == "INVALID_CREDENTIALS"
    assert data["message"] == "Invalid email or password."

def test_missing_email_returns_http_400(client):
    """12. Missing email returns HTTP 400 with MISSING_FIELD."""
    response = client.post("/api/auth/login", json={
        "password": "SomePassword123!"
    })
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert data["error_code"] == "MISSING_FIELD"

def test_missing_password_returns_http_400(client):
    """13. Missing password returns HTTP 400 with MISSING_FIELD."""
    response = client.post("/api/auth/login", json={
        "email": "alice@example.com"
    })
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert data["error_code"] == "MISSING_FIELD"

def test_non_string_email_rejected(client):
    """14. Non-string email is rejected with HTTP 400."""
    response = client.post("/api/auth/login", json={
        "email": 12345,
        "password": "SomePassword123!"
    })
    assert response.status_code == 400
    assert response.get_json()["error_code"] == "MISSING_FIELD"

def test_non_string_password_rejected(client):
    """15. Non-string password is rejected with HTTP 400."""
    response = client.post("/api/auth/login", json={
        "email": "alice@example.com",
        "password": ["not", "a", "string"]
    })
    assert response.status_code == 400
    assert response.get_json()["error_code"] == "MISSING_FIELD"

def test_malformed_non_json_request_rejected(client):
    """16. Malformed/non-JSON request is rejected safely with HTTP 400."""
    response = client.post(
        "/api/auth/login",
        data="plain text payload",
        content_type="text/plain"
    )
    assert response.status_code == 400
    assert response.get_json()["error_code"] == "INVALID_JSON"

def test_email_normalization_works_consistently(client, active_user):
    """17. Email normalization works consistently with registration (whitespace/case insensitive)."""
    padded_email = f"  {active_user['email'].upper()}  "
    response = client.post("/api/auth/login", json={
        "email": padded_email,
        "password": active_user["password"]
    })
    assert response.status_code == 200
    assert response.get_json()["success"] is True

def test_jwt_decoded_and_verified_with_secret(client, app, active_user):
    """18. Generated JWT can be decoded and verified using the configured secret."""
    response = client.post("/api/auth/login", json={
        "email": active_user["email"],
        "password": active_user["password"]
    })
    token = response.get_json()["data"]["access_token"]
    with app.app_context():
        secret_key = app.config.get("JWT_SECRET_KEY")
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        assert decoded is not None
        # Also verify AuthService.verify_token helper
        helper_decoded = AuthService.verify_token(token)
        assert helper_decoded == decoded

def test_jwt_contains_expected_user_id(client, active_user):
    """19. JWT contains the expected identity/user ID in 'sub' claim."""
    response = client.post("/api/auth/login", json={
        "email": active_user["email"],
        "password": active_user["password"]
    })
    token = response.get_json()["data"]["access_token"]
    decoded = jwt.decode(token, options={"verify_signature": False})
    assert decoded["sub"] == str(active_user["id"])

def test_jwt_contains_expiration_and_issued_at(client, active_user):
    """20. JWT contains expiration ('exp') and issued-at ('iat') claims."""
    response = client.post("/api/auth/login", json={
        "email": active_user["email"],
        "password": active_user["password"]
    })
    token = response.get_json()["data"]["access_token"]
    decoded = jwt.decode(token, options={"verify_signature": False})
    assert "exp" in decoded
    assert "iat" in decoded
    assert decoded["exp"] > decoded["iat"]
    assert (decoded["exp"] - decoded["iat"]) == 86400

def test_expired_jwt_rejected_by_verification(app):
    """21. Expired JWT is rejected by token verification."""
    with app.app_context():
        secret_key = app.config.get("JWT_SECRET_KEY")
        expired_payload = {
            "sub": "999",
            "iat": int(time.time()) - 200,
            "exp": int(time.time()) - 100
        }
        expired_token = jwt.encode(expired_payload, secret_key, algorithm="HS256")

        with pytest.raises(jwt.ExpiredSignatureError):
            AuthService.verify_token(expired_token)

def test_jwt_payload_does_not_contain_password_or_hash(client, active_user):
    """22. Token does not contain password, password_hash, or sensitive secrets."""
    response = client.post("/api/auth/login", json={
        "email": active_user["email"],
        "password": active_user["password"]
    })
    token = response.get_json()["data"]["access_token"]
    decoded = jwt.decode(token, options={"verify_signature": False})
    assert "password" not in decoded
    assert "password_hash" not in decoded
    assert "secret" not in decoded
    assert set(decoded.keys()) == {"sub", "iat", "exp"}

def test_login_does_not_alter_stored_password_hash(client, app, active_user):
    """23. Login does not alter the stored password hash."""
    with app.app_context():
        user_before = User.query.filter_by(email=active_user["email"]).first()
        original_hash = user_before.password_hash

    response = client.post("/api/auth/login", json={
        "email": active_user["email"],
        "password": active_user["password"]
    })
    assert response.status_code == 200

    with app.app_context():
        user_after = User.query.filter_by(email=active_user["email"]).first()
        assert user_after.password_hash == original_hash
