# Backend Architecture Specification

## 1. Overview
VeraMedia AI (`truthlens`) backend is a modular REST API developed using Python 3.13 and the Flask web framework, backed by a relational persistence layer using SQLAlchemy 2.0, Flask-SQLAlchemy, and Flask-Migrate (Alembic).

It provides multimodal forensic analysis services (detecting synthetic or manipulated text, images, videos, and audio), records structured database models, and generates cryptographically signed abuse takedown dossiers for online platforms.

The backend is strictly decoupled from the frontend application, communicating solely via structured, uniform JSON over HTTP/HTTPS with CORS protection.

---

## 2. Component Structure

```
truthlens/
├── backend/
│   ├── app.py                  # Application factory, blueprint & extension registration, logging
│   ├── config.py               # Environment configuration, database URLs, and security defaults
│   ├── database/               # Relational persistence layer
│   │   ├── __init__.py         # Re-exports db, migrate, and all models
│   │   ├── db.py               # Shared SQLAlchemy and Flask-Migrate instances, SQLite PRAGMA listener
│   │   └── models.py           # Declarative models: User, Scan, ScanResult, AbuseReport
│   ├── routes/                 # Flask Blueprints for HTTP endpoint handling
│   │   ├── health_routes.py    # GET /api/health
│   │   ├── text_routes.py      # POST /api/detect/text
│   │   ├── image_routes.py     # POST /api/detect/image
│   │   ├── video_routes.py     # POST /api/detect/video
│   │   ├── audio_routes.py     # POST /api/detect/audio
│   │   ├── abuse_routes.py     # POST /api/report/abuse
│   │   └── auth_routes.py      # POST /api/auth/register, POST /api/auth/login, GET /api/auth/me
│   ├── services/               # Pure forensic and business logic (no Flask request dependencies)
│   │   ├── text_service.py     # Text burstiness, perplexity, and repetition heuristics
│   │   ├── image_service.py    # Laplacian variance, Grad-CAM++ heatmap simulation (OpenCV)
│   │   ├── video_service.py    # Keyframe extraction, anomaly scoring, temporal variance (OpenCV)
│   │   ├── audio_service.py    # Zero-crossing rate, spectral energy, lip-sync desync (SciPy)
│   │   ├── abuse_service.py    # Cryptographic SHA-256 fingerprinting & dossier builder
│   │   ├── auth_service.py     # User registration, login, scrypt hashing, JWT issuance & verification
│   │   └── scan_service.py     # Scan & ScanResult transactional persistence, status management, retrieval
│   └── utils/                  # Reusable cross-cutting utilities
│       ├── auth.py             # @require_auth decorator, Bearer JWT validation, g.current_user_id
│       ├── errors.py           # Centralized error handlers for 400, 404, 405, 413, 500
│       ├── file_validator.py   # Uploaded media extension and filename validation
│       └── response.py         # Standard uniform JSON response envelope
├── docs/                       # Architectural, API, and project documentation
├── instance/                   # Local instance folder (contains truthlens.db in development)
├── migrations/                 # Alembic database migration scripts managed by Flask-Migrate
│   ├── versions/               # Migration revision files
│   ├── env.py                  # Alembic runtime environment
│   └── alembic.ini             # Alembic configuration
├── tests/                      # Automated test suite (Pytest)
│   ├── test_startup_and_health.py
│   ├── test_error_handling.py
│   ├── test_text_detection.py
│   ├── test_image_detection.py
│   ├── test_video_detection.py
│   ├── test_audio_detection.py
│   ├── test_abuse_report.py
│   ├── test_database.py        # Database models, constraints, relationships, and migration tests
│   ├── test_auth_registration.py # User registration and password hashing tests
│   ├── test_auth_login.py      # User login, anti-enumeration, and token generation tests
│   ├── test_auth_authorization.py # Route protection, Bearer validation, and claims tests
│   ├── test_scan_service.py    # Scan and ScanResult transactional persistence and retrieval tests
│   ├── test_text_persistence.py # Text detection scan persistence and user isolation tests
│   └── test_image_persistence.py # Image detection scan persistence and user isolation tests
├── .env.example                # Safe environment configuration template
├── requirements.txt            # Pinned production, database, and test dependencies
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
  4. Initializes the database layer (`db.init_app(app)`) and migration engine (`migrate.init_app(app, db)`).
  5. Binds Cross-Origin Resource Sharing (`CORS`) with `supports_credentials=True` restricted to `CLIENT_ORIGIN`.
  6. Registers centralized error handlers (`register_error_handlers(app)`).
  7. Mounts modular route Blueprints (`health_bp`, `text_bp`, `image_bp`, `video_bp`, `audio_bp`, `abuse_bp`) under the common URL prefix `/api`.
  8. When executed directly (`python -m backend.app`), starts the WSGI development server on the configured port.

---

## 4. Database Architecture & Models
The persistence layer is encapsulated in `backend/database/` using Flask-SQLAlchemy 3.1 and SQLAlchemy 2.0.

### A. Shared Instances & SQLite Foreign Key Pragma (`backend/database/db.py`)
- Exposes shared `db = SQLAlchemy()` and `migrate = Migrate()`.
- Implements an event listener on the SQLAlchemy engine connect hook:
  ```python
  @event.listens_for(Engine, "connect")
  def enforce_sqlite_foreign_keys(dbapi_connection, connection_record):
      cursor = dbapi_connection.cursor()
      cursor.execute("PRAGMA foreign_keys=ON")
      cursor.close()
  ```
  This ensures relational foreign key constraints are enforced at the database level when running SQLite.

### B. Relational Schema & Models (`backend/database/models.py`)

1. **`User`** (`users` table):
   - `id`: Integer, primary key, auto-increment.
   - `name`: String(120), nullable=False.
   - `email`: String(255), unique=True, index=True, nullable=False.
   - `password_hash`: String(255), nullable=False.
   - `is_active`: Boolean, default=True, nullable=False.
   - `created_at`: DateTime (UTC), default=utc_now, nullable=False.
   - `updated_at`: DateTime (UTC), default=utc_now, onupdate=utc_now, nullable=False.
   - **Relationships**:
     - `scans`: 1-to-many relationship with `Scan` (`back_populates="user"`, `cascade="all, delete-orphan"`).
     - `abuse_reports`: 1-to-many relationship with `AbuseReport` (`back_populates="user"`, `cascade="all, delete-orphan"`).

2. **`Scan`** (`scans` table):
   - `id`: Integer, primary key, auto-increment.
   - `user_id`: Integer, ForeignKey(`users.id`, ondelete="CASCADE"), nullable=True (nullable in Phase 2 for anonymous scans prior to auth).
   - `media_type`: String(50), nullable=False (`"text"`, `"image"`, `"video"`, `"audio"`).
   - `filename`: String(255), nullable=True.
   - `status`: String(50), default=`"PENDING"`, nullable=False (`"PENDING"`, `"PROCESSING"`, `"COMPLETED"`, `"FAILED"`).
   - `created_at`: DateTime (UTC), default=utc_now, nullable=False.
   - `completed_at`: DateTime (UTC), nullable=True.
   - **Relationships**:
     - `user`: many-to-1 relationship with `User`.
     - `result`: 1-to-1 relationship with `ScanResult` (`uselist=False`, `back_populates="scan"`, `cascade="all, delete-orphan"`).
     - `abuse_reports`: 1-to-many relationship with `AbuseReport` (`back_populates="scan"`, `cascade="all, delete-orphan"`).

3. **`ScanResult`** (`scan_results` table):
   - `id`: Integer, primary key, auto-increment.
   - `scan_id`: Integer, ForeignKey(`scans.id`, ondelete="CASCADE"), unique=True, index=True, nullable=False.
   - `prediction`: String(50), nullable=False (`"DEEPFAKE"`, `"AUTHENTIC"`, `"AI_GENERATED"`).
   - `confidence`: Float, nullable=False.
   - `risk_level`: String(50), nullable=False (`"LOW"`, `"MEDIUM"`, `"HIGH"`).
   - `result_data`: JSON, nullable=False (stores raw metrics, breakdown, heatmap data URLs).
   - `created_at`: DateTime (UTC), default=utc_now, nullable=False.
   - **Relationships**:
     - `scan`: 1-to-1 relationship with `Scan`.

4. **`AbuseReport`** (`abuse_reports` table):
   - `id`: Integer, primary key, auto-increment.
   - `user_id`: Integer, ForeignKey(`users.id`, ondelete="SET NULL"), nullable=True, index=True.
   - `scan_id`: Integer, ForeignKey(`scans.id`, ondelete="SET NULL"), nullable=True, index=True.
   - `platform`: String(50), nullable=False (`"youtube"`, `"x"`, `"meta"`, `"custom"`).
   - `status`: String(50), default=`"DISPATCHED"`, nullable=False.
   - `report_data`: JSON, nullable=False (stores dossier manifest, SHA-256 fingerprint, notes, receipt code).
   - `created_at`: DateTime (UTC), default=utc_now, nullable=False.
   - **Relationships**:
     - `user`: many-to-1 relationship with `User`.
     - `scan`: many-to-1 relationship with `Scan`.

### C. Migration Toolchain (Flask-Migrate & Alembic)
- Migration tracking is managed by Flask-Migrate inside `migrations/`.
- The initial schema migration (`f3e901358e24_initial_database_schema_users_scans_.py`) is applied to `instance/truthlens.db`.
- Upgrades and downgrades use Alembic's batch mode (`with op.batch_alter_table`), ensuring full compatibility with SQLite's table alteration limitations while remaining ready for PostgreSQL in production.

---

## 5. Route / Blueprint Layer
All API endpoints are defined inside isolated Flask Blueprints within `backend/routes/`:
- Every route handler is responsible solely for:
  - Parsing incoming HTTP requests (extracting JSON body or `multipart/form-data` files).
  - Executing input validation (validating required fields, data types, file extensions).
  - Enforcing authorization where required (e.g. `@require_auth` on `GET /api/auth/me`, `POST /api/detect/text`, and `POST /api/detect/image`).
  - Calling the corresponding domain service in `backend/services/`.
  - Triggering transactional persistence via `ScanService` for authenticated scan modalities (`POST /api/detect/text`, `POST /api/detect/image`). Note: video and audio detection, and abuse dispatch remain public and unpersisted in this step.
  - Wrapping responses and errors inside the standard uniform response envelope via `api_response()`.
  - Logging unexpected exceptions using Python's standard `logging` logger without exposing internal details to clients.

---

## 6. Service Layer
The service layer (`backend/services/`) encapsulates all core analysis and forensic processing algorithms:
- **`TextDetectionService`**:
  Calculates sentence burstiness (variance of sentence lengths), type-token lexical diversity, and per-sentence suspicion metrics.
- **`ImageDetectionService`**:
  Decodes raw image bytes with OpenCV, computes Laplacian edge/texture variance, generates an activation heatmap mask with a JET colormap overlay, and encodes the resulting visual tamper map into a Base64 JPEG data URL.
- **`VideoDetectionService`**:
  Streams video frames to a temporary file, samples up to 16 keyframes uniformly, computes frame-level Laplacian anomalies, calculates temporal instability, and renders a Grad-CAM++ style heatmap for the peak anomaly keyframe. Cleans up temporary disk files in a `finally` block.
- **`AudioDetectionService`**:
  Reads WAV audio streams using `scipy.io.wavfile`, computes Zero Crossing Rate (ZCR) and spectral energy variance, and flags temporal lip-sync discrepancy windows. Cleans up temporary disk files in a `finally` block.
- **`AbuseDispatcherService`**:
  Validates target takedown platform (YouTube, X, Meta, Custom), generates a unique report UUID, computes a deterministic SHA-256 cryptographic digest of the manifest, maps the target platform to its compliance channel, and formats a takedown dossier.
- **`AuthService`**:
  Validates registration parameters, normalizes email addresses (`strip().lower()`), verifies modern password policy (12–128 characters, no mandatory composition rules, whitespace/Unicode allowed, local weak-password blocklist), performs duplicate email checks, hashes passwords securely using Werkzeug's `generate_password_hash` (`scrypt`), and persists `User` records in the database. For login, verifies credentials via `check_password_hash`, enforces account active status, prevents user enumeration with generic 401 errors, and issues signed HS256 JWT access tokens with minimal claims (`sub`, `iat`, `exp`).
- **`ScanService`**:
  Encapsulates database persistence and query operations for forensic scans (`Scan`) and completed analysis results (`ScanResult`). Handles atomic transactions, transitions parent scan status from `PENDING` to `COMPLETED` with UTC timestamps, enforces 1-to-1 scan-to-result integrity (`ScanConflictError`), performs proportional input validation, and manages session rollback on database commit errors (`ScanDatabaseError`).

---

## 7. Utility Layer
Located in `backend/utils/`:
- **`auth.py` (`@require_auth`)**: Reusable route decorator validating Bearer access tokens from HTTP `Authorization` headers, verifying signature/claims via `AuthService.verify_token`, and binding integer user ID to `g.current_user_id`.
- **`response.py` (`api_response`)**: Enforces global `{ success, message, data, error_code }` envelope.
- **`file_validator.py`**: Pure validation functions (`validate_image_file`, `validate_video_file`, `validate_audio_file`, `allowed_file`).
- **`errors.py` (`register_error_handlers`)**: Application-level error handlers for HTTP 400, 404, 405, 413, and 500.

---

## 8. Configuration System
- **Module**: `backend/config.py`
- Configuration parameters are read from environment variables via `os.getenv` with safe development defaults.
- `DATABASE_URL` defaults to `sqlite:///truthlens.db`.
- Automatically normalizes legacy `postgres://` URLs to `postgresql://` for SQLAlchemy 2.0.
- Production safety guards prevent running with default `SECRET_KEY` or `JWT_SECRET_KEY`.
- `JWT_EXPIRATION_HOURS` configures token expiration duration (defaults to 24 hours).

---

## 9. External Dependencies
- **Flask (3.0.3)**: Web framework and routing engine.
- **Flask-CORS (4.0.1)**: Cross-origin resource sharing middleware.
- **python-dotenv (1.0.1)**: `.env` file parsing.
- **gunicorn (22.0.0)**: Production WSGI server for UNIX/Linux deployment.
- **numpy (2.2.3)**: Matrix operations and statistical calculations for signal processing.
- **opencv-python (4.11.0.86)**: Computer vision, keyframe extraction, and heatmap rendering.
- **scipy (1.15.2)**: Scientific signal processing and WAV audio decoding.
- **pytest (8.3.4)**: Automated testing framework.
- **SQLAlchemy (2.0.52)**: Object relational mapper and database toolkit.
- **Flask-SQLAlchemy (3.1.1)**: Flask extension for SQLAlchemy.
- **alembic (1.19.2)**: Database migration engine.
- **Flask-Migrate (4.1.0)**: Flask extension for Alembic database migrations.
- **Werkzeug (3.1.8)**: WSGI web server utility and cryptographic password hashing (`scrypt`).
- **PyJWT (2.10.1)**: JSON Web Token generation, signature encoding, and claim verification.

