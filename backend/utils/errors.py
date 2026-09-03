"""
Centralized Error Handling Module.
Registers standard error handlers on the Flask application to ensure all
errors return consistent, safe JSON responses adhering to the API envelope.
"""
import logging
from werkzeug.exceptions import HTTPException
from backend.utils.response import api_response

logger = logging.getLogger("backend.errors")

def register_error_handlers(app):
    """Registers standard HTTP and unhandled exception handlers on the Flask app."""

    @app.errorhandler(400)
    def handle_bad_request(e):
        return api_response(
            success=False,
            message=getattr(e, "description", "Bad request or malformed payload."),
            error_code="BAD_REQUEST",
            status_code=400
        )

    @app.errorhandler(404)
    def handle_not_found(e):
        return api_response(
            success=False,
            message="The requested resource was not found on this server.",
            error_code="NOT_FOUND",
            status_code=404
        )

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        return api_response(
            success=False,
            message="The HTTP method is not allowed for this endpoint.",
            error_code="METHOD_NOT_ALLOWED",
            status_code=405
        )

    @app.errorhandler(413)
    def handle_payload_too_large(e):
        return api_response(
            success=False,
            message="Request payload exceeds maximum permitted file size.",
            error_code="PAYLOAD_TOO_LARGE",
            status_code=413
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """Fallback handler for any other standard Werkzeug HTTP exceptions."""
        code = e.code or 500
        return api_response(
            success=False,
            message=getattr(e, "description", "An HTTP error occurred."),
            error_code=f"HTTP_{code}",
            status_code=code
        )

    @app.errorhandler(Exception)
    def handle_unhandled_exception(e):
        """
        Catch-all for unhandled exceptions.
        Logs full traceback server-side and returns a sanitized JSON response.
        """
        logger.exception("Unhandled server exception: %s", str(e))
        return api_response(
            success=False,
            message="An unexpected internal server error occurred.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )
