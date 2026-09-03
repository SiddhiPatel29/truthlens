"""
VeraMedia AI - Flask Application Entry Point.
"""
from flask import Flask
from flask_cors import CORS
from backend.config import Config
from backend.routes.health_routes import health_bp
from backend.routes.text_routes import text_bp
from backend.routes.image_routes import image_bp
from backend.routes.video_routes import video_bp
from backend.routes.audio_routes import audio_bp
from backend.routes.abuse_routes import abuse_bp

def create_app():
    """Application factory: initializes and configures the Flask server."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # 1. Enable CORS for frontend communication
    CORS(
        app,
        resources={r"/api/*": {"origins": Config.CLIENT_ORIGIN}},
        supports_credentials=True
    )

    # 2. Register Blueprints (API Routes)
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(text_bp, url_prefix="/api")
    app.register_blueprint(image_bp, url_prefix="/api")
    app.register_blueprint(video_bp, url_prefix="/api")
    app.register_blueprint(audio_bp, url_prefix="/api")
    app.register_blueprint(abuse_bp, url_prefix="/api")

    return app

if __name__ == "__main__":
    app = create_app()
    print(f"[*] VeraMedia AI Backend starting on http://localhost:{Config.PORT}")
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)