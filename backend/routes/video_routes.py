"""
Video Detection API Routes.
"""
import logging
from flask import Blueprint, request
from backend.services.video_service import VideoDetectionService
from backend.utils.file_validator import validate_video_file
from backend.utils.response import api_response

logger = logging.getLogger(__name__)
video_bp = Blueprint("video", __name__)

@video_bp.route("/detect/video", methods=["POST"])
def detect_video():
    """
    POST /api/detect/video
    Accepts multipart/form-data with a 'video' file field.
    """
    if "video" not in request.files:
        return api_response(
            success=False,
            message="No 'video' file field found in request.",
            error_code="MISSING_FILE",
            status_code=400
        )

    file = request.files["video"]
    is_valid, err_msg, err_code = validate_video_file(file)

    if not is_valid:
        return api_response(
            success=False,
            message=err_msg,
            error_code=err_code,
            status_code=400
        )

    try:
        result = VideoDetectionService.analyze_video(file)
        return api_response(
            success=True,
            message="Video analyzed successfully.",
            data=result,
            status_code=200
        )
    except ValueError as e:
        logger.warning("Video processing validation failed: %s", str(e))
        return api_response(
            success=False,
            message=str(e),
            error_code="PROCESSING_ERROR",
            status_code=400
        )
    except Exception as e:
        logger.exception("Unexpected error in video detection: %s", str(e))
        return api_response(
            success=False,
            message="An unexpected error occurred while analyzing the video.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )