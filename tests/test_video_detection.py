"""
Tests for Video Detection API Route (/api/detect/video).
"""
import io
import os
import tempfile
from unittest.mock import patch, MagicMock
import cv2
import pytest
from werkzeug.security import generate_password_hash
from backend.database.db import db
from backend.database.models import User, Scan, ScanResult

@pytest.fixture(autouse=True)
def clean_db(app):
    """Ensures a clean database state for each video detection test."""
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
def auth_user(app):
    """Creates an active test user in the database."""
    password = "ValidUserPassword123!"
    with app.app_context():
        user = User(
            name="Video Regression Tester",
            email="videotester@example.com",
            password_hash=generate_password_hash(password),
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return {"id": user_id, "email": "videotester@example.com", "password": password}

@pytest.fixture
def auth_headers(client, auth_user):
    """Generates valid Authorization headers for authenticated requests."""
    response = client.post("/api/auth/login", json={
        "email": auth_user["email"],
        "password": auth_user["password"]
    })
    token = response.get_json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_detect_video_success(client, real_video_path, auth_headers):
    """Verify valid video upload returns 200 and video forensic metrics."""
    assert os.path.exists(real_video_path), f"Test video not found at {real_video_path}"
    
    with open(real_video_path, "rb") as vid_file:
        data = {
            "video": (vid_file, "test.mp4")
        }
        response = client.post(
            "/api/detect/video",
            data=data,
            content_type="multipart/form-data",
            headers=auth_headers
        )
        
    assert response.status_code == 200
    assert response.is_json
    
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["message"] == "Video analyzed successfully."
    assert json_data["error_code"] is None
    
    payload = json_data["data"]
    assert "is_deepfake" in payload
    assert isinstance(payload["is_deepfake"], bool)
    assert "confidence_score" in payload
    assert 0.0 <= payload["confidence_score"] <= 1.0
    assert "metrics" in payload
    metrics = payload["metrics"]
    assert "duration_seconds" in metrics
    assert "total_frames_analyzed" in metrics
    assert "temporal_instability" in metrics
    assert "peak_frame_anomaly" in metrics
    assert "keyframe_heatmap_preview" in payload

def test_detect_video_missing_file_field(client, auth_headers):
    """Verify request without 'video' field returns 400 MISSING_FILE."""
    data = {
        "wrong_field": (io.BytesIO(b"fake data"), "test.mp4")
    }
    response = client.post(
        "/api/detect/video",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers
    )
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "MISSING_FILE"

def test_detect_video_empty_filename(client, auth_headers):
    """Verify request with empty filename returns 400 INVALID_FILE."""
    data = {
        "video": (io.BytesIO(b""), "")
    }
    response = client.post(
        "/api/detect/video",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers
    )
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_FILE"

def test_detect_video_unsupported_extension(client, auth_headers):
    """Verify video with invalid extension returns 400 INVALID_FORMAT."""
    data = {
        "video": (io.BytesIO(b"dummy binary data"), "test.txt")
    }
    response = client.post(
        "/api/detect/video",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers
    )
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_FORMAT"

def test_detect_video_corrupt_content(client, auth_headers):
    """Verify invalid/corrupted video payload returns 400 PROCESSING_ERROR."""
    data = {
        "video": (io.BytesIO(b"not an actual video byte stream"), "corrupted.mp4")
    }
    response = client.post(
        "/api/detect/video",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers
    )
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "PROCESSING_ERROR"

def test_detect_video_tempfile_cleanup_on_success(client, real_video_path, auth_headers):
    """Verify temporary file is removed after successful video detection."""
    created_temp_files = []
    real_mkstemp = tempfile.mkstemp

    def track_mkstemp(*args, **kwargs):
        fd, path = real_mkstemp(*args, **kwargs)
        created_temp_files.append(path)
        return fd, path

    with patch("tempfile.mkstemp", side_effect=track_mkstemp):
        with open(real_video_path, "rb") as vid_file:
            response = client.post(
                "/api/detect/video",
                data={"video": (vid_file, "test.mp4")},
                content_type="multipart/form-data",
                headers=auth_headers
            )

    assert response.status_code == 200
    assert len(created_temp_files) == 1
    # File must be cleaned up from filesystem
    assert not os.path.exists(created_temp_files[0])

def test_detect_video_cleanup_ordering_windows_semantics(client, real_video_path, auth_headers):
    """
    CRITICAL WINDOWS SEMANTICS TEST:
    Verify cap.release() executes strictly BEFORE os.remove(temp_path).
    On Windows, calling os.remove() while VideoCapture holds an open handle
    raises PermissionError (WinError 32), orphaning files on disk.
    """
    event_log = []
    real_VideoCapture = cv2.VideoCapture
    real_remove = os.remove

    class InstrumentedVideoCapture:
        def __init__(self, *args, **kwargs):
            self._real = real_VideoCapture(*args, **kwargs)
        def isOpened(self):
            return self._real.isOpened()
        def get(self, prop):
            return self._real.get(prop)
        def set(self, prop, val):
            return self._real.set(prop, val)
        def read(self):
            return self._real.read()
        def release(self):
            event_log.append("cap_released")
            return self._real.release()

    def instrumented_remove(path):
        event_log.append("file_removed")
        return real_remove(path)

    with patch("cv2.VideoCapture", side_effect=InstrumentedVideoCapture):
        with patch("os.remove", side_effect=instrumented_remove):
            with open(real_video_path, "rb") as vid_file:
                response = client.post(
                    "/api/detect/video",
                    data={"video": (vid_file, "test.mp4")},
                    content_type="multipart/form-data",
                    headers=auth_headers
                )

    assert response.status_code == 200
    assert "cap_released" in event_log
    assert "file_removed" in event_log
    # Crucial assertion: cap_released must precede file_removed
    assert event_log.index("cap_released") < event_log.index("file_removed")

def test_detect_video_cleanup_when_not_opened(client, auth_headers):
    """Verify cap.release() and os.remove() execute when cap.isOpened() is False."""
    event_log = []
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = False
    mock_cap.release.side_effect = lambda: event_log.append("cap_released")

    with patch("cv2.VideoCapture", return_value=mock_cap):
        with patch("os.remove", side_effect=lambda p: event_log.append("file_removed")):
            response = client.post(
                "/api/detect/video",
                data={"video": (io.BytesIO(b"dummy video data"), "unopened.mp4")},
                content_type="multipart/form-data",
                headers=auth_headers
            )

    assert response.status_code == 400
    assert response.get_json()["error_code"] == "PROCESSING_ERROR"
    assert "cap_released" in event_log
    assert "file_removed" in event_log
    assert event_log.index("cap_released") < event_log.index("file_removed")

def test_detect_video_cleanup_when_zero_frames(client, auth_headers):
    """Verify cap.release() and os.remove() execute when total_frames <= 0."""
    event_log = []
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.get.side_effect = lambda prop: 0 if prop == cv2.CAP_PROP_FRAME_COUNT else 30.0
    mock_cap.release.side_effect = lambda: event_log.append("cap_released")

    with patch("cv2.VideoCapture", return_value=mock_cap):
        with patch("os.remove", side_effect=lambda p: event_log.append("file_removed")):
            response = client.post(
                "/api/detect/video",
                data={"video": (io.BytesIO(b"dummy video data"), "zero_frames.mp4")},
                content_type="multipart/form-data",
                headers=auth_headers
            )

    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["error_code"] == "PROCESSING_ERROR"
    assert "zero readable frames" in json_data["message"]
    assert "cap_released" in event_log
    assert "file_removed" in event_log
    assert event_log.index("cap_released") < event_log.index("file_removed")

def test_detect_video_cleanup_when_exception_during_processing(client, real_video_path, auth_headers):
    """Verify cap.release() and os.remove() execute when unexpected exception occurs during frame read."""
    event_log = []
    real_VideoCapture = cv2.VideoCapture

    class ErrorInjectingVideoCapture:
        def __init__(self, *args, **kwargs):
            self._real = real_VideoCapture(*args, **kwargs)
        def isOpened(self):
            return self._real.isOpened()
        def get(self, prop):
            return self._real.get(prop)
        def set(self, prop, val):
            return self._real.set(prop, val)
        def read(self):
            raise RuntimeError("Simulated decoder crash during cap.read()")
        def release(self):
            event_log.append("cap_released")
            return self._real.release()

    with patch("cv2.VideoCapture", side_effect=ErrorInjectingVideoCapture):
        with patch("os.remove", side_effect=lambda p: event_log.append("file_removed")):
            with open(real_video_path, "rb") as vid_file:
                response = client.post(
                    "/api/detect/video",
                    data={"video": (vid_file, "test.mp4")},
                    content_type="multipart/form-data",
                    headers=auth_headers
                )

    assert response.status_code == 500
    assert response.get_json()["error_code"] == "INTERNAL_SERVER_ERROR"
    assert "cap_released" in event_log
    assert "file_removed" in event_log
    assert event_log.index("cap_released") < event_log.index("file_removed")

def test_detect_video_duration_exceeding_limit_rejected_400(client, real_video_path, auth_headers):
    """Verify video with duration > 120s is rejected with 400 PROCESSING_ERROR."""
    event_log = []
    real_VideoCapture = cv2.VideoCapture

    class OversizedDurationVideoCapture:
        def __init__(self, *args, **kwargs):
            self._real = real_VideoCapture(*args, **kwargs)
        def isOpened(self):
            return True
        def get(self, prop):
            if prop == cv2.CAP_PROP_FRAME_COUNT:
                return 3630
            if prop == cv2.CAP_PROP_FPS:
                return 30.0
            return self._real.get(prop)
        def set(self, prop, val):
            return self._real.set(prop, val)
        def read(self):
            return self._real.read()
        def release(self):
            event_log.append("cap_released")
            return self._real.release()

    with patch("cv2.VideoCapture", side_effect=OversizedDurationVideoCapture):
        with patch("os.remove", side_effect=lambda p: event_log.append("file_removed")):
            with open(real_video_path, "rb") as vid_file:
                response = client.post(
                    "/api/detect/video",
                    data={"video": (vid_file, "test.mp4")},
                    content_type="multipart/form-data",
                    headers=auth_headers
                )

    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "PROCESSING_ERROR"
    assert "exceeds maximum permitted limit" in json_data["message"]
    assert "121" in json_data["message"]
    # Cleanup must still occur
    assert "cap_released" in event_log
    assert "file_removed" in event_log

def test_detect_video_duration_boundary_120_seconds_accepted(client, real_video_path, auth_headers):
    """Verify video with duration exactly 120.0s (3600 frames at 30 fps) is accepted."""
    real_VideoCapture = cv2.VideoCapture

    class BoundaryDurationVideoCapture:
        def __init__(self, *args, **kwargs):
            self._real = real_VideoCapture(*args, **kwargs)
        def isOpened(self):
            return self._real.isOpened()
        def get(self, prop):
            if prop == cv2.CAP_PROP_FRAME_COUNT:
                return 3600
            if prop == cv2.CAP_PROP_FPS:
                return 30.0
            return self._real.get(prop)
        def set(self, prop, val):
            return self._real.set(prop, val)
        def read(self):
            return self._real.read()
        def release(self):
            return self._real.release()

    with patch("cv2.VideoCapture", side_effect=BoundaryDurationVideoCapture):
        with open(real_video_path, "rb") as vid_file:
            response = client.post(
                "/api/detect/video",
                data={"video": (vid_file, "test.mp4")},
                content_type="multipart/form-data",
                headers=auth_headers
            )

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["data"]["metrics"]["duration_seconds"] == 120.0

def test_detect_video_metadata_resolution_exceeding_width_rejected_400(client, real_video_path, auth_headers):
    """Verify video with metadata width > 4096 is rejected with 400 PROCESSING_ERROR."""
    real_VideoCapture = cv2.VideoCapture

    class OversizedWidthVideoCapture:
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

    with patch("cv2.VideoCapture", side_effect=OversizedWidthVideoCapture):
        with open(real_video_path, "rb") as vid_file:
            response = client.post(
                "/api/detect/video",
                data={"video": (vid_file, "test.mp4")},
                content_type="multipart/form-data",
                headers=auth_headers
            )

    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "PROCESSING_ERROR"
    assert "exceeds maximum permitted limits" in json_data["message"]
    assert "4097x1080" in json_data["message"]

def test_detect_video_metadata_resolution_exceeding_height_rejected_400(client, real_video_path, auth_headers):
    """Verify video with metadata height > 4096 is rejected with 400 PROCESSING_ERROR."""
    real_VideoCapture = cv2.VideoCapture

    class OversizedHeightVideoCapture:
        def __init__(self, *args, **kwargs):
            self._real = real_VideoCapture(*args, **kwargs)
        def isOpened(self):
            return True
        def get(self, prop):
            if prop == cv2.CAP_PROP_FRAME_WIDTH:
                return 1920
            if prop == cv2.CAP_PROP_FRAME_HEIGHT:
                return 4097
            return self._real.get(prop)
        def set(self, prop, val):
            return self._real.set(prop, val)
        def read(self):
            return self._real.read()
        def release(self):
            return self._real.release()

    with patch("cv2.VideoCapture", side_effect=OversizedHeightVideoCapture):
        with open(real_video_path, "rb") as vid_file:
            response = client.post(
                "/api/detect/video",
                data={"video": (vid_file, "test.mp4")},
                content_type="multipart/form-data",
                headers=auth_headers
            )

    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "PROCESSING_ERROR"
    assert "exceeds maximum permitted limits" in json_data["message"]
    assert "1920x4097" in json_data["message"]

def test_detect_video_metadata_resolution_exceeding_pixels_rejected_400(client, real_video_path, auth_headers):
    """Verify video with total metadata pixels > 16,777,216 is rejected with 400 PROCESSING_ERROR."""
    real_VideoCapture = cv2.VideoCapture

    class OversizedPixelsVideoCapture:
        def __init__(self, *args, **kwargs):
            self._real = real_VideoCapture(*args, **kwargs)
        def isOpened(self):
            return True
        def get(self, prop):
            if prop == cv2.CAP_PROP_FRAME_WIDTH:
                return 4000
            if prop == cv2.CAP_PROP_FRAME_HEIGHT:
                return 4200  # 16,800,000 pixels > 16,777,216
            return self._real.get(prop)
        def set(self, prop, val):
            return self._real.set(prop, val)
        def read(self):
            return self._real.read()
        def release(self):
            return self._real.release()

    with patch("cv2.VideoCapture", side_effect=OversizedPixelsVideoCapture):
        with open(real_video_path, "rb") as vid_file:
            response = client.post(
                "/api/detect/video",
                data={"video": (vid_file, "test.mp4")},
                content_type="multipart/form-data",
                headers=auth_headers
            )

    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "PROCESSING_ERROR"
    assert "exceeds maximum permitted limits" in json_data["message"]

def test_detect_video_decoded_frame_exceeding_resolution_rejected_400(client, real_video_path, auth_headers):
    """
    Verify decoded frame resolution check:
    Even if metadata reports normal resolution (e.g. 640x480),
    if an actual decoded frame exceeds maximum bounds, it is rejected immediately.
    """
    real_VideoCapture = cv2.VideoCapture
    fake_frame = MagicMock()
    fake_frame.shape = (4500, 4500, 3)

    class OversizedDecodedFrameVideoCapture:
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

    with patch("cv2.VideoCapture", side_effect=OversizedDecodedFrameVideoCapture):
        with open(real_video_path, "rb") as vid_file:
            response = client.post(
                "/api/detect/video",
                data={"video": (vid_file, "test.mp4")},
                content_type="multipart/form-data",
                headers=auth_headers
            )

    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "PROCESSING_ERROR"
    assert "Decoded video frame resolution" in json_data["message"]
    assert "4500x4500" in json_data["message"]

def test_detect_video_resolution_boundary_4096_accepted(client, real_video_path, auth_headers):
    """Verify video with metadata exactly 4096x4096 (16,777,216 pixels) is within bounds."""
    real_VideoCapture = cv2.VideoCapture

    class BoundaryResolutionVideoCapture:
        def __init__(self, *args, **kwargs):
            self._real = real_VideoCapture(*args, **kwargs)
        def isOpened(self):
            return self._real.isOpened()
        def get(self, prop):
            if prop == cv2.CAP_PROP_FRAME_WIDTH:
                return 4096
            if prop == cv2.CAP_PROP_FRAME_HEIGHT:
                return 4096
            return self._real.get(prop)
        def set(self, prop, val):
            return self._real.set(prop, val)
        def read(self):
            return self._real.read()
        def release(self):
            return self._real.release()

    with patch("cv2.VideoCapture", side_effect=BoundaryResolutionVideoCapture):
        with open(real_video_path, "rb") as vid_file:
            response = client.post(
                "/api/detect/video",
                data={"video": (vid_file, "test.mp4")},
                content_type="multipart/form-data",
                headers=auth_headers
            )

    assert response.status_code == 200
    assert response.get_json()["success"] is True

def test_detect_video_dynamic_tempfile_suffix(client, real_video_path, auth_headers):
    """Verify tempfile suffix is dynamically derived from upload filename extension."""
    captured_suffixes = []
    real_mkstemp = tempfile.mkstemp

    def spy_mkstemp(*args, **kwargs):
        suffix = kwargs.get("suffix")
        captured_suffixes.append(suffix)
        return real_mkstemp(*args, **kwargs)

    with patch("tempfile.mkstemp", side_effect=spy_mkstemp):
        for ext in ["mov", "avi", "mkv"]:
            with open(real_video_path, "rb") as vid_file:
                client.post(
                    "/api/detect/video",
                    data={"video": (vid_file, f"evidence.{ext}")},
                    content_type="multipart/form-data",
                    headers=auth_headers
                )

    assert captured_suffixes == [".mov", ".avi", ".mkv"]
