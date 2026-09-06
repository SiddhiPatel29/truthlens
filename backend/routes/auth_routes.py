"""
Authentication API Routes for VeraMedia AI.
Provides endpoints for user registration and identity management.
"""
import logging
from flask import Blueprint, request
from backend.services.auth_service import AuthService, AuthValidationError
from backend.utils.response import api_response

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/auth/register", methods=["POST"])
def register():
    """
    POST /api/auth/register
    Registers a new user account with secure password hashing.

    Request JSON:
    {
        "name": "Alice",
        "email": "alice@example.com",
        "password": "StrongPassword123"
    }

    Response (201 Created):
    {
        "success": true,
        "message": "User registered successfully.",
        "data": {
            "id": 1,
            "name": "Alice",
            "email": "alice@example.com"
        },
        "error_code": null
    }
    """
    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return api_response(
            success=False,
            message="Request body must be valid JSON.",
            error_code="INVALID_JSON",
            status_code=400
        )

    try:
        user_data = AuthService.register_user(body)
        return api_response(
            success=True,
            message="User registered successfully.",
            data=user_data,
            status_code=201
        )
    except AuthValidationError as e:
        logger.warning("Registration validation failed: %s (%s)", e.message, e.error_code)
        return api_response(
            success=False,
            message=e.message,
            error_code=e.error_code,
            status_code=400
        )
    except Exception as e:
        logger.exception("Unexpected error during user registration: %s", str(e))
        return api_response(
            success=False,
            message="An unexpected error occurred during registration.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )
