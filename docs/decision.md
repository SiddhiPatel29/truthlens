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

5. **Isolation of Audio and Abuse Modalities**:
   Audio detection and abuse dispatch routes remain public and untouched, preserving feature-by-feature progression.






