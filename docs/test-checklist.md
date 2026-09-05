# Backend Test Execution Checklist

All test entries recorded below were **actually executed** on Windows with Python 3.13.7 in the isolated `.venv` environment.

---

## 1. Automated Unit & Integration Tests (Pytest)

- **Command Executed**: `.venv\Scripts\python.exe -m pytest -v`
- **Execution Date**: 2026-09-04
- **Result Summary**: **41 passed, 0 failed, 0 skipped in 0.62s**

| Test Suite | Test Case | Target / Functionality | Status | Details |
| :--- | :--- | :--- | :---: | :--- |
| `test_startup_and_health.py` | `test_app_creation` | Flask factory initialization | **PASSED** | App object successfully created with defaults |
| `test_startup_and_health.py` | `test_health_endpoint_success` | `GET /api/health` envelope | **PASSED** | Returned HTTP 200, OPERATIONAL, 4 modalities |
| `test_startup_and_health.py` | `test_cors_headers` | CORS headers on response | **PASSED** | `Access-Control-Allow-Origin` matches client |
| `test_error_handling.py` | `test_404_not_found_returns_json` | Unknown route handler | **PASSED** | Returned HTTP 404 with JSON envelope |
| `test_error_handling.py` | `test_405_method_not_allowed_returns_json` | Wrong HTTP method | **PASSED** | Returned HTTP 405 with JSON envelope |
| `test_error_handling.py` | `test_413_payload_too_large_returns_json` | Oversized payload handler | **PASSED** | Returned HTTP 413 with `PAYLOAD_TOO_LARGE` |
| `test_error_handling.py` | `test_unhandled_exception_does_not_leak_internals` | Error sanitization | **PASSED** | Returned HTTP 500 without stack trace leakage |
| `test_text_detection.py` | `test_detect_text_success` | Valid text analysis | **PASSED** | Returned HTTP 200 with confidence and metrics |
| `test_text_detection.py` | `test_detect_text_missing_field` | Missing `"text"` field | **PASSED** | Returned HTTP 400 with `INVALID_INPUT` |
| `test_text_detection.py` | `test_detect_text_too_short` | Text < 20 characters | **PASSED** | Returned HTTP 400 with `TEXT_TOO_SHORT` |
| `test_text_detection.py` | `test_detect_text_non_string_type` | Non-string `"text"` input | **PASSED** | Returned HTTP 400 with `INVALID_INPUT` |
| `test_text_detection.py` | `test_detect_text_empty_body` | Non-JSON / empty body | **PASSED** | Returned HTTP 400 with `INVALID_INPUT` |
| `test_image_detection.py` | `test_detect_image_success` | Valid image (`test.jpg`) | **PASSED** | Returned HTTP 200 with Base64 heatmap preview |
| `test_image_detection.py` | `test_detect_image_missing_file_field` | Missing `"image"` field | **PASSED** | Returned HTTP 400 with `MISSING_FILE` |
| `test_image_detection.py` | `test_detect_image_empty_filename` | Empty filename upload | **PASSED** | Returned HTTP 400 with `INVALID_FILE` |
| `test_image_detection.py` | `test_detect_image_unsupported_extension` | Unsupported extension (`.txt`) | **PASSED** | Returned HTTP 400 with `INVALID_FILE` |
| `test_image_detection.py` | `test_detect_image_corrupt_content` | Corrupted byte stream | **PASSED** | Returned HTTP 400 with `PROCESSING_ERROR` |
| `test_video_detection.py` | `test_detect_video_success` | Valid video (`test.mp4`) | **PASSED** | Returned HTTP 200 with keyframe preview |
| `test_video_detection.py` | `test_detect_video_missing_file_field` | Missing `"video"` field | **PASSED** | Returned HTTP 400 with `MISSING_FILE` |
| `test_video_detection.py` | `test_detect_video_empty_filename` | Empty filename upload | **PASSED** | Returned HTTP 400 with `INVALID_FILE` |
| `test_video_detection.py` | `test_detect_video_unsupported_extension` | Unsupported extension (`.txt`) | **PASSED** | Returned HTTP 400 with `INVALID_FORMAT` |
| `test_audio_detection.py` | `test_detect_audio_success` | Valid audio (`test.wav`) | **PASSED** | Returned HTTP 200 with lip-sync discrepancy list |
| `test_audio_detection.py` | `test_detect_audio_missing_file_field` | Missing `"audio"` field | **PASSED** | Returned HTTP 400 with `MISSING_FILE` |
| `test_audio_detection.py` | `test_detect_audio_empty_filename` | Empty filename upload | **PASSED** | Returned HTTP 400 with `INVALID_FILE` |
| `test_audio_detection.py` | `test_detect_audio_unsupported_extension` | Unsupported extension (`.txt`) | **PASSED** | Returned HTTP 400 with `INVALID_FORMAT` |
| `test_abuse_report.py` | `test_dispatch_abuse_report_success` | Valid abuse payload | **PASSED** | Returned HTTP 201 with SHA-256 fingerprint |
| `test_abuse_report.py` | `test_dispatch_abuse_report_unsupported_platform` | Unsupported platform (`tiktok`) | **PASSED** | Returned HTTP 400 with `VALIDATION_ERROR` |
| `test_abuse_report.py` | `test_dispatch_abuse_report_missing_target_url` | Missing target URL | **PASSED** | Returned HTTP 400 with `VALIDATION_ERROR` |
| `test_abuse_report.py` | `test_dispatch_abuse_report_empty_or_invalid_json` | Non-JSON payload | **PASSED** | Returned HTTP 400 with `INVALID_JSON` |
| `test_database.py` | `test_user_model_creation` | User model creation | **PASSED** | Inserted and retrieved User with timestamp |
| `test_database.py` | `test_user_unique_email_constraint` | Unique email constraint | **PASSED** | Duplicate email raised `IntegrityError` |
| `test_database.py` | `test_scan_model_creation_nullable_user` | Scan creation with null user | **PASSED** | Anonymous scan persisted with `user_id=None` |
| `test_database.py` | `test_scan_result_model_creation` | ScanResult creation with JSON | **PASSED** | Persisted metrics and breakdown in JSON column |
| `test_database.py` | `test_abuse_report_model_creation` | AbuseReport creation with JSON | **PASSED** | Persisted dossier manifest in JSON column |
| `test_database.py` | `test_user_scans_relationship` | User → Scans (1-to-many) | **PASSED** | Scans linked via `user.scans` bidirectional |
| `test_database.py` | `test_scan_scan_result_relationship` | Scan → ScanResult (1-to-1) | **PASSED** | Result linked via `scan.result` bidirectional |
| `test_database.py` | `test_scan_abuse_reports_relationship` | Scan → AbuseReports (1-to-many) | **PASSED** | Reports linked via `scan.abuse_reports` |
| `test_database.py` | `test_user_abuse_reports_relationship` | User → AbuseReports (1-to-many) | **PASSED** | Reports linked via `user.abuse_reports` |
| `test_database.py` | `test_foreign_key_constraint_invalid_user_on_scan` | Foreign key enforcement | **PASSED** | Invalid `user_id` raised `IntegrityError` |
| `test_database.py` | `test_foreign_key_constraint_invalid_scan_on_result` | Foreign key enforcement | **PASSED** | Invalid `scan_id` raised `IntegrityError` |
| `test_database.py` | `test_migration_truthlens_db_schema` | Migration schema verification | **PASSED** | Verified all 4 tables + `alembic_version` in `truthlens.db` |

---

## 2. Live HTTP Server Verification Tests

- **Target Server**: `http://127.0.0.1:5000` (started via `.venv\Scripts\python.exe -m backend.app`)
- **Execution Method**: Real HTTP requests sent via Python urllib test script
- **Result Summary**: 10 passed, 0 failed

| Endpoint / Operation | Method | Payload Type | Expected Status | Actual Status | Envelope `success` | Result |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| `/api/health` | GET | None | 200 | 200 | True | **PASSED** |
| `/api/detect/text` | POST | JSON (> 20 chars) | 200 | 200 | True | **PASSED** |
| `/api/detect/text` | POST | JSON (< 20 chars) | 400 | 400 | False | **PASSED** |
| `/api/detect/image` | POST | Multipart (`test.jpg`) | 200 | 200 | True | **PASSED** |
| `/api/detect/video` | POST | Multipart (`test.mp4`) | 200 | 200 | True | **PASSED** |
| `/api/detect/audio` | POST | Multipart (`test.wav`) | 200 | 200 | True | **PASSED** |
| `/api/report/abuse` | POST | JSON (YouTube target) | 201 | 201 | True | **PASSED** |
| `/api/report/abuse` | POST | JSON (TikTok target) | 400 | 400 | False | **PASSED** |
| `/api/not-a-real-endpoint` | GET | None | 404 | 404 | False | **PASSED** |
| `/api/detect/text` | GET | None (Wrong method) | 405 | 405 | False | **PASSED** |

---

## 3. Database & Security Checks

| Security Check | Verification Method | Status | Notes |
| :--- | :--- | :---: | :--- |
| `.env` file untracked | `git status` | **PASSED** | Verified `.env` is ignored by `.gitignore` |
| `.env.example` trackable | `git status` | **PASSED** | Verified `.env.example` shows as untracked file ready for commit |
| SQLite database files untracked | `git status` | **PASSED** | Verified `*.db`, `*.sqlite` ignored by `.gitignore` |
| Production secret guard | Code inspection & unit logic | **PASSED** | `backend/config.py` raises `ValueError` in production if default secret used |
| Virtualenv isolation | Directory and pip listing | **PASSED** | `.venv` is ignored by git and isolates all 12 required packages |
| SQLite foreign keys enforced | PRAGMA hook & test execution | **PASSED** | Invalid foreign keys raise `IntegrityError` |
| Migration idempotency | `flask db upgrade` check | **PASSED** | Applied cleanly to `truthlens.db` |
