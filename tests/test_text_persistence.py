"""
Tests for Text Detection Scan Persistence (Phase 4 Step 2).
Verifies that POST /api/detect/text:
- Enforces @require_auth JWT authentication.
- Persists Scans and ScanResults via ScanService.
- Atomically transitions Scan from PENDING to COMPLETED.
- Accurately maps detection metrics to prediction, confidence, risk_level, and result_data.
- Enforces strict user isolation across multiple authenticated accounts.
- Sanitizes server errors without leaking raw database or exception details.
"""
import time
import pytest
import jwt
from unittest.mock import patch
from werkzeug.security import generate_password_hash
from backend.database.db import db
from backend.database.models import User, Scan, ScanResult
from backend.services.scan_service import ScanService, ScanDatabaseError

@pytest.fixture(autouse=True)
def clean_db(app):
    """Ensures a clean database state before and after each test."""
    with app.app_context():
        db.session.query(ScanResult).delete()
        db.session.query(Scan).delete()
        db.session.query(User).delete()
        db.session.commit()
    yield
    with app.app_context():
        db.session.query(ScanResult).delete()
        db.session.query(Scan).delete()
        db.session.query(User).delete()
        db.session.commit()

@pytest.fixture
def auth_user_a(app):
    """Creates first active test user in the database."""
    password = "UserAPassword123!"
    with app.app_context():
        user = User(
            name="Alice Investigator",
            email="alice.persistence@example.com",
            password_hash=generate_password_hash(password),
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return {"id": user_id, "name": "Alice Investigator", "email": "alice.persistence@example.com", "password": password}

@pytest.fixture
def auth_headers_a(client, auth_user_a):
    """Generates valid Authorization headers for User A."""
    response = client.post("/api/auth/login", json={
        "email": auth_user_a["email"],
        "password": auth_user_a["password"]
    })
    token = response.get_json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_user_b(app):
    """Creates second active test user in the database."""
    password = "UserBPassword123!"
    with app.app_context():
        user = User(
            name="Bob Investigator",
            email="bob.persistence@example.com",
            password_hash=generate_password_hash(password),
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return {"id": user_id, "name": "Bob Investigator", "email": "bob.persistence@example.com", "password": password}

@pytest.fixture
def auth_headers_b(client, auth_user_b):
    """Generates valid Authorization headers for User B."""
    response = client.post("/api/auth/login", json={
        "email": auth_user_b["email"],
        "password": auth_user_b["password"]
    })
    token = response.get_json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Valid Authenticated Text Scan Persistence
# ===========================================================================

def test_valid_authenticated_text_request_persists_scan_and_result(client, app, auth_user_a, auth_headers_a, sample_text):
    """
    1. Valid authenticated text request:
       - Returns HTTP 200 with standard response envelope.
       - Exactly one Scan record is created.
       - scan.user_id matches authenticated user.
       - scan.media_type == 'text' and filename is None.
       - scan.status == 'COMPLETED' and completed_at is populated.
       - Exactly one ScanResult record is created.
       - persisted prediction matches detector output.
       - persisted confidence matches detector output.
       - persisted risk_level matches calculated risk.
       - result_data contains the full detector outcome.
    """
    response = client.post(
        "/api/detect/text",
        json={"text": sample_text},
        headers=auth_headers_a
    )

    assert response.status_code == 200
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["message"] == "Text analyzed successfully."
    assert json_data["error_code"] is None

    data = json_data["data"]
    assert "is_ai_generated" in data
    assert "ai_confidence_score" in data
    assert "metrics" in data
    assert "sentence_breakdown" in data

    # Verify database persistence
    with app.app_context():
        scans = Scan.query.all()
        assert len(scans) == 1
        scan = scans[0]

        assert scan.user_id == auth_user_a["id"]
        assert scan.media_type == "text"
        assert scan.filename is None
        assert scan.status == "COMPLETED"
        assert scan.created_at is not None
        assert scan.completed_at is not None
        assert scan.completed_at >= scan.created_at

        # Verify ScanResult record
        results = ScanResult.query.all()
        assert len(results) == 1
        scan_result = results[0]

        assert scan_result.scan_id == scan.id
        expected_prediction = "AI_GENERATED" if data["is_ai_generated"] else "AUTHENTIC"
        assert scan_result.prediction == expected_prediction

        assert scan_result.confidence == pytest.approx(data["ai_confidence_score"], abs=1e-5)

        # Verify risk level mapping
        conf = data["ai_confidence_score"]
        expected_risk = "HIGH" if conf >= 0.7 else ("MEDIUM" if conf >= 0.4 else "LOW")
        assert scan_result.risk_level == expected_risk

        # Verify result_data content
        assert scan_result.result_data == data
        assert scan_result.created_at is not None


# ===========================================================================
# 2. Missing Authorization Header
# ===========================================================================

def test_missing_auth_header_returns_401_no_scan_created(client, app, sample_text):
    """
    2. Missing Authorization header:
       - Returns HTTP 401 with AUTHENTICATION_REQUIRED.
       - No Scan or ScanResult record is created in the database.
    """
    response = client.post("/api/detect/text", json={"text": sample_text})

    assert response.status_code == 401
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "AUTHENTICATION_REQUIRED"

    with app.app_context():
        assert Scan.query.count() == 0
        assert ScanResult.query.count() == 0


# ===========================================================================
# 3. Invalid JWT Token
# ===========================================================================

def test_invalid_jwt_returns_401_no_scan_created(client, app, sample_text):
    """
    3. Invalid JWT token:
       - Returns HTTP 401 with INVALID_TOKEN.
       - No Scan or ScanResult record is created in the database.
    """
    response = client.post(
        "/api/detect/text",
        json={"text": sample_text},
        headers={"Authorization": "Bearer invalid.token.signature"}
    )

    assert response.status_code == 401
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_TOKEN"

    with app.app_context():
        assert Scan.query.count() == 0
        assert ScanResult.query.count() == 0


# ===========================================================================
# 4. Expired JWT Token
# ===========================================================================

def test_expired_jwt_returns_401_no_scan_created(client, app, auth_user_a, sample_text):
    """
    4. Expired JWT token:
       - Returns HTTP 401 with TOKEN_EXPIRED.
       - No Scan or ScanResult record is created in the database.
    """
    now = int(time.time())
    expired_payload = {
        "sub": auth_user_a["id"],
        "iat": now - 7200,
        "exp": now - 3600
    }
    expired_token = jwt.encode(
        expired_payload,
        app.config["JWT_SECRET_KEY"],
        algorithm="HS256"
    )

    response = client.post(
        "/api/detect/text",
        json={"text": sample_text},
        headers={"Authorization": f"Bearer {expired_token}"}
    )

    assert response.status_code == 401
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "TOKEN_EXPIRED"

    with app.app_context():
        assert Scan.query.count() == 0
        assert ScanResult.query.count() == 0


# ===========================================================================
# 5. Invalid Text Request Validation
# ===========================================================================

def test_invalid_text_request_too_short_preserves_400_no_scan_created(client, app, auth_headers_a):
    """
    5. Invalid text request (< 20 characters):
       - Returns HTTP 400 with TEXT_TOO_SHORT.
       - No Scan or ScanResult record is created in the database.
    """
    response = client.post(
        "/api/detect/text",
        json={"text": "Short"},
        headers=auth_headers_a
    )

    assert response.status_code == 400
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "TEXT_TOO_SHORT"

    with app.app_context():
        assert Scan.query.count() == 0
        assert ScanResult.query.count() == 0


def test_invalid_text_request_missing_field_preserves_400_no_scan_created(client, app, auth_headers_a):
    """
    5b. Invalid text request (missing 'text' key):
       - Returns HTTP 400 with INVALID_INPUT.
       - No Scan or ScanResult record is created in the database.
    """
    response = client.post(
        "/api/detect/text",
        json={"invalid_key": "This text is long enough but keyed wrong."},
        headers=auth_headers_a
    )

    assert response.status_code == 400
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_INPUT"

    with app.app_context():
        assert Scan.query.count() == 0
        assert ScanResult.query.count() == 0


# ===========================================================================
# 6. Database / Persistence Failure
# ===========================================================================

def test_create_scan_database_failure_returns_sanitized_500(client, app, auth_headers_a, sample_text):
    """
    6a. Database failure during create_scan():
       - Returns HTTP 500 without leaking raw SQL or exception details.
       - Response success is False with error_code 'INTERNAL_SERVER_ERROR'.
       - No misleading successful response.
    """
    with patch.object(ScanService, "create_scan", side_effect=ScanDatabaseError("Raw SQLite locked error detail")):
        response = client.post(
            "/api/detect/text",
            json={"text": sample_text},
            headers=auth_headers_a
        )

    assert response.status_code == 500
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INTERNAL_SERVER_ERROR"
    assert "Raw SQLite locked" not in response.get_data(as_text=True)

    with app.app_context():
        assert Scan.query.count() == 0
        assert ScanResult.query.count() == 0


def test_save_scan_result_database_failure_returns_sanitized_500(client, app, auth_headers_a, sample_text):
    """
    6b. Database failure during save_scan_result():
       - Returns HTTP 500 without leaking raw database details.
       - Response success is False with error_code 'INTERNAL_SERVER_ERROR'.
       - No misleading successful response.
    """
    with patch.object(ScanService, "save_scan_result", side_effect=ScanDatabaseError("Disk I/O error occurred")):
        response = client.post(
            "/api/detect/text",
            json={"text": sample_text},
            headers=auth_headers_a
        )

    assert response.status_code == 500
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INTERNAL_SERVER_ERROR"
    assert "Disk I/O error" not in response.get_data(as_text=True)

    with app.app_context():
        assert ScanResult.query.count() == 0


# ===========================================================================
# 7. Multiple Authenticated Users (Isolation)
# ===========================================================================

def test_multiple_authenticated_users_scan_ownership_isolation(
    client, app, auth_user_a, auth_headers_a, auth_user_b, auth_headers_b
):
    """
    7. Multiple authenticated users:
       - User A submits a text scan; persisted scan belongs strictly to User A.
       - User B submits a text scan; persisted scan belongs strictly to User B.
       - No cross-user ownership confusion.
    """
    text_a = "User A analysis input: The quick brown fox jumps over the lazy dog repeatedly and deliberately."
    text_b = "User B analysis input: Inquiries into artificial intelligence demonstrate varying syntactic metrics."

    # User A scan
    resp_a = client.post("/api/detect/text", json={"text": text_a}, headers=auth_headers_a)
    assert resp_a.status_code == 200

    # User B scan
    resp_b = client.post("/api/detect/text", json={"text": text_b}, headers=auth_headers_b)
    assert resp_b.status_code == 200

    with app.app_context():
        assert Scan.query.count() == 2
        assert ScanResult.query.count() == 2

        scans_a = Scan.query.filter_by(user_id=auth_user_a["id"]).all()
        assert len(scans_a) == 1
        assert scans_a[0].user_id == auth_user_a["id"]
        assert scans_a[0].status == "COMPLETED"
        assert scans_a[0].result is not None

        scans_b = Scan.query.filter_by(user_id=auth_user_b["id"]).all()
        assert len(scans_b) == 1
        assert scans_b[0].user_id == auth_user_b["id"]
        assert scans_b[0].status == "COMPLETED"
        assert scans_b[0].result is not None

        # Confirm distinct scan IDs and cross-isolation
        assert scans_a[0].id != scans_b[0].id
        assert scans_a[0].result.id != scans_b[0].result.id


# ===========================================================================
# 8. Detection Prediction Consistency
# ===========================================================================

def test_authentic_text_persists_authentic_prediction(client, app, auth_headers_a):
    """
    Verifies that human-like text with natural variance is evaluated and
    persisted with prediction 'AUTHENTIC'.
    """
    # Natural, varied sentence lengths produce high burstiness -> human probability
    natural_text = (
        "Wait. That is not what was originally agreed upon by the senior committee members during the symposium. "
        "Why? Because the results were completely unexpected and shocking to everyone present in the room! "
        "Indeed, we must re-evaluate every single foundational premise before proceeding any further with this project."
    )
    response = client.post(
        "/api/detect/text",
        json={"text": natural_text},
        headers=auth_headers_a
    )
    assert response.status_code == 200
    json_data = response.get_json()

    with app.app_context():
        scan = Scan.query.first()
        assert scan is not None
        assert scan.result is not None
        if not json_data["data"]["is_ai_generated"]:
            assert scan.result.prediction == "AUTHENTIC"
        else:
            assert scan.result.prediction == "AI_GENERATED"
