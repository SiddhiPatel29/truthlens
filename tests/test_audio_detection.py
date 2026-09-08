"""
Tests for Audio Detection API Route (/api/detect/audio).
"""
import io
import os
import pytest
from werkzeug.security import generate_password_hash
from backend.database.db import db
from backend.database.models import User, Scan, ScanResult

@pytest.fixture(autouse=True)
def clean_db(app):
    """Ensures a clean database state for each audio detection test."""
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
            name="Audio Regression Tester",
            email="audiotester@example.com",
            password_hash=generate_password_hash(password),
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return {"id": user_id, "email": "audiotester@example.com", "password": password}

@pytest.fixture
def auth_headers(client, auth_user):
    """Generates valid Authorization headers for authenticated requests."""
    response = client.post("/api/auth/login", json={
        "email": auth_user["email"],
        "password": auth_user["password"]
    })
    token = response.get_json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_detect_audio_success(client, real_audio_path, auth_headers):
    """Verify valid audio upload returns 200 and audio forensic metrics."""
    assert os.path.exists(real_audio_path), f"Test audio not found at {real_audio_path}"
    
    with open(real_audio_path, "rb") as audio_file:
        data = {
            "audio": (audio_file, "test.wav")
        }
        response = client.post(
            "/api/detect/audio",
            data=data,
            content_type="multipart/form-data",
            headers=auth_headers
        )
        
    assert response.status_code == 200
    assert response.is_json
    
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["message"] == "Audio analyzed successfully."
    assert json_data["error_code"] is None
    
    payload = json_data["data"]
    assert "is_synthetic_audio" in payload
    assert isinstance(payload["is_synthetic_audio"], bool)
    assert "confidence_score" in payload
    assert 0.0 <= payload["confidence_score"] <= 1.0
    assert "metrics" in payload
    metrics = payload["metrics"]
    assert "duration_seconds" in metrics
    assert "sample_rate_hz" in metrics
    assert "zero_crossing_rate" in metrics
    assert "energy_variance" in metrics
    assert "lip_sync_discrepancies" in payload

def test_detect_audio_missing_file_field(client, auth_headers):
    """Verify request without 'audio' field returns 400 MISSING_FILE."""
    data = {
        "wrong_field": (io.BytesIO(b"fake data"), "test.wav")
    }
    response = client.post(
        "/api/detect/audio",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers
    )
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "MISSING_FILE"

def test_detect_audio_empty_filename(client, auth_headers):
    """Verify request with empty filename returns 400 INVALID_FILE."""
    data = {
        "audio": (io.BytesIO(b""), "")
    }
    response = client.post(
        "/api/detect/audio",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers
    )
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_FILE"

def test_detect_audio_unsupported_extension(client, auth_headers):
    """Verify audio with invalid extension returns 400 INVALID_FORMAT."""
    data = {
        "audio": (io.BytesIO(b"dummy binary data"), "test.txt")
    }
    response = client.post(
        "/api/detect/audio",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers
    )
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_FORMAT"
