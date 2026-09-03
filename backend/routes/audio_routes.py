"""
Audio Detection API Routes.
"""
import logging
from flask import Blueprint, request
from backend.services.audio_service import AudioDetectionService
from backend.utils.file_validator import validate_audio_file
from backend.utils.response import api_response

logger = logging.getLogger(__name__)
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
    is_valid, err_msg, err_code = validate_audio_file(file)

    if not is_valid:
        return api_response(
            success=False,
            message=err_msg,
            error_code=err_code,
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
        logger.warning("Audio processing validation failed: %s", str(e))
        return api_response(
            success=False,
            message=str(e),
            error_code="PROCESSING_ERROR",
            status_code=400
        )
    except Exception as e:
        logger.exception("Unexpected error in audio detection: %s", str(e))
        return api_response(
            success=False,
            message="An unexpected error occurred while analyzing the audio.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )