"""
Text Detection API Routes.
"""
import logging
from flask import Blueprint, request, g
from backend.services.text_service import TextDetectionService, MAX_TEXT_LENGTH
from backend.services.scan_service import ScanService, ScanServiceError
from backend.utils.auth import require_auth
from backend.utils.limiter import (
    limiter,
    get_user_rate_limit_key,
    get_limit,
    DEFAULT_LIMIT_DETECT_TEXT,
)
from backend.utils.response import api_response

logger = logging.getLogger(__name__)
text_bp = Blueprint("text", __name__)

@text_bp.route("/detect/text", methods=["POST"])
@require_auth
@limiter.limit(get_limit("RATELIMIT_DETECT_TEXT", DEFAULT_LIMIT_DETECT_TEXT), key_func=get_user_rate_limit_key)
def detect_text():
    """
    POST /api/detect/text
    Request Body: { "text": "Content to evaluate..." }
    Requires Bearer JWT Authorization header.
    Persists scan and forensic outcome for the authenticated user.
    """
    body = request.get_json(silent=True)
    
    if not body or not isinstance(body, dict) or "text" not in body:
        return api_response(
            success=False,
            message="Request body must contain a 'text' field.",
            error_code="INVALID_INPUT",
            status_code=400
        )

    input_text = body.get("text")
    if not isinstance(input_text, str):
        return api_response(
            success=False,
            message="Field 'text' must be a valid string.",
            error_code="INVALID_INPUT",
            status_code=400
        )

    if len(input_text.strip()) < 20:
        return api_response(
            success=False,
            message="Text is too short. Please provide at least 20 characters for meaningful analysis.",
            error_code="TEXT_TOO_SHORT",
            status_code=400
        )

    if len(input_text.strip()) > MAX_TEXT_LENGTH:
        return api_response(
            success=False,
            message=f"Text exceeds maximum permitted length of {MAX_TEXT_LENGTH} characters.",
            error_code="TEXT_TOO_LONG",
            status_code=400
        )

    try:
        result = TextDetectionService.analyze_text(input_text)
    except ValueError as e:
        logger.warning("Text processing validation failed: %s", str(e))
        return api_response(
            success=False,
            message=str(e),
            error_code="PROCESSING_ERROR",
            status_code=400
        )
    except Exception as e:
        logger.exception("Unexpected error in text detection: %s", str(e))
        return api_response(
            success=False,
            message="An error occurred while analyzing the text.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )

    # Persist scan and forensic outcome for authenticated user
    try:
        user_id = g.current_user_id
        scan = ScanService.create_scan(
            user_id=user_id,
            media_type="text",
            filename=None
        )

        confidence = float(result.get("ai_confidence_score", 0.0))
        is_ai = bool(result.get("is_ai_generated", False))
        prediction = "AI_GENERATED" if is_ai else "AUTHENTIC"
        risk_level = "HIGH" if confidence >= 0.7 else ("MEDIUM" if confidence >= 0.4 else "LOW")

        ScanService.save_scan_result(
            scan_id=scan.id,
            prediction=prediction,
            confidence=confidence,
            risk_level=risk_level,
            result_data=result
        )
    except ScanServiceError as e:
        logger.exception("Scan persistence failed for user %s: %s", getattr(g, "current_user_id", None), str(e))
        return api_response(
            success=False,
            message="An error occurred while persisting the scan results.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )
    except Exception as e:
        logger.exception("Unexpected error during scan persistence: %s", str(e))
        return api_response(
            success=False,
            message="An unexpected error occurred while saving the scan.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )

    return api_response(
        success=True,
        message="Text analyzed successfully.",
        data=result,
        status_code=200
    )