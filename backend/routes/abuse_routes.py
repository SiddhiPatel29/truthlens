"""
Abuse Dispatcher API Routes.
"""
from flask import Blueprint, request
from backend.services.abuse_service import AbuseDispatcherService
from backend.utils.response import api_response

abuse_bp = Blueprint("abuse", __name__)

@abuse_bp.route("/report/abuse", methods=["POST"])
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
    if not body:
        return api_response(
            success=False,
            message="Request body must be valid JSON.",
            error_code="INVALID_JSON",
            status_code=400
        )

    try:
        dossier = AbuseDispatcherService.generate_dossier(body)
        return api_response(
            success=True,
            message="Abuse dossier successfully generated and dispatched.",
            data=dossier,
            status_code=201
        )
    except ValueError as e:
        return api_response(
            success=False,
            message=str(e),
            error_code="VALIDATION_ERROR",
            status_code=400
        )
    except Exception as e:
        return api_response(
            success=False,
            message=f"Internal Error: {str(e)}",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )