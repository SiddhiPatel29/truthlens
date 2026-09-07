# VeraMedia AI Backend Context & Handover State

## 1. Project Overview
VeraMedia AI (`truthlens`) is a multi-modal deepfake detection and abuse takedown platform.
- **Backend Responsibility**: REST APIs, forensic signal processing services, database models, migrations, security, and testing.
- **Frontend Responsibility**: Independently developed by other team members. The backend must strictly avoid modifying frontend code and must preserve API contract stability.

---

## 2. Completed Work

### Phase 1: Clean, Testable, Secure Foundation
1. **Dependency declarations fixed**: Added missing dependencies (`numpy==2.2.3`, `opencv-python==4.11.0.86`, `scipy==1.15.2`, `pytest==8.3.4`) to `requirements.txt`.
2. **Environment isolation**: Created `.venv` on Python 3.13.7; verified all dependencies install cleanly.
3. **Environment configuration**: Created safe `.env.example` template; hardened `backend/config.py`.
4. **Centralized error handling**: Created `backend/utils/errors.py` registering uniform JSON handlers for 400, 404, 405, 413, and 500 errors.
5. **Information leakage prevention**: Sanitized all route exception blocks; replaced `f"Internal Error: {str(e)}"` with safe messages; replaced `print`/`traceback` with structured logging.
6. **File validation refactoring**: Centralized extension validation in `backend/utils/file_validator.py`.
7. **Automated test suite**: Built 29 unit and integration tests under `tests/`.
8. **Documentation suite**: Created 9 comprehensive documentation artifacts.

### Phase 2: Database Foundation (SQLAlchemy + Alembic)
1. **Database package added**: Added `SQLAlchemy==2.0.52`, `Flask-SQLAlchemy==3.1.1`, `alembic==1.19.2`, and `Flask-Migrate==4.1.0` to `requirements.txt`.
2. **Database architecture**:
   - `backend/database/db.py`: Shared `db` and `migrate` instances with SQLite `PRAGMA foreign_keys=ON;` connection hook.
   - `backend/database/models.py`: Declarative models:
     - `User`: id, name, email (unique index), password_hash, is_active, created_at, updated_at.
     - `Scan`: id, user_id (nullable FK), media_type, filename, status, created_at, completed_at.
     - `ScanResult`: id, scan_id (unique FK), prediction, confidence, risk_level, result_data (JSON), created_at.
     - `AbuseReport`: id, user_id (nullable FK), scan_id (nullable FK), platform, status, report_data (JSON), created_at.
   - `backend/database/__init__.py`: Re-exports `db`, `migrate`, and all 4 models.
3. **Application factory integration**: Initialized `db.init_app(app)` and `migrate.init_app(app, db)` in `backend/app.py`.
4. **Migrations**: Initialized `migrations/` with Flask-Migrate; generated initial revision `f3e901358e24`; successfully upgraded `instance/truthlens.db`.
5. **Automated testing**: Created `tests/test_database.py` with 12 tests covering model creation, unique email constraint, 1-to-many and 1-to-1 relationships, foreign key enforcement, and migration schema verification. Total test suite expanded to **41 passed tests in 0.62s**.

### Phase 3: Authentication & Identity Management (In Progress)
1. **User Registration Implemented (Step 1)**:
   - Created `backend/services/auth_service.py` (`AuthService`, `AuthValidationError`).
   - Created `backend/routes/auth_routes.py` (`auth_bp` exposing `POST /api/auth/register`).
   - Registered `auth_bp` in `backend/app.py` under `/api`.
   - Used Werkzeug's built-in `generate_password_hash` (`scrypt`) and pinned `Werkzeug==3.1.8` in `requirements.txt`.
   - Implemented modern password policy: 12-128 characters, no mandatory composition rules, spaces and Unicode allowed/preserved, local weak-password blocklist (`WEAK_PASSWORD`). (Local blocklist only; no external breached-password check).
   - Implemented validation for required name, valid email, email normalization (`strip().lower()`), and duplicate email rejection.
   - Preserved response envelope returning `{ id, name, email }` without exposing `password_hash`.
   - Added 25 unit and integration tests in `tests/test_auth_registration.py`.
2. **User Login & JWT Authentication Implemented (Step 2)**:
   - Added and pinned `PyJWT==2.10.1` in `requirements.txt`.
   - Configured `JWT_SECRET_KEY` (with production safety checks) and `JWT_EXPIRATION_HOURS` (defaults to 24h) in `backend/config.py` and `.env.example`.
   - Added `AuthCredentialsError` and `login_user` to `backend/services/auth_service.py`:
     - Validates payload structure and required non-empty string fields.
     - Normalizes email via `.strip().lower()`.
     - Verifies password against stored hash using `check_password_hash`.
     - Verifies account `is_active == True`.
     - Implements strict anti-enumeration security: nonexistent email, wrong password, and inactive user return identical HTTP 401 generic error (`INVALID_CREDENTIALS`).
     - Issues signed HS256 JWT access token with minimal claims (`sub`, `iat`, `exp`).
   - Added `verify_token` helper to decode and validate tokens against expiration and signature.
   - Implemented `POST /api/auth/login` in `backend/routes/auth_routes.py`.
   - Created `tests/test_auth_login.py` with 23 comprehensive tests.
3. **JWT Authorization & Protected Route Verification (Step 3)**:
   - Created `backend/utils/auth.py` providing the `@require_auth` decorator.
   - Enforced standard claims `['sub', 'iat', 'exp']` centrally in `AuthService.verify_token()`.
   - Bound validated integer user ID to `g.current_user_id` without query overhead.
   - Standardized 401 error codes (`AUTHENTICATION_REQUIRED`, `INVALID_TOKEN`, `TOKEN_EXPIRED`).
   - Preserved centralized error handlers so unhandled server errors return HTTP 500 without masking.
   - Added `GET /api/auth/me` returning `{ "user_id": g.current_user_id }`.
   - Created `tests/test_auth_authorization.py` with 23 comprehensive tests.

### Phase 4: Scan Persistence & User History (In Progress)
1. **Scan Persistence Foundation (Step 1)**:
   - Created `backend/services/scan_service.py` (`ScanService`):
     - `create_scan`: Validates inputs, creates `Scan` in `PENDING` status, commits transaction, executes `db.session.rollback()` on `SQLAlchemyError` (`ScanDatabaseError`).
     - `save_scan_result`: Resolves target scan, enforces 1-to-1 constraint by rejecting duplicates (`ScanConflictError`), creates `ScanResult`, updates parent `Scan.status` to `COMPLETED` and `completed_at` within the exact same database transaction, commits once, and executes `db.session.rollback()` on `SQLAlchemyError`.
     - `get_scan_by_id`: Simple retrieval helper returning `Scan` or `None`.
     - `get_scan_result_by_scan_id`: Simple retrieval helper returning `ScanResult` or `None`.
     - Proportional validation: Enforces non-empty strings and confidence float in `[0.0, 1.0]` without hard-coded prediction enums.
   - Created `tests/test_scan_service.py` with 14 comprehensive tests.
   - Total test suite expanded to **126 passed tests in 9.49s**.
2. **Text Detection Scan Persistence (Step 2)**:
   - Connected `POST /api/detect/text` to `@require_auth` and `ScanService`.
   - Identified authenticated user from `g.current_user_id` populated by `@require_auth`.
   - Persisted scan in `PENDING` status (`media_type="text"`, `filename=None`, `user_id=g.current_user_id`).
   - Mapped detector output into `prediction` (`AI_GENERATED` or `AUTHENTIC`), `confidence`, `risk_level` (`HIGH`, `MEDIUM`, `LOW`), and `result_data` JSON.
   - Saved result atomically and transitioned scan to `COMPLETED` status with UTC timestamp via `ScanService.save_scan_result()`.
   - Caught `ScanServiceError` cleanly to log server-side and return sanitized HTTP 500 without leaking raw database/SQL details.
   - Preserved all existing response envelope fields, detector output format, and 400 validation behavior.
   - Kept image, video, audio, and abuse detection endpoints public and unmodified.
   - Created `tests/test_text_persistence.py` with 10 comprehensive tests.
   - Total test suite expanded to **136 passed tests in 9.70s**.
3. **Image Detection Scan Persistence (Step 3)**:
   - Connected `POST /api/detect/image` to `@require_auth` and `ScanService`.
   - Bound authenticated user ID from `g.current_user_id`.
   - Persisted scan in `PENDING` status with `media_type="image"`, `filename=file.filename`, and `user_id=g.current_user_id`.
   - Mapped detector output into `prediction` (`DEEPFAKE` or `AUTHENTIC`), `confidence`, `risk_level` (`HIGH`, `MEDIUM`, `LOW`), and `result_data` JSON (metadata + heatmap preview; no raw image bytes).
   - Saved result atomically and transitioned scan to `COMPLETED` status with UTC timestamp via `ScanService.save_scan_result()`.
   - Handled persistence failures cleanly with sanitized HTTP 500 responses without leaking raw SQL.
   - Preserved all response envelope fields and validation behaviors.
   - Video, audio, and abuse detection endpoints remain public and unmodified.
   - Created `tests/test_image_persistence.py` with 11 comprehensive tests.
   - Total test suite expanded to **147 passed tests in 13.34s**.

---

## 3. Currently Being Worked On
- Phase 4 Step 3 (Image Detection Scan Persistence) is complete and verified with 147/147 tests passing. Ready for user commit.

---

## 4. Important Architectural Decisions
- **Application Factory (`create_app`)**: Allows flexible testing with `TestConfig` (in-memory SQLite `sqlite:///:memory:`) and dynamic configuration.
- **SQLAlchemy 2.0 & Flask-Migrate**: Portable ORM with versioned Alembic batch migrations.
- **SQLite Foreign Key Enforcement**: Enforced via SQLAlchemy engine connect event hook executing `PRAGMA foreign_keys=ON`.
- **Werkzeug `scrypt` Password Hashing**: Built-in, zero-dependency, highly secure memory-hard password hashing.
- **Stateless JWT Tokens (`PyJWT`)**: HS256 signed access tokens with minimal claims (`sub`, `iat`, `exp`) and 24-hour expiration.
- **Anti-Enumeration Login Security**: Generic HTTP 401 (`INVALID_CREDENTIALS`) for all authentication failures prevents account/email discovery.
- **Stateless Authorization Decorator (`@require_auth`)**: Pure cryptographic verification without DB hits; binds integer user ID to `g.current_user_id`.
- **Isolated Persistence Service (`ScanService`)**: Decouples database operations from pure signal processing algorithms and route controllers.
- **Atomic Single-Transaction Commit**: `save_scan_result` persists the `ScanResult` and updates the parent `Scan` in one atomic commit, rolling back on failure.
- **Controlled One-to-One Conflict Rejection**: Proactively raises `ScanConflictError` when attempting to attach a duplicate result to a scan.
- **Specific Database Error Handling**: Specifically catches `SQLAlchemyError` for session rollback and `ScanDatabaseError`, allowing unexpected programming errors to bubble up naturally.
- **Authenticated Text & Image Persistence**: Both `POST /api/detect/text` and `POST /api/detect/image` require Bearer JWT; scans are owned by authenticated users; original uploaded filename metadata is recorded for media; raw binary image bytes are excluded from database storage.
- **Uniform Response Envelope**: Every endpoint returns `{ success, message, data, error_code }`.

---

## 5. Known Limitations & Remaining Problems
1. **Unpersisted Video/Audio Endpoints**: Video and audio detection endpoints compute and return results directly to the client but do not yet invoke `ScanService` (deferred to subsequent Phase 4 steps).
2. **Heuristic vs True Deep Learning**: Detection services currently utilize signal heuristics (Laplacian edge variance, Zero Crossing Rate, burstiness) rather than heavy neural network models.
3. **Basic File Validation**: Media validation inspects extensions and sizes; binary magic-byte inspection belongs to future security hardening (Phase 5).
4. **Simulated Abuse Relay**: The abuse dispatcher calculates SHA-256 fingerprints and formats compliance dossiers, but does not yet connect to external third-party takedown APIs.
5. **Deferred Refresh Tokens & RBAC**: Tokens have a 24-hour expiration; token rotation/refresh and role-based permissions are deferred to future dedicated phases.

---

## 6. Recommended Next Backend Task (Phase 4 — Step 4)
Implement **Phase 4 Step 4: Video Detection Scan Persistence**:
1. Wire `@require_auth` into `POST /api/detect/video`.
2. Persist video scan with `media_type="video"`, `filename=file.filename`, and `user_id=g.current_user_id`.
3. Map video analysis output (`is_deepfake`, `confidence_score`, anomaly keyframe preview) to `ScanResult`.
4. Add focused video persistence tests and ensure zero regressions across other modalities.


