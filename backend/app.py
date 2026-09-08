"""
VeraMedia AI - Flask Application Entry Point.
"""
import logging
from flask import Flask
from flask_cors import CORS
from backend.config import Config
from backend.database import db, migrate
from backend.utils.errors import register_error_handlers
from backend.routes.health_routes import health_bp
from backend.routes.text_routes import text_bp
from backend.routes.image_routes import image_bp
from backend.routes.video_routes import video_bp
from backend.routes.audio_routes import audio_bp
from backend.routes.abuse_routes import abuse_bp
from backend.routes.auth_routes import auth_bp
from backend.routes.scan_routes import scan_bp

def configure_logging(app: Flask):
    """Configures structured server-side logging."""
    log_level = logging.DEBUG if app.config.get("DEBUG") else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="[%(asctime)s] %(levelname)s in %(name)s: %(message)s"
    )

def create_app(config_class=Config):
    """Application factory: initializes and configures the Flask server."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 1. Configure logging
    configure_logging(app)

    # 2. Initialize Database & Migrations
    db.init_app(app)
    migrate.init_app(app, db)

    # 3. Enable CORS for frontend communication
    CORS(
        app,
        resources={r"/api/*": {"origins": app.config.get("CLIENT_ORIGIN", "*")}},
        supports_credentials=True
    )

    # 4. Register Centralized Error Handlers
    register_error_handlers(app)

    # 5. Register Blueprints (API Routes)
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(text_bp, url_prefix="/api")
    app.register_blueprint(image_bp, url_prefix="/api")
    app.register_blueprint(video_bp, url_prefix="/api")
    app.register_blueprint(audio_bp, url_prefix="/api")
    app.register_blueprint(abuse_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(scan_bp, url_prefix="/api")

    return app

if __name__ == "__main__":
    app = create_app()
    print(f"[*] VeraMedia AI Backend starting on http://localhost:{app.config.get('PORT')}")
    app.run(
        host="0.0.0.0",
        port=app.config.get("PORT", 5000),
        debug=app.config.get("DEBUG", False)
    )