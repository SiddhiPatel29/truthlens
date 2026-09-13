"""
Comprehensive Rate Limiting & DoS Protection Tests (SEC-08).

Validates:
1. Production default limit definitions and storage contract.
2. Unauthenticated endpoint rate limiting keyed by client IP (Login, Register, Abuse).
3. Authenticated endpoint rate limiting keyed by authenticated user ID (Video, Audio, Image, Text, Scans, Me).
4. Error response contract (HTTP 429, RATE_LIMIT_EXCEEDED, standard envelope, Retry-After header).
5. Rate limit headers (Retry-After, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset) and CORS exposure.
6. Execution ordering: auth verification -> rate limiter -> expensive decoding / persistence.
   Over-limit requests must NOT create Scan/ScanResult records or call scrypt password hashing.
7. User isolation: User A exhausting a quota does NOT throttle User B.
8. IP isolation: IP A exhausting a quota does NOT throttle IP B.
9. Independent endpoint quotas: exhausting one route does not affect quotas on others.
10. Health check exemption (/api/health remains unthrottled).
11. Security invariants: IP spoofing immunity via X-Forwarded-For, IP hopping immunity for authenticated users.
"""
import io
import time
from unittest.mock import patch
import pytest
from werkzeug.security import generate_password_hash
from backend.app import create_app
from backend.database.db import db as _db
from backend.database.models import User, Scan, ScanResult, AbuseReport
from backend.services.auth_service import AuthService
from backend.utils.limiter import (
    limiter,
    DEFAULT_LIMIT_AUTH_LOGIN,
    DEFAULT_LIMIT_AUTH_REGISTER,
    DEFAULT_LIMIT_REPORT_ABUSE,
    DEFAULT_LIMIT_DETECT_VIDEO,
    DEFAULT_LIMIT_DETECT_AUDIO,
    DEFAULT_LIMIT_DETECT_IMAGE,
    DEFAULT_LIMIT_DETECT_TEXT,
    DEFAULT_LIMIT_SCANS,
    DEFAULT_LIMIT_AUTH_ME,
)
from tests.conftest import TestConfig


class RateLimitFastTestConfig(TestConfig):
    """
    Dedicated test configuration enabling rate limiting with fast, deterministic
    limits (2 per second) to test boundaries and behavior without slow timeouts.
    """
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_STRATEGY = "fixed-window"

    # Fast deterministic limits for isolated tests
    RATELIMIT_AUTH_LOGIN = "2 per second"
    RATELIMIT_AUTH_REGISTER = "2 per second"
    RATELIMIT_REPORT_ABUSE = "2 per second"
    RATELIMIT_DETECT_VIDEO = "2 per second"
    RATELIMIT_DETECT_AUDIO = "2 per second"
    RATELIMIT_DETECT_IMAGE = "2 per second"
    RATELIMIT_DETECT_TEXT = "2 per second"
    RATELIMIT_SCANS = "2 per second"
    RATELIMIT_AUTH_ME = "2 per second"


@pytest.fixture
def rl_app():
    """Provides an isolated Flask application instance with active rate limiting."""
    app = create_app(RateLimitFastTestConfig)
    with app.app_context():
        _db.create_all()
        limiter.reset()
        yield app
        limiter.reset()
        _db.session.rollback()
        _db.session.query(AbuseReport).delete()
        _db.session.query(ScanResult).delete()
        _db.session.query(Scan).delete()
        _db.session.query(User).delete()
        _db.session.commit()
        _db.session.remove()


@pytest.fixture
def rl_client(rl_app):
    """Provides a test client with rate limiting enabled."""
    return rl_app.test_client()


@pytest.fixture
def user_a(rl_app):
    """Creates first active test user."""
    password = "UserAPassword123!"
    with rl_app.app_context():
        user = User(
            name="User Alpha",
            email="user.alpha@example.com",
            password_hash=generate_password_hash(password),
            is_active=True,
        )
        _db.session.add(user)
        _db.session.commit()
        user_id = user.id
    return {"id": user_id, "name": "User Alpha", "email": "user.alpha@example.com", "password": password}


@pytest.fixture
def user_b(rl_app):
    """Creates second active test user for user isolation tests."""
    password = "UserBPassword123!"
    with rl_app.app_context():
        user = User(
            name="User Beta",
            email="user.beta@example.com",
            password_hash=generate_password_hash(password),
            is_active=True,
        )
        _db.session.add(user)
        _db.session.commit()
        user_id = user.id
    return {"id": user_id, "name": "User Beta", "email": "user.beta@example.com", "password": password}


@pytest.fixture
def inactive_user(rl_app):
    """Creates an inactive test user for auth validation tests."""
    password = "InactivePassword123!"
    with rl_app.app_context():
        user = User(
            name="Inactive User",
            email="inactive@example.com",
            password_hash=generate_password_hash(password),
            is_active=False,
        )
        _db.session.add(user)
        _db.session.commit()
        user_id = user.id
    return {"id": user_id, "email": "inactive@example.com", "password": password}


def get_token_for(client, user_dict):
    """Helper to obtain a signed JWT token via login route."""
    res = client.post(
        "/api/auth/login",
        json={"email": user_dict["email"], "password": user_dict["password"]},
    )
    assert res.status_code == 200
    return res.get_json()["data"]["access_token"]


# ==============================================================================
# SECTION 1: SPECIFICATION & CONFIGURATION VERIFICATION
# ==============================================================================

def test_production_default_limits_specification():
    """Verify that all production limit constants strictly match SEC-08 specification."""
    assert DEFAULT_LIMIT_AUTH_LOGIN == "5 per minute; 20 per hour"
    assert DEFAULT_LIMIT_AUTH_REGISTER == "3 per minute; 10 per hour"
    assert DEFAULT_LIMIT_REPORT_ABUSE == "10 per minute; 60 per hour"
    assert DEFAULT_LIMIT_DETECT_VIDEO == "5 per minute; 30 per hour"
    assert DEFAULT_LIMIT_DETECT_AUDIO == "10 per minute; 60 per hour"
    assert DEFAULT_LIMIT_DETECT_IMAGE == "15 per minute; 100 per hour"
    assert DEFAULT_LIMIT_DETECT_TEXT == "30 per minute; 200 per hour"
    assert DEFAULT_LIMIT_SCANS == "60 per minute"
    assert DEFAULT_LIMIT_AUTH_ME == "60 per minute"


# ==============================================================================
# SECTION 2: UNAUTHENTICATED ENDPOINTS (LOGIN, REGISTER, ABUSE)
# ==============================================================================

class TestLoginRateLimiting:
    """Test suite for POST /api/auth/login rate limiting."""

    def test_login_below_limit_and_over_limit_boundary(self, rl_client, user_a):
        """
        Verify:
        - Requests below limit succeed (200 OK).
        - Request exceeding limit returns HTTP 429.
        - Exact JSON response envelope and error_code 'RATE_LIMIT_EXCEEDED'.
        - Retry-After and X-RateLimit-* headers are emitted.
        """
        # Request 1 (below limit)
        res1 = rl_client.post(
            "/api/auth/login",
            json={"email": user_a["email"], "password": user_a["password"]},
        )
        assert res1.status_code == 200
        assert res1.get_json()["success"] is True

        # Request 2 (boundary)
        res2 = rl_client.post(
            "/api/auth/login",
            json={"email": user_a["email"], "password": user_a["password"]},
        )
        assert res2.status_code == 200
        assert res2.get_json()["success"] is True

        # Request 3 (exceeded)
        res3 = rl_client.post(
            "/api/auth/login",
            json={"email": user_a["email"], "password": user_a["password"]},
        )
        assert res3.status_code == 429
        data3 = res3.get_json()
        assert data3["success"] is False
        assert data3["message"] == "Rate limit exceeded. Please try again later."
        assert data3["data"] is None
        assert data3["error_code"] == "RATE_LIMIT_EXCEEDED"

        # Headers verification
        assert "Retry-After" in res3.headers
        assert "X-RateLimit-Limit" in res3.headers
        assert "X-RateLimit-Remaining" in res3.headers
        assert "X-RateLimit-Reset" in res3.headers
        assert res3.headers["X-RateLimit-Remaining"] == "0"

    def test_login_over_limit_does_not_execute_scrypt(self, rl_client, user_a):
        """
        Verify that rate limiting triggers before expensive AuthService work.
        An over-limit request must NOT call password verification / scrypt.
        """
        with patch.object(AuthService, "login_user", wraps=AuthService.login_user) as mock_login:
            # Request 1
            rl_client.post(
                "/api/auth/login",
                json={"email": user_a["email"], "password": user_a["password"]},
            )
            assert mock_login.call_count == 1

            # Request 2
            rl_client.post(
                "/api/auth/login",
                json={"email": user_a["email"], "password": user_a["password"]},
            )
            assert mock_login.call_count == 2

            # Request 3 (throttled by limiter)
            res3 = rl_client.post(
                "/api/auth/login",
                json={"email": user_a["email"], "password": user_a["password"]},
            )
            assert res3.status_code == 429
            # mock_login MUST NOT be called for the 3rd request!
            assert mock_login.call_count == 2


class TestRegistrationRateLimiting:
    """Test suite for POST /api/auth/register rate limiting."""

    def test_register_below_limit_and_over_limit(self, rl_client, rl_app):
        """
        Verify registration rate limiting and ensure that over-limit requests
        do not create User database records.
        """
        # Request 1
        res1 = rl_client.post(
            "/api/auth/register",
            json={"name": "Reg User 1", "email": "reg1@example.com", "password": "StrongPassword123!"},
        )
        assert res1.status_code == 201
        assert res1.get_json()["success"] is True

        # Request 2
        res2 = rl_client.post(
            "/api/auth/register",
            json={"name": "Reg User 2", "email": "reg2@example.com", "password": "StrongPassword123!"},
        )
        assert res2.status_code == 201

        # Request 3 (over limit)
        res3 = rl_client.post(
            "/api/auth/register",
            json={"name": "Reg User 3", "email": "reg3@example.com", "password": "StrongPassword123!"},
        )
        assert res3.status_code == 429
        assert res3.get_json()["error_code"] == "RATE_LIMIT_EXCEEDED"

        # Verify that reg3 was NEVER created in the database
        with rl_app.app_context():
            user3 = _db.session.query(User).filter_by(email="reg3@example.com").first()
            assert user3 is None


class TestAbuseReportRateLimiting:
    """Test suite for POST /api/report/abuse rate limiting."""

    def test_abuse_report_rate_limiting(self, rl_client):
        """Verify client IP rate limiting on the abuse dispatcher endpoint."""
        payload = {
            "platform": "youtube",
            "target_url": "https://youtube.com/watch?v=sample123",
            "category": "Synthetic Impersonation",
            "confidence_score": 0.95,
            "analyst_notes": "Deepfake audio detected.",
        }

        res1 = rl_client.post("/api/report/abuse", json=payload)
        assert res1.status_code == 201

        res2 = rl_client.post("/api/report/abuse", json=payload)
        assert res2.status_code == 201

        res3 = rl_client.post("/api/report/abuse", json=payload)
        assert res3.status_code == 429
        assert res3.get_json()["error_code"] == "RATE_LIMIT_EXCEEDED"


# ==============================================================================
# SECTION 3: AUTHENTICATED ENDPOINTS & ZERO-PERSISTENCE GUARANTEE
# ==============================================================================

class TestDetectionRateLimiting:
    """Test suite for detection endpoints: text, video, audio, image."""

    def test_text_detection_rate_limit_and_zero_scan_creation(self, rl_client, rl_app, user_a):
        """
        Verify:
        - Authenticated POST /api/detect/text rate limits after quota is reached.
        - Rate-limited requests create ZERO Scan and ZERO ScanResult records.
        """
        token = get_token_for(rl_client, user_a)
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"text": "This is a valid long text sample for testing AI detection models in TruthLens."}

        # Clear existing scans
        with rl_app.app_context():
            _db.session.query(ScanResult).delete()
            _db.session.query(Scan).delete()
            _db.session.commit()

        # Request 1 (success)
        res1 = rl_client.post("/api/detect/text", json=payload, headers=headers)
        assert res1.status_code == 200

        # Request 2 (success)
        res2 = rl_client.post("/api/detect/text", json=payload, headers=headers)
        assert res2.status_code == 200

        with rl_app.app_context():
            scans_before = _db.session.query(Scan).filter_by(user_id=user_a["id"]).count()
            results_before = _db.session.query(ScanResult).count()
            assert scans_before == 2
            assert results_before == 2

        # Request 3 (rate limited)
        res3 = rl_client.post("/api/detect/text", json=payload, headers=headers)
        assert res3.status_code == 429
        assert res3.get_json()["error_code"] == "RATE_LIMIT_EXCEEDED"

        # Rate-limited request MUST NOT create any Scan or ScanResult records
        with rl_app.app_context():
            scans_after = _db.session.query(Scan).filter_by(user_id=user_a["id"]).count()
            results_after = _db.session.query(ScanResult).count()
            assert scans_after == scans_before
            assert results_after == results_before

    def test_video_detection_rate_limit_and_zero_scan_creation(self, rl_client, rl_app, user_a, real_video_path):
        """
        Verify:
        - Authenticated POST /api/detect/video rate limits after quota is reached.
        - Video decoding and Scan persistence are skipped on 429.
        """
        token = get_token_for(rl_client, user_a)
        headers = {"Authorization": f"Bearer {token}"}

        with open(real_video_path, "rb") as f:
            video_bytes = f.read()

        # Clear existing scans
        with rl_app.app_context():
            _db.session.query(ScanResult).delete()
            _db.session.query(Scan).delete()
            _db.session.commit()

        # Request 1
        res1 = rl_client.post(
            "/api/detect/video",
            data={"video": (io.BytesIO(video_bytes), "test.mp4")},
            headers=headers,
            content_type="multipart/form-data",
        )
        assert res1.status_code == 200

        # Request 2
        res2 = rl_client.post(
            "/api/detect/video",
            data={"video": (io.BytesIO(video_bytes), "test.mp4")},
            headers=headers,
            content_type="multipart/form-data",
        )
        assert res2.status_code == 200

        with rl_app.app_context():
            scans_before = _db.session.query(Scan).filter_by(user_id=user_a["id"]).count()
            assert scans_before == 2

        # Request 3 (throttled)
        res3 = rl_client.post(
            "/api/detect/video",
            data={"video": (io.BytesIO(video_bytes), "test.mp4")},
            headers=headers,
            content_type="multipart/form-data",
        )
        assert res3.status_code == 429
        assert res3.get_json()["error_code"] == "RATE_LIMIT_EXCEEDED"

        with rl_app.app_context():
            scans_after = _db.session.query(Scan).filter_by(user_id=user_a["id"]).count()
            assert scans_after == scans_before

    def test_image_and_audio_routes_rate_limited(self, rl_client, user_a, real_image_path, real_audio_path):
        """Verify that image and audio routes enforce rate limiting."""
        token = get_token_for(rl_client, user_a)
        headers = {"Authorization": f"Bearer {token}"}

        # Test Image
        with open(real_image_path, "rb") as f:
            img_bytes = f.read()

        res1 = rl_client.post(
            "/api/detect/image",
            data={"image": (io.BytesIO(img_bytes), "test.jpg")},
            headers=headers,
            content_type="multipart/form-data",
        )
        assert res1.status_code == 200
        res2 = rl_client.post(
            "/api/detect/image",
            data={"image": (io.BytesIO(img_bytes), "test.jpg")},
            headers=headers,
            content_type="multipart/form-data",
        )
        assert res2.status_code == 200
        res3 = rl_client.post(
            "/api/detect/image",
            data={"image": (io.BytesIO(img_bytes), "test.jpg")},
            headers=headers,
            content_type="multipart/form-data",
        )
        assert res3.status_code == 429

        # Test Audio
        with open(real_audio_path, "rb") as f:
            audio_bytes = f.read()

        res1_a = rl_client.post(
            "/api/detect/audio",
            data={"audio": (io.BytesIO(audio_bytes), "test.wav")},
            headers=headers,
            content_type="multipart/form-data",
        )
        assert res1_a.status_code == 200
        res2_a = rl_client.post(
            "/api/detect/audio",
            data={"audio": (io.BytesIO(audio_bytes), "test.wav")},
            headers=headers,
            content_type="multipart/form-data",
        )
        assert res2_a.status_code == 200
        res3_a = rl_client.post(
            "/api/detect/audio",
            data={"audio": (io.BytesIO(audio_bytes), "test.wav")},
            headers=headers,
            content_type="multipart/form-data",
        )
        assert res3_a.status_code == 429


class TestScanHistoryAndAuthMeRateLimiting:
    """Test suite for GET /api/scans, GET /api/scans/<id>, and GET /api/auth/me."""

    def test_auth_me_rate_limiting(self, rl_client, user_a):
        """Verify GET /api/auth/me enforces user ID rate limiting."""
        token = get_token_for(rl_client, user_a)
        headers = {"Authorization": f"Bearer {token}"}

        res1 = rl_client.get("/api/auth/me", headers=headers)
        assert res1.status_code == 200

        res2 = rl_client.get("/api/auth/me", headers=headers)
        assert res2.status_code == 200

        res3 = rl_client.get("/api/auth/me", headers=headers)
        assert res3.status_code == 429
        assert res3.get_json()["error_code"] == "RATE_LIMIT_EXCEEDED"

    def test_scans_list_and_detail_rate_limiting(self, rl_client, user_a):
        """Verify GET /api/scans enforces user ID rate limiting."""
        token = get_token_for(rl_client, user_a)
        headers = {"Authorization": f"Bearer {token}"}

        res1 = rl_client.get("/api/scans", headers=headers)
        assert res1.status_code == 200

        res2 = rl_client.get("/api/scans", headers=headers)
        assert res2.status_code == 200

        res3 = rl_client.get("/api/scans", headers=headers)
        assert res3.status_code == 429
        assert res3.get_json()["error_code"] == "RATE_LIMIT_EXCEEDED"


# ==============================================================================
# SECTION 4: ISOLATION & SECURITY GUARANTEES
# ==============================================================================

class TestUserAndIPIsolation:
    """Test suite for user isolation, IP isolation, and anti-bypass guarantees."""

    def test_user_isolation_user_a_exhaustion_does_not_throttle_user_b(self, rl_client, user_a, user_b):
        """
        Verify:
        User A exhausting their quota does NOT affect User B (even on the same IP).
        """
        token_a = get_token_for(rl_client, user_a)
        token_b = get_token_for(rl_client, user_b)

        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User A makes 2 requests
        rl_client.get("/api/auth/me", headers=headers_a)
        rl_client.get("/api/auth/me", headers=headers_a)

        # User A request 3 is throttled
        res_a3 = rl_client.get("/api/auth/me", headers=headers_a)
        assert res_a3.status_code == 429

        # User B request 1 MUST succeed
        res_b1 = rl_client.get("/api/auth/me", headers=headers_b)
        assert res_b1.status_code == 200
        assert res_b1.get_json()["data"]["user_id"] == user_b["id"]

    def test_ip_isolation_ip_a_exhaustion_does_not_throttle_ip_b(self, rl_client, user_a):
        """
        Verify:
        Client at IP A exhausting login attempts does NOT throttle Client at IP B.
        """
        ip_a = "192.168.1.10"
        ip_b = "192.168.1.20"

        # IP A makes 2 requests
        rl_client.post(
            "/api/auth/login",
            json={"email": user_a["email"], "password": user_a["password"]},
            environ_base={"REMOTE_ADDR": ip_a},
        )
        rl_client.post(
            "/api/auth/login",
            json={"email": user_a["email"], "password": user_a["password"]},
            environ_base={"REMOTE_ADDR": ip_a},
        )

        # IP A request 3 is throttled
        res_a3 = rl_client.post(
            "/api/auth/login",
            json={"email": user_a["email"], "password": user_a["password"]},
            environ_base={"REMOTE_ADDR": ip_a},
        )
        assert res_a3.status_code == 429

        # IP B request 1 MUST succeed
        res_b1 = rl_client.post(
            "/api/auth/login",
            json={"email": user_a["email"], "password": user_a["password"]},
            environ_base={"REMOTE_ADDR": ip_b},
        )
        assert res_b1.status_code == 200

    def test_user_cannot_bypass_rate_limit_by_hopping_ips(self, rl_client, user_a):
        """
        Verify that an authenticated user cannot bypass rate limits by hopping IPs,
        because authenticated key is based on user ID.
        """
        token = get_token_for(rl_client, user_a)
        headers = {"Authorization": f"Bearer {token}"}

        # IP 1
        res1 = rl_client.get("/api/auth/me", headers=headers, environ_base={"REMOTE_ADDR": "10.0.0.1"})
        assert res1.status_code == 200

        # IP 2
        res2 = rl_client.get("/api/auth/me", headers=headers, environ_base={"REMOTE_ADDR": "10.0.0.2"})
        assert res2.status_code == 200

        # IP 3 (same user ID, quota exceeded)
        res3 = rl_client.get("/api/auth/me", headers=headers, environ_base={"REMOTE_ADDR": "10.0.0.3"})
        assert res3.status_code == 429
        assert res3.get_json()["error_code"] == "RATE_LIMIT_EXCEEDED"

    def test_unauthenticated_ip_spoofing_via_x_forwarded_for_is_ignored(self, rl_client, user_a):
        """
        Verify that unauthenticated rate limiting ignores user-controlled X-Forwarded-For
        headers and relies strictly on direct socket remote_addr.
        """
        client_ip = "192.168.1.50"

        # Request 1 with spoofed header
        rl_client.post(
            "/api/auth/login",
            json={"email": user_a["email"], "password": user_a["password"]},
            headers={"X-Forwarded-For": "1.1.1.1"},
            environ_base={"REMOTE_ADDR": client_ip},
        )
        # Request 2 with different spoofed header
        rl_client.post(
            "/api/auth/login",
            json={"email": user_a["email"], "password": user_a["password"]},
            headers={"X-Forwarded-For": "2.2.2.2"},
            environ_base={"REMOTE_ADDR": client_ip},
        )
        # Request 3 should be blocked because real remote_addr is identical
        res3 = rl_client.post(
            "/api/auth/login",
            json={"email": user_a["email"], "password": user_a["password"]},
            headers={"X-Forwarded-For": "3.3.3.3"},
            environ_base={"REMOTE_ADDR": client_ip},
        )
        assert res3.status_code == 429


class TestEndpointIndependence:
    """Test suite for independent endpoint quotas."""

    def test_exhausting_one_endpoint_does_not_affect_another(self, rl_client, user_a):
        """
        Verify that exhausting quota on one route does not throttle another route:
        - Exhausting /detect/text does not exhaust /auth/me.
        - Exhausting /auth/login does not exhaust /auth/register.
        """
        token = get_token_for(rl_client, user_a)
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"text": "A valid investigative statement crafted for detection verification."}

        # Exhaust text detection
        rl_client.post("/api/detect/text", json=payload, headers=headers)
        rl_client.post("/api/detect/text", json=payload, headers=headers)
        res_text3 = rl_client.post("/api/detect/text", json=payload, headers=headers)
        assert res_text3.status_code == 429

        # /auth/me should STILL be available for this user
        res_me = rl_client.get("/api/auth/me", headers=headers)
        assert res_me.status_code == 200

        # Reset limiter for unauthenticated tests
        limiter.reset()

        # Exhaust login for IP
        rl_client.post("/api/auth/login", json={"email": user_a["email"], "password": user_a["password"]})
        rl_client.post("/api/auth/login", json={"email": user_a["email"], "password": user_a["password"]})
        res_log3 = rl_client.post("/api/auth/login", json={"email": user_a["email"], "password": user_a["password"]})
        assert res_log3.status_code == 429

        # /auth/register should STILL be available for this IP
        res_reg = rl_client.post(
            "/api/auth/register",
            json={"name": "Independent Reg", "email": "indep@example.com", "password": "StrongPassword123!"},
        )
        assert res_reg.status_code == 201

    def test_exhausting_video_does_not_exhaust_text(self, rl_client, user_a, real_video_path):
        """Verify exhausting /detect/video does not exhaust /detect/text."""
        token = get_token_for(rl_client, user_a)
        headers = {"Authorization": f"Bearer {token}"}

        with open(real_video_path, "rb") as f:
            video_bytes = f.read()

        # Exhaust video (2 requests)
        for _ in range(2):
            rl_client.post(
                "/api/detect/video",
                data={"video": (io.BytesIO(video_bytes), "test.mp4")},
                headers=headers,
                content_type="multipart/form-data",
            )
        res_video3 = rl_client.post(
            "/api/detect/video",
            data={"video": (io.BytesIO(video_bytes), "test.mp4")},
            headers=headers,
            content_type="multipart/form-data",
        )
        assert res_video3.status_code == 429

        # Text endpoint should still succeed
        res_text = rl_client.post(
            "/api/detect/text",
            json={"text": "A valid investigative statement crafted for detection verification."},
            headers=headers,
        )
        assert res_text.status_code == 200

    def test_exhausting_image_does_not_exhaust_video(self, rl_client, user_a, real_image_path, real_video_path):
        """Verify exhausting /detect/image does not exhaust /detect/video."""
        token = get_token_for(rl_client, user_a)
        headers = {"Authorization": f"Bearer {token}"}

        with open(real_image_path, "rb") as f:
            img_bytes = f.read()

        # Exhaust image (2 requests)
        for _ in range(2):
            rl_client.post(
                "/api/detect/image",
                data={"image": (io.BytesIO(img_bytes), "test.jpg")},
                headers=headers,
                content_type="multipart/form-data",
            )
        res_img3 = rl_client.post(
            "/api/detect/image",
            data={"image": (io.BytesIO(img_bytes), "test.jpg")},
            headers=headers,
            content_type="multipart/form-data",
        )
        assert res_img3.status_code == 429

        # Video endpoint should still succeed
        with open(real_video_path, "rb") as f:
            video_bytes = f.read()

        res_video = rl_client.post(
            "/api/detect/video",
            data={"video": (io.BytesIO(video_bytes), "test.mp4")},
            headers=headers,
            content_type="multipart/form-data",
        )
        assert res_video.status_code == 200


class TestHealthCheckExemption:
    """Test suite for /api/health rate limit exemption."""

    def test_health_check_is_exempt(self, rl_client):
        """Verify that /api/health can be queried repeatedly without rate limiting."""
        for _ in range(10):
            res = rl_client.get("/api/health")
            assert res.status_code == 200
            assert res.get_json()["data"]["status"] == "OPERATIONAL"


# ==============================================================================
# SECTION 5: AUTHENTICATION PRECEDENCE & ERROR HANDLING
# ==============================================================================

class TestAuthPrecedenceAndErrorHandling:
    """Test suite for interaction between @require_auth and rate limiting."""

    def test_unauthenticated_request_rejected_without_consuming_user_quota(self, rl_client, user_a):
        """
        Verify:
        1. Missing token returns 401 AUTHENTICATION_REQUIRED.
        2. Invalid token returns 401 INVALID_TOKEN.
        3. Neither request consumes the authenticated user's rate limit quota.
        """
        token = get_token_for(rl_client, user_a)
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Missing token
        res_no_auth = rl_client.get("/api/auth/me")
        assert res_no_auth.status_code == 401
        assert res_no_auth.get_json()["error_code"] == "AUTHENTICATION_REQUIRED"

        # 2. Invalid token
        res_bad_auth = rl_client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.payload"})
        assert res_bad_auth.status_code == 401
        assert res_bad_auth.get_json()["error_code"] == "INVALID_TOKEN"

        # 3. Authenticated requests should still have full quota (2 requests succeed)
        res1 = rl_client.get("/api/auth/me", headers=headers)
        assert res1.status_code == 200

        res2 = rl_client.get("/api/auth/me", headers=headers)
        assert res2.status_code == 200

        # 4. Third authenticated request exceeds limit
        res3 = rl_client.get("/api/auth/me", headers=headers)
        assert res3.status_code == 429

    def test_inactive_user_token_rejected_before_rate_limit(self, rl_app, rl_client, inactive_user):
        """
        Verify that inactive users are rejected by @require_auth with 401 INVALID_TOKEN
        before reaching the rate limiter.
        """
        import jwt
        now = int(time.time())
        payload = {
            "sub": str(inactive_user["id"]),
            "iat": now,
            "exp": now + 3600,
        }
        token = jwt.encode(payload, rl_app.config["JWT_SECRET_KEY"], algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}

        res = rl_client.get("/api/auth/me", headers=headers)
        assert res.status_code == 401
        assert res.get_json()["error_code"] == "INVALID_TOKEN"


# ==============================================================================
# SECTION 6: CORS EXPOSED HEADERS
# ==============================================================================

class TestCORSRateLimitHeaders:
    """Test suite verifying CORS exposure of rate limit headers."""

    def test_cors_exposes_rate_limit_headers(self, rl_client, user_a):
        """
        Verify that CORS configuration exposes rate limit headers:
        Retry-After, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
        both on successful requests and on 429 responses.
        """
        cors_headers = {"Origin": "http://localhost:3000"}

        # Request 1 (200 OK)
        res1 = rl_client.post(
            "/api/auth/login",
            json={"email": user_a["email"], "password": user_a["password"]},
            headers=cors_headers,
        )
        assert res1.status_code == 200
        expose1 = res1.headers.get("Access-Control-Expose-Headers", "")
        assert "Retry-After" in expose1
        assert "X-RateLimit-Limit" in expose1
        assert "X-RateLimit-Remaining" in expose1
        assert "X-RateLimit-Reset" in expose1

        # Request 2 (200 OK)
        rl_client.post(
            "/api/auth/login",
            json={"email": user_a["email"], "password": user_a["password"]},
            headers=cors_headers,
        )

        # Request 3 (429 Too Many Requests)
        res3 = rl_client.post(
            "/api/auth/login",
            json={"email": user_a["email"], "password": user_a["password"]},
            headers=cors_headers,
        )
        assert res3.status_code == 429
        expose3 = res3.headers.get("Access-Control-Expose-Headers", "")
        assert "Retry-After" in expose3
        assert "X-RateLimit-Limit" in expose3
        assert "X-RateLimit-Remaining" in expose3
        assert "X-RateLimit-Reset" in expose3
        assert res3.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
