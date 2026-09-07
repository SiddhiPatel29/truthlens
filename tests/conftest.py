"""
Pytest Test Fixtures and Configuration for VeraMedia AI Backend.
"""
import os
import io
import pytest
from backend.app import create_app
from backend.config import Config
from backend.database import db as _db

class TestConfig(Config):
    """Testing configuration overriding defaults."""
    TESTING = True
    DEBUG = False
    SECRET_KEY = "test-secret-key-for-unit-tests"
    JWT_SECRET_KEY = "test-jwt-secret-key-for-unit-tests"
    JWT_EXPIRATION_HOURS = 24
    CLIENT_ORIGIN = "http://localhost:3000"
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB for testing
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

@pytest.fixture(scope="session")
def app():
    """Creates an instance of the Flask application for testing."""
    app = create_app(TestConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()

@pytest.fixture
def client(app):
    """Creates a test client for simulating HTTP requests."""
    return app.test_client()

@pytest.fixture
def db_session(app):
    """
    Provides an isolated database session per test with in-memory SQLite.
    Rolls back any changes at the end of each test.
    """
    with app.app_context():
        connection = _db.engine.connect()
        transaction = connection.begin()
        
        # Bind session to transaction
        session = _db.session
        yield session

        session.remove()
        transaction.rollback()
        connection.close()

@pytest.fixture
def sample_text():
    """A sample text string with > 20 characters for detection tests."""
    return "This is a comprehensive investigative statement crafted to analyze synthetic vocabulary and structure."

@pytest.fixture
def project_root():
    """Returns absolute path to project root."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

@pytest.fixture
def real_image_path(project_root):
    """Path to the test image."""
    return os.path.join(project_root, "test.jpg")

@pytest.fixture
def real_video_path(project_root):
    """Path to the test video."""
    return os.path.join(project_root, "test.mp4")

@pytest.fixture
def real_audio_path(project_root):
    """Path to the test audio."""
    return os.path.join(project_root, "test.wav")
