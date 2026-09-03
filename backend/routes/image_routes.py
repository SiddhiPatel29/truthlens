"""
Image Detection API Routes.
"""
import traceback
from flask import Blueprint, request
from backend.services.image_service import ImageDetectionService
from backend.utils.file_validator import validate_image_file
from backend.utils.response import api_response

image_bp = Blueprint("image", __name__)

@image_bp.route("/detect/image", methods=["POST"])
def detect_image():
    """
    POST /api/detect/image
    Accepts multipart/form-data with an 'image' file field.
    """
    if "image" not in request.files:
        return api_response(
            success=False,
            message="No 'image' file field found in request.",
            error_code="MISSING_FILE",
            status_code=400
        )

    file = request.files["image"]
    is_valid, err_msg = validate_image_file(file)

    if not is_valid:
        return api_response(
            success=False,
            message=err_msg,
            error_code="INVALID_FILE",
            status_code=400
        )

    try:
        file_bytes = file.read()
        result = ImageDetectionService.analyze_image(file_bytes)
        return api_response(
            success=True,
            message="Image analyzed successfully.",
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
        print("\n--- SERVER EXCEPTION DETECTED ---")
        traceback.print_exc()
        print("---------------------------------\n")
        return api_response(
            success=False,
            message=f"Internal Error: {str(e)}",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )