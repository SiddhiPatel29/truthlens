"""
Authentication Service for VeraMedia AI.
Handles user registration, input validation, email normalization, and secure password hashing.
"""
import re
import logging
from werkzeug.security import generate_password_hash
from backend.database.db import db
from backend.database.models import User

logger = logging.getLogger(__name__)

# Standard email validation pattern
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128

# Local blocklist of common/obvious weak passwords (checked case-insensitively with trimmed whitespace)
COMMON_WEAK_PASSWORDS = {
    "password",
    "password123",
    "12345678",
    "123456789",
    "1234567890",
    "qwerty",
    "qwerty123",
    "admin",
    "admin123",
    "letmein",
    "welcome",
    "abc123",
    # Common 12+ character weak passwords
    "123456789012",
    "1234567890123",
    "password1234",
    "password12345",
    "passwordpassword",
    "administrator",
    "qwertyuiop12",
}

class AuthValidationError(ValueError):
    """Exception raised for authentication validation failures with specific error codes."""
    def __init__(self, message: str, error_code: str):
        super().__init__(message)
        self.message = message
        self.error_code = error_code

class AuthService:
    """Service providing user authentication operations."""

    @classmethod
    def register_user(cls, data: dict) -> dict:
        """
        Validates registration payload, normalizes email, hashes password,
        and persists new user to the database.

        Returns:
            dict: Serialized safe user info: {"id": user.id, "name": user.name, "email": user.email}

        Raises:
            AuthValidationError: On input validation failure or duplicate email.
        """
        if not data or not isinstance(data, dict):
            raise AuthValidationError("Request body must be a valid JSON object.", "INVALID_JSON")

        # 1. Validate name
        name = data.get("name")
        if name is None or not isinstance(name, str) or not name.strip():
            raise AuthValidationError("Field 'name' is required.", "MISSING_FIELD")
        clean_name = name.strip()

        # 2. Validate and normalize email
        raw_email = data.get("email")
        if raw_email is None or not isinstance(raw_email, str) or not raw_email.strip():
            raise AuthValidationError("Field 'email' is required.", "MISSING_FIELD")
        
        normalized_email = raw_email.strip().lower()
        if not EMAIL_REGEX.match(normalized_email):
            raise AuthValidationError("Invalid email address format.", "INVALID_EMAIL")

        # 3. Validate password
        password = data.get("password")
        if password is None or not isinstance(password, str):
            raise AuthValidationError("Field 'password' is required.", "MISSING_FIELD")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise AuthValidationError(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.",
                "PASSWORD_TOO_SHORT"
            )
        if len(password) > MAX_PASSWORD_LENGTH:
            raise AuthValidationError(
                f"Password must not exceed {MAX_PASSWORD_LENGTH} characters.",
                "PASSWORD_TOO_LONG"
            )

        # Check weak password blocklist (case-insensitive, trimmed whitespace)
        if password.strip().lower() in COMMON_WEAK_PASSWORDS:
            raise AuthValidationError(
                "The password provided is too common or easily guessable.",
                "WEAK_PASSWORD"
            )

        # 4. Check for duplicate email
        existing_user = User.query.filter_by(email=normalized_email).first()
        if existing_user:
            raise AuthValidationError("An account with this email already exists.", "EMAIL_ALREADY_REGISTERED")

        # 5. Securely hash password (Werkzeug scrypt/pbkdf2 default)
        # Plaintext password is never stored or logged
        password_hash = generate_password_hash(password)

        # 6. Persist user in database
        user = User(
            name=clean_name,
            email=normalized_email,
            password_hash=password_hash,
            is_active=True
        )
        db.session.add(user)
        db.session.commit()

        logger.info("User registered successfully with id=%d, email=%s", user.id, user.email)

        # 7. Return safe representation (never include password_hash)
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
