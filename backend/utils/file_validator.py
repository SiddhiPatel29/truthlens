"""
File Validation Utilities.
Provides basic extension and filename validation for uploaded media.
"""
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv"}
ALLOWED_AUDIO_EXTENSIONS = {"wav"}

def allowed_file(filename: str, allowed_set: set) -> bool:
    """Checks if file has a permitted extension."""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in allowed_set

def validate_image_file(file) -> tuple[bool, str, str]:
    """Validates uploaded image file object."""
    if not file or file.filename == "":
        return False, "No image file provided.", "INVALID_FILE"
    
    if not allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS):
        return False, f"Invalid image format. Allowed: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}", "INVALID_FILE"
    
    return True, "", ""

def validate_video_file(file) -> tuple[bool, str, str]:
    """Validates uploaded video file object."""
    if not file or file.filename == "":
        return False, "No video file selected.", "INVALID_FILE"
    
    if not allowed_file(file.filename, ALLOWED_VIDEO_EXTENSIONS):
        return False, f"Invalid video format. Allowed: {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}", "INVALID_FORMAT"
    
    return True, "", ""

def validate_audio_file(file) -> tuple[bool, str, str]:
    """Validates uploaded audio file object."""
    if not file or file.filename == "":
        return False, "No audio file selected.", "INVALID_FILE"
    
    if not allowed_file(file.filename, ALLOWED_AUDIO_EXTENSIONS):
        return False, f"Invalid audio format. Allowed: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}", "INVALID_FORMAT"
    
    return True, "", ""