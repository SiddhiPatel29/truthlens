"""
Image Detection API Routes.
"""
import logging
from flask import Blueprint, request, g
from backend.services.image_service import ImageDetectionService
from backend.services.scan_service import ScanService, ScanServiceError
from backend.utils.auth import require_auth
from backend.utils.file_validator import validate_image_file
from backend.utils.response import api_response

logger = logging.getLogger(__name__)
image_bp = Blueprint("image", __name__)

@image_bp.route("/detect/image", methods=["POST"])
@require_auth
def detect_image():
    """
    POST /api/detect/image
    Accepts multipart/form-data with an 'image' file field.
    Requires Bearer JWT Authorization header.
    Persists scan and forensic outcome for the authenticated user.
    """
    if "image" not in request.files:
        return api_response(
            success=False,
            message="No 'image' file field found in request.",
            error_code="MISSING_FILE",
            status_code=400
        )

    file = request.files["image"]
    is_valid, err_msg, err_code = validate_image_file(file)

    if not is_valid:
        return api_response(
            success=False,
            message=err_msg,
            error_code=err_code,
            status_code=400
        )

    try:
        file_bytes = file.read()
        result = ImageDetectionService.analyze_image(file_bytes)
    except ValueError as e:
        logger.warning("Image processing validation failed: %s", str(e))
        return api_response(
            success=False,
            message=str(e),
            error_code="PROCESSING_ERROR",
            status_code=400
        )
    except Exception as e:
        logger.exception("Unexpected error in image detection: %s", str(e))
        return api_response(
            success=False,
            message="An unexpected error occurred while analyzing the image.",
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
            media_type="image",
            filename=filename
        )

        confidence = float(result.get("confidence_score", 0.0))
        is_deepfake = bool(result.get("is_deepfake", False))
        prediction = "DEEPFAKE" if is_deepfake else "AUTHENTIC"
        risk_level = "HIGH" if confidence >= 0.7 else ("MEDIUM" if confidence >= 0.4 else "LOW")

        ScanService.save_scan_result(
            scan_id=scan.id,
            prediction=prediction,
            confidence=confidence,
            risk_level=risk_level,
            result_data=result
        )
    except ScanServiceError as e:
        logger.exception("Scan persistence failed for image scan by user %s: %s", getattr(g, "current_user_id", None), str(e))
        return api_response(
            success=False,
            message="An error occurred while persisting the scan results.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )
    except Exception as e:
        logger.exception("Unexpected error during image scan persistence: %s", str(e))
        return api_response(
            success=False,
            message="An unexpected error occurred while saving the scan.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )

    return api_response(
        success=True,
        message="Image analyzed successfully.",
        data=result,
        status_code=200
    )