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

---

## Bug 7: Windows Video Temporary File Lock Leak and Unbounded Resource Consumption (SEC-02)

- **Problem**:
  When video processing encountered an error (corrupt video stream, zero readable frames, unhandled processing exception, or duration/resolution violation), the temporary video file created on disk was never deleted on Windows systems. The server disk steadily accumulated orphaned temporary video files (up to 50 MB each), leading to eventual disk exhaustion and server denial-of-service. Additionally, there were no constraints on video duration or decoded frame dimensions.
- **Cause**:
  1. `cap.release()` was located inside the `try` block after frame analysis. If any exception occurred before that point, `cap.release()` never executed.
  2. The `finally` block attempted `os.remove(temp_path)` while the `cv2.VideoCapture` object still held an exclusive OS file handle on Windows. On Windows, attempting to delete an open file raises `PermissionError: [WinError 32] The process cannot access the file because it is being used by another process`.
  3. The `except OSError: pass` block in `finally` silently swallowed this `PermissionError`, hiding the failure and permanently orphaning the file.
  4. Absence of video duration and frame dimension limits permitted processing of arbitrarily long or massive video files.
- **Location**:
  `backend/services/video_service.py`
- **Fix**:
  1. Restructured `analyze_video` with a deterministic `finally` cleanup:
     ```python
     finally:
         if cap is not None:
             try:
                 cap.release()
             except Exception as e:
                 logger.warning("Error releasing VideoCapture handle: %s", str(e))
         if os.path.exists(temp_path):
             try:
                 os.remove(temp_path)
             except OSError as e:
                 logger.warning("Failed to remove temporary video file %s: %s", temp_path, str(e))
     ```
  2. Dynamically derived the temporary file suffix (`.mp4`, `.mov`, `.avi`, `.mkv`) based on the validated extension.
  3. Introduced `MAX_VIDEO_DURATION_SECONDS = 120`. Rejects videos exceeding 120s with HTTP 400 `PROCESSING_ERROR` and persists zero scans.
  4. Introduced `MAX_VIDEO_WIDTH = 4096`, `MAX_VIDEO_HEIGHT = 4096`, `MAX_VIDEO_PIXELS = 16_777_216`. Checked container metadata first and validated actual decoded frame dimensions upon reading each frame.
- **Verification**:
  Automated tests in `tests/test_video_detection.py` and `tests/test_video_persistence.py` verify that `cap.release()` executes before `os.remove()`, temporary files are cleaned up on success and failure, oversized durations and resolutions return 400 `PROCESSING_ERROR`, and zero scans are created. Live verification via `scratch/verify_live_video_hardening.py` confirmed clean temp directory and proper rejection.
- **Status**:
  Fixed.

---

## Bug 8: Synthetic Noise Fallback on Audio Decode Failure and Fabricated Forensic Results (SEC-03)

- **Problem**:
  In `AudioDetectionService.analyze_audio()`, when `scipy.io.wavfile.read()` failed to decode an audio file (due to corrupt binary bytes, unsupported containers, or truncated content), the exception was caught and synthetic Gaussian noise was silently generated:
  ```python
  sample_rate = 16000
  data = np.random.normal(0, 0.1, 16000 * 3)
  ```
  This synthetic waveform was processed as if it were authentic audio from the user upload, calculating arbitrary Zero Crossing Rates, energy variances, confidence scores, and synthetic/authentic verdicts. The fabricated result was then persisted into the database as a genuine `Scan` and `ScanResult` record. In a forensic verification platform, persisting fabricated results for corrupt or unreadable files undermines platform integrity and evidentiary credibility.
- **Cause**:
  1. An artificial mock fallback in `analyze_audio` that caught all decoding exceptions and synthesized random noise rather than propagating an error.
  2. `ALLOWED_AUDIO_EXTENSIONS` allowed `mp3`, `m4a`, and `flac` despite `scipy.io.wavfile.read` having no support for non-WAV containers, forcing non-WAV uploads directly into the synthetic fallback path.
  3. Missing decoded buffer checks for empty/zero-sample arrays or non-positive sample rates.
- **Location**:
  `backend/services/audio_service.py`
  `backend/utils/file_validator.py`
- **Fix**:
  1. Completely removed the synthetic noise fallback. If `scipy.io.wavfile.read()` raises an exception, the service logs a warning and raises `ValueError("Failed to decode audio file. File might be corrupted or in an unsupported format.")`.
  2. Added explicit buffer checks: raises `ValueError("Uploaded audio contains zero readable audio samples.")` if `data.size == 0`, and `ValueError("Uploaded audio has an invalid sample rate.")` if `sample_rate <= 0`.
  3. Adopted Option A (WAV-only policy): updated `ALLOWED_AUDIO_EXTENSIONS = {"wav"}` in `backend/utils/file_validator.py` so unsupported formats fail fast with HTTP 400 `INVALID_FORMAT`.
  4. Added deterministic temporary file cleanup in `finally:` with warning logging if `os.remove(temp_path)` encounters an `OSError`.
  5. Ensured zero-scan persistence: `audio_routes.py` catches `ValueError`, returning HTTP 400 `PROCESSING_ERROR` before `ScanService.create_scan` is called, ensuring 0 `Scan` and 0 `ScanResult` records are created.
- **Verification**:
  - `tests/test_audio_detection.py`: verified corrupt WAV returns 400, empty WAV returns 400, non-WAV returns 400, synthetic noise generator is never invoked, buffer bounds work, and temp files are deleted on success and failure (17 passed).
  - `tests/test_audio_persistence.py`: verified corrupt, empty, unsupported, and failing audio files create 0 scans and 0 scan results in the database (18 passed).
  - `scratch/verify_live_audio_hardening.py`: end-to-end live verification passed across all rejection and persistence scenarios.
  - Full regression test suite: 234 tests passed.
- **Status**:
  Fixed.

---

## Bug 9: File Extension Spoofing Exposure and Unsafe Filename Path Traversal Ingestion (SEC-04)

- **Problem**:
  1. `file_validator.py` verified media uploads solely by checking the filename extension against an allowed set (`ALLOWED_IMAGE_EXTENSIONS`, `ALLOWED_VIDEO_EXTENSIONS`, `ALLOWED_AUDIO_EXTENSIONS`). The underlying byte stream was never validated for expected container headers or magic bytes. An attacker or client could upload arbitrary executable, script, or binary payloads disguised with a valid extension (e.g. `payload.exe` renamed to `evidence.jpg` or `trojan.bat` named to `audio.wav`), passing validator checks and feeding raw binary into image/video/audio decoders.
  2. Client-provided filenames were ingested without safety or traversal sanitization. Filenames containing path traversal sequences (`../../`, `..\..\`), Windows drive letters (`C:`), alternate data streams (`:`), control characters (`\x00`), or leading/trailing whitespace could cause path traversal issues, file write errors, or log pollution.
- **Cause**:
  1. Complete absence of magic-byte file signature verification on upload streams.
  2. Incomplete filename validation: only checked `filename != ""` and `'.' in filename`.
- **Location**:
  `backend/utils/file_validator.py`
  `backend/routes/image_routes.py`
  `backend/routes/video_routes.py`
  `backend/routes/audio_routes.py`
- **Fix**:
  1. Implemented `read_file_prefix(file_storage, max_bytes=32)` to safely read bounded header bytes and deterministically rewind the stream via `try ... finally: stream.seek(pos)`.
  2. Added container signature validators:
     - Images: JPEG (`\xff\xd8\xff`), PNG (`\x89PNG\r\n\x1a\n`), WebP (`RIFF....WEBP`).
     - Videos: MP4 (`ftyp` at bytes 4..8), MOV (conservative ISOBMFF `ftyp` at bytes 4..8), AVI (`RIFF....AVI ` / `AVIX`), MKV (`\x1a\x45\xdf\xa3`).
     - Audio: WAV only (`RIFF....WAVE` / `RIFX....WAVE`).
  3. Implemented `is_safe_filename(filename)`:
     - Rejects path separators (`/`, `\`), Windows drive letters and ADS colons (`:`), control characters and null bytes (`ord < 32 or ord == 127`), excessive length (> 255 chars), dot directory navigation (`.`, `..`), dot prefixes/suffixes, and leading/trailing whitespace.
     - Safely permits legitimate ordinary filenames with double dots (e.g. `audit..v1.jpg`), spaces, and international Unicode characters.
  4. Standardized error codes: `INVALID_FILE` for filename issues, `INVALID_FORMAT` for extension or signature mismatches.
  5. Guaranteed zero database persistence on rejected uploads.
- **Verification**:
  - `tests/test_file_validator.py`: 26 comprehensive unit tests covering all safety and signature rules.
  - Integration & persistence tests across `tests/test_image_detection.py`, `tests/test_image_persistence.py`, `tests/test_video_detection.py`, `tests/test_video_persistence.py`, `tests/test_audio_detection.py`, `tests/test_audio_persistence.py`.
  - In-process live verification script `scratch/verify_live_magic_bytes_and_filename.py` passed all checks.
  - Full regression test suite: 309 tests passed.
- **Status**:
  Fixed.




