"""
Tests for Application Startup, Configuration, and Health Endpoint.
"""
from backend.app import create_app
from backend.config import Config

def test_app_creation():
    """Verify application factory initializes without error."""
    app = create_app()
    assert app is not None
    assert app.name == "backend.app"

def test_health_endpoint_success(client):
    """Verify GET /api/health returns 200 OK and expected envelope."""
    response = client.get("/api/health")
    assert response.status_code == 200
    
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["message"] == "VeraMedia AI Backend is running smoothly."
    assert json_data["error_code"] is None
    
    data = json_data["data"]
    assert data["service"] == "VeraMedia AI Backend"
    assert data["status"] == "OPERATIONAL"
    assert data["version"] == "1.0.0"
    assert set(data["supported_modalities"]) == {"video", "audio", "image", "text"}

def test_cors_headers(client):
    """Verify CORS headers are set appropriately on API endpoints."""
    response = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
    assert response.headers.get("Access-Control-Allow-Credentials") == "true"
