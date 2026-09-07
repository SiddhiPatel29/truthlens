"""
Tests for Video Detection API Route (/api/detect/video).
"""
import io
import os
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
