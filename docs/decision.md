# Architectural & Technical Decisions Log

This document records the foundational architectural and technical decisions made during backend development for the VeraMedia AI (`truthlens`) project.

---

## Decision 1: Application Factory Pattern (`create_app`)

### Decision
Use a Flask application factory function `create_app(config_class=Config)` in `backend/app.py` instead of a globally instantiated `app = Flask(__name__)` singleton at module scope.

### Reason
An application factory allows dynamic instantiation of the application with varying configurations (e.g. `TestConfig` for automated tests, `DevelopmentConfig` for local runs, `ProductionConfig` for staging/production). It cleanly isolates test suites and prevents state leaks between tests.

### Alternatives Considered
- **Global `app` singleton at module level**: Simpler to write initially, but makes testing difficult because config overrides, mocking, and isolated instances cannot be created cleanly per test session.
- **Class-based application wrapper**: Over-engineered for a lightweight Flask REST backend.

### Why the Chosen Approach Was Preferred
The factory pattern is the Flask standard best practice. It provides maximum testability and clean lifecycle management with minimal boilerplate.

---

## Decision 2: Centralized Error Handling & Uniform JSON Envelope

### Decision
Implement centralized error handlers via `backend/utils/errors.py` covering HTTP 400, 404, 405, 413, and 500/unhandled exceptions, and sanitize all route exception blocks so internal stack traces and paths are never returned to clients.

### Reason
Prior to Phase 1, unhandled endpoints and method errors returned Flask's default HTML error pages, and routes like `image_routes.py` returned `f"Internal Error: {str(e)}"`. This leaked internal server paths, library names, and exception details to clients, creating security risks and breaking frontend JSON parser expectations.

### Alternatives Considered
- **Ad-hoc try/catch blocks in every route returning custom error dicts**: High maintenance, prone to human error, does not catch framework-level errors (404, 405, 413).
- **Third-party error handling extensions (e.g. Flask-RESTful error handlers)**: Introduces extra unneeded dependencies.

### Why the Chosen Approach Was Preferred
Registering `@app.errorhandler` hooks in Flask centralizes all error responses into a single function, guaranteeing that the frontend receives the identical JSON envelope (`{ success, message, data, error_code }`) regardless of what layer triggered the error.

---

## Decision 3: Pinned Dependencies Compatible with Python 3.13

### Decision
Determine the active runtime Python environment (Python 3.13.7 on Windows x64) and pin exact tested versions in `requirements.txt`:
- `Flask==3.0.3`
- `flask-cors==4.0.1`
- `python-dotenv==1.0.1`
- `gunicorn==22.0.0`
- `numpy==2.2.3`
- `opencv-python==4.11.0.86`
- `scipy==1.15.2`
- `pytest==8.3.4`
- `SQLAlchemy==2.0.52`
- `Flask-SQLAlchemy==3.1.1`
- `alembic==1.19.2`
- `Flask-Migrate==4.1.0`

### Reason
Earlier audits revealed that `numpy`, `opencv-python`, and `scipy` were actively imported by the forensic services but completely absent from `requirements.txt`. Without pinning, automated deployment or fresh clones would break with runtime `ImportError` or install incompatible wheel versions on Python 3.13. In Phase 2, SQLAlchemy and Flask-Migrate were similarly pinned to tested releases.

### Alternatives Considered
- **Open-ended version ranges (`>=`)**: Vulnerable to future breaking changes in upstream dependencies (especially with NumPy 2.x ABI changes affecting C extensions like OpenCV/SciPy).
- **Loose unpinned requirements**: Non-deterministic builds across different developer machines.

### Why the Chosen Approach Was Preferred
Using tested, pre-compiled binary wheel versions compatible with Python 3.13 ensures deterministic, fast installation without requiring local C/C++ compilers on Windows or Linux.

---

## Decision 4: Virtual Environment Isolation (`.venv`)

### Decision
Install and test all dependencies within a clean local virtual environment (`.venv`) created via `python -m venv .venv`, leaving the host system Python installation pristine.

### Reason
Ensures project dependency hygiene, prevents conflicts with other system packages, and verifies that the declared `requirements.txt` is 100% self-contained and reproducible.

### Alternatives Considered
- **Installing into the global Python environment**: Risk of polluting system packages, masking missing dependencies, or breaking system-level Python utilities.
- **Docker containers in Phase 1/2**: Explicitly ruled out to avoid premature complexity on local Windows development before core stabilization.

### Why the Chosen Approach Was Preferred
Standard Python `.venv` provides zero-overhead isolation, is natively supported across all platforms, and is already git-ignored.

---

## Decision 5: Pytest as the Testing Framework

### Decision
Adopt `pytest` with a modular test suite organized in `tests/` utilizing standard fixtures in `conftest.py`.

### Reason
`pytest` offers powerful fixture management, clean assert syntax without boilerplate subclasses, detailed diff output on failures, and fast execution speed (41 tests executed in ~0.62s).

### Alternatives Considered
- **Standard library `unittest`**: Functional, but requires verbose boilerplate classes (`self.assertEqual`) and awkward test discovery syntax.
- **No automated test runner (relying on manual Postman/curl scripts)**: Prone to regressions, impossible to run automatically, and untrustworthy.

### Why the Chosen Approach Was Preferred
`pytest` is the de facto Python industry standard. Its fixture pattern seamlessly integrates with Flask's test client (`client.get`, `client.post`) and SQLAlchemy transaction rollbacks.

---

## Decision 6: Preservation of Existing Forensic Signal Logic in Phase 1 & 2

### Decision
Retain existing heuristic forensic signal algorithms in `TextDetectionService`, `ImageDetectionService`, `VideoDetectionService`, and `AudioDetectionService` without attempting to replace them with large neural network models (e.g. CLIP, ResNet, Whisper) during Phase 1 and Phase 2.

### Reason
The goal of Phase 1 and Phase 2 is establishing a clean, secure, and testable backend and database foundation. Replacing signal-processing logic with heavy deep learning weights would introduce huge model files (>2 GB), complex GPU/Torch dependencies, high latency, and cloud deployment complexity prematurely.

### Alternatives Considered
- **Immediately downloading pre-trained PyTorch / HuggingFace deepfake models**: Would derail foundation goals, balloon dependency footprint, and introduce environment instability.
- **Stubbing services with static mock data**: Would delete working signal processing logic already present in the codebase.

### Why the Chosen Approach Was Preferred
Preserving the existing mathematical heuristics (Laplacian variance, ZCR, burstiness, Grad-CAM++ style heatmap rendering) allows the entire end-to-end API pipeline to be verified with real media while keeping the architecture lean and responsive.

---

## Decision 7: Refactoring File Validation into Shared Utilities without MIME/Magic-byte Overhaul

### Decision
Consolidate media extension checking into `backend/utils/file_validator.py` (`validate_image_file`, `validate_video_file`, `validate_audio_file`) to eliminate duplicate validation code in routes, but defer magic-byte / MIME inspection (`python-magic`) to a later security hardening phase.

### Reason
Routes were inconsistently validating filenames and extensions. Centralizing this logic into pure functions ensures DRY principles and consistent error codes (`MISSING_FILE`, `INVALID_FILE`, `INVALID_FORMAT`). Deferring binary magic-byte inspection adheres to the user instruction to avoid over-engineering file security until Phase 2 is stabilized.

### Alternatives Considered
- **Leaving validation logic duplicated inside each route**: Hard to maintain, inconsistent error messages.
- **Adding `python-magic` / `libmagic` in Phase 1/2**: `libmagic` requires external binary DLLs on Windows which often causes installation friction for beginners.

### Why the Chosen Approach Was Preferred
Cleanly refactored Python utility functions provide immediate consistency without introducing difficult external native dependencies.

---

## Decision 8: Standard Python Structured Logging over Print/Traceback

### Decision
Replace `print()` and `traceback.print_exc()` with `logging.getLogger(__name__)` configured via `logging.basicConfig()` in `backend/app.py`.

### Reason
`print()` statements cannot be filtered by log level (DEBUG, INFO, WARNING, ERROR), lack timestamps, do not include module context, and mix stdout with diagnostic output. Standard logging allows production silencing of debug messages, structured formatting, and integration with log management tools.

### Alternatives Considered
- **Leaving `print()` statements**: Insecure, difficult to manage in production.
- **Heavy logging frameworks (e.g. Loguru, ELK stack integrations)**: Overkill for foundational phases.

### Why the Chosen Approach Was Preferred
Python's built-in `logging` module is zero-dependency, robust, and standard across all Python backend architectures.

---

## Decision 9: SQLAlchemy 2.0 & Flask-SQLAlchemy 3.1 ORM for Persistence

### Decision
Adopt SQLAlchemy 2.0 via Flask-SQLAlchemy 3.1 to manage models, sessions, and relational mappings for `User`, `Scan`, `ScanResult`, and `AbuseReport`.

### Reason
SQLAlchemy provides battle-tested object-relational mapping, automatic connection pooling, unit-of-work transaction management, and portability between SQLite (local development and in-memory testing) and PostgreSQL (production).

### Alternatives Considered
- **Raw `sqlite3` queries**: No schema migrations, error-prone string query building, lack of relationship navigation, and difficult to migrate to PostgreSQL.
- **Peewee / Tortoise ORM**: Lacks the deep ecosystem, Flask-Migrate integration, and enterprise-grade Alembic support of SQLAlchemy.

### Why the Chosen Approach Was Preferred
SQLAlchemy is the undisputed gold standard for Python web backends.

---

## Decision 10: Database Migrations via Flask-Migrate & Alembic (Batch Mode)

### Decision
Manage database schema versioning using Flask-Migrate with Alembic batch mode enabled.

### Reason
Database schemas evolve continuously. Tracking schema changes through versioned migration scripts allows zero-downtime upgrades, rollbacks, and team synchronization across different development environments without destroying data.

### Alternatives Considered
- **`db.create_all()` in production**: Cannot modify existing tables, rename columns, or apply schema changes without dropping and recreating the database.
- **Manual SQL DDL upgrade scripts**: Prone to human omission and hard to verify across database dialects.

### Why the Chosen Approach Was Preferred
Flask-Migrate exposes standard CLI commands (`flask db init`, `flask db migrate`, `flask db upgrade`) and generates auto-migration scripts that inspect models against the database.

---

## Decision 11: SQLite Foreign Key Enforcement via Engine Connect Hook

### Decision
Attach an SQLAlchemy engine connect event listener in `backend/database/db.py` to issue `PRAGMA foreign_keys=ON;` whenever an SQLite connection is opened.

### Reason
By default in SQLite, `FOREIGN KEY` constraints are accepted in DDL syntax but ignored during DML execution unless explicitly enabled per-connection via PRAGMA. Without this hook, inserting records with invalid foreign keys would silently succeed, leading to orphaned records and corrupt relational integrity during development and testing.

### Alternatives Considered
- **Relying on application-level checks without DB constraints**: Brittle, bypassed by direct queries or subtle logic bugs.
- **Only enforcing foreign keys when using PostgreSQL**: Masks bugs during local development and testing.

### Why the Chosen Approach Was Preferred
The connection hook ensures SQLite behaves like a real relational database, failing fast on invalid foreign keys in both unit tests and local runs.

---

## Decision 12: Nullable `Scan.user_id` and Public Endpoints in Phase 2

### Decision
Keep `Scan.user_id` nullable (`nullable=True`) and do not yet wire existing detection endpoints to write to the database.

### Reason
Phase 2 establishes the database foundation only. Authentication, JWT tokens, and user sessions are explicitly planned for Phase 3. Keeping `user_id` nullable allows the model to support both anonymous scans (for public demo use) and authenticated user scans (in Phase 3) without breaking existing detection API contracts.

### Alternatives Considered
- **Making `user_id` non-nullable immediately**: Would require creating fake mock users or blocking unauthenticated API usage prematurely.
- **Immediately modifying detection routes to record scans**: Deviates from Phase 2 scope and risks introducing route regressions before authentication exists.

### Why the Chosen Approach Was Preferred
Preserves Phase 2 isolation and keeps detection endpoints decoupled until authentication and user context are formally implemented.

---

## Decision 13: Native JSON Column Type for Forensic Results and Dossier Manifests

### Decision
Use `db.JSON` for `ScanResult.result_data` and `AbuseReport.report_data`.

### Reason
Forensic analysis metrics (e.g. sentence breakdowns, Grad-CAM++ Base64 previews, lip-sync intervals, cryptographic manifests) vary across modalities (text vs image vs video vs audio). A structured JSON column provides maximum flexibility without requiring separate table schemas for every forensic modality.

### Alternatives Considered
- **Serialized string / Text column**: Requires manual `json.loads` / `json.dumps` across all query points and loses dialect-native JSON indexing in PostgreSQL.
- **Separate normalized tables for each modality's metrics**: High schema complexity for prototype signal data that is still evolving.

### Why the Chosen Approach Was Preferred
`db.JSON` stores native Python dictionaries seamlessly, maps to JSONB in PostgreSQL, and stores valid JSON text in SQLite.

---

## Decision 14: Werkzeug Password Hashing (`scrypt`) over External Cryptographic Libraries

### Decision
Use `werkzeug.security.generate_password_hash` and `werkzeug.security.check_password_hash` for password security, explicitly pinning `Werkzeug==3.1.8` in `requirements.txt`.

### Reason
Werkzeug is a core dependency of Flask and is already installed in the environment. In Werkzeug 3.x, `generate_password_hash` defaults to `scrypt`, an advanced memory-hard key derivation function recommended by NIST and OWASP for password storage. It provides excellent resistance against GPU/ASIC hardware-accelerated brute-force attacks.

### Alternatives Considered
- **`passlib` / `bcrypt`**: Adds external dependencies with binary C extensions that often cause build/wheel installation issues on different platforms (especially Windows with Python 3.13). Furthermore, `passlib` has been unmaintained for several years and issues deprecation warnings with modern Python versions.
- **`argon2-cffi`**: Highly secure, but introduces third-party CFFI bindings and extra packages when Werkzeug's built-in `scrypt` already meets all enterprise security standards.

### Why the Chosen Approach Was Preferred
Zero new dependencies, no CFFI build complications, natively bundled with Flask/Werkzeug, and provides industry-standard `scrypt` hashing out of the box.

---

## Decision 15: Modern Password Policy (Length & Weakness Protection over Composition Rules)

### Decision
Enforce a password policy based on length (12 to 128 characters) and an internal weak-password blocklist rather than arbitrary character-composition rules (e.g., no mandatory uppercase, lowercase, numbers, or special characters). Spaces and Unicode characters are permitted and preserved. Obvious/common weak passwords (e.g. `password`, `123456789012`, `admin123`) are rejected via a local blocklist evaluated case-insensitively and ignoring surrounding whitespace (`WEAK_PASSWORD`).

### Reason
In alignment with modern identity security guidelines (such as NIST SP 800-63B), password length and resistance to dictionary/credential-stuffing attacks provide far greater entropy and security than arbitrary composition rules. Mandatory composition rules frequently encourage predictable substitutions (such as `P@ssword1!`), whereas passphrases (e.g. `this is a long secure passphrase`) offer high entropy and usability. A maximum bound of 128 characters prevents algorithmic denial-of-service (DoS) attacks on CPU-intensive hash functions (`scrypt`).

### Distinction: Local Blocklist vs. Breached-Password Detection
- **Current implementation**: An in-memory local blocklist of common and easily guessable passwords checked synchronously at zero latency with zero external dependencies.
- **Future phase considerations**: Full breached-password detection (e.g. HaveIBeenPwned k-anonymity API) may be introduced in a future security phase as an optional microservice or background validator. The current architecture strictly avoids external network dependencies in registration.

### Alternatives Considered
- **Strict character composition regex (e.g., `(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])`)**: Rejected because NIST SP 800-63B advises against arbitrary character composition rules, as they frustrate users and result in predictable patterns.
- **Full external HaveIBeenPwned API check in Phase 3 Step 1**: Rejected to keep registration offline, resilient, fast, and free of external runtime dependencies.
- **Stripping whitespace before hashing**: Rejected. Trimming leading/trailing whitespace from the actual password alters user intent; spaces inside and around passphrases are preserved in the hash. Whitespace is only stripped during blocklist comparison.

---

## Decision 16: User Login Architecture & JWT Authentication Design

### Decision
Implement stateless JWT-based authentication for user login using `PyJWT==2.10.1`, returning a signed HS256 access token upon valid credentials (`POST /api/auth/login`).

### Reasons & Security Architectural Principles

1. **Why JWT (JSON Web Tokens) are Used**:
   TruthLens is architected as a decoupled backend providing a RESTful API consumed by a separate frontend. Stateless JWTs eliminate server-side session state and shared Redis/memory session stores, allowing horizontal scaling and seamless verification across distributed backend processes.

2. **Why Authentication Failures are Generic (Anti-Enumeration)**:
   Any invalid login attempt (whether the email does not exist in the database, the password fails cryptographic hash check, or the account is inactive) returns an identical HTTP 401 response:
   ```json
   {
     "success": false,
     "message": "Invalid email or password.",
     "data": null,
     "error_code": "INVALID_CREDENTIALS"
   }
   ```
   Differentiating errors (e.g. "Email not found" vs. "Incorrect password") would enable account enumeration and targeted credential-stuffing attacks.

3. **Why Token Claims are Minimal**:
   The token payload contains exclusively `sub` (user ID string), `iat` (issued-at timestamp), and `exp` (expiration timestamp). Sensitive data (passwords, hashes, email, permissions) are intentionally excluded because JWT payloads are base64url-encoded and decodable by anyone holding the token.

4. **Why Expiration is Mandatory**:
   Stateless tokens cannot be revoked on the server without introducing distributed token blacklists. Enforcing a bounded lifespan (`JWT_EXPIRATION_HOURS`, default 24h) minimizes the risk window if a token is inadvertently compromised on a client device.

5. **Why Secret Keys are Sourced from Environment Variables**:
   Cryptographic signature integrity depends entirely on secret confidentiality. Hardcoded secrets in code or git repositories risk catastrophic token forgery. Sourcing `JWT_SECRET_KEY` from environment variables, backed by production startup checks that fail fast if a default secret is used, guarantees separation of code and secrets.

6. **Why Refresh Tokens are Intentionally Postponed**:
   Phase 3 Step 2 establishes the core authentication foundation with minimal abstraction. Introducing refresh tokens at this stage would require database persistence for refresh token families, token rotation schemes, and revocation mechanisms. Postponing refresh tokens to a later phase maintains an understandable, incremental, and highly verifiable codebase.

### Alternatives Considered
- **Server-Side Cookie Sessions (`Flask-Session` / Redis)**: Rejected due to unnecessary stateful infrastructure dependencies for a decoupled REST API.
- **`Flask-JWT-Extended`**: Evaluated, but introduces heavy abstraction, opinionated route decorators, and framework coupling when standard `PyJWT` provides transparent, straightforward encode/decode operations in two lines of code.
- **Detailed error responses during login**: Rejected due to high risk of user enumeration.

---

## Decision 17: Reusable JWT Authorization Decorator & Protected Route Architecture

### Decision
Implement a reusable `@require_auth` route decorator in `backend/utils/auth.py` that parses the HTTP `Authorization: Bearer <token>` header, delegates token verification to `AuthService.verify_token()`, extracts the authenticated user ID from the `sub` claim, and stores it in Flask's application context `g.current_user_id`. Introduce a minimal demonstration endpoint `GET /api/auth/me`.

### Reasons & Architectural Principles

1. **Why a Reusable Decorator is Used (`@require_auth`)**:
   In Flask, decorators are the idiomatic, beginner-friendly, and declarative pattern for cross-cutting route protections. An explicit `@require_auth` decorator makes authorization requirements completely transparent on each route definition without hiding logic inside global `before_request` hooks that could accidentally intercept public or webhook endpoints.

2. **Why Flask `g` is Used (`g.current_user_id`)**:
   Flask's `g` object is specifically designed as a thread-safe, request-bound context store. Values set on `g` are created afresh for each HTTP request and automatically garbage-collected at request termination. This avoids mutable global state and avoids polluting route signatures with forced parameter injections.

3. **Why Only `user_id` is Stored in `g`**:
   The authorization decorator operates purely statelessly. Querying the database to load the entire `User` model on every single protected request introduces database latency, connection-pool pressure, and tight coupling between authorization and persistence. Downstream routes that only require user association (e.g. assigning `Scan.user_id = g.current_user_id`) do not need a full User record. Should a route later need user profile fields, it can query `User` on-demand.

4. **Why HTTP 401 is Used Instead of HTTP 403**:
   RFC 9110 specifies that HTTP 401 Unauthorized represents an authentication/identity challenge (e.g. missing, expired, or invalid credentials where providing valid authentication may succeed). HTTP 403 Forbidden is reserved for authorization where the client identity is known but lacks specific permissions/roles for the requested resource. Since Phase 3 Step 3 implements identity verification without role-based access control, 401 is the correct status code.

5. **Why Detection Routes are Intentionally NOT Protected Yet**:
   TruthLens is being developed incrementally. The existing detection endpoints (`/api/detect/text`, `/api/detect/image`, `/api/detect/video`, `/api/detect/audio`, `/api/report/abuse`) serve as public forensic tools. In Phase 4, when scan persistence and scan history are implemented, authenticated users will optionally or mandatorily have their scans associated with `current_user_id`. Leaving detection endpoints public for now prevents regressions while authorization is verified on `/api/auth/me`.

6. **Centralized Token Verification & Claims Enforcement in `AuthService.verify_token`**:
   To prevent logic duplication, `@require_auth` does not call `jwt.decode()` directly. Instead, `AuthService.verify_token()` centralizes decoding, cryptographic signature validation, expiration checking, and enforcement of mandatory standard claims (`sub`, `iat`, `exp`). This ensures consistent security invariants across the entire codebase.

7. **Separation of Authentication Failures (401) from Unexpected Server Errors (500)**:
   The `@require_auth` decorator catches only authentication-specific errors (`jwt.ExpiredSignatureError`, `jwt.InvalidTokenError`, header formatting errors). It deliberately avoids catch-all `except Exception:` blocks that convert internal exceptions to 401. Unexpected server/runtime exceptions are permitted to bubble up to the centralized error handlers in `backend/utils/errors.py`, ensuring genuine programming bugs are logged server-side and returned as sanitized HTTP 500 `INTERNAL_SERVER_ERROR`.

8. **Why Refresh Tokens and Role-Based Access Control Remain Deferred**:
   Refresh tokens require database-backed token family tracking and revocation tables. Role-based access control requires role and permission models. Deferring both to dedicated future phases prevents scope creep and keeps the current step focused and verifiable.

### Alternatives Considered
- **Global `before_request` hook**: Rejected because it applies globally and requires URL whitelist regexes, which easily leads to security bypasses or accidental blocking of public endpoints.
- **Loading full `User` model from DB inside `@require_auth`**: Rejected due to unnecessary DB overhead on every request and loss of stateless JWT scalability.
- **Catching all exceptions inside `@require_auth` and returning 401**: Rejected because it masks internal server errors and misleads API consumers and developers.

---

## Decision 18: Scan Persistence Foundation Architecture (`ScanService`)

### Decision
Encapsulate all database persistence, state transitions, and retrieval operations for forensic scans (`Scan`) and analysis results (`ScanResult`) inside a dedicated service layer module (`backend/services/scan_service.py`), keeping detection routes and public contracts untouched in Phase 4 Step 1.

### Reasons & Architectural Principles

1. **Why Persistence is Isolated in `ScanService`**:
   The forensic detection services (`TextDetectionService`, `ImageDetectionService`, etc.) are designed as pure mathematical and signal-processing engines that operate on inputs and return data dictionaries without coupling to Flask request contexts or database sessions. Encapsulating persistence operations in `ScanService` preserves this clean separation of concerns, allows independent unit testing, and ensures reusable transaction semantics across all modalities.

2. **Why Detection Routes are NOT Modified Yet**:
   TruthLens evolves through strictly verified, incremental steps. Integrating persistence into `/api/detect/*` while simultaneously building the persistence service increases regression risk. By first stabilizing and testing `ScanService` with an extensive test suite, the subsequent route integration in Step 2 can be achieved with minimal complexity and maximum reliability.

3. **Atomic Transactions at the Service Boundary**:
   When saving a scan result, `ScanService.save_scan_result()` inserts the `ScanResult` and transitions parent `Scan.status` to `COMPLETED` (updating `completed_at` timestamp) within the exact same database transaction, committing once. If commit fails, `db.session.rollback()` atomically rolls back both operations, preventing orphaned results or inconsistent `PENDING` states.

4. **Specific Database Exception Handling (`SQLAlchemyError`)**:
   `ScanService` explicitly catches `SQLAlchemyError` to handle database transaction failures, execute session rollback, and raise `ScanDatabaseError`. It deliberately avoids broad `except Exception:` blocks, ensuring unexpected programming errors (e.g., `AttributeError`, `TypeError`) remain distinguishable and bubble to centralized error handlers without being disguised as database failures.

5. **Why Duplicate `ScanResult` Creation is Rejected (`ScanConflictError`)**:
   The database schema enforces a unique constraint on `ScanResult.scan_id` (1-to-1 relationship). If `save_scan_result()` is invoked for a scan that already possesses a result, the service proactively checks `scan.result` and raises a controlled `ScanConflictError` rather than triggering unhandled database integrity crashes or silently overwriting forensic evidence.

6. **Why `Scan.user_id` Remains Nullable Temporarily**:
   The `user_id` foreign key was made nullable in Phase 2 for schema compatibility before authentication existed. Although authentication and JWT tokens were completed in Phase 3, `user_id` remains nullable in this step as temporary schema compatibility because detection endpoints are not yet wired to require authentication. Modifying schema constraints or creating migrations is deferred until authenticated scan persistence is formally integrated.

7. **Proportional Input Validation Without Artificial Constraints**:
   The service validates that inputs are well-formed (non-empty strings, positive IDs, confidence floats bounded in `[0.0, 1.0]`) without hardcoding restrictive categorical sets (e.g. rigid prediction enums). This keeps the persistence layer flexible for future detection algorithms and new forensic modalities.

### Alternatives Considered
- **Directly persisting database records inside detection services**: Rejected because it couples pure signal algorithms to SQLAlchemy models and complicates testing.
- **Directly invoking `db.session.add()` inside route controllers**: Rejected because it scatters transaction and status-transition logic across multiple route handlers.
- **Overwriting existing `ScanResult` on duplicate save**: Rejected because forensic scan outcomes must be immutable records of an analysis event.

---

## Decision 19: Text Detection Scan Persistence & Route Authorization (Phase 4 Step 2)

### Decision
Connect `POST /api/detect/text` to `@require_auth` and `ScanService`, persisting the text scan and its forensic results with user ownership, while preserving the API response envelope, input validation rules, and detector output structures. All other detection endpoints (`image`, `video`, `audio`, `abuse`) remain public and unpersisted in this step.

### Reasons & Architectural Principles

1. **Why `POST /api/detect/text` Now Requires Authentication (`@require_auth`)**:
   A persisted forensic scan record represents user-owned data in the system. To establish clean data ownership without generating anonymous orphaned records in the database, `POST /api/detect/text` requires a valid Bearer JWT access token. Unauthenticated requests are rejected with standardized HTTP 401 responses (`AUTHENTICATION_REQUIRED`, `INVALID_TOKEN`, `TOKEN_EXPIRED`), preventing database pollution and ensuring every persisted scan has an identifiable owner.

2. **Why Image/Video/Audio and Abuse Endpoints Remain Unmodified in this Step**:
   In adherence to the feature-by-feature incremental development methodology, only the text modality is connected to persistence in Step 2. Keeping media detection endpoints (`image`, `video`, `audio`) and `abuse` reporting public and unchanged prevents broad blast radiuses, simplifies regression testing, and allows each modality's specific payload and persistence characteristics (e.g. file storage, hashes) to be addressed deliberately in future steps.

3. **Separation of Concerns: Detector Output Mapping via `ScanService`**:
   `TextDetectionService.analyze_text` remains a pure analytical engine returning forensic metrics (`is_ai_generated`, `ai_confidence_score`, `metrics`, `sentence_breakdown`). The route maps these existing values into `ScanService.create_scan()` and `ScanService.save_scan_result()`:
   - `user_id = g.current_user_id`
   - `media_type = "text"`
   - `filename = None` (text has no uploaded file)
   - `confidence = float(result.get("ai_confidence_score", 0.0))`
   - `prediction = "AI_GENERATED" if is_ai else "AUTHENTIC"`
   - `risk_level = "HIGH" if confidence >= 0.7 else ("MEDIUM" if confidence >= 0.4 else "LOW")`
   - `result_data = result` (full forensic dictionary stored as JSON)

4. **Transaction Boundaries and Route-Level Failure Handling**:
   `ScanService.create_scan` and `ScanService.save_scan_result` manage their own database transactions and rollback semantics internally. The route controller does not touch `db.session` directly. If persistence fails after analysis, the route catches `ScanServiceError` and logs the exception server-side while returning a sanitized HTTP 500 response (`INTERNAL_SERVER_ERROR`), preventing raw database or SQL leakage to clients and ensuring no misleading successful response is returned.

5. **No Schema Changes or Migrations Required**:
   `Scan` and `ScanResult` tables created in Phase 2 already support `media_type="text"`, nullable `filename`, foreign key `user_id`, and native JSON `result_data`. No schema modifications or database migrations were necessary.

---

## Decision 20: Image Detection Scan Persistence & Route Authorization (Phase 4 Step 3)

### Decision
Connect `POST /api/detect/image` to `@require_auth` and `ScanService`, persisting the image scan and its forensic results with user ownership and uploaded filename metadata, while preserving the API response envelope, multipart file validation rules, and detector output structures. Video and audio detection and abuse reporting remain public and unpersisted in this step.

### Reasons & Architectural Principles

1. **Why `POST /api/detect/image` Now Requires Authentication (`@require_auth`)**:
   Persisted image scans must be associated with an authenticated user account (`Scan.user_id = g.current_user_id`). Requiring Bearer JWT authentication upfront prevents unauthorized users from filling the database with unowned scans and ensures security invariants are maintained. Missing, expired, or invalid tokens fail fast before reading file bytes or invoking image decoding.

2. **Capturing Media Filename Metadata**:
   Unlike text detection (which has no uploaded file), image detection receives an uploaded file via `request.files['image']`. The original uploaded filename (`file.filename`) is passed directly to `ScanService.create_scan(filename=...)`, allowing users to trace scan results back to their source assets.

3. **Detector Output Mapping & Raw Binary Exclusion**:
   `ImageDetectionService.analyze_image` computes spatial anomalies and renders a visual Grad-CAM++ heatmap overlay returned as a Base64 JPEG data URL. The route maps:
   - `prediction`: `"DEEPFAKE"` if `is_deepfake` is True, else `"AUTHENTIC"`
   - `confidence`: `float(result.get("confidence_score", 0.0))`
   - `risk_level`: `"HIGH"` if confidence >= 0.7, `"MEDIUM"` if confidence >= 0.4, else `"LOW"` (consistent with the application's risk classification pattern)
   - `result_data`: Stores the structured detector dictionary (`is_deepfake`, `confidence_score`, `manipulation_type`, `image_dimensions`, `heatmap_preview`).
   - **Critical Storage Rule**: Raw uploaded binary image bytes are never stored in the database. The database records forensic analysis metadata, while heavy binary handling and secure storage are deferred to Phase 5.

4. **Service Boundary & Orphan-Scan Consideration**:
   `ScanService.create_scan` and `ScanService.save_scan_result` are discrete transactional operations. The route controller treats `ScanService` as the persistence boundary and does not manipulate `db.session` directly. If `save_scan_result` fails after `create_scan` succeeds, the parent scan remains in `PENDING` status. This temporary behavior is intentional: it represents an in-progress or interrupted scan without introducing an overly complex compensation mechanism before asynchronous job processing is formally introduced.

## Decision 21: Video Detection Scan Persistence & Route Authorization (Phase 4 Step 4)

### Decision
Connect `POST /api/detect/video` to `@require_auth` and `ScanService`, persisting the video scan and its forensic results with user ownership and uploaded filename metadata, while preserving the API response envelope, multipart file validation rules, and detector output structures. Audio detection and abuse reporting remain public and unpersisted in this step.

### Reasons & Architectural Principles

1. **Why `POST /api/detect/video` Now Requires Authentication (`@require_auth`)**:
   Video processing is computationally expensive (OpenCV frame extraction, Laplacian variance calculations, and Grad-CAM++ rendering). Requiring a valid Bearer JWT access token upfront ensures that unauthorized, expired, or invalid requests fail immediately with HTTP 401 (`AUTHENTICATION_REQUIRED`, `INVALID_TOKEN`, `TOKEN_EXPIRED`) before allocating system resources, writing temporary disk files, or running frame analyses.

2. **Capturing Media Filename Metadata**:
   Like image detection, video detection receives an uploaded media file via `request.files['video']`. The original uploaded filename (`file.filename`) is passed directly to `ScanService.create_scan(filename=...)`, allowing users to identify and trace video scan records back to their source files.

3. **Detector Output Mapping & Raw Binary Exclusion**:
   `VideoDetectionService.analyze_video` samples keyframes, computes temporal and anomaly metrics, and generates a Grad-CAM++ overlay on the peak anomaly keyframe returned as a Base64 JPEG data URL.
   The route deliberately constructs `result_data`:
   - `prediction`: `"DEEPFAKE"` if `is_deepfake` is True, else `"AUTHENTIC"`
   - `confidence`: `float(result.get("confidence_score", 0.0))`
   - `risk_level`: Evaluated against the detector's confidence semantics:
     - `confidence_score` represents sequence anomaly probability in `[0.10, 0.98]` where `is_deepfake = overall_confidence > 0.65`.
     - The established application risk mapping (`HIGH >= 0.7`, `MEDIUM >= 0.4`, `LOW < 0.4`) is completely compatible with these confidence semantics.
   - `result_data`: Deliberately constructed dictionary containing `{ is_deepfake, confidence_score, metrics: { duration_seconds, total_frames_analyzed, temporal_instability, peak_frame_anomaly }, keyframe_heatmap_preview }`.
   - **Critical Storage Rule**: Raw uploaded video binary streams, unencoded frames, and large transient numpy arrays are NEVER stored in the database. Only serializable summary metrics and keyframe heatmap evidence are persisted.

4. **Service Boundary & Orphan-Scan Consideration**:
   `ScanService.create_scan` and `ScanService.save_scan_result` are discrete transactional operations. The route treats `ScanService` as the persistence boundary without touching `db.session`. If `save_scan_result` fails after `create_scan` succeeds, the parent scan remains in `PENDING` status. This temporary behavior represents an incomplete scan without introducing complex distributed rollback mechanisms before asynchronous job processing is formally introduced.

## Decision 22: Audio Detection Scan Persistence & Route Authorization (Phase 4 Step 5)

### Decision
Connect `POST /api/detect/audio` to `@require_auth` and `ScanService`, persisting the audio scan and its forensic results with user ownership and uploaded filename metadata, while preserving the API response envelope, multipart file validation rules, and detector output structures. Abuse reporting remains public and unpersisted in this step.

### Reasons & Architectural Principles

1. **Why `POST /api/detect/audio` Now Requires Authentication (`@require_auth`)**:
   Audio processing involves signal decoding (`scipy.io.wavfile`), Zero Crossing Rate (ZCR) calculations, spectral energy variance analysis, and lip-sync desynchronization evaluation. Requiring Bearer JWT authentication upfront protects backend resources from unauthenticated abuse, enforces user ownership on all persisted scans (`Scan.user_id = g.current_user_id`), and fails fast with HTTP 401 (`AUTHENTICATION_REQUIRED`, `INVALID_TOKEN`, `TOKEN_EXPIRED`) before reading audio bytes or executing signal processing algorithms.

2. **Capturing Media Filename Metadata**:
   The uploaded file is received via `request.files['audio']`. The original uploaded filename (`file.filename`) is passed directly to `ScanService.create_scan(filename=...)`, allowing users to trace audio scan records back to their original source files.

3. **Detector Output Mapping & Raw Binary Exclusion**:
   `AudioDetectionService.analyze_audio` computes acoustic anomaly metrics and flags temporal lip-sync discrepancy windows.
   The route deliberately constructs `result_data`:
   - `prediction`: `"SYNTHETIC"` if `is_synthetic_audio` is True, else `"AUTHENTIC"` (accurately reflecting synthetic voice classification semantics).
   - `confidence`: `float(result.get("confidence_score", 0.0))`.
   - `risk_level`: Evaluated against acoustic anomaly score semantics:
     - `confidence_score` represents acoustic manipulation probability in `[0.12, 0.97]` where `is_synthetic_audio = confidence_score > 0.65`.
     - The established application risk mapping (`HIGH >= 0.7`, `MEDIUM >= 0.4`, `LOW < 0.4`) aligns with these acoustic anomaly semantics.
   - `result_data`: Deliberately constructed dictionary containing:
     ```python
     {
         "is_synthetic_audio": result.get("is_synthetic_audio"),
         "confidence_score": confidence,
         "metrics": result.get("metrics"),
         "lip_sync_discrepancies": result.get("lip_sync_discrepancies", []),
     }
     ```
   - **Critical Storage Rule**: Raw uploaded audio binary streams, raw PCM samples, and transient numpy arrays are NEVER stored in the database. Only structured acoustic metrics and discrepancy windows are persisted.

4. **Service Boundary & Orphan-Scan Consideration**:
   `ScanService.create_scan` and `ScanService.save_scan_result` are discrete transactional operations. The route treats `ScanService` as the persistence boundary without touching `db.session`. If `save_scan_result` fails after `create_scan` succeeds, the parent scan remains in `PENDING` status. This temporary behavior represents an incomplete scan without premature compensation complexity before asynchronous job queues are formally introduced.

5. **Completion of All Four Forensic Modalities**:
   With Phase 4 Step 5 complete, all four multimodal forensic detection pipelines (text, image, video, and audio) now consistently require JWT authentication and persist structured scan records and forensic results via `ScanService`. Only abuse reporting remains unpersisted at this stage.

---

## Decision 23: Scan History APIs, User Ownership Scoping, Anti-IDOR 404, and Lightweight List Serialization (Phase 4 Step 6)

### Decision
Implement user-scoped scan history listing (`GET /api/scans`) and individual scan detail retrieval (`GET /api/scans/<int:scan_id>`) protected by `@require_auth`. All queries are strictly scoped to `g.current_user_id`. Requests for non-existent or unowned scans return HTTP 404 `SCAN_NOT_FOUND`. The list endpoint returns lightweight scan metadata excluding heavy `result_data`, while the detail endpoint returns full forensic metrics.

### Reasons & Architectural Principles

1. **Strict User Ownership Scoping**:
   Users must only access scans they own. All database queries in `ScanService.get_user_scans` and `ScanService.get_user_scan_by_id` explicitly filter on `Scan.user_id == user_id`. The user ID is extracted directly from the verified JWT access token (`g.current_user_id`), never from client-supplied request bodies, query parameters, or path segments.

2. **Anti-Enumeration 404 for IDOR Prevention**:
   If an authenticated user attempts to access `GET /api/scans/<scan_id>` for a scan owned by someone else, the application returns HTTP 404 (`SCAN_NOT_FOUND`) rather than HTTP 403 (`FORBIDDEN`). Returning 403 would reveal that the scan ID exists in the database, allowing an attacker to enumerate valid resource IDs. Returning 404 makes unowned scans indistinguishable from non-existent scans.

3. **Lightweight List Payload Discipline**:
   Image and video detection scans persist Base64-encoded JPEG heatmap overlays (`heatmap_preview`, `keyframe_heatmap_preview`) inside `ScanResult.result_data`, which can reach 20 KB to 100 KB+ per scan. Serializing `result_data` in history listings would inflate a 20-item response to several megabytes, degrading network performance and UI rendering. Therefore, `GET /api/scans` returns only top-level verdict summaries (`prediction`, `confidence`, `risk_level`), while full `result_data` is reserved exclusively for single-record detail inspection (`GET /api/scans/<scan_id>`).

4. **Offset Pagination with Strict Upper Bounds**:
   For forensic audit logs, users need total scan counts, total pages, and direct page navigation controls. Offset pagination (`page`, `per_page`) is predictable, robust, and supported natively. To prevent denial-of-service memory exhaustion, `per_page` is capped at 100, and non-positive or malformed parameters are rejected with HTTP 400 (`INVALID_PAGE`, `INVALID_PER_PAGE`).

5. **Deterministic Ordering**:
   Scans are ordered by `Scan.created_at.desc(), Scan.id.desc()`. The secondary sort on primary key `id.desc()` breaks ties when scans have identical timestamps, ensuring stable pagination boundaries without item duplication or drift across pages.

6. **Eager Loading (N+1 Query Elimination)**:
   To prevent executing individual SQL queries for each scan's 1-to-1 `ScanResult` relation, queries utilize `options(joinedload(Scan.result))` to fetch parent and child entities in a single SQL query with outer join.

---

## Decision 24: Image Resource Bounds, Decompression Bomb Protection, and Heatmap Thumbnail Downscaling (Phase 5 Step 2)

### Decision
Enforce strict image dimension and pixel limits (`MAX_IMAGE_WIDTH = 4096`, `MAX_IMAGE_HEIGHT = 4096`, `MAX_IMAGE_PIXELS = 16_777_216`) immediately after `cv2.imdecode()` and before full-resolution mask allocation or blur convolutions in `ImageDetectionService.analyze_image`. In addition, downscale generated heatmap overlays to a thumbnail representation (maximum dimension `512` px, preserving aspect ratio without upscaling smaller source images) before Base64 JPEG encoding and database persistence.

### Reasons & Architectural Principles

1. **Why Compressed Upload Size Alone Is Insufficient**:
   Flask's `MAX_CONTENT_LENGTH` (50 MB) limits only the HTTP request payload size over the network. A highly compressible image format (such as PNG or WebP) can pack an enormous raster matrix (e.g., $30,000 \times 30,000$ pixels) into a tiny file (< 500 KB). When decoded into uncompressed raw NumPy arrays and processed with single-precision float32 masks ($w \times h \times 4$ bytes), memory consumption balloons past 10 GB within seconds, triggering an immediate process crash via the operating system Out-Of-Memory (OOM) killer.

2. **Compound Resource Policy (Width, Height, and Total Pixels)**:
   Checking both individual dimensions ($w \le 4096, h \le 4096$) and total pixel count ($w \times h \le 16,777,216$) guards against extreme aspect ratio edge cases and guarantees an absolute upper bound of ~67 MB for any intermediate float32 mask array, ensuring deterministic memory predictability under concurrent workloads.

3. **Execution Order and Memory Safety**:
   The validation check executes immediately after `cv2.imdecode()` and before any expensive full-resolution image manipulation:
   - Evaluated before `np.zeros((h, w), dtype=np.float32)` mask allocation.
   - Evaluated before `cv2.GaussianBlur` 2D kernel convolution.
   - Evaluated before `cv2.applyColorMap` colorization and alpha blending.
   If limits are exceeded, a `ValueError` is raised immediately, caught by `image_routes.py`, and returned as HTTP 400 (`PROCESSING_ERROR`) without creating or persisting a `Scan` record in the database.

4. **Heatmap Thumbnail Downscaling for Database & Network Efficiency**:
   Previously, heatmap previews were encoded at the full input image resolution. For a 12 MP photo, the persisted Base64 JPEG data URL exceeded 1.5 MB in `ScanResult.result_data`. Downscaling the preview overlay to a maximum dimension of 512 px (using `cv2.INTER_AREA` interpolation) preserves the visual Grad-CAM++ diagnostic quality while capping preview payloads at ~20 KB to 50 KB, reducing database storage and detail API transmission costs by 90%+. Images smaller than 512 px are left unscaled to preserve original fidelity.

5. **Security vs. Legitimate High-Resolution Tradeoff**:
   A ceiling of $4096 \times 4096$ pixels (16 Megapixels) comfortably supports standard consumer and smartphone photography while neutralizing malicious gigapixel decompression bombs.

---

## Decision 25: Video Temporary File Cleanup Ordering, Windows File Handle Lock Mitigation, and Video Resource Bounds (Phase 5 Step 3)

### Decision
1. Restructure the temporary file and `cv2.VideoCapture` lifecycle in `VideoDetectionService.analyze_video` within a strict `try...finally` block such that `cap.release()` is deterministically executed **before** `os.remove(temp_path)` on all execution paths (success, invalid/corrupt stream, zero readable frames, limit violations, and unexpected exceptions).
2. Replace the hardcoded `.mp4` temporary file suffix with a dynamically derived extension matching the validated upload extension (`.mp4`, `.mov`, `.avi`, `.mkv`), safely defaulting to `.mp4`.
3. Enforce a video duration limit (`MAX_VIDEO_DURATION_SECONDS = 120`). If container metadata indicates duration exceeds 120s, reject immediately with HTTP 400 (`PROCESSING_ERROR`) without creating or persisting a `Scan` record.
4. Enforce video resolution bounds (`MAX_VIDEO_WIDTH = 4096`, `MAX_VIDEO_HEIGHT = 4096`, `MAX_VIDEO_PIXELS = 16_777_216`). Inspect container metadata (`cv2.CAP_PROP_FRAME_WIDTH`, `cv2.CAP_PROP_FRAME_HEIGHT`) first to reject oversized videos before sampling. Validate actual decoded frame dimensions (`frame.shape[:2]`) immediately upon reading each frame, rejecting oversized frames before any costly processing or array allocations.

### Reasons & Architectural Principles

1. **Why VideoCapture Handle Release Must Precede `os.remove()` (Windows Lock Mechanics)**:
   On Windows operating systems, opening a file with `cv2.VideoCapture` places an exclusive OS-level handle lock on the underlying filesystem node. If an exception occurs (e.g. `total_frames <= 0`, corrupt stream, or limit violation) and `os.remove(temp_path)` is attempted while `cap` remains unreleased, Windows raises `PermissionError: [WinError 32] The process cannot access the file because it is being used by another process`. Previously, `cap.release()` was located inside the `try` block after frame analysis, and `os.remove` caught and silently discarded `OSError`. Consequently, failed video scans left 50 MB temporary video files permanently orphaned on the server disk, creating a direct vector for disk exhaustion denial-of-service. Placing `cap.release()` inside `finally:` directly before `os.remove()` guarantees file release prior to deletion across all scenarios.

2. **Why Duration Limits Are Enforced**:
   Video deepfake analysis extracts multiple temporal frames across the video timeline and computes frame-level Laplacian variances and temporal instability metrics. Long videos (e.g. 10 minutes to several hours) place substantial sustained CPU and I/O load on the backend, increasing processing latency and holding server worker threads. Capping duration at 120 seconds bounds processing overhead while accommodating forensic short-form clips, social media uploads, and synthetic snippet verifications.

3. **Why Dual-Layer Resolution Checks (Metadata + Decoded Frame) Are Critical**:
   Container-level metadata (such as MP4 headers) may report nominal dimensions (e.g. 640x480) or be missing/corrupt, while the underlying video track contains 4K/8K raster streams. Conversely, a video with accurate 8K metadata should be rejected immediately without allocating frame decoders. Checking metadata first rejects obvious violations at zero compute cost. Validating `frame.shape[:2]` immediately upon decoding each frame guarantees that no frame exceeding 4096x4096 (16 MP) is ever passed to texture analysis or Grad-CAM++ mask generation.

4. **Zero-Scan Persistence Invariant on Rejection**:
   Consistent with the media persistence architecture, `ScanService.create_scan()` is invoked only *after* detection completes successfully. A video rejected for duration or resolution limits raises `ValueError`, returning HTTP 400 `PROCESSING_ERROR` to the client while leaving the database completely clean.

5. **Detection Algorithm Semantics Preserved**:
   Frame sampling count (16), uniform linspace sampling, Laplacian variance calculations, anomaly score heuristics, temporal instability std-dev, 0.65 deepfake threshold, risk level mappings, and response envelopes remain 100% identical.

---

## Decision 26: Audio Decoding Integrity, Elimination of Synthetic Fallback, and WAV-Only Format Policy (Phase 5 Step 4)

### Decision
1. Remove the silent synthetic Gaussian noise fallback (`np.random.normal(...)`) in `AudioDetectionService.analyze_audio`. Decoding failures from `scipy.io.wavfile.read` must immediately propagate a `ValueError` indicating that the audio file is corrupted or unsupported.
2. Adopt **Option A (Preferred)** for format support: Restrict `ALLOWED_AUDIO_EXTENSIONS` in `backend/utils/file_validator.py` strictly to `{"wav"}` because `scipy.io.wavfile.read()` is the active decoder and natively only supports RIFF/WAVE containers. Non-WAV formats (`.mp3`, `.m4a`, `.flac`) are rejected fast at the route boundary with HTTP 400 (`INVALID_FORMAT`).
3. Validate the decoded audio buffer: If the decoded NumPy array has zero size (`data.size == 0`) or the detected sample rate is non-positive (`sample_rate <= 0`), immediately raise `ValueError` to prevent divide-by-zero errors or invalid duration calculations.
4. Enforce deterministic temporary file cleanup within a `finally:` block in `AudioDetectionService.analyze_audio`. If `os.remove(temp_path)` fails, log a warning with the error details instead of silently ignoring it.
5. Uphold the strict persistence invariant: Corrupted, empty, or unreadable audio uploads must result in an immediate HTTP 400 response and **zero** `Scan` or `ScanResult` records persisted in the database.

### Reasons & Architectural Principles

1. **Why Synthetic Noise Fallback Is Unacceptable in Forensic Systems**:
   Previously, when `scipy.io.wavfile.read()` failed to decode an audio file (e.g. Due to corrupt headers, unsupported compression codecs, or non-WAV bytes), the service caught the exception and synthesized 3 seconds of pseudo-random Gaussian noise at 16 kHz. This artificial waveform was then fed into the Zero Crossing Rate (ZCR) and energy variance estimators, generating an arbitrary synthetic/authentic verdict that was saved into the audit database as genuine forensic intelligence. In a legal, evidentiary, or journalistic verification platform, fabricating results for unreadable files is catastrophic. An unreadable file must always be cleanly rejected without generating or persisting any analysis.

2. **Why Option A (Restricting to WAV Only) Was Selected**:
   The TruthLens backend relies on `scipy.io.wavfile.read()` for audio decoding without external binary dependencies (such as ffmpeg or librosa). Although earlier configurations listed `mp3`, `m4a`, and `flac` as allowed extensions, `scipy.io.wavfile.read()` cannot parse these compressed or alternative container formats. Keeping them in the allowed extension list created a false expectation of support and forced non-WAV uploads to hit the decoder error path. Restricting `ALLOWED_AUDIO_EXTENSIONS = {"wav"}` makes the API contract honest and reliable. Support for compressed audio formats (e.g. via a dedicated transcoding pipeline) is deferred to future roadmap phases.

3. **Buffer Integrity and Sample Rate Validation**:
   Even if a file conforms superficially to the WAV container structure, truncated or malformed chunks can yield empty data arrays (`data.shape == (0,)`) or corrupt sample rate headers (`sample_rate <= 0`). Explicitly checking `data.size == 0` and `sample_rate <= 0` avoids subsequent division-by-zero crashes when computing duration (`len(data) / float(sample_rate)`) or normalized ZCR (`zero_crossings / max(1, len(data))`).

4. **Deterministic Temporary File Cleanup**:
   Saving incoming audio streams to temporary disk files is necessary because `scipy.io.wavfile.read()` operates most reliably on disk paths or seekable file descriptors. Wrapping file reading and array transformations inside `try...finally` guarantees that `os.remove(temp_path)` is executed whether decoding succeeds, decoding fails, or an unexpected runtime exception occurs. Failure to clean up temporary files is logged with warning severity.

5. **Zero-Scan Persistence Invariant**:
   In `backend/routes/audio_routes.py`, `ScanService.create_scan()` is invoked strictly *after* `AudioDetectionService.analyze_audio()` completes without exception. When an invalid, corrupted, or empty file causes `analyze_audio()` to raise `ValueError`, the route catches the error, returns HTTP 400 (`PROCESSING_ERROR`), and aborts before creating any database records. Exactly 0 scans and 0 scan results are persisted for rejected audio uploads.

6. **Preservation of Forensic Algorithm Semantics**:
   For valid, readable WAV uploads, all forensic analysis semantics remain unchanged:
   - Stereo to mono downmixing via `.mean(axis=1)`.
   - Peak amplitude normalization.
   - Zero Crossing Rate (ZCR) calculation.
   - Spectral energy variance computation.
   - Spectral anomaly and confidence score derivation ($[0.12, 0.97]$).
   - Synthetic threshold ($> 0.65$).
   - Lip-sync desynchronization event window extraction.
   - Risk level categorization (`HIGH`, `MEDIUM`, `LOW`).

---

## Decision 27: File Signature (Magic-Byte) Validation, Conservative Container Checks, and Path-Traversal-Resistant Filename Security (Phase 5 Step 5)

### Decision
1. **Bounded Magic-Byte Validation**:
   Implement bounded byte signature verification in `backend/utils/file_validator.py` (`read_file_prefix`) reading at most 32 bytes from client uploads and deterministically rewinding the underlying stream using `try ... finally: stream.seek(pos)`.
2. **Format-to-Signature Mapping**:
   Enforce signature validation strictly for formats accepted by TruthLens:
   - Image: JPEG (`\xff\xd8\xff`), PNG (`\x89PNG\r\n\x1a\n`), WebP (`RIFF....WEBP`).
   - Video: MP4 (`ftyp` at bytes 4..8), MOV (conservative ISO Base Media File Format `ftyp` check at bytes 4..8, rejecting arbitrary atom/box names like `moov`, `wide`, `skip`, `free`), AVI (`RIFF....AVI ` or `RIFF....AVIX`), MKV (`\x1a\x45\xdf\xa3`).
   - Audio: WAV only (`RIFF....WAVE` or `RIFX....WAVE`).
3. **Filename Security**:
   Implement `is_safe_filename` to reject path separators (`/`, `\`), Windows drive letters and ADS colons (`:`), control characters and null bytes (`ord < 32 or ord == 127`), excessive length (> 255 chars), directory navigation references (`.` or `..`), dot prefixes/suffixes, and leading/trailing whitespace.
   Do not blindly reject filenames containing `..`; legitimate filenames with ordinary double dots (e.g. `audit..v1.jpg`), spaces, and international Unicode characters are explicitly permitted.
4. **Standardized Error Codes**:
   - `INVALID_FILE` (HTTP 400): Missing file payload, empty filename, or unsafe filename (traversal, control chars, colons, excessive length).
   - `INVALID_FORMAT` (HTTP 400): Disallowed file extension, magic-byte mismatch, or extension-content mismatch.
   - `PROCESSING_ERROR` (HTTP 400): Files with valid signatures whose internal stream cannot be decoded by OpenCV/SciPy.
5. **Zero-Scan Persistence Invariant**:
   Files rejected during filename safety, extension checking, or magic-byte verification are rejected at the route boundary before invoking detection services, ensuring exactly 0 `Scan` or `ScanResult` database records are created.

### Reasons & Architectural Principles

1. **Extension Spoofing Exposure**:
   Relying exclusively on file extensions allows arbitrary binary, executable, or text payloads disguised as media files (e.g. `malware.exe` renamed to `evidence.jpg`) to be passed to decoders. Validating leading magic bytes ensures content matches the declared container before resource allocation.

2. **Conservative MOV Validation**:
   QuickTime/ISOBMFF containers use an `ftyp` atom at bytes 4..8. Permitting arbitrary box names (`moov`, `mdat`, `wide`, `skip`, `free`) creates overly permissive validation that could accept corrupted or malformed streams. Requiring `ftyp` at bytes 4..8 provides conservative, robust validation without requiring a complex, full container parser.

3. **Non-Destructive Stream Rewind**:
   Validation must not consume the upload stream. Wrapping stream reads with `try ... finally: stream.seek(pos)` guarantees that downstream consumers (`file.read()` for images/audio or tempfile writing for videos) receive the complete file stream from offset 0.

4. **Precision in Filename Security**:
   Rejecting any filename with `..` breaks legitimate forensic naming conventions (e.g. `audit..v1.jpg`). Using `PurePosixPath` and `PureWindowsPath` traversal checks alongside explicit separator and colon checks blocks real path traversal (`../../`, `..\..\`, `/etc/`, `C:\`) while preserving valid double-dot basenames.

5. **Error Code Consistency**:
   Standardizing image format rejections to `INVALID_FORMAT` aligns image detection with video and audio modalities, establishing an unambiguous API contract across the TruthLens platform.

---

## Decision 28: Multi-Modal Resource Bounds & Forensic Payload Hardening (SEC-05, SEC-06, SEC-07)

### Context & Problem
Following Phase 5 Steps 2–5, three discrete resource bound and payload bloat gaps remained across detection pipelines:
1. **SEC-05 (Text Ingestion & Database Bloat)**: `POST /api/detect/text` enforced a minimum length (20 chars) but no maximum limit. A 50MB text payload could trigger algorithmic complexity in regex sentence splitting and persist an unbounded list of sentence dictionaries into `ScanResult.result_data`.
2. **SEC-06 (Video Keyframe Preview Bloat)**: Step 2 downscaled image heatmap previews to 512px thumbnails, but Step 3 omitted downscaling for video keyframe overlays. A 4K video frame produced a 1.5–2.5MB Base64 string in `ScanResult.result_data` on every video scan.
3. **SEC-07 (Audio Duration Limit)**: Step 3 introduced `MAX_VIDEO_DURATION_SECONDS = 120`, but audio duration was left unbounded (`MAX_AUDIO_DURATION_SECONDS`), allowing long WAV files to consume excessive processing resources.

### Decisions
1. **Authoritative Text Length Boundary**:
   Defined a single authoritative constant `MAX_TEXT_LENGTH = 25_000` in `backend/services/text_service.py` and imported it in `backend/routes/text_routes.py`. Text exceeding 25,000 characters is rejected upfront with HTTP 400 `TEXT_TOO_LONG` before `ScanService.create_scan()`.
2. **Complete Analysis with Capped Breakdown Persistence**:
   Text detection analyzes the complete accepted text (up to 25,000 characters) to calculate global statistical metrics (`total_sentences`, `total_words`, `burstiness_index`, `lexical_diversity`, `ai_probability`), but caps `sentence_breakdown` at `MAX_SENTENCE_BREAKDOWN_ITEMS = 100` entries. This ensures `ScanResult.result_data` remains compact and predictable.
3. **Post-Detection Keyframe Preview Downscaling**:
   In `VideoDetectionService.analyze_video()`, introduced `MAX_PREVIEW_DIMENSION = 512` (matching `ImageDetectionService`). The full-resolution frame is retained for anomaly detection and heatmap generation; downscaling is applied only to the final blended `overlay` thumbnail before JPEG Base64 encoding.
4. **Harmonized Audio Duration Limits**:
   Enforced `MAX_AUDIO_DURATION_SECONDS = 120` in `AudioDetectionService.analyze_audio()`, matching the video duration limit. Audio exceeding 120 seconds is cleanly rejected with HTTP 400 `PROCESSING_ERROR` and creates 0 `Scan` records.
5. **Audio Decoder Architecture Scope**:
   Evaluated determining WAV duration prior to sample loading. Because `scipy.io.wavfile` does not provide a public header-only duration parser without reading data chunks, introducing a secondary parser or calling private `_read_*` methods would violate architectural stability. Given that `MAX_CONTENT_LENGTH = 50MB` already bounds physical file size, the post-decode 120-second guard is retained and documented.

### Reasons & Tradeoffs
- **Payload Safety**: Eliminates multi-megabyte `result_data` bloat across text and video scans, keeping database records under ~100KB.
- **Persistence Invariants**: All rejections happen before `ScanService.create_scan()`, guaranteeing zero orphaned database records.
- **Zero New Dependencies**: Accomplished entirely with existing libraries (`numpy`, `cv2`, `scipy.io.wavfile`).
