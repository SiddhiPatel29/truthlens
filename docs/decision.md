# Architectural & Technical Decisions Log

This document records the foundational architectural and technical decisions made during Phase 1 of the VeraMedia AI backend development.

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

### Reason
Earlier audits revealed that `numpy`, `opencv-python`, and `scipy` were actively imported by the forensic services but completely absent from `requirements.txt`. Without pinning, automated deployment or fresh clones would break with runtime `ImportError` or install incompatible wheel versions on Python 3.13.

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
- **Docker containers in Phase 1**: Explicitly ruled out to avoid premature complexity on local Windows development before core stabilization.

### Why the Chosen Approach Was Preferred
Standard Python `.venv` provides zero-overhead isolation, is natively supported across all platforms, and is already git-ignored.

---

## Decision 5: Pytest as the Testing Framework

### Decision
Adopt `pytest` with a modular test suite organized in `tests/` utilizing standard fixtures in `conftest.py`.

### Reason
`pytest` offers powerful fixture management, clean assert syntax without boilerplate subclasses, detailed diff output on failures, and fast execution speed (29 tests executed in ~1.04s).

### Alternatives Considered
- **Standard library `unittest`**: Functional, but requires verbose boilerplate classes (`self.assertEqual`) and awkward test discovery syntax.
- **No automated test runner (relying on manual Postman/curl scripts)**: Prone to regressions, impossible to run automatically, and untrustworthy.

### Why the Chosen Approach Was Preferred
`pytest` is the de facto Python industry standard. Its fixture pattern seamlessly integrates with Flask's test client (`client.get`, `client.post`).

---

## Decision 6: Preservation of Existing Forensic Signal Logic in Phase 1

### Decision
Retain existing heuristic forensic signal algorithms in `TextDetectionService`, `ImageDetectionService`, `VideoDetectionService`, and `AudioDetectionService` without attempting to replace them with large neural network models (e.g. CLIP, ResNet, Whisper) during Phase 1.

### Reason
The goal of Phase 1 is establishing a clean, secure, and testable backend foundation. Replacing signal-processing logic with heavy deep learning weights would introduce huge model files (>2 GB), complex GPU/Torch dependencies, high latency, and cloud deployment complexity prematurely.

### Alternatives Considered
- **Immediately downloading pre-trained PyTorch / HuggingFace deepfake models**: Would derail Phase 1 foundation goals, balloon dependency footprint, and introduce environment instability.
- **Stubbing services with static mock data**: Would delete working signal processing logic already present in the codebase.

### Why the Chosen Approach Was Preferred
Preserving the existing mathematical heuristics (Laplacian variance, ZCR, burstiness, Grad-CAM++ style heatmap rendering) allows the entire end-to-end API pipeline to be verified with real media while keeping the architecture lean and responsive.

---

## Decision 7: Refactoring File Validation into Shared Utilities without MIME/Magic-byte Overhaul

### Decision
Consolidate media extension checking into `backend/utils/file_validator.py` (`validate_image_file`, `validate_video_file`, `validate_audio_file`) to eliminate duplicate validation code in routes, but defer magic-byte / MIME inspection (`python-magic`) to Phase 2.

### Reason
Routes were inconsistently validating filenames and extensions. Centralizing this logic into pure functions ensures DRY principles and consistent error codes (`MISSING_FILE`, `INVALID_FILE`, `INVALID_FORMAT`). Deferring binary magic-byte inspection adheres to the user instruction to avoid over-engineering file security until Phase 2.

### Alternatives Considered
- **Leaving validation logic duplicated inside each route**: Hard to maintain, inconsistent error messages.
- **Adding `python-magic` / `libmagic` in Phase 1**: `libmagic` requires external binary DLLs on Windows which often causes installation friction for beginners.

### Why the Chosen Approach Was Preferred
Cleanly refactored Python utility functions provide immediate consistency without introducing difficult external native dependencies.

---

## Decision 8: Standard Python Structured Logging over Print/Traceback

### Decision
Replace `print()` and `traceback.print_exc()` with `logging.getLogger(__name__)` configured via `logging.basicConfig()` in `backend/app.py`.

### Reason
`print()` statements cannot be filtered by log level (DEBUG, INFO, WARNING, ERROR), lack timestamps, do not include module context, and mix stdout with diagnostic output. Standard logging allows production silencing of debug messages, structured formatting, and integration with log management tools.

### Alternatives Considered
- **Leaving `print()` statements**: Unprofessional, insecure, difficult to manage in production.
- **Heavy logging frameworks (e.g. Loguru, ELK stack integrations)**: Overkill for Phase 1.

### Why the Chosen Approach Was Preferred
Python's built-in `logging` module is zero-dependency, robust, and standard across all Python backend architectures.
