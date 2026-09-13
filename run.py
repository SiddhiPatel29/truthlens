r"""
VeraMedia AI / TruthLens - Local Server Entry Point.
Starts the existing Flask backend application.

Usage:
    .venv\Scripts\python.exe run.py
    or:
    python run.py
"""
from backend.app import create_app

app = create_app()

if __name__ == "__main__":
    port = app.config.get("PORT", 5000)
    # Debug mode is only enabled if configured and not running in production
    is_production = app.config.get("FLASK_ENV") == "production"
    debug = app.config.get("DEBUG", False) and not is_production

    print(f"[*] VeraMedia AI Backend starting on http://localhost:{port}")
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug
    )
