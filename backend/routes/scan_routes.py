"""
Scan History API Routes.
Provides endpoints to list user scan history with pagination and media filtering,
and retrieve detailed forensic results for individual user-owned scans.
"""
import logging
from flask import Blueprint, request, g
from backend.services.scan_service import (
    ScanService,
    ScanServiceError,
    ScanValidationError,
    ScanDatabaseError,
    ALLOWED_MEDIA_TYPES,
)
from backend.utils.auth import require_auth
from backend.utils.limiter import (
    limiter,
    get_user_rate_limit_key,
    get_limit,
    DEFAULT_LIMIT_SCANS,
)
from backend.utils.response import api_response

logger = logging.getLogger(__name__)
scan_bp = Blueprint("scans", __name__)


@scan_bp.route("/scans", methods=["GET"])
@require_auth
@limiter.limit(get_limit("RATELIMIT_SCANS", DEFAULT_LIMIT_SCANS), key_func=get_user_rate_limit_key)
def list_scans():
    """
    GET /api/scans
    Query Parameters:
        - page (int, optional): Page number >= 1 (default: 1).
        - per_page (int, optional): Items per page, 1-100 (default: 10).
        - media_type (str, optional): Filter by 'text', 'image', 'video', or 'audio'.
    Requires Bearer JWT Authorization header.
    Returns paginated, lightweight list of scans owned by the authenticated user.
    """
    # 1. Parse and validate 'page'
    page_param = request.args.get("page", 1)
    try:
        page = int(page_param)
        if page < 1:
            return api_response(
                success=False,
                message="Query parameter 'page' must be an integer greater than or equal to 1.",
                error_code="INVALID_PAGE",
                status_code=400,
            )
    except (ValueError, TypeError):
        return api_response(
            success=False,
            message="Query parameter 'page' must be a valid integer.",
            error_code="INVALID_PAGE",
            status_code=400,
        )

    # 2. Parse and validate 'per_page'
    per_page_param = request.args.get("per_page", 10)
    try:
        per_page = int(per_page_param)
        if per_page < 1 or per_page > 100:
            return api_response(
                success=False,
                message="Query parameter 'per_page' must be an integer between 1 and 100.",
                error_code="INVALID_PER_PAGE",
                status_code=400,
            )
    except (ValueError, TypeError):
        return api_response(
            success=False,
            message="Query parameter 'per_page' must be a valid integer.",
            error_code="INVALID_PER_PAGE",
            status_code=400,
        )

    # 3. Parse and validate optional 'media_type'
    media_type_param = request.args.get("media_type")
    clean_media_type = None
    if media_type_param is not None:
        clean_media_type = media_type_param.strip().lower()
        if clean_media_type not in ALLOWED_MEDIA_TYPES:
            return api_response(
                success=False,
                message=f"Invalid media_type '{media_type_param}'. Allowed values are: audio, image, text, video.",
                error_code="INVALID_MEDIA_TYPE",
                status_code=400,
            )

    # 4. Query scans scoped to authenticated user
    try:
        user_id = g.current_user_id
        scans_data = ScanService.get_user_scans(
            user_id=user_id,
            page=page,
            per_page=per_page,
            media_type=clean_media_type,
        )
    except ScanValidationError as e:
        logger.warning("Scan query validation failed: %s", str(e))
        return api_response(
            success=False,
            message=str(e),
            error_code="INVALID_INPUT",
            status_code=400,
        )
    except ScanDatabaseError as e:
        logger.exception("Database error while retrieving scans for user %s: %s", getattr(g, "current_user_id", None), str(e))
        return api_response(
            success=False,
            message="An error occurred while retrieving scans.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500,
        )
    except Exception as e:
        logger.exception("Unexpected error while retrieving scans: %s", str(e))
        return api_response(
            success=False,
            message="An unexpected error occurred while retrieving scans.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500,
        )

    # 5. Serialize lightweight scan items (strictly excluding result_data)
    items = [
        {
            "id": scan.id,
            "media_type": scan.media_type,
            "filename": scan.filename,
            "status": scan.status,
            "created_at": scan.created_at.isoformat() if scan.created_at else None,
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
            "result": {
                "id": scan.result.id,
                "prediction": scan.result.prediction,
                "confidence": scan.result.confidence,
                "risk_level": scan.result.risk_level,
            } if scan.result else None,
        }
        for scan in scans_data["items"]
    ]

    return api_response(
        success=True,
        message="Scans retrieved successfully.",
        data={
            "items": items,
            "pagination": scans_data["pagination"],
        },
        status_code=200,
    )


@scan_bp.route("/scans/<int:scan_id>", methods=["GET"])
@require_auth
@limiter.limit(get_limit("RATELIMIT_SCANS", DEFAULT_LIMIT_SCANS), key_func=get_user_rate_limit_key)
def get_scan(scan_id: int):
    """
    GET /api/scans/<int:scan_id>
    Requires Bearer JWT Authorization header.
    Returns full detailed forensic results for a specific scan owned by the user.
    Returns 404 SCAN_NOT_FOUND if the scan does not exist or belongs to another user.
    """
    user_id = g.current_user_id

    try:
        scan = ScanService.get_user_scan_by_id(user_id=user_id, scan_id=scan_id)
    except ScanValidationError as e:
        logger.warning("Scan detail validation failed: %s", str(e))
        return api_response(
            success=False,
            message=str(e),
            error_code="INVALID_INPUT",
            status_code=400,
        )
    except ScanDatabaseError as e:
        logger.exception("Database error while retrieving scan %d for user %s: %s", scan_id, user_id, str(e))
        return api_response(
            success=False,
            message="An error occurred while retrieving scan details.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500,
        )
    except Exception as e:
        logger.exception("Unexpected error while retrieving scan detail: %s", str(e))
        return api_response(
            success=False,
            message="An unexpected error occurred while retrieving scan details.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500,
        )

    # If scan does not exist or belongs to another user, return 404 (IDOR prevention)
    if scan is None:
        return api_response(
            success=False,
            message="Scan not found.",
            error_code="SCAN_NOT_FOUND",
            status_code=404,
        )

    # Serialize full detail payload including result_data
    result_payload = None
    if scan.result:
        result_payload = {
            "id": scan.result.id,
            "scan_id": scan.result.scan_id,
            "prediction": scan.result.prediction,
            "confidence": scan.result.confidence,
            "risk_level": scan.result.risk_level,
            "created_at": scan.result.created_at.isoformat() if scan.result.created_at else None,
            "result_data": scan.result.result_data,
        }

    detail_data = {
        "id": scan.id,
        "user_id": scan.user_id,
        "media_type": scan.media_type,
        "filename": scan.filename,
        "status": scan.status,
        "created_at": scan.created_at.isoformat() if scan.created_at else None,
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        "result": result_payload,
    }

    return api_response(
        success=True,
        message="Scan details retrieved successfully.",
        data=detail_data,
        status_code=200,
    )
