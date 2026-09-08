# Bug Log

This document records the actual bugs discovered and fixed during Phase 1 development.

---

## Bug 1: Missing Core Runtime Dependencies

- **Problem**:
  Attempting to run image, video, or audio detection resulted in `ModuleNotFoundError` or failed deployment because essential scientific libraries were not declared.
- **Cause**:
  `requirements.txt` only listed `Flask`, `flask-cors`, `python-dotenv`, and `gunicorn`. The code in `backend/services/` actively imported `numpy`, `cv2` (`opencv-python`), and `scipy.io.wavfile` (`scipy`), which were absent from the manifest.
- **Location**:
  `requirements.txt`
- **Fix**:
  Added exact pinned versions compatible with Python 3.13:
  - `numpy==2.2.3`
  - `opencv-python==4.11.0.86`
  - `scipy==1.15.2`
  - `pytest==8.3.4`
- **Verification**:
  Installed in a fresh `.venv` with `pip install -r requirements.txt`. Verified exit code 0 and successful module imports.
- **Status**:
  Fixed.

---

## Bug 2: Internal Exception and Stack Trace Leakage to Clients

- **Problem**:
  When an exception occurred in image, video, audio, or abuse routes, the raw exception string was returned directly in the client JSON response (`message=f"Internal Error: {str(e)}"`). This exposed local filesystem paths, OpenCV C++ assertions, and library internals.
- **Cause**:
  Route exception handlers directly formatted `str(e)` into the client-facing response rather than using sanitized messages. Additionally, `image_routes.py` dumped tracebacks to stdout using `traceback.print_exc()`.
- **Location**:
  - `backend/routes/image_routes.py` (lines 58–61)
  - `backend/routes/video_routes.py` (lines 59–62)
  - `backend/routes/audio_routes.py` (lines 59–62)
  - `backend/routes/abuse_routes.py` (lines 49–52)
- **Fix**:
  Replaced raw exception formatting with safe, generic messages (e.g. `"An unexpected error occurred while analyzing the image."`) and logged full tracebacks server-side using `logger.exception()`.
- **Verification**:
  Automated test `tests/test_error_handling.py::test_unhandled_exception_does_not_leak_internals` verifies that sensitive internal paths and exception strings never leak into the response envelope.
- **Status**:
  Fixed.

---

## Bug 3: Framework-Level Errors Returned HTML Instead of Standard JSON Envelope

- **Problem**:
  When a client requested an invalid URL (404), an invalid HTTP method (405), or uploaded a file exceeding the maximum size (413), Flask returned default Werkzeug HTML error pages. This broke client JSON parsing and violated the uniform API envelope standard.
- **Cause**:
  The Flask application had no registered `@app.errorhandler` hooks for framework-level HTTP exceptions.
- **Location**:
  `backend/app.py`
- **Fix**:
  Created `backend/utils/errors.py` and registered centralized handlers for 400, 404, 405, 413, and generic exceptions in `create_app()`, returning standard `api_response` JSON structures.
- **Verification**:
  Automated tests `test_404_not_found_returns_json`, `test_405_method_not_allowed_returns_json`, and `test_413_payload_too_large_returns_json` passed. Live HTTP tests confirmed JSON content-type and correct status codes.
- **Status**:
  Fixed.

---

## Bug 4: Configuration Template `.env.example` Blocked by Gitignore

- **Problem**:
  The configuration template `.env.example` could not be tracked or committed because `.gitignore` matched `.env.*`.
- **Cause**:
  Wildcard ignore pattern `# Environment variables / secrets \n .env \n .env.*` matched `.env.example`.
- **Location**:
  `.gitignore` (line 3)
- **Fix**:
  Added the un-ignore rule `!.env.example` directly beneath `.env.*`.
- **Verification**:
  Ran `git check-ignore -v .env.example` and confirmed it is no longer ignored, while `.env` remains strictly ignored.
- **Status**:
  Fixed.

---

## Bug 5: Unhandled Non-String Type in Text Route Validation

- **Problem**:
  If a client supplied a non-string payload for the `"text"` field (such as an integer, boolean, or null: `{"text": 12345}`), calling `input_text.strip()` raised an uncaught `AttributeError`, causing an unexpected 500 error instead of a clean 400 validation error.
- **Cause**:
  Validation checked `"text" not in body` but did not check `isinstance(input_text, str)` before invoking string methods.
- **Location**:
  `backend/routes/text_routes.py`
- **Fix**:
  Added explicit type validation:
  ```python
  input_text = body.get("text")
  if not isinstance(input_text, str):
      return api_response(False, "Field 'text' must be a valid string.", None, "INVALID_INPUT", 400)
  ```
- **Verification**:
  Automated test `tests/test_text_detection.py::test_detect_text_non_string_type` passed with HTTP 400 and `INVALID_INPUT`.
- **Status**:
  Fixed.

---

## Bug 6: Unbounded Image Dimension Decompression Bomb Vulnerability (SEC-01)

- **Problem**:
  `ImageDetectionService.analyze_image()` decoded raw image bytes without dimension constraints. Allocating full-resolution float32 masks (`np.zeros((h, w), dtype=np.float32)`) on maliciously crafted images with extreme dimensions (e.g. $30,000 \times 30,000$ pixels) triggered gigabyte-scale memory spikes (> 10 GB), causing instant process termination via the operating system Out-Of-Memory (OOM) killer.
- **Cause**:
  Absence of post-decode dimension and pixel count bounds checking prior to mask allocation and Gaussian blur convolutions.
- **Location**:
  `backend/services/image_service.py`
- **Fix**:
  Introduced `MAX_IMAGE_WIDTH = 4096`, `MAX_IMAGE_HEIGHT = 4096`, and `MAX_IMAGE_PIXELS = 16_777_216`. Immediately after `cv2.imdecode()`, dimensions are validated against policy. If exceeded, `ValueError` is raised, returning HTTP 400 `PROCESSING_ERROR` without creating or persisting a `Scan` record. Additionally downscaled heatmap previews to max dimension 512 px.
- **Verification**:
  Automated tests in `tests/test_image_detection.py` and `tests/test_image_persistence.py` verify that oversized width, height, and pixel counts return HTTP 400 and persist zero database records.
- **Status**:
  Fixed.

