import os
from dotenv import load_dotenv

# Load settings from the .env file
load_dotenv()

class Config:
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = FLASK_ENV == "development"
    PORT = int(os.getenv("PORT", 5000))
    SECRET_KEY = os.getenv("SECRET_KEY", "default-dev-key")
    
    # Frontend URL (for security / CORS)
    CLIENT_ORIGIN = os.getenv("CLIENT_ORIGIN", "http://localhost:3000")
    
    # Max file upload size (50 Megabytes)
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH_MB", 50)) * 1024 * 1024