# Backend Architecture Specification

## 1. Overview
VeraMedia AI (`truthlens`) backend is a modular REST API developed using Python 3.13 and the Flask web framework. It provides multimodal forensic analysis services (detecting synthetic or manipulated text, images, videos, and audio) and generates cryptographically signed abuse takedown dossiers for online platforms.

The backend is strictly decoupled from the frontend application, communicating solely via structured, uniform JSON over HTTP/HTTPS with CORS protection.

---

## 2. Component Structure

```
truthlens/
├── backend/
│   ├── app.py                  # Application factory, blueprint registration, logging config
│   ├── config.py               # Environment configuration and security defaults
│   ├── routes/                 # Flask Blueprints for HTTP endpoint handling
│   │   ├── health_routes.py    # GET /api/health
│   │   ├── text_routes.py      # POST /api/detect/text
│   │   ├── image_routes.py     # POST /api/detect/image
│   │   ├── video_routes.py     # POST /api/detect/video
│   │   ├── audio_routes.py     # POST /api/detect/audio
│   │   └── abuse_routes.py     # POST /api/report/abuse
│   ├── services/               # Pure forensic and business logic (no Flask request dependencies)
│   │   ├── text_service.py     # Text burstiness, perplexity, and repetition heuristics
│   │   ├── image_service.py    # Laplacian variance, Grad-CAM++ heatmap simulation (OpenCV)
│   │   ├── video_service.py    # Keyframe extraction, anomaly scoring, temporal variance (OpenCV)
│   │   ├── audio_service.py    # Zero-crossing rate, spectral energy, lip-sync desync (SciPy)
│   │   └── abuse_service.py    # Cryptographic SHA-256 fingerprinting & dossier builder
│   └── utils/                  # Reusable cross-cutting utilities
│       ├── errors.py           # Centralized error handlers for 400, 404, 405, 413, 500
│       ├── file_validator.py   # Uploaded media extension and filename validation
│       └── response.py         # Standard uniform JSON response envelope
├── docs/                       # Architectural, API, and project documentation
├── tests/                      # Automated test suite (Pytest)
├── .env.example                # Safe environment configuration template
├── requirements.txt            # Pinned production and test dependencies
└── test.{jpg,mp4,wav}          # Local multimodal test media assets
```

---

## 3. Application Entry Point & Factory
- **Module**: `backend/app.py`
- **Pattern**: Application Factory via `create_app(config_class=Config)`
- **Responsibilities**:
  1. Instantiates the `Flask` application object.
  2. Applies configuration values from `backend/config.py`.
  3. Configures server-side Python structured logging via `configure_logging()`.
  4. Binds Cross-Origin Resource Sharing (`CORS`) with `supports_credentials=True` restricted to `CLIENT_ORIGIN`.
  5. Registers centralized error handlers (`register_error_handlers(app)`).
  6. Mounts modular route Blueprints (`health_bp`, `text_bp`, `image_bp`, `video_bp`, `audio_bp`, `abuse_bp`) under the common URL prefix `/api`.
  7. When executed directly (`python -m backend.app`), starts the WSGI development server on the configured port.

---

## 4. Route / Blueprint Layer
All API endpoints are defined inside isolated Flask Blueprints within `backend/routes/`:
- Every route handler is responsible solely for:
  - Parsing incoming HTTP requests (extracting JSON body or `multipart/form-data` files).
  - Executing basic input validation (validating required fields, data types, file extensions).
  - Calling the corresponding domain service in `backend/services/`.
  - Wrapping responses and errors inside the standard uniform response envelope via `api_response()`.
  - Logging unexpected exceptions using Python's standard `logging` logger without exposing internal details to clients.

---

## 5. Service Layer
The service layer (`backend/services/`) encapsulates all core analysis and forensic processing algorithms:
- **`TextDetectionService`**:
  Calculates sentence burstiness (variance of sentence lengths), type-token lexical diversity, and per-sentence suspicion metrics.
- **`ImageDetectionService`**:
  Decodes raw image bytes with OpenCV, computes Laplacian edge/texture variance, generates an activation heatmap mask with a JET colormap overlay, and encodes the resulting visual tamper map into a Base64 JPEG data URL.
- **`VideoDetectionService`**:
  Streams video frames to a temporary file, samples up to 16 keyframes uniformly, computes frame-level Laplacian anomalies, calculates temporal instability (standard deviation of frame scores), and renders a Grad-CAM++ style heatmap for the peak anomaly keyframe. Cleans up temporary disk files in a `finally` block.
- **`AudioDetectionService`**:
  Reads WAV audio streams using `scipy.io.wavfile`, computes Zero Crossing Rate (ZCR) and spectral energy variance, and flags temporal lip-sync discrepancy windows. Cleans up temporary disk files in a `finally` block.
- **`AbuseDispatcherService`**:
  Validates target takedown platform (YouTube, X, Meta, Custom), generates a unique report UUID, computes a deterministic SHA-256 cryptographic digest of the manifest, maps the target platform to its compliance channel, and formats a takedown dossier.

*Note: Services contain pure computational logic and do not import Flask request contexts, making them directly unit-testable in isolation.*

---

## 6. Utility Layer
Located in `backend/utils/`:
- **`response.py` (`api_response`)**:
  Enforces the global response contract:
  ```json
  {
      "success": true,
      "message": "Human readable summary",
      "data": { ... },
      "error_code": null
  }
  ```
- **`file_validator.py`**:
  Provides pure validation functions (`validate_image_file`, `validate_video_file`, `validate_audio_file`, `allowed_file`) ensuring filename safety and allowed extensions (`.png`, `.jpg`, `.jpeg`, `.webp`, `.mp4`, `.mov`, `.avi`, `.mkv`, `.wav`, `.mp3`, `.m4a`, `.flac`).
- **`errors.py` (`register_error_handlers`)**:
  Registers Flask application-level error handlers for HTTP 400 (Bad Request), 404 (Not Found), 405 (Method Not Allowed), 413 (Payload Too Large), and 500 / unhandled exceptions, guaranteeing that clients receive consistent JSON envelopes and never HTML error pages or raw tracebacks.

---

## 7. Configuration System
- **Module**: `backend/config.py`
- Configuration parameters are read from environment variables via `os.getenv` with safe development defaults.
- `.env` files are loaded via `python-dotenv`.
- In `FLASK_ENV == "production"`, dangerous fallback secrets (e.g. `"default-dev-key"`) raise an explicit `ValueError`, preventing insecure deployments.
- `MAX_CONTENT_LENGTH` is enforced at the Flask core engine level (defaulting to 50 MB) to protect against denial-of-service memory exhaustion.

---

## 8. External Dependencies
- **Flask (3.0.3)**: Web framework and routing engine.
- **Flask-CORS (4.0.1)**: Cross-origin resource sharing middleware.
- **python-dotenv (1.0.1)**: `.env` file parsing.
- **gunicorn (22.0.0)**: Production WSGI server for UNIX/Linux deployment.
- **numpy (2.2.3)**: Matrix operations and statistical calculations for signal processing.
- **opencv-python (4.11.0.86)**: Computer vision, keyframe extraction, and heatmap rendering.
- **scipy (1.15.2)**: Scientific signal processing and WAV audio decoding.
- **pytest (8.3.4)**: Automated testing framework.

---

## 9. Future Database Boundary (Phase 2 Preparation)
In Phase 2, a persistence layer (SQLAlchemy ORM with SQLite for development and PostgreSQL for production) will be integrated:
- **Boundary rule**: Route handlers will interact with a database repository or service abstraction, never issuing raw SQL queries directly in route functions.
- **State isolation**: Services (`ImageDetectionService`, `TextDetectionService`, etc.) will continue to receive byte buffers or strings and return analysis dictionaries. A separate persistence service will record scan results, user IDs, and timestamps to the database.
- **Migrations**: Database schema definitions and migrations will reside in a dedicated `backend/models/` and `migrations/` directory without polluting routing blueprints.
