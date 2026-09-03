"""
Pytest Test Fixtures and Configuration for VeraMedia AI Backend.
"""
import os
import io
import pytest
from backend.app import create_app
from backend.config import Config

class TestConfig(Config):
    """Testing configuration overriding defaults."""
    TESTING = True
    DEBUG = False
    SECRET_KEY = "test-secret-key-for-unit-tests"
    CLIENT_ORIGIN = "http://localhost:3000"
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB for testing

@pytest.fixture
def app():
    """Creates an instance of the Flask application for testing."""
    app = create_app(TestConfig)
    return app

@pytest.fixture
def client(app):
    """Creates a test client for simulating HTTP requests."""
    return app.test_client()

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
