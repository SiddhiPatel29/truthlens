"""
Video Detection API Routes.
"""
from flask import Blueprint, request
from backend.services.video_service import VideoDetectionService
from backend.utils.file_validator import allowed_file, ALLOWED_VIDEO_EXTENSIONS
from backend.utils.response import api_response

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
    if not file or file.filename == "":
        return api_response(
            success=False,
            message="No video file selected.",
            error_code="INVALID_FILE",
            status_code=400
        )

    if not allowed_file(file.filename, ALLOWED_VIDEO_EXTENSIONS):
        return api_response(
            success=False,
            message=f"Invalid video format. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}",
            error_code="INVALID_FORMAT",
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