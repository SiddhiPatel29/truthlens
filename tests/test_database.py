"""
Tests for Database Models, Relationships, Constraints, and Migrations.
"""
import os
import sqlite3
import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from backend.database.models import User, Scan, ScanResult, AbuseReport

def test_user_model_creation(db_session):
    """Verify creating and retrieving a User model."""
    user = User(
        name="Alice Analyst",
        email="alice@veramedia.ai",
        password_hash="argon2_hashed_secret",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()

    queried = db_session.query(User).filter_by(email="alice@veramedia.ai").first()
    assert queried is not None
    assert queried.id is not None
    assert queried.name == "Alice Analyst"
    assert queried.is_active is True
    assert isinstance(queried.created_at, datetime)
    assert isinstance(queried.updated_at, datetime)
    assert "alice@veramedia.ai" in repr(queried)

def test_user_unique_email_constraint(db_session):
    """Verify unique constraint prevents duplicate emails."""
    user1 = User(name="User One", email="duplicate@veramedia.ai", password_hash="hash1")
    user2 = User(name="User Two", email="duplicate@veramedia.ai", password_hash="hash2")

    db_session.add(user1)
    db_session.commit()

    db_session.add(user2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_scan_model_creation_nullable_user(db_session):
    """Verify Scan can be created without user_id (anonymous scan in Phase 2)."""
    scan = Scan(
        user_id=None,
        media_type="image",
        filename="test_upload.jpg",
        status="COMPLETED"
    )
    db_session.add(scan)
    db_session.commit()

    queried = db_session.query(Scan).filter_by(filename="test_upload.jpg").first()
    assert queried is not None
    assert queried.id is not None
    assert queried.user_id is None
    assert queried.media_type == "image"
    assert queried.status == "COMPLETED"
    assert isinstance(queried.created_at, datetime)

def test_scan_result_model_creation(db_session):
    """Verify ScanResult creation with JSON result_data."""
    scan = Scan(media_type="video", filename="sample.mp4", status="COMPLETED")
    db_session.add(scan)
    db_session.commit()

    result = ScanResult(
        scan_id=scan.id,
        prediction="DEEPFAKE",
        confidence=0.925,
        risk_level="HIGH",
        result_data={
            "temporal_instability": 0.082,
            "peak_frame_anomaly": 0.941,
            "total_frames": 16
        }
    )
    db_session.add(result)
    db_session.commit()

    queried = db_session.query(ScanResult).filter_by(scan_id=scan.id).first()
    assert queried is not None
    assert queried.prediction == "DEEPFAKE"
    assert queried.confidence == 0.925
    assert queried.risk_level == "HIGH"
    assert queried.result_data["total_frames"] == 16
    assert isinstance(queried.result_data, dict)

def test_abuse_report_model_creation(db_session):
    """Verify AbuseReport creation with JSON report_data."""
    report = AbuseReport(
        user_id=None,
        scan_id=None,
        platform="youtube",
        status="DISPATCHED",
        report_data={
            "target_url": "https://youtube.com/watch?v=xyz",
            "sha256_fingerprint": "abc123def456",
            "acknowledgment_code": "ACK-12345"
        }
    )
    db_session.add(report)
    db_session.commit()

    queried = db_session.query(AbuseReport).filter_by(platform="youtube").first()
    assert queried is not None
    assert queried.status == "DISPATCHED"
    assert queried.report_data["sha256_fingerprint"] == "abc123def456"

def test_user_scans_relationship(db_session):
    """Verify User -> many Scans relationship."""
    user = User(name="Forensic Analyst", email="analyst@veramedia.ai", password_hash="secret")
    scan1 = Scan(media_type="text", filename="article1.txt")
    scan2 = Scan(media_type="audio", filename="recording.wav")
    
    user.scans.append(scan1)
    user.scans.append(scan2)
    db_session.add(user)
    db_session.commit()

    queried_user = db_session.query(User).filter_by(email="analyst@veramedia.ai").first()
    assert len(queried_user.scans) == 2
    assert scan1 in queried_user.scans
    assert scan2 in queried_user.scans
    assert scan1.user == queried_user
    assert scan2.user == queried_user

def test_scan_scan_result_relationship(db_session):
    """Verify Scan -> one ScanResult (1-to-1) relationship."""
    scan = Scan(media_type="image", filename="profile.png")
    result = ScanResult(
        prediction="AUTHENTIC",
        confidence=0.18,
        risk_level="LOW",
        result_data={"variance": 42.5}
    )
    scan.result = result
    db_session.add(scan)
    db_session.commit()

    queried_scan = db_session.query(Scan).filter_by(filename="profile.png").first()
    assert queried_scan.result is not None
    assert queried_scan.result.prediction == "AUTHENTIC"
    assert queried_scan.result.scan == queried_scan

def test_scan_abuse_reports_relationship(db_session):
    """Verify Scan -> many AbuseReports relationship."""
    scan = Scan(media_type="video", filename="fake_news.mp4")
    report1 = AbuseReport(platform="youtube", report_data={"reason": "manipulation"})
    report2 = AbuseReport(platform="x", report_data={"reason": "impersonation"})

    scan.abuse_reports.extend([report1, report2])
    db_session.add(scan)
    db_session.commit()

    queried_scan = db_session.query(Scan).filter_by(filename="fake_news.mp4").first()
    assert len(queried_scan.abuse_reports) == 2
    assert report1 in queried_scan.abuse_reports
    assert report2 in queried_scan.abuse_reports
    assert report1.scan == queried_scan

def test_user_abuse_reports_relationship(db_session):
    """Verify User -> many AbuseReports relationship."""
    user = User(name="Reporter", email="reporter@veramedia.ai", password_hash="pass")
    report = AbuseReport(platform="meta", report_data={"target": "facebook.com/post/1"})
    
    user.abuse_reports.append(report)
    db_session.add(user)
    db_session.commit()

    queried_user = db_session.query(User).filter_by(email="reporter@veramedia.ai").first()
    assert len(queried_user.abuse_reports) == 1
    assert queried_user.abuse_reports[0].platform == "meta"
    assert report.user == queried_user

def test_foreign_key_constraint_invalid_user_on_scan(db_session):
    """Verify foreign key constraint fails when user_id does not exist."""
    invalid_scan = Scan(user_id=999999, media_type="text", filename="orphan.txt")
    db_session.add(invalid_scan)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_foreign_key_constraint_invalid_scan_on_result(db_session):
    """Verify foreign key constraint fails when scan_id does not exist."""
    invalid_result = ScanResult(
        scan_id=999999,
        prediction="DEEPFAKE",
        confidence=0.9,
        risk_level="HIGH",
        result_data={}
    )
    db_session.add(invalid_result)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_migration_truthlens_db_schema(project_root):
    """Verify the actual truthlens.db created by migrations has all 4 tables and alembic_version."""
    db_path = os.path.join(project_root, "instance", "truthlens.db")
    assert os.path.exists(db_path), f"Database file not found at {db_path}"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {t[0] for t in cursor.fetchall()}
    conn.close()

    expected_tables = {"users", "scans", "scan_results", "abuse_reports", "alembic_version"}
    assert expected_tables.issubset(tables), f"Missing tables in {tables}. Expected: {expected_tables}"
