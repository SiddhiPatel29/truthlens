"""
Tests for Scan Persistence Service (ScanService).
Verifies scan creation, scan result persistence, atomic status updates,
duplicate rejection, transaction rollback, and clean retrieval helpers.
"""
from datetime import datetime
import pytest
from backend.database.db import db
from backend.database.models import User, Scan, ScanResult
from backend.services.scan_service import (
    ScanService,
    ScanServiceError,
    ScanValidationError,
    ScanNotFoundError,
    ScanConflictError,
    ScanDatabaseError
)

@pytest.fixture(autouse=True)
def clean_db(app):
    """Ensures a clean database state before and after each test."""
    with app.app_context():
        db.session.query(ScanResult).delete()
        db.session.query(Scan).delete()
        db.session.query(User).delete()
        db.session.commit()
    yield
    with app.app_context():
        db.session.query(ScanResult).delete()
        db.session.query(Scan).delete()
        db.session.query(User).delete()
        db.session.commit()

@pytest.fixture
def sample_user(app):
    """Creates an active test user in the database."""
    with app.app_context():
        user = User(
            name="Scan Tester",
            email="scantester@example.com",
            password_hash="hashed_pw",
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return user_id


# ===========================================================================
# A. Scan Creation Tests
# ===========================================================================

def test_create_scan_with_valid_user_id(app, sample_user):
    """1-7. Create scan with valid user_id verifies id, fields, PENDING status, and timestamps."""
    with app.app_context():
        scan = ScanService.create_scan(
            user_id=sample_user,
            media_type="image",
            filename="suspicious_face.jpg"
        )
        assert scan is not None
        assert scan.id is not None
        assert isinstance(scan.id, int)
        assert scan.user_id == sample_user
        assert scan.media_type == "image"
        assert scan.filename == "suspicious_face.jpg"
        assert scan.status == "PENDING"
        assert isinstance(scan.created_at, datetime)
        assert scan.completed_at is None

def test_create_scan_anonymous_user_none(app):
    """Temporary schema compatibility: create scan with user_id=None."""
    with app.app_context():
        scan = ScanService.create_scan(
            user_id=None,
            media_type="video",
            filename="clip.mp4"
        )
        assert scan.id is not None
        assert scan.user_id is None
        assert scan.status == "PENDING"
        assert scan.media_type == "video"

def test_create_scan_invalid_media_type_raises_validation_error(app):
    """Create scan with missing or empty media_type raises ScanValidationError."""
    with app.app_context():
        with pytest.raises(ScanValidationError):
            ScanService.create_scan(user_id=None, media_type="")

        with pytest.raises(ScanValidationError):
            ScanService.create_scan(user_id=None, media_type="   ")

        with pytest.raises(ScanValidationError):
            ScanService.create_scan(user_id=None, media_type=None)

def test_create_scan_invalid_user_id_raises_validation_error(app):
    """Create scan with negative, zero, or non-integer user_id raises ScanValidationError."""
    with app.app_context():
        with pytest.raises(ScanValidationError):
            ScanService.create_scan(user_id=-1, media_type="image")

        with pytest.raises(ScanValidationError):
            ScanService.create_scan(user_id=0, media_type="image")

        with pytest.raises(ScanValidationError):
            ScanService.create_scan(user_id="not_an_int", media_type="image")

        with pytest.raises(ScanValidationError):
            ScanService.create_scan(user_id=True, media_type="image")  # bool guard


# ===========================================================================
# B. Scan Result Persistence Tests
# ===========================================================================

def test_save_scan_result_success_and_updates_scan(app, sample_user):
    """8-15. Save scan result attaches to scan, updates status to COMPLETED, and sets completed_at."""
    with app.app_context():
        scan = ScanService.create_scan(
            user_id=sample_user,
            media_type="audio",
            filename="speech.wav"
        )
        assert scan.status == "PENDING"
        assert scan.completed_at is None

        result_payload = {
            "zero_crossing_rate": 0.042,
            "spectral_variance": 128.5
        }
        result = ScanService.save_scan_result(
            scan_id=scan.id,
            prediction="DEEPFAKE",
            confidence=0.875,
            risk_level="HIGH",
            result_data=result_payload
        )

        assert result is not None
        assert result.id is not None
        assert result.scan_id == scan.id
        assert result.prediction == "DEEPFAKE"
        assert result.confidence == 0.875
        assert result.risk_level == "HIGH"
        assert result.result_data == result_payload
        assert isinstance(result.created_at, datetime)

        # Verify parent scan was updated in the same transaction
        updated_scan = ScanService.get_scan_by_id(scan.id)
        assert updated_scan.status == "COMPLETED"
        assert isinstance(updated_scan.completed_at, datetime)
        assert updated_scan.result.id == result.id

def test_save_scan_result_with_none_result_data_defaults_to_dict(app):
    """Saving result with result_data=None persists an empty dictionary."""
    with app.app_context():
        scan = ScanService.create_scan(media_type="text")
        result = ScanService.save_scan_result(
            scan_id=scan.id,
            prediction="AUTHENTIC",
            confidence=0.15,
            risk_level="LOW",
            result_data=None
        )
        assert result.result_data == {}

def test_save_scan_result_nonexistent_scan_raises_not_found(app):
    """Attempting to save result for non-existent scan raises ScanNotFoundError."""
    with app.app_context():
        with pytest.raises(ScanNotFoundError):
            ScanService.save_scan_result(
                scan_id=99999,
                prediction="DEEPFAKE",
                confidence=0.9,
                risk_level="HIGH"
            )

def test_save_scan_result_duplicate_raises_conflict_error(app):
    """Attempting to save a second result for the same scan raises ScanConflictError."""
    with app.app_context():
        scan = ScanService.create_scan(media_type="image")
        ScanService.save_scan_result(
            scan_id=scan.id,
            prediction="DEEPFAKE",
            confidence=0.95,
            risk_level="HIGH"
        )

        # Attempting second result must raise ScanConflictError
        with pytest.raises(ScanConflictError):
            ScanService.save_scan_result(
                scan_id=scan.id,
                prediction="AUTHENTIC",
                confidence=0.10,
                risk_level="LOW"
            )

def test_save_scan_result_validation_failures(app):
    """Proportional validation rejects invalid confidence, missing prediction/risk_level."""
    with app.app_context():
        scan = ScanService.create_scan(media_type="image")

        # Confidence out of bounds
        with pytest.raises(ScanValidationError):
            ScanService.save_scan_result(scan.id, "DEEPFAKE", 1.5, "HIGH")

        with pytest.raises(ScanValidationError):
            ScanService.save_scan_result(scan.id, "DEEPFAKE", -0.1, "HIGH")

        # Non-numeric confidence
        with pytest.raises(ScanValidationError):
            ScanService.save_scan_result(scan.id, "DEEPFAKE", "invalid", "HIGH")

        # Missing or empty prediction
        with pytest.raises(ScanValidationError):
            ScanService.save_scan_result(scan.id, "", 0.5, "HIGH")

        # Missing or empty risk_level
        with pytest.raises(ScanValidationError):
            ScanService.save_scan_result(scan.id, "DEEPFAKE", 0.5, "  ")

        # Invalid result_data type (not a dict)
        with pytest.raises(ScanValidationError):
            ScanService.save_scan_result(scan.id, "DEEPFAKE", 0.5, "HIGH", result_data="string")


# ===========================================================================
# C. Retrieval Helper Tests
# ===========================================================================

def test_get_scan_by_id_success(app, sample_user):
    """16. get_scan_by_id returns the correct Scan object."""
    with app.app_context():
        scan = ScanService.create_scan(user_id=sample_user, media_type="text")
        retrieved = ScanService.get_scan_by_id(scan.id)
        assert retrieved is not None
        assert retrieved.id == scan.id
        assert retrieved.user_id == sample_user
        assert retrieved.media_type == "text"

def test_get_scan_by_id_unknown_returns_none(app):
    """17. get_scan_by_id returns None for an unknown or invalid ID."""
    with app.app_context():
        assert ScanService.get_scan_by_id(99999) is None
        assert ScanService.get_scan_by_id(-1) is None
        assert ScanService.get_scan_by_id("abc") is None

def test_get_scan_result_by_scan_id_success(app):
    """18. get_scan_result_by_scan_id returns the correct ScanResult object."""
    with app.app_context():
        scan = ScanService.create_scan(media_type="video")
        result = ScanService.save_scan_result(
            scan_id=scan.id,
            prediction="SUSPICIOUS",
            confidence=0.68,
            risk_level="MEDIUM"
        )
        retrieved = ScanService.get_scan_result_by_scan_id(scan.id)
        assert retrieved is not None
        assert retrieved.id == result.id
        assert retrieved.prediction == "SUSPICIOUS"
        assert retrieved.confidence == 0.68

def test_get_scan_result_by_scan_id_unknown_returns_none(app):
    """19. get_scan_result_by_scan_id returns None for unknown scan ID or scan without result."""
    with app.app_context():
        assert ScanService.get_scan_result_by_scan_id(99999) is None
        scan = ScanService.create_scan(media_type="text")
        assert ScanService.get_scan_result_by_scan_id(scan.id) is None


# ===========================================================================
# D. Transaction Rollback & Error Behavior Tests
# ===========================================================================

def test_database_failure_causes_rollback_and_session_usable(app):
    """
    20-21. Realistic database failure (foreign key violation) causes rollback,
    raises ScanDatabaseError, and leaves the session clean and usable for subsequent transactions.
    """
    with app.app_context():
        non_existent_user_id = 999999

        # Attempt creating scan with non-existent user_id violates SQLite foreign key
        with pytest.raises(ScanDatabaseError):
            ScanService.create_scan(
                user_id=non_existent_user_id,
                media_type="image",
                filename="failed_fk.jpg"
            )

        # Verify no orphaned scan was committed
        assert db.session.query(Scan).filter_by(filename="failed_fk.jpg").first() is None

        # Verify session remains completely usable for a new, valid transaction
        valid_scan = ScanService.create_scan(
            user_id=None,
            media_type="text",
            filename="recovered.txt"
        )
        assert valid_scan is not None
        assert valid_scan.id is not None
        assert db.session.query(Scan).filter_by(filename="recovered.txt").first() is not None
