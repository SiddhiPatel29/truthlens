"""
Tests for Audio Detection API Route (/api/detect/audio).
"""
import io
import os

def test_detect_audio_success(client, real_audio_path):
    """Verify valid audio upload returns 200 and audio forensic metrics."""
    assert os.path.exists(real_audio_path), f"Test audio not found at {real_audio_path}"
    
    with open(real_audio_path, "rb") as audio_file:
        data = {
            "audio": (audio_file, "test.wav")
        }
        response = client.post(
            "/api/detect/audio",
            data=data,
            content_type="multipart/form-data"
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

def test_detect_audio_missing_file_field(client):
    """Verify request without 'audio' field returns 400 MISSING_FILE."""
    data = {
        "wrong_field": (io.BytesIO(b"fake data"), "test.wav")
    }
    response = client.post("/api/detect/audio", data=data, content_type="multipart/form-data")
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "MISSING_FILE"

def test_detect_audio_empty_filename(client):
    """Verify request with empty filename returns 400 INVALID_FILE."""
    data = {
        "audio": (io.BytesIO(b""), "")
    }
    response = client.post("/api/detect/audio", data=data, content_type="multipart/form-data")
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_FILE"

def test_detect_audio_unsupported_extension(client):
    """Verify audio with invalid extension returns 400 INVALID_FORMAT."""
    data = {
        "audio": (io.BytesIO(b"dummy binary data"), "test.txt")
    }
    response = client.post("/api/detect/audio", data=data, content_type="multipart/form-data")
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_FORMAT"
