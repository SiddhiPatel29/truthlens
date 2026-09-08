"""
Tests for Image Detection Scan Persistence (Phase 4 Step 3).
Verifies that POST /api/detect/image:
- Enforces @require_auth JWT authentication.
- Persists Scans and ScanResults via ScanService.
- Correctly captures original uploaded media filename metadata.
- Atomically transitions Scan from PENDING to COMPLETED status with timestamp.
- Accurately maps detection metrics to prediction, confidence, risk_level, and result_data.
- Stores detector metadata in result_data without storing raw image bytes.
- Enforces strict user isolation across multiple authenticated accounts.
- Sanitizes server errors without leaking raw database or exception details.
"""
import base64
import io
import os
import time
import cv2
import numpy as np
import pytest
import jwt
from unittest.mock import patch
from werkzeug.security import generate_password_hash
from backend.database.db import db
from backend.database.models import User, Scan, ScanResult
from backend.services.scan_service import ScanService, ScanDatabaseError

def make_test_jpeg(width: int, height: int, color=(128, 128, 128)) -> io.BytesIO:
    """Creates a synthetic in-memory JPEG image with specified dimensions."""
    arr = np.full((height, width, 3), color, dtype=np.uint8)
    success, buf = cv2.imencode(".jpg", arr)
    assert success, f"Failed to encode test image of dimensions {width}x{height}"
    return io.BytesIO(buf.tobytes())

def decode_base64_jpeg(data_url: str):
    """Decodes a Base64 data URL into an OpenCV image matrix."""
    prefix = "data:image/jpeg;base64,"
    assert data_url.startswith(prefix), f"Expected prefix {prefix}"
    b64_str = data_url[len(prefix):]
    raw_bytes = base64.b64decode(b64_str)
    arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    assert img is not None, "Failed to decode Base64 JPEG into OpenCV matrix"
    return img

@pytest.fixture(autouse=True)
def clean_db(app):
    """Ensures a clean database state before and after each test."""
    with app.app_context():
        db.session.rollback()
        db.session.query(ScanResult).delete()
        db.session.query(Scan).delete()
        db.session.query(User).delete()
        db.session.commit()
    db.session.remove()
    yield
    with app.app_context():
        db.session.rollback()
        db.session.query(ScanResult).delete()
        db.session.query(Scan).delete()
        db.session.query(User).delete()
        db.session.commit()
    db.session.remove()

@pytest.fixture
def auth_user_a(app):
    """Creates first active test user in the database."""
    password = "UserAPassword123!"
    with app.app_context():
        user = User(
            name="Alice Image Investigator",
            email="alice.image@example.com",
            password_hash=generate_password_hash(password),
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return {"id": user_id, "name": "Alice Image Investigator", "email": "alice.image@example.com", "password": password}

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
            name="Bob Image Investigator",
            email="bob.image@example.com",
            password_hash=generate_password_hash(password),
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return {"id": user_id, "name": "Bob Image Investigator", "email": "bob.image@example.com", "password": password}

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
# 1. Valid Authenticated Image Scan Persistence
# ===========================================================================

def test_valid_authenticated_image_request_persists_scan_and_result(
    client, app, real_image_path, auth_user_a, auth_headers_a
):
    """
    1. Valid authenticated image request:
       - Returns HTTP 200 with standard response envelope.
       - Exactly one Scan record is created.
       - scan.user_id matches authenticated user.
       - scan.media_type == 'image'.
       - scan.filename is persisted correctly as 'test.jpg'.
       - scan.status == 'COMPLETED' and completed_at is populated.
       - Exactly one ScanResult record is created.
       - persisted prediction matches detector output ('DEEPFAKE' or 'AUTHENTIC').
       - persisted confidence matches detector output.
       - persisted risk_level matches calculated risk ('HIGH', 'MEDIUM', or 'LOW').
       - result_data contains the full detector outcome without raw binary bytes.
    """
    assert os.path.exists(real_image_path), f"Test image missing at {real_image_path}"

    with open(real_image_path, "rb") as img_file:
        data = {"image": (img_file, "test.jpg")}
        response = client.post(
            "/api/detect/image",
            data=data,
            content_type="multipart/form-data",
            headers=auth_headers_a
        )

    assert response.status_code == 200
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["message"] == "Image analyzed successfully."
    assert json_data["error_code"] is None

    payload = json_data["data"]
    assert "is_deepfake" in payload
    assert "confidence_score" in payload
    assert "manipulation_type" in payload
    assert "image_dimensions" in payload
    assert "heatmap_preview" in payload

    # Verify database persistence
    with app.app_context():
        scans = Scan.query.all()
        assert len(scans) == 1
        scan = scans[0]

        assert scan.user_id == auth_user_a["id"]
        assert scan.media_type == "image"
        assert scan.filename == "test.jpg"
        assert scan.status == "COMPLETED"
        assert scan.created_at is not None
        assert scan.completed_at is not None
        assert scan.completed_at >= scan.created_at

        # Verify ScanResult record
        results = ScanResult.query.all()
        assert len(results) == 1
        scan_result = results[0]

        assert scan_result.scan_id == scan.id
        expected_prediction = "DEEPFAKE" if payload["is_deepfake"] else "AUTHENTIC"
        assert scan_result.prediction == expected_prediction
        assert scan_result.confidence == pytest.approx(payload["confidence_score"], abs=1e-5)

        conf = payload["confidence_score"]
        expected_risk = "HIGH" if conf >= 0.7 else ("MEDIUM" if conf >= 0.4 else "LOW")
        assert scan_result.risk_level == expected_risk

        # Verify result_data content matches detector output
        assert scan_result.result_data == payload
        # Ensure no raw binary image bytes are stored in result_data
        assert "image_bytes" not in scan_result.result_data
        assert scan_result.created_at is not None


# ===========================================================================
# 2. Missing Authorization Header
# ===========================================================================

def test_missing_auth_header_returns_401_no_scan_created(client, app, real_image_path):
    """
    2. Missing Authorization header:
       - Returns HTTP 401 with AUTHENTICATION_REQUIRED.
       - No Scan or ScanResult record is created in the database.
    """
    with open(real_image_path, "rb") as img_file:
        data = {"image": (img_file, "test.jpg")}
        response = client.post(
            "/api/detect/image",
            data=data,
            content_type="multipart/form-data"
        )

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

def test_invalid_jwt_returns_401_no_scan_created(client, app, real_image_path):
    """
    3. Invalid JWT token:
       - Returns HTTP 401 with INVALID_TOKEN.
       - No Scan or ScanResult record is created in the database.
    """
    with open(real_image_path, "rb") as img_file:
        data = {"image": (img_file, "test.jpg")}
        response = client.post(
            "/api/detect/image",
            data=data,
            content_type="multipart/form-data",
            headers={"Authorization": "Bearer invalid.jwt.token"}
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

def test_expired_jwt_returns_401_no_scan_created(client, app, auth_user_a, real_image_path):
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

    with open(real_image_path, "rb") as img_file:
        data = {"image": (img_file, "test.jpg")}
        response = client.post(
            "/api/detect/image",
            data=data,
            content_type="multipart/form-data",
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
# 5. Missing Image / File Field
# ===========================================================================

def test_missing_image_file_field_preserves_400_no_scan_created(client, app, auth_headers_a):
    """
    5. Missing 'image' multipart field:
       - Returns HTTP 400 with MISSING_FILE.
       - No Scan or ScanResult record is created in the database.
    """
    data = {"wrong_field": (io.BytesIO(b"fake image data"), "test.jpg")}
    response = client.post(
        "/api/detect/image",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers_a
    )

    assert response.status_code == 400
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "MISSING_FILE"

    with app.app_context():
        assert Scan.query.count() == 0
        assert ScanResult.query.count() == 0


# ===========================================================================
# 6. Unsupported Image Extension
# ===========================================================================

def test_unsupported_image_extension_preserves_400_no_scan_created(client, app, auth_headers_a):
    """
    6. Unsupported file extension:
       - Returns HTTP 400 with INVALID_FILE.
       - No Scan or ScanResult record is created in the database.
    """
    data = {"image": (io.BytesIO(b"arbitrary text content"), "payload.txt")}
    response = client.post(
        "/api/detect/image",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers_a
    )

    assert response.status_code == 400
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_FILE"

    with app.app_context():
        assert Scan.query.count() == 0
        assert ScanResult.query.count() == 0


# ===========================================================================
# 7. Empty Filename & Corrupt Content Validation
# ===========================================================================

def test_empty_filename_preserves_400_no_scan_created(client, app, auth_headers_a):
    """
    7a. Empty filename provided:
       - Returns HTTP 400 with INVALID_FILE.
       - No Scan or ScanResult record is created in the database.
    """
    data = {"image": (io.BytesIO(b""), "")}
    response = client.post(
        "/api/detect/image",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers_a
    )

    assert response.status_code == 400
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_FILE"

    with app.app_context():
        assert Scan.query.count() == 0
        assert ScanResult.query.count() == 0


def test_corrupt_image_content_preserves_400_no_scan_created(client, app, auth_headers_a):
    """
    7b. Corrupted/unreadable image byte stream:
       - Returns HTTP 400 with PROCESSING_ERROR.
       - No Scan or ScanResult record is created in the database.
    """
    data = {"image": (io.BytesIO(b"corrupted binary stream"), "broken.jpg")}
    response = client.post(
        "/api/detect/image",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers_a
    )

    assert response.status_code == 400
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "PROCESSING_ERROR"

    with app.app_context():
        assert Scan.query.count() == 0
        assert ScanResult.query.count() == 0


# ===========================================================================
# 8. Database Failure During create_scan
# ===========================================================================

def test_create_scan_database_failure_returns_sanitized_500(
    client, app, real_image_path, auth_headers_a
):
    """
    8. Database failure during create_scan():
       - Returns HTTP 500 without leaking raw SQL or exception details.
       - Response success is False with error_code 'INTERNAL_SERVER_ERROR'.
       - No misleading successful response.
    """
    with patch.object(ScanService, "create_scan", side_effect=ScanDatabaseError("Raw SQLite disk I/O lock error")):
        with open(real_image_path, "rb") as img_file:
            data = {"image": (img_file, "test.jpg")}
            response = client.post(
                "/api/detect/image",
                data=data,
                content_type="multipart/form-data",
                headers=auth_headers_a
            )

    assert response.status_code == 500
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INTERNAL_SERVER_ERROR"
    assert "Raw SQLite disk" not in response.get_data(as_text=True)

    with app.app_context():
        assert Scan.query.count() == 0
        assert ScanResult.query.count() == 0


# ===========================================================================
# 9. Database Failure During save_scan_result
# ===========================================================================

def test_save_scan_result_database_failure_returns_sanitized_500(
    client, app, real_image_path, auth_headers_a
):
    """
    9. Database failure during save_scan_result():
       - Returns HTTP 500 without leaking raw database details.
       - Response success is False with error_code 'INTERNAL_SERVER_ERROR'.
       - No misleading successful response.
    """
    with patch.object(ScanService, "save_scan_result", side_effect=ScanDatabaseError("Simulated DB transaction crash")):
        with open(real_image_path, "rb") as img_file:
            data = {"image": (img_file, "test.jpg")}
            response = client.post(
                "/api/detect/image",
                data=data,
                content_type="multipart/form-data",
                headers=auth_headers_a
            )

    assert response.status_code == 500
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INTERNAL_SERVER_ERROR"
    assert "Simulated DB transaction crash" not in response.get_data(as_text=True)

    with app.app_context():
        assert ScanResult.query.count() == 0


# ===========================================================================
# 10. Multiple Authenticated Users (Isolation)
# ===========================================================================

def test_multiple_authenticated_users_image_scan_isolation(
    client, app, real_image_path, auth_user_a, auth_headers_a, auth_user_b, auth_headers_b
):
    """
    10. Multiple authenticated users:
       - User A submits an image scan; persisted scan belongs strictly to User A.
       - User B submits an image scan; persisted scan belongs strictly to User B.
       - No cross-user ownership confusion.
    """
    # User A image scan
    with open(real_image_path, "rb") as img_a:
        resp_a = client.post(
            "/api/detect/image",
            data={"image": (img_a, "user_a_evidence.jpg")},
            content_type="multipart/form-data",
            headers=auth_headers_a
        )
    assert resp_a.status_code == 200

    # User B image scan
    with open(real_image_path, "rb") as img_b:
        resp_b = client.post(
            "/api/detect/image",
            data={"image": (img_b, "user_b_evidence.jpg")},
            content_type="multipart/form-data",
            headers=auth_headers_b
        )
    assert resp_b.status_code == 200

    with app.app_context():
        assert Scan.query.count() == 2
        assert ScanResult.query.count() == 2

        scans_a = Scan.query.filter_by(user_id=auth_user_a["id"]).all()
        assert len(scans_a) == 1
        assert scans_a[0].user_id == auth_user_a["id"]
        assert scans_a[0].filename == "user_a_evidence.jpg"
        assert scans_a[0].status == "COMPLETED"
        assert scans_a[0].result is not None

        scans_b = Scan.query.filter_by(user_id=auth_user_b["id"]).all()
        assert len(scans_b) == 1
        assert scans_b[0].user_id == auth_user_b["id"]
        assert scans_b[0].filename == "user_b_evidence.jpg"
        assert scans_b[0].status == "COMPLETED"
        assert scans_b[0].result is not None

        # Verify distinct scan IDs and cross-isolation
        assert scans_a[0].id != scans_b[0].id
        assert scans_a[0].result.id != scans_b[0].result.id

def test_oversized_image_persists_no_scan(client, app, auth_headers_a):
    """Verify that an oversized image (5000x1000) rejected with 400 creates zero Scan or ScanResult records."""
    img_io = make_test_jpeg(width=5000, height=1000)
    data = {"image": (img_io, "oversized_test.jpg")}

    response = client.post(
        "/api/detect/image",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers_a
    )

    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "PROCESSING_ERROR"

    with app.app_context():
        assert Scan.query.count() == 0
        assert ScanResult.query.count() == 0

def test_persisted_image_scan_result_contains_downscaled_thumbnail(client, app, auth_headers_a, auth_user_a):
    """Verify that a large image scan persists a thumbnail heatmap preview (<= 512px) in ScanResult.result_data."""
    img_io = make_test_jpeg(width=1000, height=600)
    data = {"image": (img_io, "hires_photo.jpg")}

    response = client.post(
        "/api/detect/image",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers_a
    )

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True

    with app.app_context():
        assert Scan.query.count() == 1
        assert ScanResult.query.count() == 1

        scan = Scan.query.filter_by(user_id=auth_user_a["id"]).first()
        assert scan is not None
        assert scan.status == "COMPLETED"
        assert scan.filename == "hires_photo.jpg"

        result = scan.result
        assert result is not None
        assert isinstance(result.result_data, dict)
        assert result.result_data["image_dimensions"] == {"width": 1000, "height": 600}

        # Check persisted heatmap preview
        persisted_preview = result.result_data.get("heatmap_preview")
        assert persisted_preview is not None
        assert persisted_preview.startswith("data:image/jpeg;base64,")

        # Decode persisted thumbnail and verify dimensions <= 512
        thumb = decode_base64_jpeg(persisted_preview)
        assert thumb.shape[1] == 512
        assert thumb.shape[0] == 307
        assert thumb.shape[1] <= 512
        assert thumb.shape[0] <= 512

