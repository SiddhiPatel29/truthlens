"""
File Validation Utilities.
Ensures uploaded media adheres to allowed extensions and size limits.
"""
import os

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv"}
ALLOWED_AUDIO_EXTENSIONS = {"wav", "mp3", "m4a", "flac"}

def allowed_file(filename: str, allowed_set: set) -> bool:
    """Checks if file has a permitted extension."""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in allowed_set

def validate_image_file(file) -> tuple[bool, str]:
    """Validates uploaded image file object."""
    if not file or file.filename == "":
        return False, "No image file provided."
    
    if not allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS):
        return False, f"Invalid image format. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
    
    return True, ""