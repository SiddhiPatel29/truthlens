"""
Video Detection API Routes.
"""
import logging
from flask import Blueprint, request, g
from backend.services.video_service import VideoDetectionService
from backend.services.scan_service import ScanService, ScanServiceError
from backend.utils.auth import require_auth
from backend.utils.file_validator import validate_video_file
from backend.utils.limiter import (
    limiter,
    get_user_rate_limit_key,
    get_limit,
    DEFAULT_LIMIT_DETECT_VIDEO,
)
from backend.utils.response import api_response

logger = logging.getLogger(__name__)
video_bp = Blueprint("video", __name__)

@video_bp.route("/detect/video", methods=["POST"])
@require_auth
@limiter.limit(get_limit("RATELIMIT_DETECT_VIDEO", DEFAULT_LIMIT_DETECT_VIDEO), key_func=get_user_rate_limit_key)
def detect_video():
    """
    POST /api/detect/video
    Accepts multipart/form-data with a 'video' file field.
    Requires Bearer JWT Authorization header.
    Persists scan and forensic outcome for the authenticated user.
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

    # Persist scan and forensic outcome for authenticated user
    try:
        user_id = g.current_user_id
        # Preserve actual uploaded filename if provided
        filename = file.filename if (file and file.filename and file.filename.strip()) else None

        scan = ScanService.create_scan(
            user_id=user_id,
            media_type="video",
            filename=filename
        )

        confidence = float(result.get("confidence_score", 0.0))
        is_deepfake = bool(result.get("is_deepfake", False))
        prediction = "DEEPFAKE" if is_deepfake else "AUTHENTIC"
        risk_level = "HIGH" if confidence >= 0.7 else ("MEDIUM" if confidence >= 0.4 else "LOW")

        # Deliberately construct result_data: serializable metrics + keyframe thumbnail
        # Excludes raw video bytes and unnecessary transient frame objects
        metrics = result.get("metrics", {}) if isinstance(result.get("metrics"), dict) else {}
        result_data = {
            "is_deepfake": is_deepfake,
            "confidence_score": confidence,
            "metrics": {
                "duration_seconds": float(metrics.get("duration_seconds", 0.0)),
                "total_frames_analyzed": int(metrics.get("total_frames_analyzed", 0)),
                "temporal_instability": float(metrics.get("temporal_instability", 0.0)),
                "peak_frame_anomaly": float(metrics.get("peak_frame_anomaly", 0.0))
            },
            "keyframe_heatmap_preview": result.get("keyframe_heatmap_preview")
        }

        ScanService.save_scan_result(
            scan_id=scan.id,
            prediction=prediction,
            confidence=confidence,
            risk_level=risk_level,
            result_data=result_data
        )
    except ScanServiceError as e:
        logger.exception("Scan persistence failed for video scan by user %s: %s", getattr(g, "current_user_id", None), str(e))
        return api_response(
            success=False,
            message="An error occurred while persisting the scan results.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )
    except Exception as e:
        logger.exception("Unexpected error during video scan persistence: %s", str(e))
        return api_response(
            success=False,
            message="An unexpected error occurred while saving the scan.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )

    return api_response(
        success=True,
        message="Video analyzed successfully.",
        data=result,
        status_code=200
    )