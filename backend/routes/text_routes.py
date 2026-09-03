"""
Text Detection API Routes.
"""
from flask import Blueprint, request
from backend.services.text_service import TextDetectionService
from backend.utils.response import api_response

text_bp = Blueprint("text", __name__)

@text_bp.route("/detect/text", methods=["POST"])
def detect_text():
    """
    POST /api/detect/text
    Request Body: { "text": "Content to evaluate..." }
    """
    body = request.get_json(silent=True)
    
    if not body or "text" not in body:
        return api_response(
            success=False,
            message="Request body must contain a 'text' field.",
            error_code="INVALID_INPUT",
            status_code=400
        )

    input_text = body.get("text", "")

    if len(input_text.strip()) < 20:
        return api_response(
            success=False,
            message="Text is too short. Please provide at least 20 characters for meaningful analysis.",
            error_code="TEXT_TOO_SHORT",
            status_code=400
        )

    try:
        result = TextDetectionService.analyze_text(input_text)
        return api_response(
            success=True,
            message="Text analyzed successfully.",
            data=result,
            status_code=200
        )
    except ValueError as e:
        return api_response(
            success=False,
            message=str(e),
            error_code="PROCESSING_ERROR",
            status_code=400
        )
    except Exception as e:
        return api_response(
            success=False,
            message="An error occurred while analyzing the text.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )