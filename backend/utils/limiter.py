"""
Rate Limiting Infrastructure for VeraMedia AI (SEC-08).
Provides shared Flask-Limiter instance, keying strategies, dynamic limit resolvers,
and centralized default endpoint limits.
"""
from typing import Callable
from flask import current_app, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Default Endpoint Rate Limits (SEC-08)
# Unauthenticated Endpoints (Key: Client IP)
DEFAULT_LIMIT_AUTH_LOGIN = "5 per minute; 20 per hour"
DEFAULT_LIMIT_AUTH_REGISTER = "3 per minute; 10 per hour"
DEFAULT_LIMIT_REPORT_ABUSE = "10 per minute; 60 per hour"

# Authenticated Endpoints (Key: Authenticated User ID)
DEFAULT_LIMIT_DETECT_VIDEO = "5 per minute; 30 per hour"
DEFAULT_LIMIT_DETECT_AUDIO = "10 per minute; 60 per hour"
DEFAULT_LIMIT_DETECT_IMAGE = "15 per minute; 100 per hour"
DEFAULT_LIMIT_DETECT_TEXT = "30 per minute; 200 per hour"
DEFAULT_LIMIT_SCANS = "60 per minute"
DEFAULT_LIMIT_AUTH_ME = "60 per minute"


def get_user_rate_limit_key() -> str:
    """
    Returns rate limit key based on authenticated user ID: f"user:{g.current_user_id}".

    Security rationale:
    1. Independent quotas per authenticated user account.
    2. Users cannot bypass rate limits by hopping IP addresses or rotating proxies.
    3. User A exhausting their quota never throttles or starves User B (even on a
       shared NAT, corporate proxy, or campus network IP).
    4. Evaluated after @require_auth so g.current_user_id is guaranteed valid.

    Falls back to client IP only if user context is unexpectedly missing.
    """
    user_id = getattr(g, "current_user_id", None)
    if user_id is not None:
        return f"user:{user_id}"
    return get_remote_address()


def get_limit(config_key: str, default: str) -> Callable[[], str]:
    """
    Returns a callable suitable for @limiter.limit() that dynamically resolves
    the limit string from current_app.config or falls back to default.

    This design ensures:
    1. Production uses configured limits or secure defaults.
    2. Dedicated test environments can inject deterministic small limits (e.g. "2 per second")
       without modifying route decorators.
    3. Storage backends and limits can be tuned via environment variables.
    """
    def _limit_resolver() -> str:
        if not current_app:
            return default
        return current_app.config.get(config_key, default)
    return _limit_resolver


# Shared Limiter Extension Instance
# Defaults to in-process memory storage (memory://) and fixed-window strategy.
# NOTE: In-process memory storage is process-local and is not globally synchronized
# across multiple Gunicorn worker processes. For multi-worker production deployments,
# set RATELIMIT_STORAGE_URI to a shared backend such as redis://localhost:6379/0.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    headers_enabled=True,
    strategy="fixed-window",
)


@limiter.request_filter
def _is_rate_limiting_disabled() -> bool:
    """
    Exempts requests dynamically when RATELIMIT_ENABLED is False in current_app.config.
    This guarantees that testing suites running with RATELIMIT_ENABLED = False remain
    completely unthrottled, regardless of extension instance reuse across test apps.
    """
    if not current_app:
        return False
    return not current_app.config.get("RATELIMIT_ENABLED", True)
