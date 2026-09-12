# Feature Log

This document records the features implemented during each development phase of the VeraMedia AI backend.

---

## Phase 1: Clean, Testable, Secure Backend Foundation

### Feature 1: Pinned Dependency Remediation & Virtual Environment Setup
- **Feature**: Complete dependency specification and isolated runtime environment.
- **Reason**: The backend imported `numpy`, `cv2` (`opencv-python`), and `scipy.io.wavfile` (`scipy`), but these were missing from `requirements.txt`. Without them, any fresh clone would fail with `ModuleNotFoundError`.
- **Files Changed**: `requirements.txt`, `.gitignore`
- **Implementation**: Pinned exact packages for Python 3.13; created isolated `.venv`.
- **Tests**: Verified pip installation exit code 0 and module imports in `.venv`.
- **Current Status**: Complete.

### Feature 2: Safe Environment Configuration & Secret Protection
- **Feature**: Standardized `.env.example` template and hardened configuration loader.
- **Reason**: Ensure developers have a safe template without hardcoded or accidentally committed credentials.
- **Files Changed**: `.env.example`, `backend/config.py`, `.gitignore`
- **Implementation**: Created `.env.example`; supported `FLASK_DEBUG`; added production fail-fast check against default secret key; updated `.gitignore`.
- **Tests**: Verified git ignores `.env` and tracks `.env.example`.
- **Current Status**: Complete.

### Feature 3: Centralized Error Handling & Exception Sanitization
- **Feature**: Uniform JSON error responses and server-side structured logging.
- **Reason**: Default Flask error responses returned raw HTML pages on 404, 405, and 413. Route exception blocks returned `f"Internal Error: {str(e)}"`, which leaked stack traces, library internals, and filesystem paths.
- **Files Changed**: `backend/utils/errors.py`, `backend/app.py`, route files.
- **Implementation**: Registered `@app.errorhandler` for 400, 404, 405, 413, 500; replaced raw exception messages with sanitized envelopes; added `logger.exception()`.
- **Tests**: `tests/test_error_handling.py` (4 tests passed).
- **Current Status**: Complete.

---

## 16. Video Detection Scan Persistence (Phase 4 Step 4)
- **Status**: Completed (Phase 4 Step 4).
- **Reason**: Connect the existing video detection endpoint to authentication and scan persistence so that analyzed video scans are recorded, associated with the authenticated user, and transitioned to `COMPLETED` status with uploaded filename metadata.
- **Files Changed / Created**:
  - `backend/routes/video_routes.py` (Modified - protected with `@require_auth`, calls `ScanService.create_scan` with `filename=file.filename` and `ScanService.save_scan_result`, handles `ScanServiceError` cleanly)
  - `tests/test_video_detection.py` (Modified - updated regression tests with authentication fixtures and headers, added corrupt content test)
  - `tests/test_video_persistence.py` (New - 11 comprehensive unit and integration tests)
- **Implementation**:
  - `@require_auth`: Guards `POST /api/detect/video`, ensuring unauthenticated requests are rejected with standardized 401 responses before reading video streams or running OpenCV keyframe analysis.
  - Forensic Mapping: Maps detector outputs (`is_deepfake`, `confidence_score`, `metrics`, `keyframe_heatmap_preview`) into `prediction` (`DEEPFAKE` or `AUTHENTIC`), `confidence`, `risk_level` (`HIGH`, `MEDIUM`, `LOW`), and deliberately constructed `result_data` JSON.
  - Media Metadata: Records original uploaded filename in `Scan.filename`.
  - Exclusion of Raw Binary Bytes: Heavy uploaded video files, uncompressed frames, and transient arrays are not stored in the database.
  - Scan Lifecycle: Scan is created in `PENDING` status (`user_id=g.current_user_id`, `media_type="video"`, `filename=file.filename`), then updated atomically to `COMPLETED` with timestamp upon `save_scan_result()`.
  - Failure Handling: Catches `ScanServiceError` and logs server-side without leaking raw SQL or database errors, returning sanitized HTTP 500.
  - Preservation: Response envelope and detector data output remain completely backward-compatible. Audio and abuse routes remain public and unchanged.
- **Tests**:
  - `tests/test_video_persistence.py` (11 tests passed in 4.35s).
  - `tests/test_video_detection.py` (5 tests passed in 0.59s).
  - Complete test suite: 159 passed out of 159 tests in 24.70s.
- **Current Status**: Complete.


### Feature 4: Media File Validation Refactoring
- **Feature**: Reusable media validation helpers for image, video, and audio uploads.
- **Reason**: Video and audio routes had duplicated inline file validation logic.
- **Files Changed**: `backend/utils/file_validator.py`, `backend/routes/video_routes.py`, `backend/routes/audio_routes.py`
- **Implementation**: Added `validate_video_file` and `validate_audio_file` helpers returning `(is_valid, error_message, error_code)`.
- **Tests**: File validation unit tests for images, videos, audio (passed).
- **Current Status**: Complete.

### Feature 5: Automated Pytest Suite Foundation
- **Feature**: Comprehensive unit and integration test suite.
- **Reason**: Provide automated regression protection and verify all existing API contracts against actual code execution.
- **Files Changed**: `tests/conftest.py`, `tests/test_startup_and_health.py`, `tests/test_error_handling.py`, detection tests.
- **Implementation**: Created 29 automated tests across all 6 endpoints.
- **Tests**: All 29 tests passed in 1.04s.
- **Current Status**: Complete.

### Feature 6: Live Server Verification & Documentation Suite
- **Feature**: Live verification against running backend server and 9 comprehensive documentation artifacts.
- **Reason**: Verify the server runs in real-world conditions and document the actual implementation.
- **Files Changed**: `docs/*.md`
- **Implementation**: Verified live server with 10 HTTP requests; authored 9 documents.
- **Tests**: 10 out of 10 live HTTP requests passed.
- **Current Status**: Complete.

---

## Phase 2: Database Foundation (SQLAlchemy + Alembic)

### Feature 7: Relational Database Package & Declarative Models
- **Feature**: Production-ready ORM layer with `User`, `Scan`, `ScanResult`, and `AbuseReport` models.
- **Reason**: Prepare the system for user management, forensic scan persistence, and abuse takedown tracking with relational integrity.
- **Files Changed**:
  - `requirements.txt` (Added `SQLAlchemy==2.0.52`, `Flask-SQLAlchemy==3.1.1`, `alembic==1.19.2`, `Flask-Migrate==4.1.0`)
  - `backend/config.py` (Added `DATABASE_URL` with default `sqlite:///truthlens.db` and PostgreSQL normalization)
  - `backend/database/db.py` (New - Shared `db` and `migrate` instances with SQLite `PRAGMA foreign_keys=ON` hook)
  - `backend/database/models.py` (New - `User`, `Scan`, `ScanResult`, `AbuseReport` models)
  - `backend/database/__init__.py` (New - Re-exported database symbols)
  - `backend/app.py` (Initialized `db.init_app(app)` and `migrate.init_app(app, db)`)
  - `.env.example` (Added `DATABASE_URL`)
  - `.gitignore` (Added `*.db`, `*.sqlite`, `*.sqlite3`)
- **Implementation**:
  - `User`: id, name, email (unique index), password_hash, is_active, created_at, updated_at.
  - `Scan`: id, user_id (nullable foreign key), media_type, filename, status, created_at, completed_at.
  - `ScanResult`: id, scan_id (unique foreign key), prediction, confidence, risk_level, result_data (JSON), created_at.
  - `AbuseReport`: id, user_id (nullable FK), scan_id (nullable FK), platform, status, report_data (JSON), created_at.
  - Established ORM relationships: User → many Scans, Scan → one ScanResult, Scan → many AbuseReports, User → many AbuseReports.
- **Tests**:
  - `tests/test_database.py::test_user_model_creation` (PASSED)
  - `tests/test_database.py::test_user_unique_email_constraint` (PASSED)
  - `tests/test_database.py::test_scan_model_creation_nullable_user` (PASSED)
  - `tests/test_database.py::test_scan_result_model_creation` (PASSED)
  - `tests/test_database.py::test_abuse_report_model_creation` (PASSED)
  - `tests/test_database.py::test_user_scans_relationship` (PASSED)
  - `tests/test_database.py::test_scan_scan_result_relationship` (PASSED)
  - `tests/test_database.py::test_scan_abuse_reports_relationship` (PASSED)
  - `tests/test_database.py::test_user_abuse_reports_relationship` (PASSED)
  - `tests/test_database.py::test_foreign_key_constraint_invalid_user_on_scan` (PASSED)
  - `tests/test_database.py::test_foreign_key_constraint_invalid_scan_on_result` (PASSED)
- **Current Status**: Complete.

### Feature 8: Database Migration Toolchain (Flask-Migrate + Alembic)
- **Feature**: Automated, version-controlled schema migrations.
- **Reason**: Enable non-destructive schema evolution across development and production environments.
- **Files Changed**:
  - `migrations/` (Alembic configuration and version scripts)
  - `migrations/versions/f3e901358e24_initial_database_schema_users_scans_.py` (Initial migration script)
- **Implementation**:
  - Initialized migration repository via `flask db init`.
  - Generated initial revision `f3e901358e24` creating all 4 tables, unique indexes, and foreign keys.
  - Applied migration via `flask db upgrade` creating `instance/truthlens.db`.
- **Tests**:
  - `tests/test_database.py::test_migration_truthlens_db_schema` (PASSED - verified 5 tables in `truthlens.db`).
- **Current Status**: Complete.

### Feature 9: Database Testing Infrastructure
- **Feature**: Fast, isolated in-memory testing for models and relationships.
- **Reason**: Ensure database operations and relational integrity are tested without disk I/O bottlenecks or polluting persistent databases.
- **Files Changed**:
  - `tests/conftest.py` (Configured `sqlite:///:memory:` and `db_session` fixture)
  - `tests/test_database.py` (12 automated database test cases)
- **Implementation**:
  - Test session creates in-memory database on start and drops on teardown.
  - Each database test runs in a scoped transaction that rolls back automatically.
- **Tests**:
  - Complete test suite: 41 passed out of 41 tests in 0.62s.
- **Current Status**: Complete.

---

## Phase 3: Authentication & Identity Management

### Feature 10: Secure User Registration & Password Hashing (Step 1)
- **Feature**: User registration endpoint (`POST /api/auth/register`) with cryptographic password hashing and modern password policy.
- **Reason**: Enable new users to register accounts securely with email normalization, modern password length and weak-password protection, and duplicate rejection.
- **Files Changed**:
  - `requirements.txt` (Pinned `Werkzeug==3.1.8`)
  - `backend/services/auth_service.py` (New - `AuthService` registration logic, modern password validation, and `AuthValidationError`)
  - `backend/routes/auth_routes.py` (New - `auth_bp` blueprint with `POST /api/auth/register`)
  - `backend/app.py` (Registered `auth_bp` blueprint under `/api`)
  - `tests/test_auth_registration.py` (New - 25 comprehensive registration & password policy tests)
- **Implementation**:
  - Validates JSON payload existence, required non-empty `name`, required valid `email`.
  - Normalizes email (`strip().lower()`).
  - Enforces duplicate email rejection with safe client error (`EMAIL_ALREADY_REGISTERED`).
  - **Modern Password Policy**:
    - Length: 12 to 128 characters (`PASSWORD_TOO_SHORT`, `PASSWORD_TOO_LONG`).
    - Composition: No mandatory uppercase, lowercase, numbers, or special characters. Spaces and Unicode characters are accepted and preserved.
    - Weak password blocklist: Local list of obvious/common passwords evaluated case-insensitively and ignoring surrounding whitespace (`WEAK_PASSWORD`). (Local blocklist only; no external breached-password dependencies).
  - Hashes passwords using Werkzeug's secure `generate_password_hash` (`scrypt`). Plaintext is never stored or logged. Unstripped raw passwords are preserved for hashing.
  - Persists new `User` record to database.
  - Returns `201 Created` with standard envelope containing safe user dictionary (`id`, `name`, `email`), omitting `password_hash`.
- **Current Status**: Complete.

---

### Feature 11: User Login & JWT Authentication (Step 2)
- **Feature**: User authentication endpoint (`POST /api/auth/login`) issuing signed JSON Web Tokens (JWT).
- **Reason**: Enable registered users to authenticate securely with email normalization and password hash verification, receiving a stateless, time-bounded JWT access token for API identity.
- **Files Changed / Created**:
  - `requirements.txt` (Pinned `PyJWT==2.10.1`)
  - `backend/config.py` (Added `JWT_SECRET_KEY` with production safety check and `JWT_EXPIRATION_HOURS`)
  - `.env.example` (Added safe configuration placeholders for `JWT_SECRET_KEY` and `JWT_EXPIRATION_HOURS`)
  - `backend/services/auth_service.py` (Added `AuthCredentialsError`, `AuthService.login_user`, and `AuthService.verify_token`)
  - `backend/routes/auth_routes.py` (Added `POST /api/auth/login` endpoint)
  - `tests/conftest.py` (Added `JWT_SECRET_KEY` and `JWT_EXPIRATION_HOURS` to `TestConfig`)
  - `tests/test_auth_login.py` (New - 23 comprehensive login and JWT verification tests)
- **Implementation**:
  - Validates JSON payload structure, required string `email`, and required string `password`.
  - Normalizes email via `.strip().lower()`.
  - Queries `User` by normalized email.
  - Verifies submitted password against stored hash using `werkzeug.security.check_password_hash`.
  - Verifies account `is_active` status.
  - **Anti-Enumeration Security**: Nonexistent user, incorrect password, or inactive account all return an identical HTTP 401 response with `error_code: "INVALID_CREDENTIALS"` and message `"Invalid email or password."`.
  - Generates an HS256-signed JWT token containing minimal claims (`sub`, `iat`, `exp`). Excludes passwords, hashes, and personal data.
  - Returns `200 OK` with standard envelope containing `{ access_token, token_type: "Bearer", expires_in }`.
- **Tests**:
  - `tests/test_auth_login.py` (23 tests passed in 3.56s).
  - Complete test suite: 89 passed out of 89 tests in 5.09s.
- **Current Status**: Complete.

---

## 12. JWT Route Authorization & Identity Verification (Phase 3 Step 3)
- **Status**: Completed (Phase 3 Step 3).
- **Reason**: Provide a reusable, robust `@require_auth` decorator enabling protected API routes to securely identify the authenticated user from standard HTTP Bearer tokens.
- **Files Changed / Created**:
  - `backend/utils/auth.py` (New - reusable `@require_auth` decorator)
  - `backend/services/auth_service.py` (Enforced standard claims `['sub', 'iat', 'exp']` in `verify_token`)
  - `backend/routes/auth_routes.py` (Added protected demonstration endpoint `GET /api/auth/me`)
  - `tests/test_auth_authorization.py` (New - 23 comprehensive authorization tests)
- **Implementation**:
  - Extracts and validates HTTP `Authorization: Bearer <token>` header.
  - Returns HTTP 401 with `AUTHENTICATION_REQUIRED` for missing, empty, or non-Bearer headers.
  - Cryptographically verifies token signature, expiration, and mandatory claims (`sub`, `iat`, `exp`) using centralized `AuthService.verify_token()`.
  - Returns HTTP 401 with `TOKEN_EXPIRED` for expired tokens.
  - Returns HTTP 401 with `INVALID_TOKEN` for malformed, tampered, or claim-violating tokens.
  - Validates positive integer `sub` and binds it to request context: `g.current_user_id`.
  - Operates statelessly without querying database on every request.
  - Does NOT mask unexpected server exceptions as 401; permits internal errors to reach centralized HTTP 500 error handler.
  - Exposes `GET /api/auth/me` returning `{ "user_id": g.current_user_id }` inside the standard response envelope.
- **Tests**:
  - `tests/test_auth_authorization.py` (23 tests passed in 2.07s).
  - Complete test suite: 112 passed out of 112 tests in 10.02s.
- **Current Status**: Complete.

---

## 13. Scan Persistence Foundation (Phase 4 Step 1)
- **Status**: Completed (Phase 4 Step 1).
- **Reason**: Establish a reliable, transactional persistence foundation (`ScanService`) for persisting scans and analysis results without modifying detection routes or database schemas prematurely.
- **Files Changed / Created**:
  - `backend/services/scan_service.py` (New - `ScanService` with `create_scan`, `save_scan_result`, `get_scan_by_id`, `get_scan_result_by_scan_id`)
  - `tests/test_scan_service.py` (New - 14 comprehensive unit and integration tests)
- **Implementation**:
  - `create_scan`: Validates `media_type` and optional `user_id`, creates `Scan` with status `PENDING`, commits transaction, rolls back on `SQLAlchemyError` (`ScanDatabaseError`).
  - `save_scan_result`: Resolves target scan, verifies no existing result exists (`ScanConflictError`), creates `ScanResult`, updates parent `Scan.status` to `COMPLETED` and `completed_at` timestamp within the exact same database transaction, commits once, rolls back on `SQLAlchemyError` (`ScanDatabaseError`).
  - `get_scan_by_id`: Simple retrieval helper returning `Scan` model or `None`.
  - `get_scan_result_by_scan_id`: Simple retrieval helper returning `ScanResult` model or `None`.
  - Proportional input validation: Enforces non-empty strings and confidence float bounded in `[0.0, 1.0]` without rigid categorical restrictions.
  - Zero modifications to existing detection routes, authentication logic, or database schema.
- **Tests**:
  - `tests/test_scan_service.py` (14 tests passed in 0.88s).
  - Complete test suite: 126 passed out of 126 tests in 9.49s.
- **Current Status**: Complete.

---

## 14. Text Detection Scan Persistence (Phase 4 Step 2)
- **Status**: Completed (Phase 4 Step 2).
- **Reason**: Connect the existing text detection endpoint to authentication and scan persistence so that analyzed text scans are recorded, associated with the authenticated user, and transitioned to `COMPLETED` status.
- **Files Changed / Created**:
  - `backend/routes/text_routes.py` (Modified - protected with `@require_auth`, calls `ScanService.create_scan` and `ScanService.save_scan_result`, handles `ScanServiceError` cleanly)
  - `tests/test_text_detection.py` (Modified - updated regression tests with authentication fixtures and headers)
  - `tests/test_error_handling.py` (Modified - added auth header in 413 oversized payload test)
  - `tests/test_text_persistence.py` (New - 10 comprehensive unit and integration tests)
- **Implementation**:
  - `@require_auth`: Guards `POST /api/detect/text`, ensuring unauthenticated requests are rejected with standardized 401 responses.
  - Forensic Mapping: Maps detector outputs (`is_ai_generated`, `ai_confidence_score`, `metrics`, `sentence_breakdown`) into `prediction` (`AI_GENERATED` or `AUTHENTIC`), `confidence`, `risk_level` (`HIGH`, `MEDIUM`, `LOW`), and `result_data` JSON.
  - Scan Lifecycle: Scan is created in `PENDING` status (`user_id=g.current_user_id`, `media_type="text"`, `filename=None`), then updated atomically to `COMPLETED` with timestamp upon `save_scan_result()`.
  - Failure Handling: Catches `ScanServiceError` and logs server-side without leaking raw SQL or database errors, returning sanitized HTTP 500.
  - Preservation: Response envelope and detector data output remain completely backward-compatible. Image, video, audio, and abuse routes remain public and unchanged.
- **Tests**:
  - `tests/test_text_persistence.py` (10 tests passed in 2.25s).
  - `tests/test_text_detection.py` (5 tests passed in 1.28s).
  - Complete test suite: 136 passed out of 136 tests in 9.70s.
- **Current Status**: Complete.

---

## 15. Image Detection Scan Persistence (Phase 4 Step 3)
- **Status**: Completed (Phase 4 Step 3).
- **Reason**: Connect the existing image detection endpoint to authentication and scan persistence so that analyzed image scans are recorded, associated with the authenticated user, and transitioned to `COMPLETED` status with uploaded filename metadata.
- **Files Changed / Created**:
  - `backend/routes/image_routes.py` (Modified - protected with `@require_auth`, calls `ScanService.create_scan` with `filename=file.filename` and `ScanService.save_scan_result`, handles `ScanServiceError` cleanly)
  - `tests/test_image_detection.py` (Modified - updated regression tests with authentication fixtures and headers)
  - `tests/test_image_persistence.py` (New - 11 comprehensive unit and integration tests)
- **Implementation**:
  - `@require_auth`: Guards `POST /api/detect/image`, ensuring unauthenticated requests are rejected with standardized 401 responses before reading image bytes or running analysis.
  - Forensic Mapping: Maps detector outputs (`is_deepfake`, `confidence_score`, `manipulation_type`, `image_dimensions`, `heatmap_preview`) into `prediction` (`DEEPFAKE` or `AUTHENTIC`), `confidence`, `risk_level` (`HIGH`, `MEDIUM`, `LOW`), and `result_data` JSON.
  - Media Metadata: Records original uploaded filename in `Scan.filename`.
  - Exclusion of Raw Binary Bytes: Heavy uploaded file bytes are not stored in the database.
  - Scan Lifecycle: Scan is created in `PENDING` status (`user_id=g.current_user_id`, `media_type="image"`, `filename=file.filename`), then updated atomically to `COMPLETED` with timestamp upon `save_scan_result()`.
  - Failure Handling: Catches `ScanServiceError` and logs server-side without leaking raw SQL or database errors, returning sanitized HTTP 500.
  - Preservation: Response envelope and detector data output remain completely backward-compatible. Video, audio, and abuse routes remain public and unchanged.
- **Tests**:
  - `tests/test_image_persistence.py` (11 tests passed in 2.30s).
  - `tests/test_image_detection.py` (5 tests passed in 1.34s).
  - Complete test suite: 147 passed out of 147 tests in 13.34s.
- **Current Status**: Complete.

---

## 16. Video Detection Scan Persistence (Phase 4 Step 4)
- **Status**: Completed (Phase 4 Step 4).
- **Reason**: Connect the existing video detection endpoint to authentication and scan persistence so that analyzed video scans are recorded, associated with the authenticated user, and transitioned to `COMPLETED` status with uploaded filename metadata.
- **Files Changed / Created**:
  - `backend/routes/video_routes.py` (Modified - protected with `@require_auth`, calls `ScanService.create_scan` with `filename=file.filename` and `ScanService.save_scan_result`, handles `ScanServiceError` cleanly)
  - `tests/test_video_detection.py` (Modified - updated regression tests with authentication fixtures and headers)
  - `tests/test_video_persistence.py` (New - 12 comprehensive unit and integration tests)
- **Implementation**:
  - `@require_auth`: Guards `POST /api/detect/video`, ensuring unauthenticated requests are rejected with standardized 401 responses before saving temporary disk files or running frame analyses.
  - Forensic Mapping: Maps detector outputs (`is_deepfake`, `confidence_score`, `metrics`, `keyframe_heatmap_preview`) into `prediction` (`DEEPFAKE` or `AUTHENTIC`), `confidence`, `risk_level` (`HIGH`, `MEDIUM`, `LOW`), and `result_data` JSON.
  - Media Metadata: Records original uploaded filename in `Scan.filename`.
  - Exclusion of Raw Binary Bytes: Heavy uploaded video files, frames, and numpy arrays are not stored in the database.
  - Scan Lifecycle: Scan is created in `PENDING` status (`user_id=g.current_user_id`, `media_type="video"`, `filename=file.filename`), then updated atomically to `COMPLETED` with timestamp upon `save_scan_result()`.
  - Failure Handling: Catches `ScanServiceError` and logs server-side without leaking raw SQL or database errors, returning sanitized HTTP 500.
  - Preservation: Response envelope and detector data output remain completely backward-compatible. Audio and abuse routes remained unchanged in this step.
- **Tests**:
  - `tests/test_video_persistence.py` (12 tests passed in 4.54s).
  - `tests/test_video_detection.py` (5 tests passed).
  - Complete test suite: 159 passed out of 159 tests.
- **Current Status**: Complete.

---

## 17. Audio Detection Scan Persistence (Phase 4 Step 5)
- **Status**: Completed (Phase 4 Step 5).
- **Reason**: Connect the existing audio detection endpoint to authentication and scan persistence so that analyzed audio scans are recorded, associated with the authenticated user, and transitioned to `COMPLETED` status with uploaded filename metadata.
- **Files Changed / Created**:
  - `backend/routes/audio_routes.py` (Modified - protected with `@require_auth`, calls `ScanService.create_scan` with `filename=file.filename` and `ScanService.save_scan_result`, handles `ScanServiceError` cleanly)
  - `tests/test_audio_detection.py` (Modified - updated regression tests with authentication fixtures and headers)
  - `tests/test_audio_persistence.py` (New - 11 comprehensive unit and integration tests)
- **Implementation**:
  - `@require_auth`: Guards `POST /api/detect/audio`, ensuring unauthenticated requests are rejected with standardized 401 responses before running audio decoding or acoustic analysis.
  - Forensic Mapping: Maps detector outputs (`is_synthetic_audio`, `confidence_score`, `metrics`, `lip_sync_discrepancies`) into `prediction` (`SYNTHETIC` or `AUTHENTIC`), `confidence`, `risk_level` (`HIGH`, `MEDIUM`, `LOW`), and `result_data` JSON.
  - Media Metadata: Records original uploaded filename in `Scan.filename`.
  - Exclusion of Raw Binary Bytes: Heavy uploaded audio files, raw PCM samples, and numpy arrays are not stored in the database.
  - Scan Lifecycle: Scan is created in `PENDING` status (`user_id=g.current_user_id`, `media_type="audio"`, `filename=file.filename`), then updated atomically to `COMPLETED` with timestamp upon `save_scan_result()`.
  - Failure Handling: Catches `ScanServiceError` and logs server-side without leaking raw SQL or database errors, returning sanitized HTTP 500.
  - Preservation: Response envelope and detector data output remain completely backward-compatible. All 4 forensic modalities (text, image, video, audio) are now authenticated and persisted.
- **Tests**:
  - `tests/test_audio_persistence.py` (11 tests passed in 4.67s).
  - `tests/test_audio_detection.py` (4 tests passed).
  - Complete test suite: 170 passed out of 170 tests in 24.75s.
- **Current Status**: Complete.

---

## 18. User Scan History & Forensic Detail APIs (Phase 4 Step 6)
- **Status**: Completed (Phase 4 Step 6).
- **Reason**: Provide authenticated users with paginated, filterable access to their historical forensic scans, as well as single-scan detailed forensic views, with strict server-side user ownership scoping and anti-IDOR protections.
- **Files Changed / Created**:
  - `backend/services/scan_service.py` (Modified - added `get_user_scans` with eager loading and `get_user_scan_by_id`)
  - `backend/routes/scan_routes.py` (New - Blueprint implementing `GET /api/scans` and `GET /api/scans/<int:scan_id>`)
  - `backend/app.py` (Modified - registered `scan_bp` under `/api` URL prefix)
  - `tests/test_scan_history.py` (New - 20 comprehensive unit and integration tests)
- **Implementation**:
  - `@require_auth`: Protects both endpoints, extracting `user_id` strictly from verified JWT `sub` claims (`g.current_user_id`). Client-supplied `user_id` inputs are completely ignored.
  - User Ownership Scoping: All database queries filter on `Scan.user_id == g.current_user_id`.
  - IDOR Protection: Requesting an unowned scan returns HTTP 404 `SCAN_NOT_FOUND` (never 403), preventing scan ID enumeration.
  - Lightweight List Serialization: `GET /api/scans` returns lightweight summary items (`id`, `media_type`, `filename`, `status`, `created_at`, `completed_at`, and summary `result` fields `id`, `prediction`, `confidence`, `risk_level`), strictly excluding heavy Base64 `result_data`.
  - Full Forensic Detail: `GET /api/scans/<scan_id>` returns full forensic outcomes including complete `result_data` and heatmap data URLs.
  - Offset Pagination: Bounded pagination ($1 \le \text{page}$, $1 \le \text{per\_page} \le 100$) with `total_items`, `total_pages`, `has_next`, and `has_prev`.
  - Media Type Filtering: Optional `?media_type=` in `{"text", "image", "video", "audio"}` with strict 400 rejection of invalid types.
  - Query Performance: Uses `joinedload(Scan.result)` to eliminate N+1 queries.
  - Deterministic Ordering: Orders by `Scan.created_at.desc(), Scan.id.desc()`.
  - Error Sanitization: Catches `ScanDatabaseError` and returns sanitized HTTP 500 without leaking SQL.
- **Tests**:
  - `tests/test_scan_history.py` (20 tests passed in 6.03s).
  - Complete test suite: 190 passed out of 190 tests in 26.01s.
- **Current Status**: Complete.

---

## 19. Image Resource Bounds & Heatmap Thumbnail Downscaling (Phase 5 Step 2)
- **Status**: Completed (Phase 5 Step 2).
- **Reason**: Protect the backend from decompression-bomb memory exhaustion attacks (gigapixel images causing >10 GB RAM spikes and OOM worker crashes), and prevent multi-megabyte Base64 heatmap data URLs from bloating database storage and network responses.
- **Files Changed / Created**:
  - `backend/services/image_service.py` (Modified - added `MAX_IMAGE_WIDTH = 4096`, `MAX_IMAGE_HEIGHT = 4096`, `MAX_IMAGE_PIXELS = 16_777_216`, and `MAX_PREVIEW_DIMENSION = 512`; enforced post-decode dimension checking; downscaled heatmap overlay to thumbnail dimensions before Base64 encoding)
  - `tests/test_image_detection.py` (Modified - added 6 tests for width, height, pixel limits, boundary conditions, and thumbnail downscaling/no-upscaling)
  - `tests/test_image_persistence.py` (Modified - added 2 tests for oversized image zero-scan persistence and thumbnail persistence in ScanResult)
- **Implementation**:
  - Post-Decode Guard: Immediately after `cv2.imdecode()`, validates `w <= 4096`, `h <= 4096`, and `w * h <= 16,777,216`. If violated, raises `ValueError` returning HTTP 400 `PROCESSING_ERROR` before allocating float32 masks or running 2D Gaussian blurs.
  - Zero Orphan Scans: Rejected oversized images abort before `ScanService.create_scan()`, creating 0 database records.
  - Thumbnail Downscaling: Resizes preview overlay to max 512 px using `cv2.INTER_AREA` interpolation while preserving aspect ratio and leaving smaller images unscaled.
  - Slashed Storage: Reduces persisted preview sizes by 90%+ while preserving visual Grad-CAM++ diagnostic quality and API envelope compatibility.
- **Tests**:
  - `tests/test_image_detection.py` (11 tests passed in 2.97s).
  - `tests/test_image_persistence.py` (13 tests passed in 2.86s).
  - Complete test suite: 198 passed out of 198 tests in 25.21s.
- **Current Status**: Complete.

---

## 20. Video Temp File Cleanup & Resource Hardening (Phase 5 Step 3)
- **Status**: Completed (Phase 5 Step 3).
- **Reason**: Fix the critical Windows file handle lock leak where `cv2.VideoCapture` prevented temporary file deletion on failure, orphaning up to 50 MB files on disk. Enforce bounded resource consumption with video duration limits (max 120s) and resolution limits (max 4096x4096 / 16 MP) at container metadata and decoded frame levels.
- **Files Changed / Created**:
  - `backend/services/video_service.py` (Modified - restructured VideoCapture and tempfile lifecycle with deterministic `cap.release() -> os.remove()` cleanup order; dynamic upload suffix matching; enforced `MAX_VIDEO_DURATION_SECONDS = 120` and `MAX_VIDEO_WIDTH = 4096`, `MAX_VIDEO_HEIGHT = 4096`, `MAX_VIDEO_PIXELS = 16_777_216` on container metadata and decoded frame sampling)
  - `tests/test_video_detection.py` (Modified - added 13 focused tests for cleanup ordering, failure cleanup, duration limit, resolution bounds, boundary cases, and dynamic extensions)
  - `tests/test_video_persistence.py` (Modified - added 3 tests ensuring oversized duration/resolution videos create zero Scan records)
- **Implementation**:
  - **Deterministic Cleanup**: VideoCapture handle release is guaranteed before `os.remove(temp_path)` in `finally:`, preventing Windows `PermissionError [WinError 32]`. Warnings logged on failure instead of silent swallowing.
  - **Dynamic Extension Suffix**: Derives tempfile suffix from validated extension (`.mp4`, `.mov`, `.avi`, `.mkv`), safely defaulting to `.mp4`.
  - **Duration Bound**: If `fps > 0 and total_frames > 0` and `total_frames / fps > 120`, raises `ValueError` returning HTTP 400 `PROCESSING_ERROR` before keyframe sampling.
  - **Resolution Bounds**: Reads `CAP_PROP_FRAME_WIDTH` and `CAP_PROP_FRAME_HEIGHT` first, rejecting oversized videos at zero decode cost. Validates `frame.shape[:2]` during sampling to guard against missing/spoofed metadata.
  - **Persistence Invariant**: Rejected oversized/invalid videos abort before `ScanService.create_scan()`, persisting 0 scans.
  - **Detection Algorithm Preservation**: Number of sampled frames (16), Laplacian scoring, temporal instability, deepfake verdict threshold (0.65), and risk mapping remain identical.
- **Tests**:
  - `tests/test_video_detection.py` (18 tests passed in 4.54s).
  - `tests/test_video_persistence.py` (14 tests passed in 4.19s).
  - Complete test suite: 214 passed out of 214 tests in 44.17s.
- **Current Status**: Complete.

---

## 21. Audio Decoding & Format Integrity Hardening (Phase 5 Step 4)
- **Status**: Completed (Phase 5 Step 4).
- **Reason**: Eliminate the dangerous vulnerability where decoding failures silently generated synthetic random Gaussian noise (`np.random.normal(0, 0.1, 16000 * 3)`), producing fabricated detection results that were persisted into the forensic database. Restrict supported audio formats honestly to WAV (Option A) to match active decoder capabilities, validate decoded audio buffer integrity, enforce deterministic temporary file removal, and guarantee zero database persistence on rejected uploads.
- **Files Changed / Created**:
  - `backend/services/audio_service.py` (Modified - removed `np.random.normal` fallback; propagated clean `ValueError` on decode failure; validated `data.size > 0` and `sample_rate > 0`; ensured deterministic `try...finally` tempfile cleanup with warning logging on `OSError`)
  - `backend/utils/file_validator.py` (Modified - restricted `ALLOWED_AUDIO_EXTENSIONS` to `{"wav"}` to eliminate false claims of MP3/M4A/FLAC support for `scipy.io.wavfile`)
  - `tests/test_audio_detection.py` (Modified - added 10 tests for corrupt content, empty WAV, unsupported formats, elimination of synthetic noise fallback, buffer validation, and tempfile cleanup)
  - `tests/test_audio_persistence.py` (Modified - added 5 persistence invariant tests for corrupt, empty, unsupported, decoder failure, and zero-sample uploads)
  - `docs/decision.md` (Updated - added Decision 26)
  - `docs/flow.md` (Updated - updated Audio Detection flow with validation, error propagation, buffer checks, and cleanup)
  - `docs/bug.md` (Updated - added Bug 8 SEC-03)
  - `docs/test-checklist.md` (Updated - updated test counts to 234 passed and added audio test matrices)
  - `docs/context.md` (Updated - updated current status, architectural decisions, and next steps)
  - `docs/api/backend-api.md` (Updated - updated audio endpoint specs, WAV format restriction, and error responses)
- **Implementation**:
  - **Elimination of Fabricated Forensics**: Any failure to read or decode audio raises `ValueError("Failed to decode audio file. File might be corrupted or in an unsupported format.")`. The synthetic random normal generator was completely eliminated.
  - **Option A (WAV-Only Policy)**: Set `ALLOWED_AUDIO_EXTENSIONS = {"wav"}`. Non-WAV audio formats (`.mp3`, `.m4a`, `.flac`) fail fast at the validation boundary with HTTP 400 `INVALID_FORMAT`.
  - **Buffer Bounds**: Decoded buffers with zero samples (`data.size == 0`) or non-positive sample rates (`sample_rate <= 0`) immediately raise `ValueError`, preventing downstream division-by-zero crashes.
  - **Deterministic Cleanup**: `AudioDetectionService.analyze_audio()` wraps processing in `try...finally`. If `os.remove(temp_path)` fails, a warning is logged with error details instead of crashing or leaking files.
  - **Persistence Invariant**: Route catches `ValueError`, returning HTTP 400 `PROCESSING_ERROR` before calling `ScanService.create_scan()`. Corrupt, empty, or unreadable audio creates 0 `Scan` and 0 `ScanResult` records in the database.
  - **Algorithm Preservation**: Stereo-to-mono downmixing, peak normalization, ZCR, spectral energy variance, confidence scoring, lip-sync anomaly windows, risk level mappings, and success envelopes remain 100% identical for valid WAV files.
- **Tests**:
  - `tests/test_audio_detection.py` (17 passed in 6.97s).
  - `tests/test_audio_persistence.py` (18 passed in 6.96s).
  - Complete test suite: **234 passed out of 234 tests in 51.27s**.
- **Current Status**: Complete.

---

## 22. File Format / Magic-Byte Validation & Filename Security Hardening (Phase 5 Step 5)
- **Status**: Completed (Phase 5 Step 5).
- **Reason**: Protect TruthLens against file extension spoofing (arbitrary executables/scripts disguised as media files) and filename-based path traversal, alternate data stream abuse, control character injection, and directory navigation attacks.
- **Files Changed / Created**:
  - `backend/utils/file_validator.py` (Modified - implemented bounded stream prefix read with deterministic rewind; added magic-byte signature validation for images, videos, and audio; added `is_safe_filename` with length, control char, path separator, drive letter, and path traversal checks; standardized error codes)
  - `tests/test_file_validator.py` (Created - 26 unit tests for filename security, stream prefix rewind, format signatures, and error codes)
  - `tests/test_image_detection.py` (Modified - updated unsupported extension error code to `INVALID_FORMAT`, corrupt content test with valid JPEG prefix, added 7 magic-byte and filename security tests)
  - `tests/test_image_persistence.py` (Modified - updated unsupported extension error code, corrupt content test, added 3 persistence invariant tests)
  - `tests/test_video_detection.py` (Modified - updated corrupt content and mocked VideoCapture tests with valid MP4 header, dynamic suffix test with matching container headers, added 7 magic-byte and filename security tests)
  - `tests/test_video_persistence.py` (Modified - updated corrupt content test, added 3 persistence invariant tests)
  - `tests/test_audio_detection.py` (Modified - updated empty WAV error code, zero samples payload, invalid rate payload, cleanup on decoder failure payload, added 7 magic-byte and filename security tests)
  - `tests/test_audio_persistence.py` (Modified - updated empty audio error code, zero-sample payload, mock payload, added 3 persistence invariant tests)
  - `docs/decision.md` (Updated - added Decision 27)
  - `docs/flow.md` (Updated - updated Image, Video, and Audio detection flows with multi-layer validation)
  - `docs/feature.md` (Updated - added Feature 22)
  - `docs/bug.md` (Updated - added Bug 9 SEC-04)
  - `docs/test-checklist.md` (Updated - updated test counts and matrices)
  - `docs/context.md` (Updated - updated Phase 5 roadmap status)
  - `docs/api/backend-api.md` (Updated - updated API documentation with error codes and validation requirements)
- **Implementation**:
  - **Bounded Stream Reading & Deterministic Rewind**: `read_file_prefix(file_storage, 32)` reads only the initial 32 bytes and deterministically executes `stream.seek(pos)` in a `finally:` block, preventing consumption of the file stream for downstream decoders.
  - **Format-to-Signature Matching**:
    - Image: JPEG (`\xff\xd8\xff`), PNG (`\x89PNG\r\n\x1a\n`), WebP (`RIFF....WEBP`).
    - Video: MP4 (`ftyp` at bytes 4..8), MOV (conservative `ftyp` check at bytes 4..8), AVI (`RIFF....AVI ` / `AVIX`), MKV (`\x1a\x45\xdf\xa3`).
    - Audio: WAV only (`RIFF....WAVE` / `RIFX....WAVE`).
  - **Path Traversal & Filename Security**:
    - Rejects path separators (`/`, `\`), Windows drive letters (`:`), control characters and null bytes (`ord < 32 or ord == 127`), excessive length (> 255 chars), dot directory navigation (`.`, `..`), dot prefixes/suffixes, and leading/trailing whitespace.
    - Explicitly allows legitimate ordinary characters: spaces, international Unicode characters, and ordinary double dots (e.g. `audit..v1.jpg`).
  - **Standardized Error Codes**:
    - `INVALID_FILE` (HTTP 400): File missing, empty filename, or unsafe filename.
    - `INVALID_FORMAT` (HTTP 400): Disallowed extension, signature mismatch, or extension-content mismatch.
    - `PROCESSING_ERROR` (HTTP 400): Malformed internal stream failing decoder execution.
  - **Zero-Scan Persistence Invariant**: All invalid or spoofed uploads are rejected at the validator boundary before reaching detection services, creating exactly 0 `Scan` or `ScanResult` database records.
- **Tests**:
  - `tests/test_file_validator.py` (26 passed).
  - `tests/test_image_detection.py` (24 passed).
  - `tests/test_image_persistence.py` (16 passed).
  - `tests/test_video_detection.py` (31 passed).
  - `tests/test_video_persistence.py` (17 passed).
  - `tests/test_audio_detection.py` (31 passed).
  - `tests/test_audio_persistence.py` (21 passed).
  - Complete test suite: **309 passed out of 309 tests in 83.47s**.
- **Current Status**: Complete.

---

## 23. Multi-Modal Resource Bounds & Forensic Payload Hardening (Phase 5 Step 6)
- **Status**: Completed (Phase 5 Step 6).
- **Reason**: Harmonize resource constraints and enforce strict database payload discipline across all four detection modalities (Text, Video, Audio, Image). Resolves SEC-05 (unbounded text input DoS & sentence breakdown database explosion), SEC-06 (unscaled 4K video keyframe heatmap preview bloat), and SEC-07 (missing audio duration bounds).
- **Files Changed / Created**:
  - `backend/services/text_service.py` (Modified - introduced authoritative `MAX_TEXT_LENGTH = 25_000` and `MAX_SENTENCE_BREAKDOWN_ITEMS = 100`; analyzes complete accepted text while capping persisted sentence breakdown; documented capping behavior)
  - `backend/routes/text_routes.py` (Modified - imported `MAX_TEXT_LENGTH`; added validation check rejecting text > 25,000 characters with HTTP 400 `TEXT_TOO_LONG` before database scan creation)
  - `backend/services/video_service.py` (Modified - introduced `MAX_PREVIEW_DIMENSION = 512`; downscaled keyframe heatmap overlay thumbnail using `cv2.INTER_AREA` before JPEG Base64 encoding without resizing detection frame)
  - `backend/services/audio_service.py` (Modified - introduced `MAX_AUDIO_DURATION_SECONDS = 120`; cleanly rejects audio exceeding 120s with HTTP 400 `PROCESSING_ERROR` before persistence)
  - `tests/test_text_detection.py` (Modified - added 4 unit/route tests for `TEXT_TOO_LONG`, 25,000 char boundary, and 100-sentence breakdown capping)
  - `tests/test_text_persistence.py` (Modified - added 2 persistence invariant tests verifying 0 scans created on `TEXT_TOO_LONG` and persisted breakdown capping in `ScanResult.result_data`)
  - `tests/test_video_detection.py` (Modified - added 2 tests verifying 1280x720 video keyframe preview is downscaled to <= 512px thumbnail while small video is not upscaled)
  - `tests/test_video_persistence.py` (Modified - added 1 persistence test verifying high-res video persists downscaled thumbnail in database)
  - `tests/test_audio_detection.py` (Modified - added 3 tests for audio duration limit enforcement (> 120s rejected, 120.0s boundary accepted, direct service exception))
  - `tests/test_audio_persistence.py` (Modified - added 1 persistence invariant test verifying audio > 120s creates 0 scans)
  - `scratch/verify_live_resource_bounds_and_payloads.py` (Created - live in-process verification script covering all 7 scenarios and database invariants)
  - `docs/decision.md` (Updated - added Decision 28)
  - `docs/flow.md` (Updated - updated Text, Video, and Audio detection execution flows)
  - `docs/feature.md` (Updated - added Feature 23)
  - `docs/bug.md` (Updated - added Bug 10 SEC-05, SEC-06, SEC-07)
  - `docs/test-checklist.md` (Updated - updated test counts and matrix entries)
  - `docs/context.md` (Updated - updated completed work, architecture decisions, and roadmap status)
  - `docs/api/backend-api.md` (Updated - updated API documentation with text length bounds, `TEXT_TOO_LONG` error code, audio duration limits, and thumbnail downscaling guarantees)
- **Implementation**:
  - **Text Length Bounds**: Defined `MAX_TEXT_LENGTH = 25_000` (~4,000–5,000 words). Validated at route level before any database operations; returns HTTP 400 `TEXT_TOO_LONG`.
  - **Sentence Breakdown Capping**: `TextDetectionService.analyze_text` evaluates global metrics over the complete accepted text, but caps `sentence_breakdown` list to the first 100 entries (`MAX_SENTENCE_BREAKDOWN_ITEMS = 100`) to prevent database bloat.
  - **Video Keyframe Thumbnail Downscaling**: Applied `MAX_PREVIEW_DIMENSION = 512` to `suspicious_frame` overlay before JPEG encoding, slashing payload from ~2.5MB down to ~30–60KB per scan while keeping detection frames at original resolution.
  - **Audio Duration Bounds**: Enforced `MAX_AUDIO_DURATION_SECONDS = 120` in `AudioDetectionService.analyze_audio()`, aligning with the video duration limit.
  - **Zero-Scan Persistence Invariants**: All out-of-bounds or rejected uploads return HTTP 400 before `ScanService.create_scan()`, guaranteeing exactly 0 `Scan` and 0 `ScanResult` database records.
- **Tests**:
  - `tests/test_text_detection.py`: 9 passed.
  - `tests/test_text_persistence.py`: 12 passed.
  - `tests/test_video_detection.py`: 33 passed.
  - `tests/test_video_persistence.py`: 18 passed.
  - `tests/test_audio_detection.py`: 34 passed.
  - `tests/test_audio_persistence.py`: 22 passed.
  - Complete test suite: **322 passed out of 322 tests in 67.88s**.
- **Current Status**: Complete.
