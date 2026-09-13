"""
Authentication and Authorization Utilities for VeraMedia AI.
Provides the @require_auth route decorator to validate Bearer JWT tokens,
enforce security invariants, and bind the authenticated user ID to Flask's g context.
"""
from functools import wraps
import logging
from flask import request, g
import jwt
from backend.database.db import db
from backend.database.models import User
from backend.services.auth_service import AuthService
from backend.utils.response import api_response

logger = logging.getLogger(__name__)

def require_auth(f):
    """
    Route decorator requiring a valid Bearer JWT access token.

    Validates HTTP Authorization header:
        Authorization: Bearer <token>

    Delegates token cryptographic verification and claim requirements ('sub', 'iat', 'exp')
    to AuthService.verify_token(), then verifies that the referenced user exists
    and is active in the database.

    On success:
        Binds integer user ID from the 'sub' claim to `g.current_user_id` and the
        authenticated User record to `g.current_user`.

    On authentication failure (401 Unauthorized):
        - Missing, empty, or non-Bearer header -> AUTHENTICATION_REQUIRED
        - Expired token -> TOKEN_EXPIRED
        - Malformed token, bad signature, or invalid claims -> INVALID_TOKEN
        - Nonexistent user or inactive user account -> INVALID_TOKEN

    Note: Unexpected server exceptions are deliberately NOT caught here to allow
    Flask's centralized error handlers to safely return HTTP 500 without masking errors.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.strip():
            return api_response(
                success=False,
                message="Authentication required.",
                error_code="AUTHENTICATION_REQUIRED",
                status_code=401
            )

        parts = auth_header.strip().split(None, 1)
        if len(parts) != 2 or parts[0] != "Bearer":
            return api_response(
                success=False,
                message="Authentication required.",
                error_code="AUTHENTICATION_REQUIRED",
                status_code=401
            )

        token = parts[1].strip()
        if not token:
            return api_response(
                success=False,
                message="Authentication required.",
                error_code="AUTHENTICATION_REQUIRED",
                status_code=401
            )

        try:
            payload = AuthService.verify_token(token)
        except jwt.ExpiredSignatureError:
            return api_response(
                success=False,
                message="Authentication token has expired.",
                error_code="TOKEN_EXPIRED",
                status_code=401
            )
        except jwt.InvalidTokenError:
            return api_response(
                success=False,
                message="Invalid authentication token.",
                error_code="INVALID_TOKEN",
                status_code=401
            )

        # Validate sub claim for application use
        sub = payload.get("sub")
        try:
            user_id = int(sub)
            if user_id <= 0:
                raise ValueError("user_id must be a positive integer")
        except (TypeError, ValueError):
            return api_response(
                success=False,
                message="Invalid authentication token.",
                error_code="INVALID_TOKEN",
                status_code=401
            )

        # SEC-09: Verify that referenced user exists and is active
        user = db.session.get(User, user_id, populate_existing=True)
        if user is None or not user.is_active:
            return api_response(
                success=False,
                message="Invalid authentication token.",
                error_code="INVALID_TOKEN",
                status_code=401
            )

        g.current_user_id = user_id
        g.current_user = user
        return f(*args, **kwargs)

    return decorated
