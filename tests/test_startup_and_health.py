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

def test_run_py_imports_existing_app():
    """Verify root run.py imports and exposes the existing Flask app from backend.app."""
    import run
    from flask import Flask

    assert hasattr(run, "app")
    assert isinstance(run.app, Flask)
    assert run.app.name == "backend.app"
    blueprint_names = set(run.app.blueprints.keys())
    assert {"health", "auth", "scans", "text", "image", "video", "audio", "abuse"}.issubset(blueprint_names)

def test_cors_headers(client):
    """Verify CORS headers allow configured origins (localhost:3000, localhost:5173) and reject arbitrary origins."""
    # 1. localhost:3000 remains allowed
    res_3000 = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert res_3000.status_code == 200
    assert res_3000.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
    assert res_3000.headers.get("Access-Control-Allow-Credentials") == "true"

    # 2. localhost:5173 is allowed
    res_5173 = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert res_5173.status_code == 200
    assert res_5173.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
    assert res_5173.headers.get("Access-Control-Allow-Credentials") == "true"

    # 3. arbitrary origin is NOT allowed
    res_arbitrary = client.get("/api/health", headers={"Origin": "http://arbitrary-untrusted-origin.com"})
    assert res_arbitrary.status_code == 200
    assert res_arbitrary.headers.get("Access-Control-Allow-Origin") is None
