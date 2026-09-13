"""
Tests for Abuse Report Dispatcher API Route (/api/report/abuse) & Persistence.
Verifies that POST /api/report/abuse:
- Validates request payload according to supported platforms and URL requirements.
- Generates cryptographically hashed takedown dossiers.
- Persists valid reports to the abuse_reports table in an atomic transaction.
- Preserves referential integrity for optional scan and user relationships without inventing fake IDs.
- Guarantees zero database records are persisted upon validation failure or database errors.
- Handles database exceptions gracefully with sanitized HTTP 500 error envelopes.
"""
import hashlib
import json
import pytest
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError
from backend.database.db import db
from backend.database.models import AbuseReport, User, Scan

@pytest.fixture(autouse=True)
def clean_db(app):
    """Ensures a clean database state before and after each test."""
    with app.app_context():
        db.session.rollback()
        db.session.query(AbuseReport).delete()
        db.session.query(Scan).delete()
        db.session.query(User).delete()
        db.session.commit()
    db.session.remove()
    yield
    with app.app_context():
        db.session.rollback()
        db.session.query(AbuseReport).delete()
        db.session.query(Scan).delete()
        db.session.query(User).delete()
        db.session.commit()
    db.session.remove()

def test_dispatch_abuse_report_success(client, app):
    """1. Verify valid report returns 201 Created and creates exactly one database row with matching data."""
    payload = {
        "platform": "youtube",
        "target_url": "https://youtube.com/watch?v=sample123",
        "category": "Synthetic Impersonation",
        "confidence_score": 0.982,
        "analyst_notes": "Deepfake face-swap detected on frame 142."
    }
    response = client.post("/api/report/abuse", json=payload)
    assert response.status_code == 201
    assert response.is_json

    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["message"] == "Abuse dossier successfully generated and dispatched."
    assert json_data["error_code"] is None

    data = json_data["data"]
    assert "report_id" in data
    assert data["report_id"].startswith("VM-REP-")
    assert data["status"] == "DISPATCHED"
    assert "dispatch_timestamp" in data
    assert "platform_destination" in data
    assert data["platform_destination"]["platform"] == "Youtube"
    assert "forensic_evidence" in data
    assert "sha256_fingerprint" in data["forensic_evidence"]
    assert len(data["forensic_evidence"]["sha256_fingerprint"]) == 64
    assert "dispatch_receipt" in data
    assert "acknowledgment_code" in data["dispatch_receipt"]

    # Verify database persistence
    with app.app_context():
        assert AbuseReport.query.count() == 1
        report = AbuseReport.query.first()
        assert report is not None
        assert report.platform == "youtube"
        assert report.status == "DISPATCHED"
        assert report.user_id is None
        assert report.scan_id is None
        assert report.created_at is not None
        assert report.report_data["report_id"] == data["report_id"]
        assert report.report_data["forensic_evidence"]["sha256_fingerprint"] == data["forensic_evidence"]["sha256_fingerprint"]
        assert report.report_data["platform_destination"]["target_url"] == payload["target_url"]

def test_dispatch_abuse_report_unsupported_platform(client, app):
    """2. Verify report for unsupported platform returns 400 and creates ZERO database rows."""
    payload = {
        "platform": "tiktok",
        "target_url": "https://tiktok.com/@user/video/123",
        "category": "Synthetic Impersonation"
    }
    response = client.post("/api/report/abuse", json=payload)
    assert response.status_code == 400

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "VALIDATION_ERROR"
    assert "unsupported platform" in json_data["message"].lower()

    with app.app_context():
        assert AbuseReport.query.count() == 0

def test_dispatch_abuse_report_missing_target_url(client, app):
    """3. Verify report without target_url returns 400 and creates ZERO database rows."""
    payload = {
        "platform": "meta",
        "category": "Synthetic Impersonation"
    }
    response = client.post("/api/report/abuse", json=payload)
    assert response.status_code == 400

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "VALIDATION_ERROR"
    assert "target url" in json_data["message"].lower()

    with app.app_context():
        assert AbuseReport.query.count() == 0

def test_dispatch_abuse_report_empty_or_invalid_json(client, app):
    """4. Verify non-JSON payload returns 400 INVALID_JSON and creates ZERO database rows."""
    response = client.post("/api/report/abuse", data="not json", content_type="text/plain")
    assert response.status_code == 400

    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INVALID_JSON"

    with app.app_context():
        assert AbuseReport.query.count() == 0

def test_dispatch_abuse_report_database_failure_handling(client, app):
    """5. Verify database commit failure returns sanitized 500 and leaves ZERO partial rows."""
    payload = {
        "platform": "x",
        "target_url": "https://x.com/user/status/123456789",
        "category": "Impersonation",
        "confidence_score": 0.99
    }

    with patch.object(db.session, "commit", side_effect=SQLAlchemyError("Simulated database write error")):
        response = client.post("/api/report/abuse", json=payload)

    assert response.status_code == 500
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["error_code"] == "INTERNAL_SERVER_ERROR"
    assert "unexpected error" in json_data["message"].lower()
    # Database internals must not leak in error message
    assert "Simulated database write error" not in json_data["message"]

    with app.app_context():
        assert AbuseReport.query.count() == 0

def test_dispatch_abuse_report_with_valid_scan_link(client, app):
    """6. Verify optional scan_id relationship is linked when a valid scan exists."""
    with app.app_context():
        scan = Scan(media_type="image", filename="evidence.png", status="COMPLETED")
        db.session.add(scan)
        db.session.commit()
        scan_id = scan.id

    payload = {
        "platform": "meta",
        "target_url": "https://facebook.com/post/999",
        "scan_id": scan_id
    }
    response = client.post("/api/report/abuse", json=payload)
    assert response.status_code == 201

    with app.app_context():
        assert AbuseReport.query.count() == 1
        report = AbuseReport.query.first()
        assert report.scan_id == scan_id
        # Verify bidirectional relationship
        persisted_scan = db.session.get(Scan, scan_id)
        assert report in persisted_scan.abuse_reports

def test_dispatch_abuse_report_hash_signature_integrity(client, app):
    """7. Verify generated sha256_fingerprint cryptographically matches manifest data."""
    payload = {
        "platform": "youtube",
        "target_url": "https://youtube.com/watch?v=verify_hash",
        "category": "Synthetic Voice",
        "confidence_score": 0.91
    }
    response = client.post("/api/report/abuse", json=payload)
    assert response.status_code == 201
    data = response.get_json()["data"]

    # Reconstruct raw manifest exactly as service does
    raw_manifest = {
        "report_id": data["report_id"],
        "target_url": payload["target_url"],
        "platform": payload["platform"],
        "confidence_score": payload["confidence_score"],
        "timestamp": data["dispatch_timestamp"]
    }
    expected_hash = hashlib.sha256(json.dumps(raw_manifest, sort_keys=True).encode("utf-8")).hexdigest()

    assert data["forensic_evidence"]["sha256_fingerprint"] == expected_hash

    with app.app_context():
        report = AbuseReport.query.first()
        assert report.report_data["forensic_evidence"]["sha256_fingerprint"] == expected_hash
