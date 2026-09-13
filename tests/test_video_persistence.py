"""
Tests for Video Detection Scan Persistence (Phase 4 Step 4).
Verifies that POST /api/detect/video:
- Enforces @require_auth JWT authentication before processing video streams.
- Persists Scans and ScanResults via ScanService.
- Correctly captures original uploaded media filename metadata.
- Atomically transitions Scan from PENDING to COMPLETED status with timestamp.
- Accurately maps detection metrics to prediction, confidence, risk_level, and result_data.
- Stores deliberate serializable detector metadata in result_data without storing raw video bytes.
- Enforces strict user isolation across multiple authenticated accounts.
- Sanitizes server errors without leaking raw database or exception details.
"""
import io
import os
import time
import pytest
import jwt
from unittest.mock import patch, MagicMock
import cv2
from werkzeug.security import generate_password_hash
from backend.database.db import db
from backend.database.models import User, Scan, ScanResult
from backend.services.scan_service import ScanService, ScanDatabaseError
from backend.services.video_service import VideoDetectionService

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
            name="Alice Video Investigator",
            email="alice.video@example.com",
            password_hash=generate_password_hash(password),
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return {"id": user_id, "name": "Alice Video Investigator", "email": "alice.video@example.com", "password": password}

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
            name="Bob Video Investigator",
            email="bob.video@example.com",
            password_hash=generate_password_hash(password),
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return {"id": user_id, "name": "Bob Video Investigator", "email": "bob.video@example.com", "password": password}

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
# 1. Valid Authenticated Video Scan Persistence
# ===========================================================================

def test_valid_authenticated_video_request_persists_scan_and_result(
    client, app, real_video_path, auth_user_a, auth_headers_a
):
    """
    1. Valid authenticated video request:
       - Returns HTTP 200 with standard response envelope.
       - Exactly one Scan record is created.
       - scan.user_id matches authenticated user.
       - scan.media_type == 'video'.
       - scan.filename is persisted correctly as 'test.mp4'.
       - scan.status == 'COMPLETED' and completed_at is populated.
       - Exactly one ScanResult record is created.
       - persisted prediction matches detector output ('DEEPFAKE' or 'AUTHENTIC').
       - persisted confidence matches detector output.
       - persisted risk_level matches calculated risk ('HIGH', 'MEDIUM', or 'LOW').
       - result_data contains deliberately constructed serializable metrics and preview without raw video bytes.
    """
    assert os.path.exists(real_video_path), f"Test video missing at {real_video_path}"

    with open(real_video_path, "rb") as vid_file:
        data = {"video": (vid_file, "test.mp4")}
        response = client.post(
            "/api/detect/video",
            data=data,
            content_type="multipart/form-data",
            headers=auth_headers_a
        )

    assert response.status_code == 200
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["message"] == "Video analyzed successfully."
    assert json_data["error_code"] is None

    payload = json_data["data"]
    assert "scan_id" in payload
    assert isinstance(payload["scan_id"], int)
    assert payload["scan_id"] > 0
    assert "is_deepfake" in payload
    assert "confidence_score" in payload
    assert "metrics" in payload
    assert "keyframe_heatmap_preview" in payload

    # Verify database persistence
    with app.app_context():
        scans = Scan.query.all()
        assert len(scans) == 1
        scan = scans[0]

        assert payload["scan_id"] == scan.id
        assert scan.user_id == auth_user_a["id"]
        assert scan.media_type == "video"
        assert scan.filename == "test.mp4"
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

        # Verify result_data content is deliberately constructed
        assert "is_deepfake" in scan_result.result_data
        assert "confidence_score" in scan_result.result_data
        assert "metrics" in scan_result.result_data
        assert "duration_seconds" in scan_result.result_data["metrics"]
        assert "total_frames_analyzed" in scan_result.result_data["metrics"]
        assert "temporal_instability" in scan_result.result_data["metrics"]
        assert "peak_frame_anomaly" in scan_result.result_data["metrics"]
        assert "keyframe_heatmap_preview" in scan_result.result_data

        # Verify no raw video binary bytes or transient objects are stored in result_data
        assert "video_bytes" not in scan_result.result_data
        assert "frame_scores" not in scan_result.result_data
        assert "raw_frames" not in scan_result.result_data
        assert scan_result.created_at is not None


# ===========================================================================
# 2. Missing Authorization Header
# ===========================================================================

def test_missing_auth_header_returns_401_no_scan_created(client, app, real_video_path):
    """
    2. Missing Authorization header:
       - Returns HTTP 401 with AUTHENTICATION_REQUIRED.
       - No Scan or ScanResult record is created in the database.
       - Video processing does not execute.
    """
    with patch.object(VideoDetectionService, "analyze_video") as mock_analyze:
        with open(real_video_path, "rb") as vid_file:
            data = {"video": (vid_file, "test.mp4")}
            response = client.post(
                "/api/detect/video",
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

def test_invalid_jwt_returns_401_no_scan_created(client, app, real_video_path):
    """
    3. Invalid JWT token:
       - Returns HTTP 401 with INVALID_TOKEN.
       - No Scan or ScanResult record is created in the database.
       - Video processing does not execute.
    """
    with patch.object(VideoDetectionService, "analyze_video") as mock_analyze:
        with open(real_video_path, "rb") as vid_file:
            data = {"video": (vid_file, "test.mp4")}
            response = client.post(
                "/api/detect/video",
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

def test_expired_jwt_returns_401_no_scan_created(client, app, auth_user_a, real_video_path):
    """
    4. Expired JWT token:
       - Returns HTTP 401 with TOKEN_EXPIRED.
       - No Scan or ScanResult record is created in the database.
       - Video processing does not execute.
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

    with patch.object(VideoDetectionService, "analyze_video") as mock_analyze:
        with open(real_video_path, "rb") as vid_file:
            data = {"video": (vid_file, "test.mp4")}
            response = client.post(
                "/api/detect/video",
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
# 5. Missing Video / File Field
# ===========================================================================

def test_missing_video_file_field_preserves_400_no_scan_created(client, app, auth_headers_a):
    """
    5. Missing 'video' multipart field:
       - Returns HTTP 400 with MISSING_FILE.
       - No Scan or ScanResult record is created in the database.
    """
    data = {"wrong_field": (io.BytesIO(b"fake video data"), "test.mp4")}
    response = client.post(
        "/api/detect/video",
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
# 6. Unsupported Video Extension
# ===========================================================================

def test_unsupported_video_extension_preserves_400_no_scan_created(client, app, auth_headers_a):
    """
    6. Unsupported file extension:
       - Returns HTTP 400 with INVALID_FORMAT.
       - No Scan or ScanResult record is created in the database.
    """
    data = {"video": (io.BytesIO(b"arbitrary binary content"), "payload.txt")}
    response = client.post(
        "/api/detect/video",
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
    data = {"video": (io.BytesIO(b""), "")}
    response = client.post(
        "/api/detect/video",
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
# 8. Corrupt / Invalid Video Payload
# ===========================================================================

def test_corrupt_video_content_preserves_400_no_scan_created(client, app, auth_headers_a):
    """
    8. Corrupted video byte stream with valid magic bytes:
       - Returns HTTP 400 with PROCESSING_ERROR.
       - No Scan or ScanResult record is created in the database.
    """
    data = {"video": (io.BytesIO(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00corrupt_payload"), "broken.mp4")}
    response = client.post(
        "/api/detect/video",
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
# 9. Database Failure During create_scan
# ===========================================================================

def test_create_scan_database_failure_returns_sanitized_500(
    client, app, real_video_path, auth_headers_a
):
    """
    9. Database failure during create_scan():
       - Returns HTTP 500 without leaking raw SQL or exception details.
       - Response success is False with error_code 'INTERNAL_SERVER_ERROR'.
       - No misleading successful response.
    """
    with patch.object(ScanService, "create_scan", side_effect=ScanDatabaseError("Raw SQLite disk I/O lock error")):
        with open(real_video_path, "rb") as vid_file:
            data = {"video": (vid_file, "test.mp4")}
            response = client.post(
                "/api/detect/video",
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
# 10. Database Failure During save_scan_result
# ===========================================================================

def test_save_scan_result_database_failure_returns_sanitized_500(
    client, app, real_video_path, auth_headers_a
):
    """
    10. Database failure during save_scan_result():
        - Returns HTTP 500 without leaking raw database details.
        - Response success is False with error_code 'INTERNAL_SERVER_ERROR'.
        - No misleading successful response.
        - ScanResult is not created.
    """
    with patch.object(ScanService, "save_scan_result", side_effect=ScanDatabaseError("Simulated DB transaction crash")):
        with open(real_video_path, "rb") as vid_file:
            data = {"video": (vid_file, "test.mp4")}
            response = client.post(
                "/api/detect/video",
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
# 11. Multiple Authenticated Users (Isolation)
# ===========================================================================

def test_multiple_authenticated_users_video_scan_isolation(
    client, app, real_video_path, auth_user_a, auth_headers_a, auth_user_b, auth_headers_b
):
    """
    11. Multiple authenticated users:
        - User A submits a video scan; persisted scan belongs strictly to User A.
        - User B submits a video scan; persisted scan belongs strictly to User B.
        - No cross-user ownership confusion.
    """
    # User A video scan
    with open(real_video_path, "rb") as vid_a:
        resp_a = client.post(
            "/api/detect/video",
            data={"video": (vid_a, "user_a_evidence.mp4")},
            content_type="multipart/form-data",
            headers=auth_headers_a
        )
    assert resp_a.status_code == 200

    # User B video scan
    with open(real_video_path, "rb") as vid_b:
        resp_b = client.post(
            "/api/detect/video",
            data={"video": (vid_b, "user_b_evidence.mp4")},
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
        assert scans_a[0].filename == "user_a_evidence.mp4"
        assert scans_a[0].status == "COMPLETED"
        assert scans_a[0].result is not None

        scans_b = Scan.query.filter_by(user_id=auth_user_b["id"]).all()
        assert len(scans_b) == 1
        assert scans_b[0].user_id == auth_user_b["id"]
        assert scans_b[0].filename == "user_b_evidence.mp4"
        assert scans_b[0].status == "COMPLETED"
        assert scans_b[0].result is not None

        # Verify distinct scan IDs and cross-isolation
        assert scans_a[0].id != scans_b[0].id
        assert scans_a[0].result.id != scans_b[0].result.id


# ===========================================================================
# 12. Oversized Duration Video Persists No Scan
# ===========================================================================

def test_oversized_duration_video_persists_no_scan(
    client, app, real_video_path, auth_headers_a
):
    """
    12. Video exceeding maximum duration (120s):
        - Returns HTTP 400 PROCESSING_ERROR.
        - Exactly zero Scan and ScanResult records are created in DB.
    """
    real_VideoCapture = cv2.VideoCapture

    class FakeOversizedDurationCapture:
        def __init__(self, *args, **kwargs):
            self._real = real_VideoCapture(*args, **kwargs)
        def isOpened(self):
            return True
        def get(self, prop):
            if prop == cv2.CAP_PROP_FRAME_COUNT:
                return 3630  # 121s at 30 fps
            if prop == cv2.CAP_PROP_FPS:
                return 30.0
            return self._real.get(prop)
        def set(self, prop, val):
            return self._real.set(prop, val)
        def read(self):
            return self._real.read()
        def release(self):
            return self._real.release()

    with patch("cv2.VideoCapture", side_effect=FakeOversizedDurationCapture):
        with open(real_video_path, "rb") as vid_file:
            response = client.post(
                "/api/detect/video",
                data={"video": (vid_file, "long_video.mp4")},
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


# ===========================================================================
# 13. Oversized Resolution Video Persists No Scan
# ===========================================================================

def test_oversized_resolution_metadata_persists_no_scan(
    client, app, real_video_path, auth_headers_a
):
    """
    13. Video exceeding resolution limits in container metadata:
        - Returns HTTP 400 PROCESSING_ERROR.
        - Exactly zero Scan and ScanResult records are created in DB.
    """
    real_VideoCapture = cv2.VideoCapture

    class FakeOversizedResolutionCapture:
        def __init__(self, *args, **kwargs):
            self._real = real_VideoCapture(*args, **kwargs)
        def isOpened(self):
            return True
        def get(self, prop):
            if prop == cv2.CAP_PROP_FRAME_WIDTH:
                return 4097
            if prop == cv2.CAP_PROP_FRAME_HEIGHT:
                return 1080
            return self._real.get(prop)
        def set(self, prop, val):
            return self._real.set(prop, val)
        def read(self):
            return self._real.read()
        def release(self):
            return self._real.release()

    with patch("cv2.VideoCapture", side_effect=FakeOversizedResolutionCapture):
        with open(real_video_path, "rb") as vid_file:
            response = client.post(
                "/api/detect/video",
                data={"video": (vid_file, "huge_res.mp4")},
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


# ===========================================================================
# 14. Oversized Decoded Frame Persists No Scan
# ===========================================================================

def test_oversized_decoded_frame_persists_no_scan(
    client, app, real_video_path, auth_headers_a
):
    """
    14. Decoded frame exceeding resolution bounds during sampling:
        - Returns HTTP 400 PROCESSING_ERROR.
        - Exactly zero Scan and ScanResult records are created in DB.
    """
    real_VideoCapture = cv2.VideoCapture
    fake_frame = MagicMock()
    fake_frame.shape = (4800, 4800, 3)

    class FakeOversizedFrameCapture:
        def __init__(self, *args, **kwargs):
            self._real = real_VideoCapture(*args, **kwargs)
        def isOpened(self):
            return self._real.isOpened()
        def get(self, prop):
            if prop == cv2.CAP_PROP_FRAME_WIDTH:
                return 640
            if prop == cv2.CAP_PROP_FRAME_HEIGHT:
                return 480
            return self._real.get(prop)
        def set(self, prop, val):
            return self._real.set(prop, val)
        def read(self):
            return True, fake_frame
        def release(self):
            return self._real.release()

    with patch("cv2.VideoCapture", side_effect=FakeOversizedFrameCapture):
        with open(real_video_path, "rb") as vid_file:
            response = client.post(
                "/api/detect/video",
                data={"video": (vid_file, "frame_bomb.mp4")},
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


# ===========================================================================
# 14. Phase 5 Step 5: Video Magic-Byte and Filename Persistence Invariants
# ===========================================================================

def test_invalid_video_magic_bytes_preserves_400_no_scan_created(client, app, auth_headers_a):
    """
    14.1. Arbitrary random bytes with .mp4 extension:
        - Returns HTTP 400 with INVALID_FORMAT.
        - Verifies Scan count == 0 and ScanResult count == 0.
    """
    data = {"video": (io.BytesIO(b"random non-video bytes here"), "payload.mp4")}
    response = client.post(
        "/api/detect/video",
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


def test_video_path_traversal_filename_preserves_400_no_scan_created(client, app, real_video_path, auth_headers_a):
    """
    14.2. Filename path traversal attempt:
        - Returns HTTP 400 with INVALID_FILE.
        - Verifies Scan count == 0 and ScanResult count == 0.
    """
    with open(real_video_path, "rb") as vid_file:
        data = {"video": (vid_file, "../../evil_traversal.mp4")}
        response = client.post(
            "/api/detect/video",
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


def test_video_double_dot_filename_persists_scan(client, app, real_video_path, auth_headers_a, auth_user_a):
    """
    14.3. Legitimate double dot in filename (e.g. clip..v1.mp4):
        - Returns HTTP 200.
        - Persists Scan with scan.filename == 'clip..v1.mp4'.
    """
    with open(real_video_path, "rb") as vid_file:
        data = {"video": (vid_file, "clip..v1.mp4")}
        response = client.post(
            "/api/detect/video",
            data=data,
            content_type="multipart/form-data",
            headers=auth_headers_a
        )

    assert response.status_code == 200
    assert response.is_json

    with app.app_context():
        assert Scan.query.count() == 1
        scan = Scan.query.filter_by(user_id=auth_user_a["id"]).first()
        assert scan is not None
        assert scan.filename == "clip..v1.mp4"
        assert scan.status == "COMPLETED"
        assert scan.result is not None


def test_video_persistence_records_downscaled_keyframe_thumbnail(client, app, real_video_path, auth_headers_a, auth_user_a):
    """
    15. Verify that a video scan with high-resolution frames persists
        a downscaled (<= 512px) thumbnail preview in ScanResult.result_data.
    """
    import base64
    import numpy as np

    class HighResVideoCapture:
        def __init__(self, *args, **kwargs):
            pass
        def isOpened(self):
            return True
        def get(self, prop):
            if prop == cv2.CAP_PROP_FRAME_COUNT:
                return 30
            if prop == cv2.CAP_PROP_FPS:
                return 30.0
            if prop == cv2.CAP_PROP_FRAME_WIDTH:
                return 1920
            if prop == cv2.CAP_PROP_FRAME_HEIGHT:
                return 1080
            return 0
        def set(self, prop, val):
            pass
        def read(self):
            frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
            cv2.circle(frame, (960, 540), 200, (255, 255, 255), -1)
            return True, frame
        def release(self):
            pass

    with patch("cv2.VideoCapture", side_effect=HighResVideoCapture):
        with open(real_video_path, "rb") as vid_file:
            response = client.post(
                "/api/detect/video",
                data={"video": (vid_file, "hd_clip.mp4")},
                content_type="multipart/form-data",
                headers=auth_headers_a
            )

    assert response.status_code == 200

    with app.app_context():
        scan = Scan.query.filter_by(user_id=auth_user_a["id"]).first()
        assert scan is not None
        assert scan.result is not None
        preview_b64 = scan.result.result_data.get("keyframe_heatmap_preview")
        assert preview_b64 is not None
        assert preview_b64.startswith("data:image/jpeg;base64,")

        raw_b64 = preview_b64.split(",", 1)[1]
        img_bytes = base64.b64decode(raw_b64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        thumb = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        assert thumb is not None
        assert max(thumb.shape[:2]) <= 512
        # 1920 x 1080 -> 512 x 288
        assert thumb.shape[1] == 512
        assert thumb.shape[0] == 288
