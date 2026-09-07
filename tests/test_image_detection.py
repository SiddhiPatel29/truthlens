"""
Tests for Image Detection API Route (/api/detect/image).
"""
import io
import os
import pytest
from werkzeug.security import generate_password_hash
from backend.database.db import db
from backend.database.models import User, Scan, ScanResult

@pytest.fixture(autouse=True)
def clean_db(app):
    """Ensures a clean database state for each image detection test."""
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
            name="Image Regression Tester",
            email="imagetester@example.com",
            password_hash=generate_password_hash(password),
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return {"id": user_id, "email": "imagetester@example.com", "password": password}

@pytest.fixture
def auth_headers(client, auth_user):
    """Generates valid Authorization headers for authenticated requests."""
    response = client.post("/api/auth/login", json={
        "email": auth_user["email"],
        "password": auth_user["password"]
    })
    token = response.get_json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_detect_image_success(client, real_image_path, auth_headers):
    """Verify valid image upload returns 200 and image analysis schema."""
    assert os.path.exists(real_image_path), f"Test image not found at {real_image_path}"
    
    with open(real_image_path, "rb") as img_file:
        data = {
            "image": (img_file, "test.jpg")
        }
        response = client.post(
            "/api/detect/image",
            data=data,
            content_type="multipart/form-data",
            headers=auth_headers
        )
        
    assert response.status_code == 200
    assert response.is_json
    
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["message"] == "Image analyzed successfully."
    assert json_data["error_code"] is None
    
    payload = json_data["data"]
    assert "is_deepfake" in payload
    assert isinstance(payload["is_deepfake"], bool)
    assert "confidence_score" in payload
    assert 0.0 <= payload["confidence_score"] <= 1.0
    assert "manipulation_type" in payload
    assert "image_dimensions" in payload
    assert payload["image_dimensions"]["width"] > 0
    assert payload["image_dimensions"]["height"] > 0
    assert "heatmap_preview" in payload
    assert payload["heatmap_preview"].startswith("data:image/jpeg;base64,")

def test_detect_image_missing_file_field(client, auth_headers):
    """Verify multipart request without 'image' field returns 400 MISSING_FILE."""
    data = {
        "wrong_field": (io.BytesIO(b"fake data"), "test.jpg")
    }
    response = client.post(
        "/api/detect/image",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers
    )
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "MISSING_FILE"

def test_detect_image_empty_filename(client, auth_headers):
    """Verify request with empty filename returns 400 INVALID_FILE."""
    data = {
        "image": (io.BytesIO(b""), "")
    }
    response = client.post(
        "/api/detect/image",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers
    )
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_FILE"

def test_detect_image_unsupported_extension(client, auth_headers):
    """Verify file with invalid extension returns 400 INVALID_FILE."""
    data = {
        "image": (io.BytesIO(b"dummy binary data"), "test.txt")
    }
    response = client.post(
        "/api/detect/image",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers
    )
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_FILE"

def test_detect_image_corrupt_content(client, auth_headers):
    """Verify invalid/corrupted image payload returns 400 PROCESSING_ERROR."""
    data = {
        "image": (io.BytesIO(b"not an actual image byte stream"), "corrupted.jpg")
    }
    response = client.post(
        "/api/detect/image",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers
    )
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "PROCESSING_ERROR"
