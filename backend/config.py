"""
Configuration Module for VeraMedia AI Backend.
Loads environment variables and provides structured settings for Flask.
"""
import os
import logging
from dotenv import load_dotenv

# Load settings from .env if present
load_dotenv()

logger = logging.getLogger(__name__)

class Config:
    """Base application configuration loaded from environment variables."""
    
    FLASK_ENV = os.getenv("FLASK_ENV", "development").lower()
    
    # Flask 3.x uses FLASK_DEBUG; retain backwards-compatibility with FLASK_ENV
    _env_debug = os.getenv("FLASK_DEBUG")
    if _env_debug is not None:
        DEBUG = _env_debug.strip() in ("1", "true", "True")
    else:
        DEBUG = FLASK_ENV == "development"

    TESTING = os.getenv("TESTING", "0").strip() in ("1", "true", "True")

    # Server Port
    try:
        PORT = int(os.getenv("PORT", "5000"))
    except ValueError:
        PORT = 5000

    # Secret Key
    SECRET_KEY = os.getenv("SECRET_KEY", "default-dev-key")

    # Security check: prevent default secret key in production
    if FLASK_ENV == "production" and (not SECRET_KEY or SECRET_KEY in ("default-dev-key", "dev_insecure_secret_key_change_in_production")):
        raise ValueError(
            "CRITICAL SECURITY CONFIGURATION ERROR: "
            "A secure, non-default SECRET_KEY must be provided when running in production."
        )

    # JWT Configuration
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-key-change-in-production")
    if FLASK_ENV == "production" and (not JWT_SECRET_KEY or JWT_SECRET_KEY in ("dev-jwt-secret-key-change-in-production", "default-dev-key", "dev_jwt_secret_key_change_in_production")):
        raise ValueError(
            "CRITICAL SECURITY CONFIGURATION ERROR: "
            "A secure, non-default JWT_SECRET_KEY must be provided when running in production."
        )

    try:
        JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    except ValueError:
        JWT_EXPIRATION_HOURS = 24

    # Allowed origins for CORS (Frontend communication)
    # Supports comma-separated list of origins. Defaults to local React (3000) and Vite (5173).
    CLIENT_ORIGIN = os.getenv("CLIENT_ORIGIN", "http://localhost:3000,http://localhost:5173")

    # Maximum upload payload size in bytes (defaults to 50 MB)
    try:
        _max_mb = int(os.getenv("MAX_CONTENT_LENGTH_MB", "50"))
    except ValueError:
        _max_mb = 50
    MAX_CONTENT_LENGTH = _max_mb * 1024 * 1024

    # Database Configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///truthlens.db")
    # Normalize legacy postgres:// scheme to postgresql:// for SQLAlchemy 2.0
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Rate Limiting Configuration (SEC-08)
    RATELIMIT_ENABLED = os.getenv("RATELIMIT_ENABLED", "true").strip().lower() in ("1", "true", "yes")
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_STRATEGY = os.getenv("RATELIMIT_STRATEGY", "fixed-window")
    RATELIMIT_HEADERS_ENABLED = True

    # Endpoint-specific rate limits (SEC-08)
    RATELIMIT_AUTH_LOGIN = os.getenv("RATELIMIT_AUTH_LOGIN", "5 per minute; 20 per hour")
    RATELIMIT_AUTH_REGISTER = os.getenv("RATELIMIT_AUTH_REGISTER", "3 per minute; 10 per hour")
    RATELIMIT_REPORT_ABUSE = os.getenv("RATELIMIT_REPORT_ABUSE", "10 per minute; 60 per hour")
    RATELIMIT_DETECT_VIDEO = os.getenv("RATELIMIT_DETECT_VIDEO", "5 per minute; 30 per hour")
    RATELIMIT_DETECT_AUDIO = os.getenv("RATELIMIT_DETECT_AUDIO", "10 per minute; 60 per hour")
    RATELIMIT_DETECT_IMAGE = os.getenv("RATELIMIT_DETECT_IMAGE", "15 per minute; 100 per hour")
    RATELIMIT_DETECT_TEXT = os.getenv("RATELIMIT_DETECT_TEXT", "30 per minute; 200 per hour")
    RATELIMIT_SCANS = os.getenv("RATELIMIT_SCANS", "60 per minute")
    RATELIMIT_AUTH_ME = os.getenv("RATELIMIT_AUTH_ME", "60 per minute")