"""
Tests for Text Detection API Route (/api/detect/text).
"""
import pytest
from werkzeug.security import generate_password_hash
from backend.database.db import db
from backend.database.models import User, Scan, ScanResult

@pytest.fixture(autouse=True)
def clean_db(app):
    """Ensures a clean database state for each text detection test."""
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
def auth_user(app):
    """Creates an active test user in the database."""
    password = "ValidUserPassword123!"
    with app.app_context():
        user = User(
            name="Text Regression Tester",
            email="texttester@example.com",
            password_hash=generate_password_hash(password),
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return {"id": user_id, "email": "texttester@example.com", "password": password}

@pytest.fixture
def auth_headers(client, auth_user):
    """Generates valid Authorization headers for authenticated requests."""
    response = client.post("/api/auth/login", json={
        "email": auth_user["email"],
        "password": auth_user["password"]
    })
    token = response.get_json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_detect_text_success(client, sample_text, auth_headers):
    """Verify valid text input returns 200 and expected forensic metrics."""
    response = client.post("/api/detect/text", json={"text": sample_text}, headers=auth_headers)
    assert response.status_code == 200
    assert response.is_json
    
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["message"] == "Text analyzed successfully."
    assert json_data["error_code"] is None
    
    data = json_data["data"]
    assert "is_ai_generated" in data
    assert isinstance(data["is_ai_generated"], bool)
    assert "ai_confidence_score" in data
    assert 0.0 <= data["ai_confidence_score"] <= 1.0
    assert "metrics" in data
    assert data["metrics"]["total_words"] > 0
    assert "sentence_breakdown" in data
    assert len(data["sentence_breakdown"]) > 0

def test_detect_text_missing_field(client, auth_headers):
    """Verify request without 'text' field returns 400 INVALID_INPUT."""
    response = client.post("/api/detect/text", json={"wrong_field": "content"}, headers=auth_headers)
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_INPUT"

def test_detect_text_too_short(client, auth_headers):
    """Verify text under 20 characters returns 400 TEXT_TOO_SHORT."""
    response = client.post("/api/detect/text", json={"text": "Too short"}, headers=auth_headers)
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "TEXT_TOO_SHORT"

def test_detect_text_non_string_type(client, auth_headers):
    """Verify non-string input returns 400 INVALID_INPUT."""
    response = client.post("/api/detect/text", json={"text": 12345678901234567890}, headers=auth_headers)
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_INPUT"

def test_detect_text_empty_body(client, auth_headers):
    """Verify empty or non-JSON body returns 400 INVALID_INPUT."""
    response = client.post("/api/detect/text", data="not json", content_type="text/plain", headers=auth_headers)
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_INPUT"
