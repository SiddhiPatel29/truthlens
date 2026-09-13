"""
Tests for Audio Detection API Route (/api/detect/audio).
"""
import io
import os
import tempfile
from unittest.mock import patch, MagicMock
import numpy as np
import pytest
from werkzeug.security import generate_password_hash
from backend.database.db import db
from backend.database.models import User, Scan, ScanResult
from backend.services.audio_service import AudioDetectionService

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
    assert "scan_id" in payload
    assert isinstance(payload["scan_id"], int) and payload["scan_id"] > 0
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

@pytest.mark.parametrize("ext", ["mp3", "m4a", "flac", "ogg", "aac"])
def test_detect_audio_unsupported_formats_rejected(client, auth_headers, ext):
    """Verify non-WAV audio formats are rejected with 400 INVALID_FORMAT."""
    data = {
        "audio": (io.BytesIO(b"dummy compressed audio data"), f"track.{ext}")
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
    assert "Invalid audio format. Allowed: wav" in json_data["message"]

def test_detect_audio_corrupt_content(client, auth_headers):
    """Verify corrupt WAV byte stream is rejected with 400 PROCESSING_ERROR."""
    data = {
        "audio": (io.BytesIO(b"RIFF\x00\x00\x00\x00WAVEcorrupted_garbage_bytes"), "corrupted.wav")
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
    assert json_data["error_code"] == "PROCESSING_ERROR"
    assert "Failed to decode audio file" in json_data["message"]

def test_detect_audio_empty_wav(client, auth_headers):
    """Verify 0-byte WAV upload is rejected with 400 INVALID_FORMAT."""
    data = {
        "audio": (io.BytesIO(b""), "empty.wav")
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

def test_detect_audio_no_synthetic_noise_fallback(client, real_audio_path, auth_headers):
    """
    CRITICAL INTEGRITY TEST:
    Verify that when wavfile.read() fails, the service does NOT fall back
    to generating synthetic Gaussian noise. It must propagate an error.
    """
    with patch("scipy.io.wavfile.read", side_effect=ValueError("Corrupt wave chunk header")):
        with patch("numpy.random.normal") as mock_random:
            with open(real_audio_path, "rb") as audio_file:
                response = client.post(
                    "/api/detect/audio",
                    data={"audio": (audio_file, "failing.wav")},
                    content_type="multipart/form-data",
                    headers=auth_headers
                )

    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "PROCESSING_ERROR"
    assert "Failed to decode audio file" in json_data["message"]
    # Verify synthetic random generator was NEVER invoked
    mock_random.assert_not_called()

def test_detect_audio_zero_samples_buffer_rejected(client, auth_headers):
    """Verify empty/zero-sample decoded buffer raises 400 PROCESSING_ERROR."""
    valid_wav_header = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    with patch("scipy.io.wavfile.read", return_value=(16000, np.array([], dtype=np.float32))):
        response = client.post(
            "/api/detect/audio",
            data={"audio": (io.BytesIO(valid_wav_header), "zero_samples.wav")},
            content_type="multipart/form-data",
            headers=auth_headers
        )

    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "PROCESSING_ERROR"
    assert "zero readable audio samples" in json_data["message"]

def test_detect_audio_invalid_sample_rate_rejected(client, auth_headers):
    """Verify non-positive sample rate raises 400 PROCESSING_ERROR."""
    valid_wav_header = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    with patch("scipy.io.wavfile.read", return_value=(0, np.array([0.1, 0.2], dtype=np.float32))):
        response = client.post(
            "/api/detect/audio",
            data={"audio": (io.BytesIO(valid_wav_header), "zero_rate.wav")},
            content_type="multipart/form-data",
            headers=auth_headers
        )

    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "PROCESSING_ERROR"
    assert "invalid sample rate" in json_data["message"]

def test_detect_audio_tempfile_cleanup_on_success(client, real_audio_path, auth_headers):
    """Verify temporary audio file is removed from disk after successful detection."""
    created_temp_files = []
    real_mkstemp = tempfile.mkstemp

    def track_mkstemp(*args, **kwargs):
        fd, path = real_mkstemp(*args, **kwargs)
        created_temp_files.append(path)
        return fd, path

    with patch("tempfile.mkstemp", side_effect=track_mkstemp):
        with open(real_audio_path, "rb") as audio_file:
            response = client.post(
                "/api/detect/audio",
                data={"audio": (audio_file, "cleanup_test.wav")},
                content_type="multipart/form-data",
                headers=auth_headers
            )

    assert response.status_code == 200
    assert len(created_temp_files) == 1
    assert not os.path.exists(created_temp_files[0])

def test_detect_audio_tempfile_cleanup_on_decoder_failure(client, auth_headers):
    """Verify temporary audio file is removed from disk when decoder fails."""
    created_temp_files = []
    real_mkstemp = tempfile.mkstemp

    def track_mkstemp(*args, **kwargs):
        fd, path = real_mkstemp(*args, **kwargs)
        created_temp_files.append(path)
        return fd, path

    with patch("tempfile.mkstemp", side_effect=track_mkstemp):
        response = client.post(
            "/api/detect/audio",
            data={"audio": (io.BytesIO(b"RIFF\x24\x00\x00\x00WAVEcorrupted binary wav"), "corrupt_cleanup.wav")},
            content_type="multipart/form-data",
            headers=auth_headers
        )

    assert response.status_code == 400
    assert len(created_temp_files) == 1
    assert not os.path.exists(created_temp_files[0])

def test_detect_audio_tempfile_cleanup_on_processing_exception(client, real_audio_path, auth_headers):
    """Verify temporary audio file is removed from disk even if an unhandled exception occurs."""
    created_temp_files = []
    real_mkstemp = tempfile.mkstemp

    def track_mkstemp(*args, **kwargs):
        fd, path = real_mkstemp(*args, **kwargs)
        created_temp_files.append(path)
        return fd, path

    with patch("tempfile.mkstemp", side_effect=track_mkstemp):
        with patch("scipy.io.wavfile.read", side_effect=RuntimeError("Hardware failure")):
            with open(real_audio_path, "rb") as audio_file:
                response = client.post(
                    "/api/detect/audio",
                    data={"audio": (audio_file, "exception_test.wav")},
                    content_type="multipart/form-data",
                    headers=auth_headers
                )

    assert response.status_code == 400
    assert len(created_temp_files) == 1
    assert not os.path.exists(created_temp_files[0])


# ===========================================================================
# Phase 5 Step 5: Audio Magic-Byte and Filename Security Tests
# ===========================================================================

def test_detect_audio_invalid_magic_bytes_rejected(client, auth_headers):
    """Verify arbitrary random bytes with .wav extension return 400 INVALID_FORMAT."""
    data = {
        "audio": (io.BytesIO(b"not an actual wav byte stream at all"), "corrupted.wav")
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
    assert "WAV container signature" in json_data["message"]


def test_detect_audio_mp3_header_rejected(client, auth_headers):
    """Verify MP3 stream (ID3 header) uploaded as .wav is rejected with 400 INVALID_FORMAT."""
    data = {
        "audio": (io.BytesIO(b"ID3\x03\x00\x00\x00\x00\x00\x00mp3_audio_data"), "fake.wav")
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
    assert "WAV container signature" in json_data["message"]


def test_detect_audio_riff_non_wave_rejected(client, auth_headers):
    """Verify RIFF container that is not WAVE (e.g. AVI) is rejected with 400 INVALID_FORMAT."""
    data = {
        "audio": (io.BytesIO(b"RIFF\x24\x00\x00\x00AVI LIST\x00\x00\x00\x00payload"), "fake.wav")
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


@pytest.mark.parametrize("bad_name", [
    "../../evil.wav",
    r"..\..\evil.wav",
    "sub/folder/evil.wav",
    r"sub\folder\evil.wav",
    "C:evil.wav",
    ".hidden.wav",
    "evil.wav.",
    "evil.wav ",
])
def test_detect_audio_path_traversal_and_unsafe_filenames_rejected(client, auth_headers, bad_name):
    """Verify path traversal, separators, colons, dot prefixes/suffixes return 400 INVALID_FILE."""
    valid_wav = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    data = {
        "audio": (io.BytesIO(valid_wav), bad_name)
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


def test_detect_audio_control_char_filename_rejected(client, auth_headers):
    """Verify null bytes or control characters in filename return 400 INVALID_FILE."""
    valid_wav = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    data = {
        "audio": (io.BytesIO(valid_wav), "evil\x00audio.wav")
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


def test_detect_audio_double_dot_filename_accepted(client, real_audio_path, auth_headers):
    """Verify legitimate ordinary double dots in filename (e.g. recording..final.wav) are accepted."""
    with open(real_audio_path, "rb") as aud_file:
        data = {"audio": (aud_file, "recording..final.wav")}
        response = client.post(
            "/api/detect/audio",
            data=data,
            content_type="multipart/form-data",
            headers=auth_headers
        )
    assert response.status_code == 200
    assert response.get_json()["success"] is True


def test_detect_audio_spaces_and_unicode_filename_accepted(client, real_audio_path, auth_headers):
    """Verify spaces and international Unicode characters in filename are accepted."""
    with open(real_audio_path, "rb") as aud_file:
        data = {"audio": (aud_file, "intercepted voice recording 2026.wav")}
        response = client.post(
            "/api/detect/audio",
            data=data,
            content_type="multipart/form-data",
            headers=auth_headers
        )
    assert response.status_code == 200
    assert response.get_json()["success"] is True


def test_detect_audio_duration_exceeding_limit_rejected_400(client, auth_headers):
    """
    Verify audio with duration > 120s is rejected with 400 PROCESSING_ERROR.
    Uses small sample rate (1000 Hz) to avoid unnecessary memory allocations:
    121s * 1000 samples/sec = 121,000 samples (only ~242 KB).
    """
    from scipy.io import wavfile
    sample_rate = 1000
    samples = np.zeros(121000, dtype=np.int16)
    buf = io.BytesIO()
    wavfile.write(buf, sample_rate, samples)
    buf.seek(0)

    response = client.post(
        "/api/detect/audio",
        data={"audio": (buf, "oversized_duration.wav")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "PROCESSING_ERROR"
    assert "exceeds maximum permitted limit (120s)" in json_data["message"]
    assert "121" in json_data["message"]


def test_detect_audio_duration_boundary_120_seconds_accepted(client, auth_headers):
    """
    Verify audio with duration exactly 120.0s is accepted.
    120s * 1000 samples/sec = 120,000 samples (only ~240 KB).
    """
    from scipy.io import wavfile
    sample_rate = 1000
    # Provide sinusoidal data so ZCR and variance compute cleanly
    t = np.linspace(0, 120, 120000, endpoint=False)
    samples = (np.sin(2 * np.pi * 5 * t) * 10000).astype(np.int16)
    buf = io.BytesIO()
    wavfile.write(buf, sample_rate, samples)
    buf.seek(0)

    response = client.post(
        "/api/detect/audio",
        data={"audio": (buf, "boundary_120s.wav")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["data"]["metrics"]["duration_seconds"] == 120.0


def test_audio_service_direct_duration_exceeded_raises_value_error():
    """Verify AudioDetectionService.analyze_audio raises ValueError when audio exceeds 120s."""
    from scipy.io import wavfile
    sample_rate = 1000
    samples = np.zeros(122000, dtype=np.int16)  # 122s
    buf = io.BytesIO()
    wavfile.write(buf, sample_rate, samples)
    buf.seek(0)

    class DummyFileStorage:
        def __init__(self, stream):
            self.stream = stream
        def save(self, dst):
            self.stream.seek(0)
            dst.write(self.stream.read())

    with pytest.raises(ValueError, match="exceeds maximum permitted limit"):
        AudioDetectionService.analyze_audio(DummyFileStorage(buf))
