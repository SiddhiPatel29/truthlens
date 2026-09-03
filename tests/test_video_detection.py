"""
Tests for Video Detection API Route (/api/detect/video).
"""
import io
import os

def test_detect_video_success(client, real_video_path):
    """Verify valid video upload returns 200 and video forensic metrics."""
    assert os.path.exists(real_video_path), f"Test video not found at {real_video_path}"
    
    with open(real_video_path, "rb") as vid_file:
        data = {
            "video": (vid_file, "test.mp4")
        }
        response = client.post(
            "/api/detect/video",
            data=data,
            content_type="multipart/form-data"
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

def test_detect_video_missing_file_field(client):
    """Verify request without 'video' field returns 400 MISSING_FILE."""
    data = {
        "wrong_field": (io.BytesIO(b"fake data"), "test.mp4")
    }
    response = client.post("/api/detect/video", data=data, content_type="multipart/form-data")
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "MISSING_FILE"

def test_detect_video_empty_filename(client):
    """Verify request with empty filename returns 400 INVALID_FILE."""
    data = {
        "video": (io.BytesIO(b""), "")
    }
    response = client.post("/api/detect/video", data=data, content_type="multipart/form-data")
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_FILE"

def test_detect_video_unsupported_extension(client):
    """Verify video with invalid extension returns 400 INVALID_FORMAT."""
    data = {
        "video": (io.BytesIO(b"dummy binary data"), "test.txt")
    }
    response = client.post("/api/detect/video", data=data, content_type="multipart/form-data")
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_FORMAT"
