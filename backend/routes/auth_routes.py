"""
Authentication API Routes for VeraMedia AI.
Provides endpoints for user registration and identity management.
"""
import logging
from flask import Blueprint, request
from backend.services.auth_service import AuthService, AuthValidationError, AuthCredentialsError
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

@auth_bp.route("/auth/login", methods=["POST"])
def login():
    """
    POST /api/auth/login
    Authenticates user credentials and issues a signed JWT access token.

    Request JSON:
    {
        "email": "alice@example.com",
        "password": "StrongPassword123"
    }

    Response (200 OK):
    {
        "success": true,
        "message": "Login successful.",
        "data": {
            "access_token": "ey...",
            "token_type": "Bearer",
            "expires_in": 86400
        },
        "error_code": null
    }

    Error Responses:
    - 400 Bad Request: Malformed JSON, missing or non-string email/password.
    - 401 Unauthorized: Invalid credentials (anti-enumeration: same response for nonexistent email, wrong password, or inactive user).
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
        login_data = AuthService.login_user(body)
        return api_response(
            success=True,
            message="Login successful.",
            data=login_data,
            status_code=200
        )
    except AuthValidationError as e:
        logger.warning("Login validation failed: %s (%s)", e.message, e.error_code)
        return api_response(
            success=False,
            message=e.message,
            error_code=e.error_code,
            status_code=400
        )
    except AuthCredentialsError as e:
        logger.warning("Login failed: %s (%s)", e.message, e.error_code)
        return api_response(
            success=False,
            message=e.message,
            error_code=e.error_code,
            status_code=401
        )
    except Exception as e:
        logger.exception("Unexpected error during login: %s", str(e))
        return api_response(
            success=False,
            message="An unexpected error occurred during login.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )

