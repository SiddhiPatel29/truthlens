"""
Tests for Audio Detection Scan Persistence (Phase 4 Step 5).
Verifies that POST /api/detect/audio:
- Enforces @require_auth JWT authentication before processing audio streams.
- Persists Scans and ScanResults via ScanService.
- Correctly captures original uploaded media filename metadata.
- Atomically transitions Scan from PENDING to COMPLETED status with timestamp.
- Accurately maps detection metrics to prediction, confidence, risk_level, and result_data.
- Stores deliberate serializable detector metadata in result_data without storing raw audio bytes.
- Enforces strict user isolation across multiple authenticated accounts.
- Sanitizes server errors without leaking raw database or exception details.
"""
import io
import os
import time
import numpy as np
import pytest
import jwt
from unittest.mock import patch
from werkzeug.security import generate_password_hash
from backend.database.db import db
from backend.database.models import User, Scan, ScanResult
from backend.services.scan_service import ScanService, ScanDatabaseError
from backend.services.audio_service import AudioDetectionService

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
            name="Alice Audio Investigator",
            email="alice.audio@example.com",
            password_hash=generate_password_hash(password),
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return {"id": user_id, "name": "Alice Audio Investigator", "email": "alice.audio@example.com", "password": password}

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
            name="Bob Audio Investigator",
            email="bob.audio@example.com",
            password_hash=generate_password_hash(password),
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return {"id": user_id, "name": "Bob Audio Investigator", "email": "bob.audio@example.com", "password": password}

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
# 1. Valid Authenticated Audio Scan Persistence
# ===========================================================================

def test_valid_authenticated_audio_request_persists_scan_and_result(
    client, app, real_audio_path, auth_user_a, auth_headers_a
):
    """
    1. Valid authenticated audio request:
       - Returns HTTP 200 with standard response envelope.
       - Exactly one Scan record is created.
       - scan.user_id matches authenticated user.
       - scan.media_type == 'audio'.
       - scan.filename is persisted correctly as 'test.wav'.
       - scan.status == 'COMPLETED' and completed_at is populated.
       - Exactly one ScanResult record is created.
       - persisted prediction matches detector output ('SYNTHETIC' or 'AUTHENTIC').
       - persisted confidence matches detector output.
       - persisted risk_level matches calculated risk ('HIGH', 'MEDIUM', or 'LOW').
       - result_data contains deliberately constructed serializable metrics and lip-sync events without raw audio bytes.
    """
    assert os.path.exists(real_audio_path), f"Test audio missing at {real_audio_path}"

    with open(real_audio_path, "rb") as aud_file:
        data = {"audio": (aud_file, "test.wav")}
        response = client.post(
            "/api/detect/audio",
            data=data,
            content_type="multipart/form-data",
            headers=auth_headers_a
        )

    assert response.status_code == 200
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["message"] == "Audio analyzed successfully."
    assert json_data["error_code"] is None

    payload = json_data["data"]
    assert "is_synthetic_audio" in payload
    assert "confidence_score" in payload
    assert "metrics" in payload
    assert "lip_sync_discrepancies" in payload

    # Verify database persistence
    with app.app_context():
        scans = Scan.query.all()
        assert len(scans) == 1
        scan = scans[0]

        assert scan.user_id == auth_user_a["id"]
        assert scan.media_type == "audio"
        assert scan.filename == "test.wav"
        assert scan.status == "COMPLETED"
        assert scan.created_at is not None
        assert scan.completed_at is not None
        assert scan.completed_at >= scan.created_at

        # Verify ScanResult record
        results = ScanResult.query.all()
        assert len(results) == 1
        scan_result = results[0]

        assert scan_result.scan_id == scan.id
        expected_prediction = "SYNTHETIC" if payload["is_synthetic_audio"] else "AUTHENTIC"
        assert scan_result.prediction == expected_prediction
        assert scan_result.confidence == pytest.approx(payload["confidence_score"], abs=1e-5)

        conf = payload["confidence_score"]
        expected_risk = "HIGH" if conf >= 0.7 else ("MEDIUM" if conf >= 0.4 else "LOW")
        assert scan_result.risk_level == expected_risk

        # Verify result_data content is deliberately constructed
        assert "is_synthetic_audio" in scan_result.result_data
        assert "confidence_score" in scan_result.result_data
        assert "metrics" in scan_result.result_data
        assert "duration_seconds" in scan_result.result_data["metrics"]
        assert "sample_rate_hz" in scan_result.result_data["metrics"]
        assert "zero_crossing_rate" in scan_result.result_data["metrics"]
        assert "energy_variance" in scan_result.result_data["metrics"]
        assert "lip_sync_discrepancies" in scan_result.result_data

        # Verify no raw audio binary bytes or temporary arrays are stored in result_data
        assert "audio_bytes" not in scan_result.result_data
        assert "raw_samples" not in scan_result.result_data
        assert "data" not in scan_result.result_data
        assert scan_result.created_at is not None


# ===========================================================================
# 2. Missing Authorization Header
# ===========================================================================

def test_missing_auth_header_returns_401_no_scan_created(client, app, real_audio_path):
    """
    2. Missing Authorization header:
       - Returns HTTP 401 with AUTHENTICATION_REQUIRED.
       - No Scan or ScanResult record is created in the database.
       - Audio processing does not execute.
    """
    with patch.object(AudioDetectionService, "analyze_audio") as mock_analyze:
        with open(real_audio_path, "rb") as aud_file:
            data = {"audio": (aud_file, "test.wav")}
            response = client.post(
                "/api/detect/audio",
                data=data,
                content_type="multipart/form-data"
            )

        mock_analyze.assert_not_called()

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

def test_invalid_jwt_returns_401_no_scan_created(client, app, real_audio_path):
    """
    3. Invalid JWT token:
       - Returns HTTP 401 with INVALID_TOKEN.
       - No Scan or ScanResult record is created in the database.
       - Audio processing does not execute.
    """
    with patch.object(AudioDetectionService, "analyze_audio") as mock_analyze:
        with open(real_audio_path, "rb") as aud_file:
            data = {"audio": (aud_file, "test.wav")}
            response = client.post(
                "/api/detect/audio",
                data=data,
                content_type="multipart/form-data",
                headers={"Authorization": "Bearer invalid.jwt.token"}
            )

        mock_analyze.assert_not_called()

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

def test_expired_jwt_returns_401_no_scan_created(client, app, auth_user_a, real_audio_path):
    """
    4. Expired JWT token:
       - Returns HTTP 401 with TOKEN_EXPIRED.
       - No Scan or ScanResult record is created in the database.
       - Audio processing does not execute.
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

    with patch.object(AudioDetectionService, "analyze_audio") as mock_analyze:
        with open(real_audio_path, "rb") as aud_file:
            data = {"audio": (aud_file, "test.wav")}
            response = client.post(
                "/api/detect/audio",
                data=data,
                content_type="multipart/form-data",
                headers={"Authorization": f"Bearer {expired_token}"}
            )

        mock_analyze.assert_not_called()

    assert response.status_code == 401
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "TOKEN_EXPIRED"

    with app.app_context():
        assert Scan.query.count() == 0
        assert ScanResult.query.count() == 0


# ===========================================================================
# 5. Missing Audio / File Field
# ===========================================================================

def test_missing_audio_file_field_preserves_400_no_scan_created(client, app, auth_headers_a):
    """
    5. Missing 'audio' multipart field:
       - Returns HTTP 400 with MISSING_FILE.
       - No Scan or ScanResult record is created in the database.
    """
    data = {"wrong_field": (io.BytesIO(b"fake audio data"), "test.wav")}
    response = client.post(
        "/api/detect/audio",
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
# 6. Unsupported Audio Extension
# ===========================================================================

def test_unsupported_audio_extension_preserves_400_no_scan_created(client, app, auth_headers_a):
    """
    6. Unsupported file extension:
       - Returns HTTP 400 with INVALID_FORMAT.
       - No Scan or ScanResult record is created in the database.
    """
    data = {"audio": (io.BytesIO(b"arbitrary binary content"), "payload.txt")}
    response = client.post(
        "/api/detect/audio",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers_a
    )

    assert response.status_code == 400
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_FORMAT"

    with app.app_context():
        assert Scan.query.count() == 0
        assert ScanResult.query.count() == 0


# ===========================================================================
# 7. Empty Filename
# ===========================================================================

def test_empty_filename_preserves_400_no_scan_created(client, app, auth_headers_a):
    """
    7. Empty filename provided:
       - Returns HTTP 400 with INVALID_FILE.
       - No Scan or ScanResult record is created in the database.
    """
    data = {"audio": (io.BytesIO(b""), "")}
    response = client.post(
        "/api/detect/audio",
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
# 8. Database Failure During create_scan
# ===========================================================================

def test_create_scan_database_failure_returns_sanitized_500(
    client, app, real_audio_path, auth_headers_a
):
    """
    8. Database failure during create_scan():
       - Returns HTTP 500 without leaking raw SQL or exception details.
       - Response success is False with error_code 'INTERNAL_SERVER_ERROR'.
       - No misleading successful response.
    """
    with patch.object(ScanService, "create_scan", side_effect=ScanDatabaseError("Raw SQLite disk I/O lock error")):
        with open(real_audio_path, "rb") as aud_file:
            data = {"audio": (aud_file, "test.wav")}
            response = client.post(
                "/api/detect/audio",
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
    client, app, real_audio_path, auth_headers_a
):
    """
    9. Database failure during save_scan_result():
       - Returns HTTP 500 without leaking raw database details.
       - Response success is False with error_code 'INTERNAL_SERVER_ERROR'.
       - No misleading successful response.
       - ScanResult is not created.
    """
    with patch.object(ScanService, "save_scan_result", side_effect=ScanDatabaseError("Simulated DB transaction crash")):
        with open(real_audio_path, "rb") as aud_file:
            data = {"audio": (aud_file, "test.wav")}
            response = client.post(
                "/api/detect/audio",
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

def test_multiple_authenticated_users_audio_scan_isolation(
    client, app, real_audio_path, auth_user_a, auth_headers_a, auth_user_b, auth_headers_b
):
    """
    10. Multiple authenticated users:
        - User A submits an audio scan; persisted scan belongs strictly to User A.
        - User B submits an audio scan; persisted scan belongs strictly to User B.
        - No cross-user ownership confusion.
    """
    # User A audio scan
    with open(real_audio_path, "rb") as aud_a:
        resp_a = client.post(
            "/api/detect/audio",
            data={"audio": (aud_a, "user_a_evidence.wav")},
            content_type="multipart/form-data",
            headers=auth_headers_a
        )
    assert resp_a.status_code == 200

    # User B audio scan
    with open(real_audio_path, "rb") as aud_b:
        resp_b = client.post(
            "/api/detect/audio",
            data={"audio": (aud_b, "user_b_evidence.wav")},
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
        assert scans_a[0].filename == "user_a_evidence.wav"
        assert scans_a[0].status == "COMPLETED"
        assert scans_a[0].result is not None

        scans_b = Scan.query.filter_by(user_id=auth_user_b["id"]).all()
        assert len(scans_b) == 1
        assert scans_b[0].user_id == auth_user_b["id"]
        assert scans_b[0].filename == "user_b_evidence.wav"
        assert scans_b[0].status == "COMPLETED"
        assert scans_b[0].result is not None

        # Verify distinct scan IDs and cross-isolation
        assert scans_a[0].id != scans_b[0].id
        assert scans_a[0].result.id != scans_b[0].result.id


# ===========================================================================
# 11. Authentic Audio Outcome Persistence
# ===========================================================================

def test_authentic_audio_persists_authentic_prediction(client, app, auth_headers_a):
    """
    11. Authentic audio detection result:
        - When detector indicates is_synthetic_audio is False,
        - Prediction is persisted as 'AUTHENTIC',
        - Confidence and risk_level match expected low/medium risk.
    """
    mock_result = {
        "is_synthetic_audio": False,
        "confidence_score": 0.28,
        "metrics": {
            "duration_seconds": 2.5,
            "sample_rate_hz": 16000,
            "zero_crossing_rate": 0.035,
            "energy_variance": 0.012
        },
        "lip_sync_discrepancies": []
    }

    with patch.object(AudioDetectionService, "analyze_audio", return_value=mock_result):
        data = {"audio": (io.BytesIO(b"fake wav data"), "authentic_voice.wav")}
        response = client.post(
            "/api/detect/audio",
            data=data,
            content_type="multipart/form-data",
            headers=auth_headers_a
        )

    assert response.status_code == 200
    assert response.is_json
    assert response.get_json()["data"]["is_synthetic_audio"] is False

    with app.app_context():
        scan = Scan.query.first()
        assert scan is not None
        assert scan.status == "COMPLETED"
        assert scan.result is not None
        assert scan.result.prediction == "AUTHENTIC"
        assert scan.result.confidence == 0.28
        assert scan.result.risk_level == "LOW"
        assert scan.result.result_data["is_synthetic_audio"] is False


# ===========================================================================
# 12. Phase 5 Step 4: Audio Decoding and Integrity Rejection Invariants
# ===========================================================================

def test_corrupt_audio_persists_no_scan(client, app, auth_headers_a):
    """
    12.1. Corrupt WAV byte stream:
        - Uploading invalid bytes named 'corrupt.wav' fails with HTTP 400.
        - Verifies Scan count == 0 and ScanResult count == 0.
    """
    data = {"audio": (io.BytesIO(b"RIFF\x00\x00\x00\x00WAVEcorrupt_bytes"), "corrupt.wav")}
    response = client.post(
        "/api/detect/audio",
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

def test_empty_audio_persists_no_scan(client, app, auth_headers_a):
    """
    12.2. Empty WAV upload:
        - Uploading 0 bytes named 'empty.wav' fails with HTTP 400.
        - Verifies Scan count == 0 and ScanResult count == 0.
    """
    data = {"audio": (io.BytesIO(b""), "empty.wav")}
    response = client.post(
        "/api/detect/audio",
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

@pytest.mark.parametrize("ext", ["mp3", "m4a", "flac"])
def test_unsupported_audio_formats_persist_no_scan(client, app, auth_headers_a, ext):
    """
    12.3. Unsupported audio extensions (MP3/M4A/FLAC):
        - Fails fast with HTTP 400 INVALID_FORMAT.
        - Verifies Scan count == 0 and ScanResult count == 0.
    """
    data = {"audio": (io.BytesIO(b"dummy audio data"), f"evidence.{ext}")}
    response = client.post(
        "/api/detect/audio",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers_a
    )

    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_FORMAT"

    with app.app_context():
        assert Scan.query.count() == 0
        assert ScanResult.query.count() == 0

def test_decoder_failure_persists_no_scan(client, app, real_audio_path, auth_headers_a):
    """
    12.4. wavfile.read() decoder failure:
        - When wavfile.read raises an exception, the request fails with HTTP 400.
        - No synthetic fallback occurs and Scan count == 0, ScanResult count == 0.
    """
    with patch("scipy.io.wavfile.read", side_effect=ValueError("Header truncated")):
        with open(real_audio_path, "rb") as aud_file:
            response = client.post(
                "/api/detect/audio",
                data={"audio": (aud_file, "failing_decoder.wav")},
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

def test_zero_samples_audio_persists_no_scan(client, app, auth_headers_a):
    """
    12.5. Zero readable samples buffer:
        - Decoded buffer with size 0 fails with HTTP 400.
        - Verifies Scan count == 0 and ScanResult count == 0.
    """
    with patch("scipy.io.wavfile.read", return_value=(16000, np.array([], dtype=np.float32))):
        response = client.post(
            "/api/detect/audio",
            data={"audio": (io.BytesIO(b"dummy"), "zero_samples.wav")},
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

