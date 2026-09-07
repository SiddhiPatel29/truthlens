"""
Scan Persistence Service for VeraMedia AI.
Handles transactional persistence and retrieval of forensic scans and scan results
using the existing SQLAlchemy database models.
"""
import logging
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from backend.database.db import db
from backend.database.models import Scan, ScanResult, utc_now

logger = logging.getLogger(__name__)

class ScanServiceError(Exception):
    """Base exception for all scan persistence service errors."""
    pass

class ScanValidationError(ScanServiceError, ValueError):
    """Exception raised when scan input validation fails."""
    pass

class ScanNotFoundError(ScanServiceError):
    """Exception raised when a requested scan does not exist in the database."""
    pass

class ScanConflictError(ScanServiceError):
    """Exception raised when attempting to attach a duplicate result to a scan."""
    pass

class ScanDatabaseError(ScanServiceError):
    """Exception raised when an underlying database transaction fails."""
    pass

class ScanService:
    """Service providing transactional persistence and retrieval for scans and results."""

    @classmethod
    def create_scan(cls, user_id=None, media_type: str = None, filename: str = None) -> Scan:
        """
        Creates and persists a new Scan record in PENDING status.

        Args:
            user_id (int, optional): The ID of the owning user, or None for temporary schema compatibility.
            media_type (str): Media modality (e.g. "image", "video", "audio", "text").
            filename (str, optional): Original uploaded filename or identifier.

        Returns:
            Scan: The persisted Scan instance with database-assigned id.

        Raises:
            ScanValidationError: If media_type is invalid or user_id is non-positive.
            ScanDatabaseError: If database persistence fails.
        """
        # Validate user_id if provided
        if user_id is not None:
            if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
                raise ScanValidationError("user_id must be a positive integer or None.")

        # Validate media_type
        if not media_type or not isinstance(media_type, str) or not media_type.strip():
            raise ScanValidationError("media_type is required and must be a non-empty string.")
        clean_media_type = media_type.strip().lower()

        # Clean filename
        clean_filename = filename.strip() if (filename and isinstance(filename, str)) else None

        scan = Scan(
            user_id=user_id,
            media_type=clean_media_type,
            filename=clean_filename,
            status="PENDING",
            created_at=utc_now()
        )

        try:
            db.session.add(scan)
            db.session.commit()
            return scan
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception("Database error occurred while creating scan: %s", str(e))
            raise ScanDatabaseError("A database error occurred while creating the scan.") from e

    @classmethod
    def save_scan_result(
        cls,
        scan_id: int,
        prediction: str,
        confidence: float,
        risk_level: str,
        result_data: dict = None
    ) -> ScanResult:
        """
        Persists forensic analysis outcomes for an existing scan and marks the parent
        Scan as COMPLETED within a single atomic database transaction.

        Args:
            scan_id (int): ID of the target Scan record.
            prediction (str): Analysis outcome label.
            confidence (float): Confidence score between 0.0 and 1.0.
            risk_level (str): Calculated risk classification.
            result_data (dict, optional): Structured forensic metrics dictionary.

        Returns:
            ScanResult: The persisted ScanResult instance.

        Raises:
            ScanValidationError: If input fields are invalid or out of bounds.
            ScanNotFoundError: If target scan_id does not exist.
            ScanConflictError: If a ScanResult is already attached to this scan.
            ScanDatabaseError: If database transaction fails.
        """
        # Validate scan_id
        if isinstance(scan_id, bool) or not isinstance(scan_id, int) or scan_id <= 0:
            raise ScanValidationError("scan_id must be a positive integer.")

        # Look up parent scan
        scan = db.session.get(Scan, scan_id)
        if scan is None:
            raise ScanNotFoundError(f"Scan with id {scan_id} does not exist.")

        # Enforce one-to-one constraint: reject duplicate result creation
        if scan.result is not None:
            raise ScanConflictError(f"Scan with id {scan_id} already has an associated ScanResult.")

        # Validate prediction
        if not prediction or not isinstance(prediction, str) or not prediction.strip():
            raise ScanValidationError("prediction is required and must be a non-empty string.")
        clean_prediction = prediction.strip()

        # Validate confidence (float between 0.0 and 1.0)
        try:
            conf_val = float(confidence)
        except (TypeError, ValueError):
            raise ScanValidationError("confidence must be a float between 0.0 and 1.0.")
        if conf_val < 0.0 or conf_val > 1.0:
            raise ScanValidationError("confidence must be a float between 0.0 and 1.0.")

        # Validate risk_level
        if not risk_level or not isinstance(risk_level, str) or not risk_level.strip():
            raise ScanValidationError("risk_level is required and must be a non-empty string.")
        clean_risk_level = risk_level.strip()

        # Validate result_data
        if result_data is not None and not isinstance(result_data, dict):
            raise ScanValidationError("result_data must be a dictionary or None.")
        clean_result_data = result_data if isinstance(result_data, dict) else {}

        now = utc_now()
        scan_result = ScanResult(
            scan_id=scan.id,
            prediction=clean_prediction,
            confidence=conf_val,
            risk_level=clean_risk_level,
            result_data=clean_result_data,
            created_at=now
        )

        # Update parent scan within the same atomic transaction
        scan.status = "COMPLETED"
        scan.completed_at = now

        try:
            db.session.add(scan_result)
            db.session.commit()
            return scan_result
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception("Database error occurred while saving scan result: %s", str(e))
            raise ScanDatabaseError("A database error occurred while saving the scan result.") from e

    @classmethod
    def get_scan_by_id(cls, scan_id: int) -> Scan | None:
        """
        Retrieves a Scan record by primary key ID.

        Args:
            scan_id (int): Database primary key ID.

        Returns:
            Scan or None: The Scan instance if found, otherwise None.
        """
        if isinstance(scan_id, bool) or not isinstance(scan_id, int) or scan_id <= 0:
            return None
        return db.session.get(Scan, scan_id)

    @classmethod
    def get_scan_result_by_scan_id(cls, scan_id: int) -> ScanResult | None:
        """
        Retrieves a ScanResult record by associated scan_id.

        Args:
            scan_id (int): ID of the associated Scan.

        Returns:
            ScanResult or None: The ScanResult instance if found, otherwise None.
        """
        if isinstance(scan_id, bool) or not isinstance(scan_id, int) or scan_id <= 0:
            return None
        return ScanResult.query.filter_by(scan_id=scan_id).first()
