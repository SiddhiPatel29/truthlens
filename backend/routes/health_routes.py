"""
System Health and Diagnostics Route.
"""
from flask import Blueprint
from backend.utils.response import api_response

health_bp = Blueprint("health", __name__)

@health_bp.route("/health", methods=["GET"])
def health_check():
    """
    GET /api/health
    Returns server operational status and supported modalities.
    """
    health_data = {
        "service": "VeraMedia AI Backend",
        "status": "OPERATIONAL",
        "version": "1.0.0",
        "supported_modalities": ["video", "audio", "image", "text"]
    }
    return api_response(
        success=True,
        message="VeraMedia AI Backend is running smoothly.",
        data=health_data,
        status_code=200
    )