"""
Tests for User Registration and Password Hashing API (POST /api/auth/register).
Includes verification of the modern password length & weak-password policy.
"""
import pytest
from werkzeug.security import check_password_hash
from backend.database.models import User
from backend.database.db import db

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

def test_register_success(client):
    """Verify successful user registration with HTTP 201 and proper envelope."""
    payload = {
        "name": "Alice Smith",
        "email": "alice@example.com",
        "password": "StrongPassword123"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["message"] == "User registered successfully."
    assert json_data["error_code"] is None

    user_info = json_data["data"]
    assert "id" in user_info
    assert isinstance(user_info["id"], int)
    assert user_info["name"] == "Alice Smith"
    assert user_info["email"] == "alice@example.com"
    assert "password_hash" not in user_info
    assert "password" not in user_info

def test_password_is_hashed_and_plaintext_not_stored(client, app):
    """Verify password is encrypted using secure hash and plaintext is never in DB."""
    plaintext = "MySecretPass_2026!"
    payload = {
        "name": "Bob Security",
        "email": "bob@example.com",
        "password": plaintext
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201

    with app.app_context():
        user = User.query.filter_by(email="bob@example.com").first()
        assert user is not None
        # Plaintext must not be saved
        assert user.password_hash != plaintext
        # Must be valid Werkzeug hash (scrypt or pbkdf2)
        assert ":" in user.password_hash
        # Verify password matches hash
        assert check_password_hash(user.password_hash, plaintext) is True
        # Verify incorrect password fails
        assert check_password_hash(user.password_hash, "WrongPassword123") is False

def test_register_duplicate_email(client):
    """Verify duplicate email registration is rejected with safe client error."""
    payload = {
        "name": "Charlie",
        "email": "charlie@example.com",
        "password": "StrongPassword123"
    }
    # First registration should succeed
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    # Second registration with same email must fail
    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 400
    assert res2.is_json

    data = res2.get_json()
    assert data["success"] is False
    assert data["error_code"] == "EMAIL_ALREADY_REGISTERED"
    assert "already exists" in data["message"].lower()

def test_register_email_normalization(client, app):
    """Verify email is trimmed of whitespace and converted to lowercase."""
    payload = {
        "name": "Dana White",
        "email": "  Dana.White@EXAMPLE.COM  ",
        "password": "StrongPassword123"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201

    json_data = response.get_json()
    assert json_data["data"]["email"] == "dana.white@example.com"

    with app.app_context():
        user = User.query.filter_by(email="dana.white@example.com").first()
        assert user is not None
        assert user.email == "dana.white@example.com"

    # Subsequent attempt with lowercase version must be detected as duplicate
    duplicate_payload = {
        "name": "Dana Imposter",
        "email": "dana.white@example.com",
        "password": "StrongPassword123"
    }
    dup_res = client.post("/api/auth/register", json=duplicate_payload)
    assert dup_res.status_code == 400
    assert dup_res.get_json()["error_code"] == "EMAIL_ALREADY_REGISTERED"

def test_register_missing_name(client):
    """Verify missing or whitespace-only name is rejected."""
    # Missing name key
    res1 = client.post("/api/auth/register", json={
        "email": "noname@example.com",
        "password": "StrongPassword123"
    })
    assert res1.status_code == 400
    assert res1.get_json()["error_code"] == "MISSING_FIELD"

    # Empty name
    res2 = client.post("/api/auth/register", json={
        "name": "   ",
        "email": "noname2@example.com",
        "password": "StrongPassword123"
    })
    assert res2.status_code == 400
    assert res2.get_json()["error_code"] == "MISSING_FIELD"

def test_register_missing_email(client):
    """Verify missing or whitespace-only email is rejected."""
    res = client.post("/api/auth/register", json={
        "name": "Alice",
        "password": "StrongPassword123"
    })
    assert res.status_code == 400
    assert res.get_json()["error_code"] == "MISSING_FIELD"

def test_register_missing_password(client):
    """Verify missing password is rejected."""
    res = client.post("/api/auth/register", json={
        "name": "Alice",
        "email": "alice@example.com"
    })
    assert res.status_code == 400
    assert res.get_json()["error_code"] == "MISSING_FIELD"

@pytest.mark.parametrize("invalid_email", [
    "not-an-email",
    "alice@",
    "@example.com",
    "alice@domain",
    "alice smith@example.com"
])
def test_register_invalid_email_format(client, invalid_email):
    """Verify various invalid email patterns are rejected."""
    payload = {
        "name": "Test User",
        "email": invalid_email,
        "password": "StrongPassword123"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    assert response.get_json()["error_code"] == "INVALID_EMAIL"

def test_register_malformed_non_json(client):
    """Verify non-JSON request body is rejected."""
    response = client.post(
        "/api/auth/register",
        data="non-json raw text string",
        content_type="text/plain"
    )
    assert response.status_code == 400
    assert response.get_json()["error_code"] == "INVALID_JSON"

def test_response_does_not_expose_password_hash(client):
    """Verify raw response payload does not contain password_hash or salt strings."""
    payload = {
        "name": "Inspector",
        "email": "inspector@example.com",
        "password": "SecretPassword_123"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201

    raw_text = response.get_data(as_text=True)
    assert "password_hash" not in raw_text
    assert "scrypt:" not in raw_text
    assert "pbkdf2:" not in raw_text
    assert "SecretPassword_123" not in raw_text

# ==============================================================================
# Modern Password Policy Tests (Length & Weakness Protection)
# ==============================================================================

def test_register_password_min_length_12_accepted(client):
    """Verify that a password with exactly 12 characters is accepted."""
    payload = {
        "name": "Min Length User",
        "email": "minlength@example.com",
        "password": "exact12chars"
    }
    assert len(payload["password"]) == 12
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    assert response.get_json()["success"] is True

def test_register_password_11_chars_rejected_too_short(client):
    """Verify that an 11-character password is rejected with PASSWORD_TOO_SHORT."""
    payload = {
        "name": "Short Password User",
        "email": "shortpw@example.com",
        "password": "shortpass11"  # exactly 11 characters
    }
    assert len(payload["password"]) == 11
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert data["error_code"] == "PASSWORD_TOO_SHORT"
    assert "at least 12 characters" in data["message"].lower()

def test_register_password_max_length_128_accepted(client):
    """Verify that a 128-character password is accepted."""
    pw_128 = "A" * 128
    payload = {
        "name": "Max Length User",
        "email": "maxlength@example.com",
        "password": pw_128
    }
    assert len(payload["password"]) == 128
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    assert response.get_json()["success"] is True

def test_register_password_129_chars_rejected_too_long(client):
    """Verify that a 129-character password is rejected with PASSWORD_TOO_LONG."""
    pw_129 = "A" * 129
    payload = {
        "name": "Too Long User",
        "email": "toolong@example.com",
        "password": pw_129
    }
    assert len(payload["password"]) == 129
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert data["error_code"] == "PASSWORD_TOO_LONG"
    assert "exceed 128 characters" in data["message"].lower()

def test_register_password_complex_characters_accepted(client):
    """Verify that a password with upper, lower, numbers, and special chars is accepted."""
    payload = {
        "name": "Complex User",
        "email": "complex@example.com",
        "password": "Secure#Pass1234!"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    assert response.get_json()["success"] is True

def test_register_password_passphrase_accepted(client):
    """Verify long password without upper/lower/number/special requirements is accepted."""
    payload = {
        "name": "Passphrase User",
        "email": "passphrase@example.com",
        "password": "this is a long secure passphrase"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    assert response.get_json()["success"] is True

def test_register_password_spaces_preserved_and_accepted(client, app):
    """Verify spaces inside and around a valid password are preserved and accepted."""
    raw_password = "  my spaced secure passphrase  "
    payload = {
        "name": "Spaced User",
        "email": "spaced@example.com",
        "password": raw_password
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201

    with app.app_context():
        user = User.query.filter_by(email="spaced@example.com").first()
        assert user is not None
        # Must verify against the exact raw unstripped password
        assert check_password_hash(user.password_hash, raw_password) is True
        # Must NOT match trimmed version, proving whitespace was preserved in hash
        assert check_password_hash(user.password_hash, raw_password.strip()) is False

def test_register_password_unicode_accepted(client, app):
    """Verify Unicode characters in a sufficiently long password are accepted."""
    unicode_password = "MünchenSecurePass2026!✓"
    payload = {
        "name": "Unicode User",
        "email": "unicode@example.com",
        "password": unicode_password
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201

    with app.app_context():
        user = User.query.filter_by(email="unicode@example.com").first()
        assert user is not None
        assert check_password_hash(user.password_hash, unicode_password) is True

def test_register_weak_password_rejected(client):
    """Verify obvious/common weak passwords are rejected with WEAK_PASSWORD."""
    payload = {
        "name": "Weak User",
        "email": "weak@example.com",
        "password": "123456789012"  # 12-char common weak sequence
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert data["error_code"] == "WEAK_PASSWORD"
    assert "common or easily guessable" in data["message"].lower()

def test_register_weak_password_case_insensitive(client):
    """Verify weak-password comparison is case-insensitive."""
    payload = {
        "name": "Weak Case User",
        "email": "weakcase@example.com",
        "password": "PASSWORD12345"  # Uppercase variant of common weak password
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert data["error_code"] == "WEAK_PASSWORD"

def test_register_weak_password_surrounding_whitespace_blocked(client):
    """Verify surrounding whitespace does not allow a weak password to bypass the blocklist."""
    payload = {
        "name": "Whitespace Weak User",
        "email": "wsweak@example.com",
        "password": "   password123   "  # 17 chars total, but strips to 'password123'
    }
    assert len(payload["password"]) > 12
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert data["error_code"] == "WEAK_PASSWORD"
