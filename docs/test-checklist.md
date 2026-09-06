# Backend Test Execution Checklist

All test entries recorded below were **actually executed** on Windows with Python 3.13.7 in the isolated `.venv` environment.

---

## 1. Automated Unit & Integration Tests (Pytest)

- **Command Executed**: `.venv\Scripts\python.exe -m pytest -v`
- **Execution Date**: 2026-09-06
- **Result Summary**: **66 passed, 0 failed, 0 skipped in 2.43s**

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
| `test_text_detection.py` | `test_detect_text_empty_body` | Empty request payload | **PASSED** | Returned HTTP 400 with `INVALID_INPUT` |
| `test_image_detection.py` | `test_detect_image_success` | Valid image analysis | **PASSED** | Returned HTTP 200 with forensic metrics |
| `test_image_detection.py` | `test_detect_image_missing_file_field` | Missing file in upload | **PASSED** | Returned HTTP 400 with `MISSING_FILE` |
| `test_image_detection.py` | `test_detect_image_empty_filename` | Empty filename uploaded | **PASSED** | Returned HTTP 400 with `NO_SELECTED_FILE` |
| `test_image_detection.py` | `test_detect_image_unsupported_extension` | Unsupported file extension | **PASSED** | Returned HTTP 400 with `UNSUPPORTED_MEDIA_TYPE` |
| `test_image_detection.py` | `test_detect_image_corrupt_content` | Unparseable/corrupt image | **PASSED** | Returned HTTP 400 with `CORRUPT_OR_UNREADABLE_FILE` |
| `test_video_detection.py` | `test_detect_video_success` | Valid video analysis | **PASSED** | Returned HTTP 200 with temporal metrics |
| `test_video_detection.py` | `test_detect_video_missing_file_field` | Missing file in upload | **PASSED** | Returned HTTP 400 with `MISSING_FILE` |
| `test_video_detection.py` | `test_detect_video_empty_filename` | Empty filename uploaded | **PASSED** | Returned HTTP 400 with `NO_SELECTED_FILE` |
| `test_video_detection.py` | `test_detect_video_unsupported_extension` | Unsupported file extension | **PASSED** | Returned HTTP 400 with `UNSUPPORTED_MEDIA_TYPE` |
| `test_audio_detection.py` | `test_detect_audio_success` | Valid audio analysis | **PASSED** | Returned HTTP 200 with spectral metrics |
| `test_audio_detection.py` | `test_detect_audio_missing_file_field` | Missing file in upload | **PASSED** | Returned HTTP 400 with `MISSING_FILE` |
| `test_audio_detection.py` | `test_detect_audio_empty_filename` | Empty filename uploaded | **PASSED** | Returned HTTP 400 with `NO_SELECTED_FILE` |
| `test_audio_detection.py` | `test_detect_audio_unsupported_extension` | Unsupported file extension | **PASSED** | Returned HTTP 400 with `UNSUPPORTED_MEDIA_TYPE` |
| `test_abuse_report.py` | `test_dispatch_abuse_report_success` | Valid report submission | **PASSED** | Returned HTTP 200 with dossier payload |
| `test_abuse_report.py` | `test_dispatch_abuse_report_unsupported_platform` | Unknown platform report | **PASSED** | Returned HTTP 400 with `UNSUPPORTED_PLATFORM` |
| `test_abuse_report.py` | `test_dispatch_abuse_report_missing_target_url` | Missing target URL | **PASSED** | Returned HTTP 400 with `MISSING_FIELD` |
| `test_abuse_report.py` | `test_dispatch_abuse_report_empty_or_invalid_json` | Malformed report JSON | **PASSED** | Returned HTTP 400 with `INVALID_JSON` |
| `test_database.py` | `test_user_model_creation` | User model attributes | **PASSED** | Model created with default values and timestamps |
| `test_database.py` | `test_user_unique_email_constraint` | Unique email constraint | **PASSED** | Duplicate email raised `IntegrityError` |
| `test_database.py` | `test_scan_model_creation_nullable_user` | Nullable `user_id` on Scan | **PASSED** | Scan created without user association |
| `test_database.py` | `test_scan_result_model_creation` | ScanResult JSON storage | **PASSED** | Model persisted with complex JSON payload |
| `test_database.py` | `test_abuse_report_model_creation` | AbuseReport model creation | **PASSED** | Model persisted with platform and report JSON |
| `test_database.py` | `test_user_scans_relationship` | User → Scans (1-to-many) | **PASSED** | Scans linked via `user.scans` bidirectional |
| `test_database.py` | `test_scan_scan_result_relationship` | Scan → ScanResult (1-to-1) | **PASSED** | Result linked via `scan.result` bidirectional |
| `test_database.py` | `test_scan_abuse_reports_relationship` | Scan → AbuseReports (1-to-many) | **PASSED** | Reports linked via `scan.abuse_reports` |
| `test_database.py` | `test_user_abuse_reports_relationship` | User → AbuseReports (1-to-many) | **PASSED** | Reports linked via `user.abuse_reports` |
| `test_database.py` | `test_foreign_key_constraint_invalid_user_on_scan` | Foreign key enforcement | **PASSED** | Invalid `user_id` raised `IntegrityError` |
| `test_database.py` | `test_foreign_key_constraint_invalid_scan_on_result` | Foreign key enforcement | **PASSED** | Invalid `scan_id` raised `IntegrityError` |
| `test_database.py` | `test_migration_truthlens_db_schema` | Migration schema verification | **PASSED** | Verified all 4 tables + `alembic_version` in `truthlens.db` |
| `test_auth_registration.py` | `test_register_success` | User registration success | **PASSED** | Returned HTTP 201 with `{ id, name, email }` |
| `test_auth_registration.py` | `test_password_is_hashed_and_plaintext_not_stored` | Password hashing & security | **PASSED** | Plaintext not stored; matches Werkzeug `scrypt` hash |
| `test_auth_registration.py` | `test_register_duplicate_email` | Duplicate email rejection | **PASSED** | Returned HTTP 400 with `EMAIL_ALREADY_REGISTERED` |
| `test_auth_registration.py` | `test_register_email_normalization` | Email normalization | **PASSED** | Lowercased and trimmed whitespace; checked duplicate |
| `test_auth_registration.py` | `test_register_missing_name` | Name required validation | **PASSED** | Missing / whitespace name returned HTTP 400 `MISSING_FIELD` |
| `test_auth_registration.py` | `test_register_missing_email` | Email required validation | **PASSED** | Missing email returned HTTP 400 `MISSING_FIELD` |
| `test_auth_registration.py` | `test_register_missing_password` | Password required validation | **PASSED** | Missing password returned HTTP 400 `MISSING_FIELD` |
| `test_auth_registration.py` | `test_register_invalid_email_format[not-an-email]` | Email format validation | **PASSED** | Returned HTTP 400 `INVALID_EMAIL` |
| `test_auth_registration.py` | `test_register_invalid_email_format[alice@]` | Email format validation | **PASSED** | Returned HTTP 400 `INVALID_EMAIL` |
| `test_auth_registration.py` | `test_register_invalid_email_format[@example.com]` | Email format validation | **PASSED** | Returned HTTP 400 `INVALID_EMAIL` |
| `test_auth_registration.py` | `test_register_invalid_email_format[alice@domain]` | Email format validation | **PASSED** | Returned HTTP 400 `INVALID_EMAIL` |
| `test_auth_registration.py` | `test_register_invalid_email_format[alice smith@example.com]` | Email format validation | **PASSED** | Returned HTTP 400 `INVALID_EMAIL` |
| `test_auth_registration.py` | `test_register_malformed_non_json` | Non-JSON payload validation | **PASSED** | Non-JSON body returned HTTP 400 `INVALID_JSON` |
| `test_auth_registration.py` | `test_response_does_not_expose_password_hash` | Password leak prevention | **PASSED** | Response string does not contain `password_hash` or salt |
| `test_auth_registration.py` | `test_register_password_min_length_12_accepted` | Min length boundary (12 chars) | **PASSED** | 12-char password accepted with HTTP 201 |
| `test_auth_registration.py` | `test_register_password_11_chars_rejected_too_short` | Min length rejection (11 chars) | **PASSED** | 11-char password rejected with `PASSWORD_TOO_SHORT` |
| `test_auth_registration.py` | `test_register_password_max_length_128_accepted` | Max length boundary (128 chars) | **PASSED** | 128-char password accepted with HTTP 201 |
| `test_auth_registration.py` | `test_register_password_129_chars_rejected_too_long` | Max length rejection (129 chars) | **PASSED** | 129-char password rejected with `PASSWORD_TOO_LONG` |
| `test_auth_registration.py` | `test_register_password_complex_characters_accepted` | Complex character combination | **PASSED** | Upper, lower, digit, special accepted with HTTP 201 |
| `test_auth_registration.py` | `test_register_password_passphrase_accepted` | Long passphrase without composition rules | **PASSED** | All-lowercase passphrase accepted with HTTP 201 |
| `test_auth_registration.py` | `test_register_password_spaces_preserved_and_accepted` | Password spaces preserved in hash | **PASSED** | Leading/trailing/internal spaces preserved in hash |
| `test_auth_registration.py` | `test_register_password_unicode_accepted` | Unicode character acceptance | **PASSED** | Passwords with Unicode characters hashed & verified |
| `test_auth_registration.py` | `test_register_weak_password_rejected` | Local weak-password blocklist | **PASSED** | Common weak sequence rejected with `WEAK_PASSWORD` |
| `test_auth_registration.py` | `test_register_weak_password_case_insensitive` | Case-insensitive blocklist | **PASSED** | Uppercase weak password rejected with `WEAK_PASSWORD` |
| `test_auth_registration.py` | `test_register_weak_password_surrounding_whitespace_blocked` | Whitespace bypass prevention | **PASSED** | Padded weak password rejected with `WEAK_PASSWORD` |

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
