"""
Tests for Centralized Error Handling and Information Leakage Prevention.
"""
from backend.app import create_app
from backend.config import Config
from backend.utils.response import api_response

def test_404_not_found_returns_json(client):
    """Verify requesting an unknown endpoint returns JSON envelope rather than default HTML."""
    response = client.get("/api/nonexistent-endpoint")
    assert response.status_code == 404
    assert response.is_json
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["data"] is None
    assert json_data["error_code"] == "NOT_FOUND"
    assert "not found" in json_data["message"].lower()

def test_405_method_not_allowed_returns_json(client):
    """Verify calling an endpoint with wrong method returns JSON envelope."""
    response = client.get("/api/detect/text")
    assert response.status_code == 405
    assert response.is_json
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["data"] is None
    assert json_data["error_code"] == "METHOD_NOT_ALLOWED"
    assert "method is not allowed" in json_data["message"].lower()

def test_413_payload_too_large_returns_json():
    """Verify oversized payloads trigger 413 JSON response."""
    import time
    import jwt

    class TinyConfig(Config):
        TESTING = True
        MAX_CONTENT_LENGTH = 100  # 100 bytes max
        JWT_SECRET_KEY = "test-tiny-jwt-secret-key"
        
    from backend.database.db import db
    from backend.database.models import User

    app = create_app(TinyConfig)
    with app.app_context():
        db.create_all()
        user = User.query.first()
        if not user:
            user = User(
                name="Tiny User",
                email="tiny_unique@example.com",
                password_hash="fakehash",
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
        else:
            user.is_active = True
            db.session.commit()
        user_id = user.id

    tiny_client = app.test_client()

    now = int(time.time())
    token = jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": now + 3600},
        "test-tiny-jwt-secret-key",
        algorithm="HS256"
    )
    
    large_payload = {"text": "A" * 500}
    response = tiny_client.post(
        "/api/detect/text",
        json=large_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 413
    assert response.is_json
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "PAYLOAD_TOO_LARGE"

def test_unhandled_exception_does_not_leak_internals():
    """Verify an unhandled exception inside a route returns generic safe message and 500 code."""
    class BuggyConfig(Config):
        TESTING = True
        DEBUG = False

    app = create_app(BuggyConfig)

    # Register an intentionally broken test endpoint
    @app.route("/api/test-crash", methods=["GET"])
    def buggy_endpoint():
        raise RuntimeError("Sensitive internal database path: /var/secrets/creds.json")

    client = app.test_client()
    response = client.get("/api/test-crash")
    assert response.status_code == 500
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INTERNAL_SERVER_ERROR"
    # Ensure no internal path or exception string is leaked
    assert "Sensitive" not in json_data["message"]
    assert "creds.json" not in json_data["message"]
    assert json_data["message"] == "An unexpected internal server error occurred."
