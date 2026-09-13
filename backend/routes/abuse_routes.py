"""
Abuse Dispatcher API Routes.
"""
import logging
from flask import Blueprint, g, request
from backend.database.db import db
from backend.database.models import User, Scan
from backend.services.abuse_service import AbuseDispatcherService, AbuseDatabaseError
from backend.utils.limiter import limiter, get_limit, DEFAULT_LIMIT_REPORT_ABUSE
from backend.utils.response import api_response

logger = logging.getLogger(__name__)
abuse_bp = Blueprint("abuse", __name__)

@abuse_bp.route("/report/abuse", methods=["POST"])
@limiter.limit(get_limit("RATELIMIT_REPORT_ABUSE", DEFAULT_LIMIT_REPORT_ABUSE))
def dispatch_abuse_report():
    """
    POST /api/report/abuse
    Request JSON:
    {
        "platform": "youtube",
        "target_url": "https://youtube.com/watch?v=sample123",
        "category": "Synthetic Impersonation",
        "confidence_score": 0.982,
        "analyst_notes": "Deepfake face-swap detected on frame 142."
    }
    """
    body = request.get_json(silent=True)
    if not body or not isinstance(body, dict):
        return api_response(
            success=False,
            message="Request body must be valid JSON.",
            error_code="INVALID_JSON",
            status_code=400
        )

    try:
        dossier = AbuseDispatcherService.generate_dossier(body)
        platform = body.get("platform", "").lower().strip()

        # Resolve optional relationships if validly present in context or payload
        user_id = None
        current_uid = getattr(g, "current_user_id", None)
        if isinstance(current_uid, int) and current_uid > 0:
            if db.session.get(User, current_uid):
                user_id = current_uid

        scan_id = None
        raw_scan_id = body.get("scan_id")
        if isinstance(raw_scan_id, int) and raw_scan_id > 0:
            if db.session.get(Scan, raw_scan_id):
                scan_id = raw_scan_id

        AbuseDispatcherService.save_report(
            platform=platform,
            dossier=dossier,
            user_id=user_id,
            scan_id=scan_id
        )

        return api_response(
            success=True,
            message="Abuse dossier successfully generated and dispatched.",
            data=dossier,
            status_code=201
        )
    except ValueError as e:
        logger.warning("Abuse report validation failed: %s", str(e))
        return api_response(
            success=False,
            message=str(e),
            error_code="VALIDATION_ERROR",
            status_code=400
        )
    except (AbuseDatabaseError, Exception) as e:
        logger.exception("Unexpected error in abuse report processing: %s", str(e))
        return api_response(
            success=False,
            message="An unexpected error occurred while processing the abuse report.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )