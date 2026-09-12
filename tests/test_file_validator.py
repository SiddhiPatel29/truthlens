"""
Unit tests for backend/utils/file_validator.py.
Tests filename security, extension validation, bounded stream prefix reading,
and magic-byte file signature validation across images, videos, and audio.
"""
import io
import pytest
from backend.utils.file_validator import (
    is_safe_filename,
    allowed_file,
    read_file_prefix,
    validate_image_signature,
    validate_video_signature,
    validate_audio_signature,
    validate_image_file,
    validate_video_file,
    validate_audio_file,
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_VIDEO_EXTENSIONS,
    ALLOWED_AUDIO_EXTENSIONS,
    MAX_FILENAME_LENGTH,
    MAGIC_BYTE_PREFIX_LENGTH,
)


class MockFileStorage:
    """Mock Flask FileStorage for unit testing file validation."""
    def __init__(self, stream: io.BytesIO, filename: str):
        self.stream = stream
        self.filename = filename


# ===========================================================================
# 1. Filename Safety Unit Tests
# ===========================================================================

def test_is_safe_filename_valid_names():
    """Verify valid typical filenames are accepted."""
    valid_names = [
        "image.jpg",
        "video.mp4",
        "audio.wav",
        "test_file_123.png",
        "My-Report-2026.jpeg",
        "UPPERCASE.JPG",
    ]
    for name in valid_names:
        is_safe, err = is_safe_filename(name)
        assert is_safe is True, f"Expected {name} to be safe, got error: {err}"
        assert err == ""


def test_is_safe_filename_double_dots_accepted():
    """Verify legitimate ordinary double dots in filenames are NOT rejected."""
    double_dot_names = [
        "audit..v1.jpg",
        "my..scan..report.png",
        "clip..final.mp4",
        "voice..take2..clean.wav",
    ]
    for name in double_dot_names:
        is_safe, err = is_safe_filename(name)
        assert is_safe is True, f"Expected {name} to be accepted, got error: {err}"
        assert err == ""


def test_is_safe_filename_spaces_and_unicode_accepted():
    """Verify filenames with spaces and international Unicode are accepted."""
    unicode_names = [
        "forensic evidence sample.jpg",
        "données_médicales.png",
        "foto küche.jpg",
        "证据_音频.wav",
        "über_alles.mp4",
    ]
    for name in unicode_names:
        is_safe, err = is_safe_filename(name)
        assert is_safe is True, f"Expected {name} to be accepted, got error: {err}"
        assert err == ""


def test_is_safe_filename_empty_or_whitespace():
    """Verify empty or whitespace-only filenames are rejected."""
    for bad in ["", "   ", "\t", None]:
        is_safe, err = is_safe_filename(bad)
        assert is_safe is False
        assert "empty" in err.lower()


def test_is_safe_filename_excessive_length():
    """Verify filenames exceeding MAX_FILENAME_LENGTH are rejected."""
    long_name = "a" * (MAX_FILENAME_LENGTH + 1) + ".jpg"
    is_safe, err = is_safe_filename(long_name)
    assert is_safe is False
    assert "exceeds maximum permitted length" in err


def test_is_safe_filename_control_characters():
    """Verify null bytes and control characters are rejected."""
    bad_names = [
        "bad\x00file.jpg",
        "newline\nfile.png",
        "return\rfile.wav",
        "tab\tfile.mp4",
        "del\x7ffile.jpg",
        "escape\x1bfile.jpg",
    ]
    for name in bad_names:
        is_safe, err = is_safe_filename(name)
        assert is_safe is False, f"Expected {name!r} to be rejected"
        assert "control characters" in err.lower()


def test_is_safe_filename_path_separators():
    """Verify POSIX and Windows path separators are rejected."""
    bad_names = [
        "../../evil.jpg",
        r"..\..\evil.jpg",
        "folder/image.png",
        r"folder\image.png",
        "/etc/passwd.jpg",
        r"C:\Windows\System32\cmd.exe.jpg",
    ]
    for name in bad_names:
        is_safe, err = is_safe_filename(name)
        assert is_safe is False, f"Expected {name} to be rejected"
        assert "path separators" in err.lower() or "drive letters" in err.lower() or "path traversal" in err.lower()


def test_is_safe_filename_drive_letters():
    """Verify Windows drive letters and alternate data stream colons are rejected."""
    bad_names = [
        "C:test.jpg",
        "D:video.mp4",
        "file.jpg:stream",
    ]
    for name in bad_names:
        is_safe, err = is_safe_filename(name)
        assert is_safe is False, f"Expected {name} to be rejected"
        assert "colon" in err.lower() or "drive letters" in err.lower()


def test_is_safe_filename_directory_navigation():
    """Verify bare '.' and '..' are rejected."""
    for name in [".", "..", " . ", " .. "]:
        is_safe, err = is_safe_filename(name)
        assert is_safe is False
        assert any(term in err.lower() for term in ("directory navigation", "dot", "whitespace"))


def test_is_safe_filename_dot_prefix_and_suffix():
    """Verify leading dots and trailing dots/spaces are rejected."""
    bad_names = [
        ".hidden.jpg",
        ".env",
        ".gitignore",
        "evil.jpg.",
        "evil.jpg ",
    ]
    for name in bad_names:
        is_safe, err = is_safe_filename(name)
        assert is_safe is False, f"Expected {name} to be rejected"


# ===========================================================================
# 2. Bounded Prefix Reading & Rewind Tests
# ===========================================================================

def test_read_file_prefix_bounded_and_rewound():
    """Verify read_file_prefix only reads bounded prefix and rewinds stream."""
    data = b"0123456789" * 10  # 100 bytes
    stream = io.BytesIO(data)
    storage = MockFileStorage(stream, "test.bin")

    prefix = read_file_prefix(storage, max_bytes=16)
    assert len(prefix) == 16
    assert prefix == data[:16]
    # Stream must be rewound to original position 0
    assert stream.tell() == 0

    # Reading full stream after prefix read must return entire content
    full_content = stream.read()
    assert full_content == data


def test_read_file_prefix_preserves_non_zero_position():
    """Verify stream position is preserved even if starting non-zero."""
    data = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    stream = io.BytesIO(data)
    stream.seek(5)
    storage = MockFileStorage(stream, "test.bin")

    prefix = read_file_prefix(storage, max_bytes=10)
    assert prefix == data[5:15]
    assert stream.tell() == 5


def test_read_file_prefix_empty_or_none():
    """Verify None or empty storage returns b''."""
    assert read_file_prefix(None) == b""
    assert read_file_prefix(MockFileStorage(io.BytesIO(b""), "empty.bin")) == b""


# ===========================================================================
# 3. Image Signature Validation Tests
# ===========================================================================

def test_validate_image_signature_jpeg():
    """Verify valid JPEG magic bytes (FF D8 FF) pass, non-JPEG fails."""
    valid_prefix = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00"
    for ext in ("jpg", "jpeg"):
        is_valid, err = validate_image_signature(valid_prefix, ext)
        assert is_valid is True
        assert err == ""

    invalid_prefix = b"\x89PNG\r\n\x1a\n"
    for ext in ("jpg", "jpeg"):
        is_valid, err = validate_image_signature(invalid_prefix, ext)
        assert is_valid is False
        assert "JPEG signature" in err


def test_validate_image_signature_png():
    """Verify valid PNG magic bytes pass, non-PNG fails."""
    valid_prefix = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    is_valid, err = validate_image_signature(valid_prefix, "png")
    assert is_valid is True
    assert err == ""

    invalid_prefix = b"\xff\xd8\xff\xe0"
    is_valid, err = validate_image_signature(invalid_prefix, "png")
    assert is_valid is False
    assert "PNG signature" in err


def test_validate_image_signature_webp():
    """Verify valid WebP magic bytes (RIFF....WEBP) pass, invalid fails."""
    valid_prefix = b"RIFF\x20\x00\x00\x00WEBPVP8 "
    is_valid, err = validate_image_signature(valid_prefix, "webp")
    assert is_valid is True
    assert err == ""

    # RIFF but not WEBP (e.g. AVI or WAVE)
    riff_wave = b"RIFF\x20\x00\x00\x00WAVEfmt "
    is_valid, err = validate_image_signature(riff_wave, "webp")
    assert is_valid is False
    assert "WebP signature" in err


def test_validate_image_signature_insufficient_bytes():
    """Verify insufficient bytes are rejected cleanly."""
    is_valid, err = validate_image_signature(b"\xff", "jpg")
    assert is_valid is False
    assert "insufficient data" in err


# ===========================================================================
# 4. Video Signature Validation Tests
# ===========================================================================

def test_validate_video_signature_mp4():
    """Verify valid MP4 ftyp box passes, non-MP4 fails."""
    valid_prefix = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00"
    is_valid, err = validate_video_signature(valid_prefix, "mp4")
    assert is_valid is True
    assert err == ""

    invalid_prefix = b"RIFF\x20\x00\x00\x00AVI LIST"
    is_valid, err = validate_video_signature(invalid_prefix, "mp4")
    assert is_valid is False
    assert "MP4 container signature" in err


def test_validate_video_signature_mov():
    """Verify valid MOV ftyp box passes, arbitrary box names are rejected."""
    valid_prefix = b"\x00\x00\x00\x14ftypqt  \x00\x00\x00\x00"
    is_valid, err = validate_video_signature(valid_prefix, "mov")
    assert is_valid is True
    assert err == ""

    # Arbitrary box names must NOT be accepted under conservative rule
    moov_prefix = b"\x00\x00\x00\x18moov\x00\x00\x00\x00"
    is_valid, err = validate_video_signature(moov_prefix, "mov")
    assert is_valid is False
    assert "QuickTime/ISOBMFF container signature" in err

    wide_prefix = b"\x00\x00\x00\x08wide\x00\x00\x00\x00"
    is_valid, err = validate_video_signature(wide_prefix, "mov")
    assert is_valid is False


def test_validate_video_signature_avi():
    """Verify valid AVI (RIFF....AVI  and AVIX) pass, invalid fails."""
    valid_avi = b"RIFF\x30\x00\x00\x00AVI LIST\x00\x00"
    is_valid, err = validate_video_signature(valid_avi, "avi")
    assert is_valid is True

    valid_avix = b"RIFF\x30\x00\x00\x00AVIXLIST\x00\x00"
    is_valid, err = validate_video_signature(valid_avix, "avi")
    assert is_valid is True

    riff_wave = b"RIFF\x30\x00\x00\x00WAVEfmt \x00\x00"
    is_valid, err = validate_video_signature(riff_wave, "avi")
    assert is_valid is False
    assert "AVI container signature" in err


def test_validate_video_signature_mkv():
    """Verify valid MKV (EBML 1A 45 DF A3) passes, invalid fails."""
    valid_mkv = b"\x1a\x45\xdf\xa3\x93\x42\x86\x81\x01\x42\xf7"
    is_valid, err = validate_video_signature(valid_mkv, "mkv")
    assert is_valid is True

    invalid_mkv = b"\x00\x00\x00\x18ftypmp42"
    is_valid, err = validate_video_signature(invalid_mkv, "mkv")
    assert is_valid is False
    assert "Matroska/EBML container signature" in err


# ===========================================================================
# 5. Audio Signature Validation Tests (WAV Only)
# ===========================================================================

def test_validate_audio_signature_wav():
    """Verify valid WAV (RIFF....WAVE and RIFX....WAVE) pass, non-WAV fails."""
    valid_riff_wave = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
    is_valid, err = validate_audio_signature(valid_riff_wave, "wav")
    assert is_valid is True
    assert err == ""

    valid_rifx_wave = b"RIFX\x00\x00\x00\x24WAVEfmt \x00\x00\x00\x10"
    is_valid, err = validate_audio_signature(valid_rifx_wave, "wav")
    assert is_valid is True
    assert err == ""


def test_validate_audio_signature_rejects_non_wav():
    """Verify MP3 ID3, AVI, or truncated streams fail WAV signature verification."""
    mp3_id3 = b"ID3\x03\x00\x00\x00\x00\x00\x00TIT2"
    is_valid, err = validate_audio_signature(mp3_id3, "wav")
    assert is_valid is False
    assert "WAV container signature" in err

    riff_avi = b"RIFF\x24\x00\x00\x00AVI LIST\x10\x00"
    is_valid, err = validate_audio_signature(riff_avi, "wav")
    assert is_valid is False
    assert "WAV container signature" in err

    truncated = b"RIFF\x24\x00"
    is_valid, err = validate_audio_signature(truncated, "wav")
    assert is_valid is False
    assert "insufficient data" in err


# ===========================================================================
# 6. Composite Validator 3-Tuple and Error Code Tests
# ===========================================================================

def test_validate_image_file_error_codes():
    """Verify error codes: INVALID_FILE for missing/unsafe names, INVALID_FORMAT for ext/magic-byte errors."""
    # Missing file
    valid, msg, code = validate_image_file(None)
    assert valid is False and code == "INVALID_FILE"

    # Empty filename
    valid, msg, code = validate_image_file(MockFileStorage(io.BytesIO(b"data"), ""))
    assert valid is False and code == "INVALID_FILE"

    # Path traversal filename
    valid, msg, code = validate_image_file(MockFileStorage(io.BytesIO(b"\xff\xd8\xff\xe0"), "../../evil.jpg"))
    assert valid is False and code == "INVALID_FILE"

    # Disallowed extension
    valid, msg, code = validate_image_file(MockFileStorage(io.BytesIO(b"some text"), "payload.txt"))
    assert valid is False and code == "INVALID_FORMAT"

    # Signature mismatch
    valid, msg, code = validate_image_file(MockFileStorage(io.BytesIO(b"not a jpeg"), "sample.jpg"))
    assert valid is False and code == "INVALID_FORMAT"

    # Valid JPEG
    valid, msg, code = validate_image_file(MockFileStorage(io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF"), "sample.jpg"))
    assert valid is True and code == ""


def test_validate_video_file_error_codes():
    """Verify video error codes: INVALID_FILE vs INVALID_FORMAT."""
    valid, msg, code = validate_video_file(None)
    assert valid is False and code == "INVALID_FILE"

    valid, msg, code = validate_video_file(MockFileStorage(io.BytesIO(b"data"), "..\\evil.mp4"))
    assert valid is False and code == "INVALID_FILE"

    valid, msg, code = validate_video_file(MockFileStorage(io.BytesIO(b"data"), "movie.exe"))
    assert valid is False and code == "INVALID_FORMAT"

    valid, msg, code = validate_video_file(MockFileStorage(io.BytesIO(b"bad video bytes"), "movie.mp4"))
    assert valid is False and code == "INVALID_FORMAT"

    valid, msg, code = validate_video_file(MockFileStorage(io.BytesIO(b"\x00\x00\x00\x18ftypmp42"), "movie.mp4"))
    assert valid is True and code == ""


def test_validate_audio_file_error_codes():
    """Verify audio error codes: INVALID_FILE vs INVALID_FORMAT."""
    valid, msg, code = validate_audio_file(None)
    assert valid is False and code == "INVALID_FILE"

    valid, msg, code = validate_audio_file(MockFileStorage(io.BytesIO(b"data"), "bad\x00name.wav"))
    assert valid is False and code == "INVALID_FILE"

    valid, msg, code = validate_audio_file(MockFileStorage(io.BytesIO(b"data"), "track.mp3"))
    assert valid is False and code == "INVALID_FORMAT"

    valid, msg, code = validate_audio_file(MockFileStorage(io.BytesIO(b"random bytes"), "track.wav"))
    assert valid is False and code == "INVALID_FORMAT"

    valid, msg, code = validate_audio_file(MockFileStorage(io.BytesIO(b"RIFF\x24\x00\x00\x00WAVEfmt "), "track.wav"))
    assert valid is True and code == ""
