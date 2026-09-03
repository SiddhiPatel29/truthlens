"""
Audio Detection API Routes.
"""
from flask import Blueprint, request
from backend.services.audio_service import AudioDetectionService
from backend.utils.file_validator import allowed_file, ALLOWED_AUDIO_EXTENSIONS
from backend.utils.response import api_response

audio_bp = Blueprint("audio", __name__)

@audio_bp.route("/detect/audio", methods=["POST"])
def detect_audio():
    """
    POST /api/detect/audio
    Accepts multipart/form-data with an 'audio' file field.
    """
    if "audio" not in request.files:
        return api_response(
            success=False,
            message="No 'audio' file field found in request.",
            error_code="MISSING_FILE",
            status_code=400
        )

    file = request.files["audio"]
    if not file or file.filename == "":
        return api_response(
            success=False,
            message="No audio file selected.",
            error_code="INVALID_FILE",
            status_code=400
        )

    if not allowed_file(file.filename, ALLOWED_AUDIO_EXTENSIONS):
        return api_response(
            success=False,
            message=f"Invalid audio format. Allowed: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}",
            error_code="INVALID_FORMAT",
            status_code=400
        )

    try:
        result = AudioDetectionService.analyze_audio(file)
        return api_response(
            success=True,
            message="Audio analyzed successfully.",
            data=result,
            status_code=200
        )
    except ValueError as e:
        return api_response(
            success=False,
            message=str(e),
            error_code="PROCESSING_ERROR",
            status_code=400
        )
    except Exception as e:
        return api_response(
            success=False,
            message=f"Internal Error: {str(e)}",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )