"""
Audio Detection API Routes.
"""
import logging
from flask import Blueprint, request, g
from backend.services.audio_service import AudioDetectionService
from backend.services.scan_service import ScanService, ScanServiceError
from backend.utils.auth import require_auth
from backend.utils.file_validator import validate_audio_file
from backend.utils.response import api_response

logger = logging.getLogger(__name__)
audio_bp = Blueprint("audio", __name__)

@audio_bp.route("/detect/audio", methods=["POST"])
@require_auth
def detect_audio():
    """
    POST /api/detect/audio
    Accepts multipart/form-data with an 'audio' file field.
    Requires Bearer JWT Authorization header.
    Persists scan and forensic outcome for the authenticated user.
    """
    if "audio" not in request.files:
        return api_response(
            success=False,
            message="No 'audio' file field found in request.",
            error_code="MISSING_FILE",
            status_code=400
        )

    file = request.files["audio"]
    is_valid, err_msg, err_code = validate_audio_file(file)

    if not is_valid:
        return api_response(
            success=False,
            message=err_msg,
            error_code=err_code,
            status_code=400
        )

    try:
        result = AudioDetectionService.analyze_audio(file)
    except ValueError as e:
        logger.warning("Audio processing validation failed: %s", str(e))
        return api_response(
            success=False,
            message=str(e),
            error_code="PROCESSING_ERROR",
            status_code=400
        )
    except Exception as e:
        logger.exception("Unexpected error in audio detection: %s", str(e))
        return api_response(
            success=False,
            message="An unexpected error occurred while analyzing the audio.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )

    # Persist scan and forensic outcome for authenticated user
    try:
        user_id = g.current_user_id
        # Preserve actual uploaded filename if provided
        filename = file.filename if (file and file.filename and file.filename.strip()) else None

        scan = ScanService.create_scan(
            user_id=user_id,
            media_type="audio",
            filename=filename
        )

        confidence = float(result.get("confidence_score", 0.0))
        is_synthetic = bool(result.get("is_synthetic_audio", False))
        prediction = "SYNTHETIC" if is_synthetic else "AUTHENTIC"
        risk_level = "HIGH" if confidence >= 0.7 else ("MEDIUM" if confidence >= 0.4 else "LOW")

        # Deliberately construct result_data: serializable metrics + lip-sync events
        # Excludes raw audio bytes and unnecessary intermediate arrays
        metrics = result.get("metrics", {}) if isinstance(result.get("metrics"), dict) else {}
        discrepancies = result.get("lip_sync_discrepancies", [])
        if not isinstance(discrepancies, list):
            discrepancies = []

        result_data = {
            "is_synthetic_audio": is_synthetic,
            "confidence_score": confidence,
            "metrics": {
                "duration_seconds": float(metrics.get("duration_seconds", 0.0)),
                "sample_rate_hz": int(metrics.get("sample_rate_hz", 0)),
                "zero_crossing_rate": float(metrics.get("zero_crossing_rate", 0.0)),
                "energy_variance": float(metrics.get("energy_variance", 0.0))
            },
            "lip_sync_discrepancies": [
                {
                    "start_timestamp": str(d.get("start_timestamp", "")),
                    "end_timestamp": str(d.get("end_timestamp", "")),
                    "measured_offset_ms": int(d.get("measured_offset_ms", 0)),
                    "severity": str(d.get("severity", "")),
                    "description": str(d.get("description", ""))
                }
                for d in discrepancies if isinstance(d, dict)
            ]
        }

        ScanService.save_scan_result(
            scan_id=scan.id,
            prediction=prediction,
            confidence=confidence,
            risk_level=risk_level,
            result_data=result_data
        )
    except ScanServiceError as e:
        logger.exception("Scan persistence failed for audio scan by user %s: %s", getattr(g, "current_user_id", None), str(e))
        return api_response(
            success=False,
            message="An error occurred while persisting the scan results.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )
    except Exception as e:
        logger.exception("Unexpected error during audio scan persistence: %s", str(e))
        return api_response(
            success=False,
            message="An unexpected error occurred while saving the scan.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )

    return api_response(
        success=True,
        message="Audio analyzed successfully.",
        data=result,
        status_code=200
    )