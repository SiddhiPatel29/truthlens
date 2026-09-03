"""
Tests for Image Detection API Route (/api/detect/image).
"""
import io
import os

def test_detect_image_success(client, real_image_path):
    """Verify valid image upload returns 200 and image analysis schema."""
    assert os.path.exists(real_image_path), f"Test image not found at {real_image_path}"
    
    with open(real_image_path, "rb") as img_file:
        data = {
            "image": (img_file, "test.jpg")
        }
        response = client.post(
            "/api/detect/image",
            data=data,
            content_type="multipart/form-data"
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

def test_detect_image_missing_file_field(client):
    """Verify multipart request without 'image' field returns 400 MISSING_FILE."""
    data = {
        "wrong_field": (io.BytesIO(b"fake data"), "test.jpg")
    }
    response = client.post("/api/detect/image", data=data, content_type="multipart/form-data")
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "MISSING_FILE"

def test_detect_image_empty_filename(client):
    """Verify request with empty filename returns 400 INVALID_FILE."""
    data = {
        "image": (io.BytesIO(b""), "")
    }
    response = client.post("/api/detect/image", data=data, content_type="multipart/form-data")
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_FILE"

def test_detect_image_unsupported_extension(client):
    """Verify file with invalid extension returns 400 INVALID_FILE."""
    data = {
        "image": (io.BytesIO(b"dummy binary data"), "test.txt")
    }
    response = client.post("/api/detect/image", data=data, content_type="multipart/form-data")
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_FILE"

def test_detect_image_corrupt_content(client):
    """Verify invalid/corrupted image payload returns 400 PROCESSING_ERROR."""
    data = {
        "image": (io.BytesIO(b"not an actual image byte stream"), "corrupted.jpg")
    }
    response = client.post("/api/detect/image", data=data, content_type="multipart/form-data")
    assert response.status_code == 400
    
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "PROCESSING_ERROR"
