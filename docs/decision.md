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


