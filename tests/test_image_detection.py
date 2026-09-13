"""
Tests for Image Detection API Route (/api/detect/image).
"""
import base64
import io
import os
from unittest.mock import patch
import cv2
import numpy as np
import pytest
from werkzeug.security import generate_password_hash
from backend.database.db import db
from backend.database.models import User, Scan, ScanResult

def make_test_jpeg(width: int, height: int, color=(128, 128, 128)) -> io.BytesIO:
    """Creates a synthetic in-memory JPEG image with specified dimensions."""
    arr = np.full((height, width, 3), color, dtype=np.uint8)
    success, buf = cv2.imencode(".jpg", arr)
    assert success, f"Failed to encode test image of dimensions {width}x{height}"
    return io.BytesIO(buf.tobytes())

def decode_base64_jpeg(data_url: str):
    """Decodes a Base64 data URL into an OpenCV image matrix."""
    prefix = "data:image/jpeg;base64,"
    assert data_url.startswith(prefix), f"Expected prefix {prefix}"
    b64_str = data_url[len(prefix):]
    raw_bytes = base64.b64decode(b64_str)
    arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    assert img is not None, "Failed to decode Base64 JPEG into OpenCV matrix"
    return img

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
    assert "scan_id" in payload
    assert isinstance(payload["scan_id"], int) and payload["scan_id"] > 0
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
    """Verify file with invalid extension returns 400 INVALID_FORMAT."""
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
    assert json_data["error_code"] == "INVALID_FORMAT"

def test_detect_image_corrupt_content(client, auth_headers):
    """Verify corrupted image payload with valid magic bytes returns 400 PROCESSING_ERROR."""
    data = {
        "image": (io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00corrupt_payload"), "corrupted.jpg")
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

def test_detect_image_width_exceeding_maximum_rejected_400(client, auth_headers, app):
    """Verify image with width > 4096 is rejected with 400 PROCESSING_ERROR and no scan persisted."""
    img_io = make_test_jpeg(width=5000, height=1000)
    data = {
        "image": (img_io, "wide_oversized.jpg")
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
    assert "exceed maximum permitted limits" in json_data["message"]

    with app.app_context():
        assert db.session.query(Scan).count() == 0
        assert db.session.query(ScanResult).count() == 0

def test_detect_image_height_exceeding_maximum_rejected_400(client, auth_headers, app):
    """Verify image with height > 4096 is rejected with 400 PROCESSING_ERROR and no scan persisted."""
    img_io = make_test_jpeg(width=1000, height=5000)
    data = {
        "image": (img_io, "tall_oversized.jpg")
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
    assert "exceed maximum permitted limits" in json_data["message"]

    with app.app_context():
        assert db.session.query(Scan).count() == 0
        assert db.session.query(ScanResult).count() == 0

def test_detect_image_pixel_count_exceeding_maximum_rejected_400(client, auth_headers, app):
    """Verify image exceeding total pixel limit is rejected independently of individual dimensions."""
    # Under a 500k pixel policy, an 800x800 image has w=800 <= 4096 and h=800 <= 4096, but 640k pixels > 500k
    with patch("backend.services.image_service.MAX_IMAGE_PIXELS", 500_000):
        img_io = make_test_jpeg(width=800, height=800)
        data = {
            "image": (img_io, "pixel_oversized.jpg")
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
        assert "exceed maximum permitted limits" in json_data["message"]

        with app.app_context():
            assert db.session.query(Scan).count() == 0
            assert db.session.query(ScanResult).count() == 0

def test_detect_image_boundary_case_permitted(client, auth_headers, app):
    """Verify image exactly at maximum width boundary (4096x16) is accepted and processed."""
    img_io = make_test_jpeg(width=4096, height=16)
    data = {
        "image": (img_io, "boundary_image.jpg")
    }
    response = client.post(
        "/api/detect/image",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers
    )
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["data"]["image_dimensions"] == {"width": 4096, "height": 16}

    # Verify heatmap preview is downscaled to thumbnail representation
    thumb = decode_base64_jpeg(json_data["data"]["heatmap_preview"])
    assert thumb.shape[1] == 512
    assert thumb.shape[0] == 2  # 16 * (512 / 4096) = 2

    with app.app_context():
        assert db.session.query(Scan).count() == 1
        assert db.session.query(ScanResult).count() == 1

def test_detect_image_heatmap_thumbnail_dimensions_downscaled(client, auth_headers):
    """Verify large image heatmap preview is downscaled to max 512px maintaining aspect ratio."""
    # 1000 x 600 -> downscaled to 512 x 307
    img_io = make_test_jpeg(width=1000, height=600)
    data = {
        "image": (img_io, "large_photo.jpg")
    }
    response = client.post(
        "/api/detect/image",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers
    )
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True
    # image_dimensions preserves original input dimensions
    assert json_data["data"]["image_dimensions"] == {"width": 1000, "height": 600}

    # Decoded heatmap preview must be thumbnail sized
    thumb = decode_base64_jpeg(json_data["data"]["heatmap_preview"])
    assert thumb.shape[1] == 512  # width downscaled from 1000 to 512
    assert thumb.shape[0] == 307  # height downscaled from 600 to 307
    assert thumb.shape[1] <= 512
    assert thumb.shape[0] <= 512

def test_detect_image_heatmap_small_source_not_upscaled(client, auth_headers):
    """Verify small image heatmap preview is not upscaled beyond original dimensions."""
    # 200 x 150 -> max_dim 200 <= 512, should remain 200 x 150
    img_io = make_test_jpeg(width=200, height=150)
    data = {
        "image": (img_io, "small_icon.jpg")
    }
    response = client.post(
        "/api/detect/image",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers
    )
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["data"]["image_dimensions"] == {"width": 200, "height": 150}

    thumb = decode_base64_jpeg(json_data["data"]["heatmap_preview"])
    assert thumb.shape[1] == 200
    assert thumb.shape[0] == 150


# ===========================================================================
# Phase 5 Step 5: Magic-Byte and Filename Security Tests
# ===========================================================================

def test_detect_image_invalid_magic_bytes_rejected(client, auth_headers):
    """Verify arbitrary random bytes with .jpg extension return 400 INVALID_FORMAT."""
    data = {
        "image": (io.BytesIO(b"not an actual image byte stream at all"), "corrupted.jpg")
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
    assert json_data["error_code"] == "INVALID_FORMAT"
    assert "JPEG signature" in json_data["message"]


def test_detect_image_signature_mismatch_rejected(client, auth_headers):
    """Verify PNG payload uploaded with .jpg extension is rejected with 400 INVALID_FORMAT."""
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    data = {
        "image": (io.BytesIO(png_bytes), "mismatched.jpg")
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
    assert json_data["error_code"] == "INVALID_FORMAT"


@pytest.mark.parametrize("bad_name", [
    "../../evil.jpg",
    r"..\..\evil.jpg",
    "sub/folder/evil.jpg",
    r"sub\folder\evil.jpg",
    "C:evil.jpg",
    ".hidden.jpg",
    "evil.jpg.",
    "evil.jpg ",
])
def test_detect_image_path_traversal_and_unsafe_filenames_rejected(client, auth_headers, bad_name):
    """Verify path traversal, separators, colons, dot prefixes/suffixes return 400 INVALID_FILE."""
    data = {
        "image": (io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF"), bad_name)
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


def test_detect_image_control_char_filename_rejected(client, auth_headers):
    """Verify null bytes or control characters in filename return 400 INVALID_FILE."""
    data = {
        "image": (io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF"), "test\x00image.jpg")
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


def test_detect_image_double_dot_filename_accepted(client, real_image_path, auth_headers):
    """Verify legitimate ordinary double dots in filename (e.g. audit..v1.jpg) are accepted."""
    with open(real_image_path, "rb") as img_file:
        data = {"image": (img_file, "audit..v1.jpg")}
        response = client.post(
            "/api/detect/image",
            data=data,
            content_type="multipart/form-data",
            headers=auth_headers
        )
    assert response.status_code == 200
    assert response.get_json()["success"] is True


def test_detect_image_spaces_and_unicode_filename_accepted(client, real_image_path, auth_headers):
    """Verify spaces and international Unicode characters in filename are accepted."""
    with open(real_image_path, "rb") as img_file:
        data = {"image": (img_file, "forensic evidence photo 2026.jpg")}
        response = client.post(
            "/api/detect/image",
            data=data,
            content_type="multipart/form-data",
            headers=auth_headers
        )
    assert response.status_code == 200
    assert response.get_json()["success"] is True


