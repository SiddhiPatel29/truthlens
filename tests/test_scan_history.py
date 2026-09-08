"""
Tests for Scan History APIs (Phase 4 Step 6).
Verifies that:
- GET /api/scans returns paginated, lightweight scans for the authenticated user.
- GET /api/scans/<scan_id> returns detailed forensic outcomes for the owned scan.
- Scans are strictly scoped to g.current_user_id (no cross-user access).
- Unowned or non-existent scans return HTTP 404 SCAN_NOT_FOUND (IDOR prevention).
- List response excludes result_data to prevent large Base64 payloads.
- Detail response includes full result_data.
- Sensitive user data (passwords, user objects) is never serialized.
- Pagination supports page/per_page with strict validation (per_page <= 100).
- Optional media_type filter strictly validates against allowed types.
- Deterministic ordering by created_at DESC, id DESC.
- Database errors return sanitized HTTP 500 responses without leaking internals.
"""
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import pytest
import jwt
from werkzeug.security import generate_password_hash
from backend.database.db import db
from backend.database.models import User, Scan, ScanResult, utc_now
from backend.services.scan_service import ScanService, ScanDatabaseError


@pytest.fixture(autouse=True)
def clean_db(app):
    """Ensures a clean database state before and after each test."""
    with app.app_context():
        db.session.rollback()
        db.session.query(ScanResult).delete()
        db.session.query(Scan).delete()
        db.session.query(User).delete()
        db.session.commit()
    db.session.remove()
    yield
    with app.app_context():
        db.session.rollback()
        db.session.query(ScanResult).delete()
        db.session.query(Scan).delete()
        db.session.query(User).delete()
        db.session.commit()
    db.session.remove()


@pytest.fixture
def user_a(app):
    """Creates primary active test user Alice."""
    password = "AliceSecurePassword123!"
    with app.app_context():
        user = User(
            name="Alice Investigator",
            email="alice.history@example.com",
            password_hash=generate_password_hash(password),
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return {"id": user_id, "name": "Alice Investigator", "email": "alice.history@example.com", "password": password}


@pytest.fixture
def headers_a(client, user_a):
    """Generates valid Bearer Authorization header for Alice."""
    res = client.post("/api/auth/login", json={"email": user_a["email"], "password": user_a["password"]})
    token = res.get_json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_b(app):
    """Creates secondary active test user Bob for isolation tests."""
    password = "BobSecurePassword123!"
    with app.app_context():
        user = User(
            name="Bob Analyst",
            email="bob.history@example.com",
            password_hash=generate_password_hash(password),
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return {"id": user_id, "name": "Bob Analyst", "email": "bob.history@example.com", "password": password}


@pytest.fixture
def headers_b(client, user_b):
    """Generates valid Bearer Authorization header for Bob."""
    res = client.post("/api/auth/login", json={"email": user_b["email"], "password": user_b["password"]})
    token = res.get_json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_completed_scan(app, user_id, media_type="text", filename="sample.txt", prediction="AUTHENTIC", confidence=0.2, risk_level="LOW", result_data=None, created_at=None):
    """Helper to insert a completed Scan with associated ScanResult."""
    with app.app_context():
        scan = ScanService.create_scan(user_id=user_id, media_type=media_type, filename=filename)
        res_data = result_data if result_data is not None else {"sample_key": "sample_val"}
        result = ScanService.save_scan_result(
            scan_id=scan.id,
            prediction=prediction,
            confidence=confidence,
            risk_level=risk_level,
            result_data=res_data,
        )
        if created_at is not None:
            scan.created_at = created_at
            db.session.commit()
        scan_id = scan.id
    return scan_id


# ===========================================================================
# A. Authenticated Empty History Tests
# ===========================================================================

def test_authenticated_empty_history(client, headers_a):
    """1. Valid authenticated request with no scans returns HTTP 200 with empty items."""
    res = client.get("/api/scans", headers=headers_a)
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assert body["message"] == "Scans retrieved successfully."
    assert body["error_code"] is None
    assert body["data"]["items"] == []
    assert body["data"]["pagination"] == {
        "page": 1,
        "per_page": 10,
        "total_items": 0,
        "total_pages": 0,
        "has_next": False,
        "has_prev": False,
    }


# ===========================================================================
# B. Authenticated History Retrieval & Ordering Tests
# ===========================================================================

def test_authenticated_history_retrieval_and_ordering(app, client, user_a, headers_a):
    """2. Retrieves user scans ordered by created_at DESC with all required fields."""
    t0 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 3, 10, 0, 0, tzinfo=timezone.utc)

    id1 = create_completed_scan(app, user_a["id"], media_type="text", filename=None, prediction="AUTHENTIC", confidence=0.1, created_at=t0)
    id2 = create_completed_scan(app, user_a["id"], media_type="image", filename="pic.jpg", prediction="DEEPFAKE", confidence=0.85, risk_level="HIGH", created_at=t1)
    id3 = create_completed_scan(app, user_a["id"], media_type="video", filename="clip.mp4", prediction="AUTHENTIC", confidence=0.3, risk_level="LOW", created_at=t2)

    res = client.get("/api/scans", headers=headers_a)
    assert res.status_code == 200
    body = res.get_json()
    items = body["data"]["items"]
    assert len(items) == 3

    # Newest first
    assert items[0]["id"] == id3
    assert items[0]["media_type"] == "video"
    assert items[0]["filename"] == "clip.mp4"
    assert items[0]["status"] == "COMPLETED"
    assert items[0]["result"]["prediction"] == "AUTHENTIC"
    assert items[0]["result"]["confidence"] == 0.3
    assert items[0]["result"]["risk_level"] == "LOW"

    assert items[1]["id"] == id2
    assert items[1]["media_type"] == "image"

    assert items[2]["id"] == id1
    assert items[2]["media_type"] == "text"


# ===========================================================================
# C. Pagination Navigation Tests
# ===========================================================================

def test_pagination_navigation(app, client, user_a, headers_a):
    """3. Verifies page and per_page pagination metadata across multiple pages."""
    for i in range(5):
        create_completed_scan(app, user_a["id"], media_type="text", filename=f"doc_{i}.txt")

    # Page 1 of 3 (2 items per page)
    res1 = client.get("/api/scans?page=1&per_page=2", headers=headers_a)
    assert res1.status_code == 200
    data1 = res1.get_json()["data"]
    assert len(data1["items"]) == 2
    assert data1["pagination"] == {
        "page": 1,
        "per_page": 2,
        "total_items": 5,
        "total_pages": 3,
        "has_next": True,
        "has_prev": False,
    }

    # Page 2 of 3
    res2 = client.get("/api/scans?page=2&per_page=2", headers=headers_a)
    assert res2.status_code == 200
    data2 = res2.get_json()["data"]
    assert len(data2["items"]) == 2
    assert data2["pagination"]["has_next"] is True
    assert data2["pagination"]["has_prev"] is True

    # Page 3 of 3 (1 item remaining)
    res3 = client.get("/api/scans?page=3&per_page=2", headers=headers_a)
    assert res3.status_code == 200
    data3 = res3.get_json()["data"]
    assert len(data3["items"]) == 1
    assert data3["pagination"]["has_next"] is False
    assert data3["pagination"]["has_prev"] is True


# ===========================================================================
# D. Maximum Page Size Boundary Tests
# ===========================================================================

def test_maximum_page_size_boundary(client, headers_a):
    """4. per_page=100 is accepted (200), per_page=101 is rejected with 400."""
    # 100 is allowed
    res_ok = client.get("/api/scans?per_page=100", headers=headers_a)
    assert res_ok.status_code == 200
    assert res_ok.get_json()["data"]["pagination"]["per_page"] == 100

    # 101 exceeds maximum
    res_err = client.get("/api/scans?per_page=101", headers=headers_a)
    assert res_err.status_code == 400
    assert res_err.get_json()["error_code"] == "INVALID_PER_PAGE"


# ===========================================================================
# E. Invalid Pagination Parameters Tests
# ===========================================================================

@pytest.mark.parametrize("param_str,expected_error", [
    ("page=0", "INVALID_PAGE"),
    ("page=-1", "INVALID_PAGE"),
    ("page=abc", "INVALID_PAGE"),
    ("per_page=0", "INVALID_PER_PAGE"),
    ("per_page=-5", "INVALID_PER_PAGE"),
    ("per_page=xyz", "INVALID_PER_PAGE"),
])
def test_invalid_pagination_parameters(client, headers_a, param_str, expected_error):
    """5. Rejects non-positive or non-integer page and per_page values with 400."""
    res = client.get(f"/api/scans?{param_str}", headers=headers_a)
    assert res.status_code == 400
    body = res.get_json()
    assert body["success"] is False
    assert body["error_code"] == expected_error


# ===========================================================================
# F. Media Type Filtering Tests
# ===========================================================================

def test_media_type_filtering(app, client, user_a, headers_a):
    """6. Filters scans by valid media_type ('text', 'image', 'video', 'audio') and rejects invalid."""
    create_completed_scan(app, user_a["id"], media_type="text", filename="note.txt")
    create_completed_scan(app, user_a["id"], media_type="image", filename="photo.png")
    create_completed_scan(app, user_a["id"], media_type="video", filename="movie.mp4")
    create_completed_scan(app, user_a["id"], media_type="audio", filename="voice.wav")

    # Filter image
    res_img = client.get("/api/scans?media_type=image", headers=headers_a)
    assert res_img.status_code == 200
    items_img = res_img.get_json()["data"]["items"]
    assert len(items_img) == 1
    assert items_img[0]["media_type"] == "image"

    # Filter video (case-insensitive)
    res_vid = client.get("/api/scans?media_type=VIDEO", headers=headers_a)
    assert res_vid.status_code == 200
    items_vid = res_vid.get_json()["data"]["items"]
    assert len(items_vid) == 1
    assert items_vid[0]["media_type"] == "video"

    # Filter audio
    res_aud = client.get("/api/scans?media_type=audio", headers=headers_a)
    assert res_aud.status_code == 200
    assert len(res_aud.get_json()["data"]["items"]) == 1

    # Filter text
    res_txt = client.get("/api/scans?media_type=text", headers=headers_a)
    assert res_txt.status_code == 200
    assert len(res_txt.get_json()["data"]["items"]) == 1

    # Reject unsupported media_type
    res_invalid = client.get("/api/scans?media_type=hologram", headers=headers_a)
    assert res_invalid.status_code == 400
    assert res_invalid.get_json()["error_code"] == "INVALID_MEDIA_TYPE"


# ===========================================================================
# G. Multi-User Isolation in Scan Listing
# ===========================================================================

def test_multi_user_isolation(app, client, user_a, user_b, headers_a, headers_b):
    """7. User A and User B lists are strictly isolated with no cross-user scans."""
    create_completed_scan(app, user_a["id"], media_type="text", filename="alice_doc.txt")
    create_completed_scan(app, user_a["id"], media_type="image", filename="alice_face.jpg")
    create_completed_scan(app, user_b["id"], media_type="video", filename="bob_clip.mp4")

    # User A sees only 2 scans
    res_a = client.get("/api/scans", headers=headers_a)
    assert res_a.status_code == 200
    items_a = res_a.get_json()["data"]["items"]
    assert len(items_a) == 2
    assert all(it["filename"] in ("alice_doc.txt", "alice_face.jpg") for it in items_a)

    # User B sees only 1 scan
    res_b = client.get("/api/scans", headers=headers_b)
    assert res_b.status_code == 200
    items_b = res_b.get_json()["data"]["items"]
    assert len(items_b) == 1
    assert items_b[0]["filename"] == "bob_clip.mp4"


# ===========================================================================
# H. IDOR Prevention Tests
# ===========================================================================

def test_idor_prevention_cross_user_access_returns_404(app, client, user_a, user_b, headers_a):
    """8. Requesting an existing scan owned by another user returns HTTP 404 SCAN_NOT_FOUND (not 403)."""
    # Create scan owned by Bob
    bob_scan_id = create_completed_scan(app, user_b["id"], media_type="video", filename="bob_secret.mp4")

    # Alice attempts to access Bob's scan ID
    res = client.get(f"/api/scans/{bob_scan_id}", headers=headers_a)
    assert res.status_code == 404
    body = res.get_json()
    assert body["success"] is False
    assert body["message"] == "Scan not found."
    assert body["error_code"] == "SCAN_NOT_FOUND"
    assert body["data"] is None


# ===========================================================================
# I. Scan Detail Retrieval Success
# ===========================================================================

def test_scan_detail_success(app, client, user_a, headers_a):
    """9. Valid owned scan returns HTTP 200 with full forensic detail and result_data."""
    full_result_data = {
        "is_deepfake": True,
        "confidence_score": 0.89,
        "manipulation_type": "Face-Swap",
        "metrics": {"width": 1920, "height": 1080},
        "heatmap_preview": "data:image/jpeg;base64,sample_heatmap_data"
    }

    scan_id = create_completed_scan(
        app,
        user_a["id"],
        media_type="image",
        filename="evidence.jpg",
        prediction="DEEPFAKE",
        confidence=0.89,
        risk_level="HIGH",
        result_data=full_result_data,
    )

    res = client.get(f"/api/scans/{scan_id}", headers=headers_a)
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assert body["message"] == "Scan details retrieved successfully."

    data = body["data"]
    assert data["id"] == scan_id
    assert data["user_id"] == user_a["id"]
    assert data["media_type"] == "image"
    assert data["filename"] == "evidence.jpg"
    assert data["status"] == "COMPLETED"
    assert data["created_at"] is not None
    assert data["completed_at"] is not None

    result = data["result"]
    assert result is not None
    assert result["prediction"] == "DEEPFAKE"
    assert result["confidence"] == 0.89
    assert result["risk_level"] == "HIGH"
    assert result["result_data"] == full_result_data


# ===========================================================================
# J. Missing Scan Detail Tests
# ===========================================================================

def test_missing_scan_detail_returns_404(client, headers_a):
    """10. Requesting a completely non-existent scan ID returns HTTP 404 SCAN_NOT_FOUND."""
    res = client.get("/api/scans/999999", headers=headers_a)
    assert res.status_code == 404
    body = res.get_json()
    assert body["success"] is False
    assert body["error_code"] == "SCAN_NOT_FOUND"


# ===========================================================================
# K. Authentication Enforcement Tests
# ===========================================================================

def test_unauthenticated_requests_fail(client, app, user_a):
    """11. Missing, invalid, or expired JWT tokens return HTTP 401."""
    scan_id = create_completed_scan(app, user_a["id"], media_type="text")

    # Missing header on list
    res_list_no_auth = client.get("/api/scans")
    assert res_list_no_auth.status_code == 401
    assert res_list_no_auth.get_json()["error_code"] == "AUTHENTICATION_REQUIRED"

    # Missing header on detail
    res_det_no_auth = client.get(f"/api/scans/{scan_id}")
    assert res_det_no_auth.status_code == 401
    assert res_det_no_auth.get_json()["error_code"] == "AUTHENTICATION_REQUIRED"

    # Invalid token
    res_invalid = client.get("/api/scans", headers={"Authorization": "Bearer not.a.real.token"})
    assert res_invalid.status_code == 401
    assert res_invalid.get_json()["error_code"] == "INVALID_TOKEN"

    # Expired token
    with app.app_context():
        secret_key = app.config.get("JWT_SECRET_KEY")
        expired_payload = {
            "sub": str(user_a["id"]),
            "iat": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
            "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
        }
        expired_token = jwt.encode(expired_payload, secret_key, algorithm="HS256")

    res_expired = client.get("/api/scans", headers={"Authorization": f"Bearer {expired_token}"})
    assert res_expired.status_code == 401
    assert res_expired.get_json()["error_code"] == "TOKEN_EXPIRED"


# ===========================================================================
# L. List Payload Discipline Tests
# ===========================================================================

def test_list_payload_discipline(app, client, user_a, headers_a):
    """12. List response excludes heavy result_data, user object, password_hash, and raw media."""
    heavy_data = {
        "is_deepfake": True,
        "heatmap_preview": "data:image/jpeg;base64," + "A" * 5000  # large payload
    }
    create_completed_scan(app, user_a["id"], media_type="image", filename="heavy.jpg", result_data=heavy_data)

    res = client.get("/api/scans", headers=headers_a)
    assert res.status_code == 200
    item = res.get_json()["data"]["items"][0]

    # Required summary fields present
    assert "prediction" in item["result"]
    assert "confidence" in item["result"]
    assert "risk_level" in item["result"]

    # Heavy payload strictly omitted
    assert "result_data" not in item["result"]
    assert "heatmap_preview" not in str(res.get_json())

    # User entity and credentials strictly omitted
    assert "password_hash" not in str(res.get_json())
    assert "user" not in item


# ===========================================================================
# M. Detail Payload Discipline Tests
# ===========================================================================

def test_detail_payload_discipline(app, client, user_a, headers_a):
    """13. Detail response contains result_data, but strictly excludes password_hash and user entity."""
    scan_id = create_completed_scan(
        app,
        user_a["id"],
        media_type="text",
        result_data={"breakdown": [{"sentence": "Hello world", "score": 0.1}]},
    )

    res = client.get(f"/api/scans/{scan_id}", headers=headers_a)
    assert res.status_code == 200
    data = res.get_json()["data"]

    # result_data is present
    assert "result_data" in data["result"]
    assert "breakdown" in data["result"]["result_data"]

    # Sensitive user entity and password hash are absent
    assert "password_hash" not in str(res.get_json())
    assert "user" not in data


# ===========================================================================
# N. Deterministic Ordering Tests
# ===========================================================================

def test_deterministic_ordering_tiebreaker(app, client, user_a, headers_a):
    """14. Scans with identical created_at timestamps are ordered by id DESC as tiebreaker."""
    same_time = datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc)
    id1 = create_completed_scan(app, user_a["id"], filename="first.txt", created_at=same_time)
    id2 = create_completed_scan(app, user_a["id"], filename="second.txt", created_at=same_time)
    id3 = create_completed_scan(app, user_a["id"], filename="third.txt", created_at=same_time)

    res = client.get("/api/scans", headers=headers_a)
    assert res.status_code == 200
    items = res.get_json()["data"]["items"]

    # Higher ID appears before lower ID
    ids = [it["id"] for it in items]
    assert ids == [id3, id2, id1]


# ===========================================================================
# O. Database Failure Handling Tests
# ===========================================================================

def test_database_failure_returns_sanitized_500(client, headers_a):
    """15. Database exceptions in list and detail endpoints return sanitized HTTP 500 without leaking SQL."""
    # Failure on list endpoint
    with patch("backend.services.scan_service.ScanService.get_user_scans") as mock_get_scans:
        mock_get_scans.side_effect = ScanDatabaseError("OperationalError: disk I/O failure")
        res_list = client.get("/api/scans", headers=headers_a)
        assert res_list.status_code == 500
        body_list = res_list.get_json()
        assert body_list["success"] is False
        assert body_list["error_code"] == "INTERNAL_SERVER_ERROR"
        assert "disk I/O failure" not in body_list["message"]
        assert "OperationalError" not in body_list["message"]

    # Failure on detail endpoint
    with patch("backend.services.scan_service.ScanService.get_user_scan_by_id") as mock_get_scan:
        mock_get_scan.side_effect = ScanDatabaseError("OperationalError: table locked")
        res_det = client.get("/api/scans/1", headers=headers_a)
        assert res_det.status_code == 500
        body_det = res_det.get_json()
        assert body_det["success"] is False
        assert body_det["error_code"] == "INTERNAL_SERVER_ERROR"
        assert "table locked" not in body_det["message"]
