"""
File Validation Utilities.
Provides robust filename security, extension validation, and bounded
magic-byte / file signature verification for uploaded media.
"""
import os
from pathlib import PurePath, PurePosixPath, PureWindowsPath

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv"}
ALLOWED_AUDIO_EXTENSIONS = {"wav"}

MAX_FILENAME_LENGTH = 255
MAGIC_BYTE_PREFIX_LENGTH = 32

def is_safe_filename(filename: str) -> tuple[bool, str]:
    """
    Validates that a client-provided filename is safe against path traversal,
    path separators, absolute paths, drive letters, control characters,
    and excessive length.
    
    Permits legitimate ordinary characters (including spaces, unicode characters,
    and ordinary double dots like 'audit..v1.jpg').
    """
    if not filename or not isinstance(filename, str) or not filename.strip():
        return False, "Filename cannot be empty."

    if len(filename) > MAX_FILENAME_LENGTH:
        return False, f"Filename exceeds maximum permitted length of {MAX_FILENAME_LENGTH} characters."

    # Check for null bytes and ASCII control characters (0-31 and 127)
    for ch in filename:
        code = ord(ch)
        if code < 32 or code == 127:
            return False, "Filename contains invalid or control characters."

    # Reject path separators (POSIX '/' and Windows '\')
    if "/" in filename or "\\" in filename:
        return False, "Filename cannot contain path separators."

    # Reject Windows drive letters and alternate data stream colons
    if ":" in filename:
        return False, "Filename cannot contain drive letters or colon characters."

    # Reject leading or trailing whitespace
    if filename != filename.strip():
        return False, "Filename cannot have leading or trailing whitespace."

    # Reject directory navigation references
    if filename in (".", ".."):
        return False, "Filename cannot be a directory navigation reference."

    # Reject hidden files starting with a dot
    if filename.startswith("."):
        return False, "Filename cannot start with a dot."

    # Reject trailing dots (Windows path truncation issue)
    if filename.endswith("."):
        return False, "Filename cannot end with a dot."

    # Verify that the filename represents a pure basename without path components
    if PurePosixPath(filename).name != filename or PureWindowsPath(filename).name != filename:
        return False, "Filename cannot contain path traversal components."

    return True, ""

def allowed_file(filename: str, allowed_set: set) -> bool:
    """Checks if file has a permitted extension."""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in allowed_set

def read_file_prefix(file_storage, max_bytes: int = MAGIC_BYTE_PREFIX_LENGTH) -> bytes:
    """
    Safely reads a bounded prefix from file_storage without consuming the stream,
    ensuring the stream position is deterministically rewound.
    """
    if not file_storage:
        return b""
    stream = getattr(file_storage, "stream", file_storage)
    pos = stream.tell() if hasattr(stream, "tell") else 0
    try:
        prefix = stream.read(max_bytes)
    finally:
        if hasattr(stream, "seek"):
            stream.seek(pos)
    return prefix if prefix is not None else b""

def validate_image_signature(prefix: bytes, ext: str) -> tuple[bool, str]:
    """
    Validates magic bytes for accepted image formats:
    - JPEG (.jpg, .jpeg): FF D8 FF
    - PNG (.png): 89 50 4E 47 0D 0A 1A 0A
    - WebP (.webp): RIFF....WEBP
    """
    if not prefix or len(prefix) < 3:
        return False, f"File is empty or contains insufficient data for .{ext} signature verification."

    if ext in ("jpg", "jpeg"):
        if prefix.startswith(b"\xff\xd8\xff"):
            return True, ""
        return False, f"File content does not match expected JPEG signature for .{ext}."

    if ext == "png":
        if prefix.startswith(b"\x89PNG\r\n\x1a\n"):
            return True, ""
        return False, "File content does not match expected PNG signature for .png."

    if ext == "webp":
        if len(prefix) >= 12 and prefix[:4] == b"RIFF" and prefix[8:12] == b"WEBP":
            return True, ""
        return False, "File content does not match expected WebP signature for .webp."

    return False, f"Unsupported image extension .{ext}."

def validate_video_signature(prefix: bytes, ext: str) -> tuple[bool, str]:
    """
    Validates magic bytes for accepted video container formats:
    - MP4 (.mp4): ISO Base Media File Format ftyp box (bytes 4..8 == 'ftyp')
    - MOV (.mov): QuickTime / ISOBMFF ftyp box (bytes 4..8 == 'ftyp')
    - AVI (.avi): RIFF....AVI  or RIFF....AVIX (bytes 0..4 == 'RIFF', bytes 8..12 in ('AVI ', 'AVIX'))
    - MKV (.mkv): EBML header (bytes 0..4 == 1A 45 DF A3)
    """
    if not prefix or len(prefix) < 4:
        return False, f"File is empty or contains insufficient data for .{ext} signature verification."

    if ext == "mp4":
        if len(prefix) >= 8 and prefix[4:8] == b"ftyp":
            return True, ""
        return False, "File content does not match expected MP4 container signature for .mp4."

    if ext == "mov":
        if len(prefix) >= 8 and prefix[4:8] == b"ftyp":
            return True, ""
        return False, "File content does not match expected QuickTime/ISOBMFF container signature for .mov."

    if ext == "avi":
        if len(prefix) >= 12 and prefix[:4] == b"RIFF" and prefix[8:12] in (b"AVI ", b"AVIX"):
            return True, ""
        return False, "File content does not match expected AVI container signature for .avi."

    if ext == "mkv":
        if len(prefix) >= 4 and prefix[:4] == b"\x1a\x45\xdf\xa3":
            return True, ""
        return False, "File content does not match expected Matroska/EBML container signature for .mkv."

    return False, f"Unsupported video extension .{ext}."

def validate_audio_signature(prefix: bytes, ext: str) -> tuple[bool, str]:
    """
    Validates magic bytes for accepted audio formats (WAV only):
    - WAV (.wav): RIFF....WAVE or RIFX....WAVE
    """
    if not prefix or len(prefix) < 12:
        return False, "File is empty or contains insufficient data for .wav signature verification."

    if ext == "wav":
        if prefix[:4] in (b"RIFF", b"RIFX") and prefix[8:12] == b"WAVE":
            return True, ""
        return False, "File content does not match expected WAV container signature for .wav."

    return False, f"Unsupported audio extension .{ext}."

def validate_image_file(file) -> tuple[bool, str, str]:
    """
    Validates uploaded image file object:
    1. File presence and filename non-empty.
    2. Filename safety (traversal, control chars, length).
    3. Permitted extension (png, jpg, jpeg, webp).
    4. Bounded magic-byte signature check.
    """
    if not file or not getattr(file, "filename", None) or file.filename == "":
        return False, "No image file provided.", "INVALID_FILE"

    is_safe, err_msg = is_safe_filename(file.filename)
    if not is_safe:
        return False, f"Invalid filename: {err_msg}", "INVALID_FILE"

    if not allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS):
        return False, f"Invalid image format. Allowed: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}", "INVALID_FORMAT"

    ext = file.filename.rsplit(".", 1)[1].lower()
    prefix = read_file_prefix(file, MAGIC_BYTE_PREFIX_LENGTH)
    is_valid_sig, sig_err = validate_image_signature(prefix, ext)
    if not is_valid_sig:
        return False, sig_err, "INVALID_FORMAT"

    return True, "", ""

def validate_video_file(file) -> tuple[bool, str, str]:
    """
    Validates uploaded video file object:
    1. File presence and filename non-empty.
    2. Filename safety (traversal, control chars, length).
    3. Permitted extension (mp4, mov, avi, mkv).
    4. Bounded magic-byte signature check.
    """
    if not file or not getattr(file, "filename", None) or file.filename == "":
        return False, "No video file selected.", "INVALID_FILE"

    is_safe, err_msg = is_safe_filename(file.filename)
    if not is_safe:
        return False, f"Invalid filename: {err_msg}", "INVALID_FILE"

    if not allowed_file(file.filename, ALLOWED_VIDEO_EXTENSIONS):
        return False, f"Invalid video format. Allowed: {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}", "INVALID_FORMAT"

    ext = file.filename.rsplit(".", 1)[1].lower()
    prefix = read_file_prefix(file, MAGIC_BYTE_PREFIX_LENGTH)
    is_valid_sig, sig_err = validate_video_signature(prefix, ext)
    if not is_valid_sig:
        return False, sig_err, "INVALID_FORMAT"

    return True, "", ""

def validate_audio_file(file) -> tuple[bool, str, str]:
    """
    Validates uploaded audio file object:
    1. File presence and filename non-empty.
    2. Filename safety (traversal, control chars, length).
    3. Permitted extension (wav only).
    4. Bounded magic-byte signature check.
    """
    if not file or not getattr(file, "filename", None) or file.filename == "":
        return False, "No audio file selected.", "INVALID_FILE"

    is_safe, err_msg = is_safe_filename(file.filename)
    if not is_safe:
        return False, f"Invalid filename: {err_msg}", "INVALID_FILE"

    if not allowed_file(file.filename, ALLOWED_AUDIO_EXTENSIONS):
        return False, f"Invalid audio format. Allowed: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}", "INVALID_FORMAT"

    ext = file.filename.rsplit(".", 1)[1].lower()
    prefix = read_file_prefix(file, MAGIC_BYTE_PREFIX_LENGTH)
    is_valid_sig, sig_err = validate_audio_signature(prefix, ext)
    if not is_valid_sig:
        return False, sig_err, "INVALID_FORMAT"

    return True, "", ""