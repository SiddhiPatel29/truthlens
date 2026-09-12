# Backend REST API Specification

This document specifies the exact API contract for all endpoints currently available in the VeraMedia AI backend. This specification is designed for the frontend engineering team.

---

## Global Response Structure

All API endpoints return a standardized JSON envelope:

### Successful Response Envelope
```json
{
  "success": true,
  "message": "Human readable confirmation message.",
  "data": { ... },
  "error_code": null
}
```

### Error Response Envelope
```json
{
  "success": false,
  "message": "Safe human readable description of the error.",
  "data": null,
  "error_code": "SPECIFIC_ERROR_CODE"
}
```

---

## 1. System Health Check

- **Method**: `GET`
- **Path**: `/api/health`
- **Authentication**: None (Public)
- **Service Called**: None (Direct controller response)
- **Request Headers**: None required
- **Request Body**: None

### Validation Rules
None.

### Success Response (`200 OK`)
```json
{
  "success": true,
  "message": "VeraMedia AI Backend is running smoothly.",
  "data": {
    "service": "VeraMedia AI Backend",
    "status": "OPERATIONAL",
    "version": "1.0.0",
    "supported_modalities": ["video", "audio", "image", "text"]
  },
  "error_code": null
}
```

---

## 2. Text Deepfake & Synthetic Content Detection

- **Method**: `POST`
- **Path**: `/api/detect/text`
- **Authentication**: Required (`Authorization: Bearer <access_token>`) via `@require_auth`
- **Services Called**: `TextDetectionService.analyze_text`, `ScanService.create_scan`, `ScanService.save_scan_result`
- **Persistence**: Persists a `Scan` (modality `text`, owned by the authenticated user) in `PENDING` status, followed by an atomic commit of a `ScanResult` (`COMPLETED` status, timestamp, calculated `prediction`, `confidence`, and `risk_level`).
- **Request Headers**:
  - `Content-Type: application/json`
  - `Authorization: Bearer <token>`
- **Request Body**:
```json
{
  "text": "The investigative report confirmed that generative text tools exhibit uniform sentence lengths."
}
```

### Validation Rules
1. Request must contain a valid Bearer JWT in the `Authorization` header.
2. Body must be valid JSON object containing key `"text"`.
3. `"text"` must be a string.
4. `len(text.strip()) >= 20` characters.

### Success Response (`200 OK`)
```json
{
  "success": true,
  "message": "Text analyzed successfully.",
  "data": {
    "is_ai_generated": false,
    "ai_confidence_score": 0.32,
    "metrics": {
      "total_sentences": 1,
      "total_words": 12,
      "burstiness_index": 0.0,
      "lexical_diversity": 1.0
    },
    "sentence_breakdown": [
      {
        "sentence": "The investigative report confirmed that generative text tools exhibit uniform sentence lengths.",
        "word_count": 12,
        "suspicious": false
      }
    ]
  },
  "error_code": null
}
```

### Error Responses
- **Missing or non-Bearer `Authorization` header (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Authentication required.",
    "data": null,
    "error_code": "AUTHENTICATION_REQUIRED"
  }
  ```
- **Expired JWT access token (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Authentication token has expired.",
    "data": null,
    "error_code": "TOKEN_EXPIRED"
  }
  ```
- **Invalid or malformed JWT token (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Invalid authentication token.",
    "data": null,
    "error_code": "INVALID_TOKEN"
  }
  ```
- **Missing or non-string `"text"` field (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Request body must contain a 'text' field.",
    "data": null,
    "error_code": "INVALID_INPUT"
  }
  ```
- **Text under 20 characters (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Text is too short. Please provide at least 20 characters for meaningful analysis.",
    "data": null,
    "error_code": "TEXT_TOO_SHORT"
  }
  ```
- **Persistence Failure (`500 Internal Server Error`)**:
  ```json
  {
    "success": false,
    "message": "An error occurred while persisting the scan results.",
    "data": null,
    "error_code": "INTERNAL_SERVER_ERROR"
  }
  ```

---

## 3. Image Tamper & Deepfake Detection

- **Method**: `POST`
- **Path**: `/api/detect/image`
- **Authentication**: Required (`Authorization: Bearer <access_token>`) via `@require_auth`
- **Services Called**: `ImageDetectionService.analyze_image`, `ScanService.create_scan`, `ScanService.save_scan_result`
- **Persistence**: Persists a `Scan` (modality `image`, `filename` set to uploaded filename, owned by authenticated user) in `PENDING` status, followed by an atomic commit of a `ScanResult` (`COMPLETED` status, timestamp, calculated `prediction` `DEEPFAKE` or `AUTHENTIC`, `confidence`, and `risk_level`). Raw image bytes are NOT stored in the database.
- **Request Headers**:
  - `Content-Type: multipart/form-data`
  - `Authorization: Bearer <token>`
- **Request Body**:
  - `image` (binary file): Supported formats: `.png`, `.jpg`, `.jpeg`, `.webp`.

### Validation Rules
1. Request must contain a valid Bearer JWT in the `Authorization` header.
2. Request must be `multipart/form-data` with form field name `image`.
3. File must be present and filename non-empty.
4. Filename must be safe: length <= 255, no path traversal separators (`/`, `\`), no drive letters or ADS colons (`:`), no control characters or null bytes, no directory navigation (`.` or `..`), no leading/trailing whitespace. Legitimate double dots (e.g. `audit..v1.jpg`), spaces, and international Unicode are accepted. (Violations return 400 `INVALID_FILE`).
5. Extension must be in `{"png", "jpg", "jpeg", "webp"}`. (Violations return 400 `INVALID_FORMAT`).
6. Magic-byte signature must match the declared format: JPEG (`\xff\xd8\xff`), PNG (`\x89PNG\r\n\x1a\n`), WebP (`RIFF....WEBP`). Bounded 32-byte header inspection with deterministic stream rewind. (Violations return 400 `INVALID_FORMAT`).
7. Dimensions must not exceed 4096x4096px or 16,777,216 total pixels. (Violations return 400 `PROCESSING_ERROR`).
8. Total payload must not exceed `MAX_CONTENT_LENGTH` (50 MB).

### Success Response (`200 OK`)
```json
{
  "success": true,
  "message": "Image analyzed successfully.",
  "data": {
    "is_deepfake": false,
    "confidence_score": 0.446,
    "manipulation_type": "Authentic Pixel Distribution",
    "image_dimensions": {
      "width": 640,
      "height": 480
    },
    "heatmap_preview": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/..."
  },
  "error_code": null
}
```

### Error Responses
- **Missing or non-Bearer `Authorization` header (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Authentication required.",
    "data": null,
    "error_code": "AUTHENTICATION_REQUIRED"
  }
  ```
- **Expired JWT access token (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Authentication token has expired.",
    "data": null,
    "error_code": "TOKEN_EXPIRED"
  }
  ```
- **Invalid or malformed JWT token (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Invalid authentication token.",
    "data": null,
    "error_code": "INVALID_TOKEN"
  }
  ```
- **Missing `image` field (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "No 'image' file field found in request.",
    "data": null,
    "error_code": "MISSING_FILE"
  }
  ```
- **Unsafe filename or path traversal attempt (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Invalid filename: Filename cannot contain path separators.",
    "data": null,
    "error_code": "INVALID_FILE"
  }
  ```
- **Disallowed extension or magic-byte mismatch (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "File content does not match expected JPEG signature for .jpg.",
    "data": null,
    "error_code": "INVALID_FORMAT"
  }
  ```
- **Unreadable / corrupted image stream (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Failed to decode image. File might be corrupted or in an unsupported format.",
    "data": null,
    "error_code": "PROCESSING_ERROR"
  }
  ```
- **Persistence Failure (`500 Internal Server Error`)**:
  ```json
  {
    "success": false,
    "message": "An error occurred while persisting the scan results.",
    "data": null,
    "error_code": "INTERNAL_SERVER_ERROR"
  }
  ```

---

## 4. Video Temporal Deepfake Detection

- **Method**: `POST`
- **Path**: `/api/detect/video`
- **Authentication**: Required (`Authorization: Bearer <access_token>`) via `@require_auth`
- **Services Called**: `VideoDetectionService.analyze_video`, `ScanService.create_scan`, `ScanService.save_scan_result`
- **Persistence**: Persists a `Scan` (modality `video`, `filename` set to uploaded filename, owned by authenticated user) in `PENDING` status, followed by an atomic commit of a `ScanResult` (`COMPLETED` status, timestamp, calculated `prediction` `DEEPFAKE` or `AUTHENTIC`, `confidence`, and `risk_level`). Raw video bytes are NOT stored in the database.
- **Request Headers**:
  - `Content-Type: multipart/form-data`
  - `Authorization: Bearer <token>`
- **Request Body**:
  - `video` (binary file): Supported formats: `.mp4`, `.mov`, `.avi`, `.mkv`.

### Validation Rules
1. Request must contain a valid Bearer JWT in the `Authorization` header.
2. Request must be `multipart/form-data` with form field name `video`.
3. File must be present and filename non-empty.
4. Filename must be safe: length <= 255, no path traversal separators (`/`, `\`), no drive letters or ADS colons (`:`), no control characters or null bytes, no directory navigation (`.` or `..`), no leading/trailing whitespace. Legitimate double dots (e.g. `clip..v1.mp4`), spaces, and international Unicode are accepted. (Violations return 400 `INVALID_FILE`).
5. Extension must be in `{"mp4", "mov", "avi", "mkv"}`. (Violations return 400 `INVALID_FORMAT`).
6. Magic-byte signature must match the declared container: MP4 (`ftyp` at bytes 4..8), MOV (conservative ISOBMFF `ftyp` at bytes 4..8), AVI (`RIFF....AVI ` / `AVIX`), MKV (`\x1a\x45\xdf\xa3`). Bounded 32-byte header inspection with deterministic stream rewind. (Violations return 400 `INVALID_FORMAT`).
7. Video file must have at least 1 readable frame.
8. Total payload must not exceed `MAX_CONTENT_LENGTH` (50 MB).
9. Video duration must not exceed 120 seconds (`MAX_VIDEO_DURATION_SECONDS`). Videos exceeding 120s are rejected with HTTP 400 `PROCESSING_ERROR`.
10. Video container resolution and decoded frames must not exceed 4096x4096 px or 16,777,216 pixels (`MAX_VIDEO_WIDTH`, `MAX_VIDEO_HEIGHT`, `MAX_VIDEO_PIXELS`). Oversized videos are rejected with HTTP 400 `PROCESSING_ERROR`.

### Success Response (`200 OK`)
```json
{
  "success": true,
  "message": "Video analyzed successfully.",
  "data": {
    "is_deepfake": false,
    "confidence_score": 0.412,
    "metrics": {
      "duration_seconds": 2.5,
      "total_frames_analyzed": 16,
      "temporal_instability": 0.045,
      "peak_frame_anomaly": 0.472
    },
    "keyframe_heatmap_preview": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
  },
  "error_code": null
}
```

### Error Responses
- **Missing or non-Bearer `Authorization` header (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Authentication required.",
    "data": null,
    "error_code": "AUTHENTICATION_REQUIRED"
  }
  ```
- **Expired JWT access token (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Authentication token has expired.",
    "data": null,
    "error_code": "TOKEN_EXPIRED"
  }
  ```
- **Invalid or malformed JWT token (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Invalid authentication token.",
    "data": null,
    "error_code": "INVALID_TOKEN"
  }
  ```
- **Missing `video` field (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "No 'video' file field found in request.",
    "data": null,
    "error_code": "MISSING_FILE"
  }
  ```
- **Empty file or unsafe filename (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Invalid filename: Filename cannot contain path separators.",
    "data": null,
    "error_code": "INVALID_FILE"
  }
  ```
- **Unsupported format or signature mismatch (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "File content does not match expected MP4 container signature for .mp4.",
    "data": null,
    "error_code": "INVALID_FORMAT"
  }
  ```
- **Unreadable / corrupted video stream (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Failed to open or decode video stream.",
    "data": null,
    "error_code": "PROCESSING_ERROR"
  }
  ```
- **Video duration exceeds limit (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Video duration (125.0s) exceeds maximum permitted limit (120s).",
    "data": null,
    "error_code": "PROCESSING_ERROR"
  }
  ```
- **Video resolution exceeds limit (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Video resolution (5000x4000) exceeds maximum permitted limits (max 4096x4096, max 16777216 pixels).",
    "data": null,
    "error_code": "PROCESSING_ERROR"
  }
  ```
- **Decoded frame resolution exceeds limit (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Decoded video frame resolution (4800x4800) exceeds maximum permitted limits (max 4096x4096, max 16777216 pixels).",
    "data": null,
    "error_code": "PROCESSING_ERROR"
  }
  ```
- **Persistence Failure (`500 Internal Server Error`)**:
  ```json
  {
    "success": false,
    "message": "An error occurred while persisting the scan results.",
    "data": null,
    "error_code": "INTERNAL_SERVER_ERROR"
  }
  ```

---

## 5. Audio Synthetic Voice & Lip-Sync Analysis

- **Method**: `POST`
- **Path**: `/api/detect/audio`
- **Authentication**: Required (`Authorization: Bearer <access_token>`) via `@require_auth`
- **Services Called**: `AudioDetectionService.analyze_audio`, `ScanService.create_scan`, `ScanService.save_scan_result`
- **Persistence**: Persists a `Scan` (modality `audio`, `filename` set to uploaded filename, owned by authenticated user) in `PENDING` status, followed by an atomic commit of a `ScanResult` (`COMPLETED` status, timestamp, calculated `prediction` `SYNTHETIC` or `AUTHENTIC`, `confidence`, and `risk_level`). Raw audio bytes are NOT stored in the database.
- **Request Headers**:
  - `Content-Type: multipart/form-data`
  - `Authorization: Bearer <token>`
- **Request Body**:
  - `audio` (binary file): Supported format: `.wav` (Option A: WAV-only policy for active `scipy.io.wavfile` decoder).

### Validation Rules
1. Request must contain a valid Bearer JWT in the `Authorization` header.
2. Request must be `multipart/form-data` with form field name `audio`.
3. File must be present and filename non-empty.
4. Filename must be safe: length <= 255, no path traversal separators (`/`, `\`), no drive letters or ADS colons (`:`), no control characters or null bytes, no directory navigation (`.` or `..`), no leading/trailing whitespace. Legitimate double dots (e.g. `recording..v1.wav`), spaces, and international Unicode are accepted. (Violations return 400 `INVALID_FILE`).
5. Extension must be in `{"wav"}`. (Violations return 400 `INVALID_FORMAT`).
6. Magic-byte signature must match WAV container: `RIFF....WAVE` or `RIFX....WAVE`. Bounded 32-byte header inspection with deterministic stream rewind. (Violations return 400 `INVALID_FORMAT`).
7. Decoded audio buffer must contain at least 1 readable sample (`data.size > 0`) and sample rate must be positive (`sample_rate > 0`). (Violations return 400 `PROCESSING_ERROR`).
8. Max payload size: 50 MB.

### Success Response (`200 OK`)
```json
{
  "success": true,
  "message": "Audio analyzed successfully.",
  "data": {
    "is_synthetic_audio": false,
    "confidence_score": 0.354,
    "metrics": {
      "duration_seconds": 3.0,
      "sample_rate_hz": 16000,
      "zero_crossing_rate": 0.0421,
      "energy_variance": 0.0128
    },
    "lip_sync_discrepancies": [
      {
        "start_timestamp": "00:01.200",
        "end_timestamp": "00:02.450",
        "measured_offset_ms": 320,
        "severity": "HIGH",
        "description": "Phoneme plosive burst desynchronized with visual viseme mouth closure."
      }
    ]
  },
  "error_code": null
}
```

### Error Responses
- **Missing or non-Bearer `Authorization` header (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Authentication required.",
    "data": null,
    "error_code": "AUTHENTICATION_REQUIRED"
  }
  ```
- **Expired JWT access token (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Authentication token has expired.",
    "data": null,
    "error_code": "TOKEN_EXPIRED"
  }
  ```
- **Invalid or malformed JWT token (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Invalid authentication token.",
    "data": null,
    "error_code": "INVALID_TOKEN"
  }
  ```
- **Missing `audio` field (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "No 'audio' file field found in request.",
    "data": null,
    "error_code": "MISSING_FILE"
  }
  ```
- **Empty file or unsafe filename (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Invalid filename: Filename cannot contain path separators.",
    "data": null,
    "error_code": "INVALID_FILE"
  }
  ```
- **Unsupported format or signature mismatch (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "File content does not match expected WAV container signature for .wav.",
    "data": null,
    "error_code": "INVALID_FORMAT"
  }
  ```
- **Unreadable / corrupted / empty audio stream (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Failed to decode audio file. File might be corrupted or in an unsupported format.",
    "data": null,
    "error_code": "PROCESSING_ERROR"
  }
  ```
- **Zero readable audio samples (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Uploaded audio contains zero readable audio samples.",
    "data": null,
    "error_code": "PROCESSING_ERROR"
  }
  ```
- **Persistence Failure (`500 Internal Server Error`)**:
  ```json
  {
    "success": false,
    "message": "An error occurred while persisting the scan results.",
    "data": null,
    "error_code": "INTERNAL_SERVER_ERROR"
  }
  ```

---

## 6. Abuse Report & Evidence Dossier Dispatcher

- **Method**: `POST`
- **Path**: `/api/report/abuse`
- **Authentication**: None (Public in Phase 1)
- **Service Called**: `AbuseDispatcherService.generate_dossier`
- **Request Headers**: `Content-Type: application/json`
- **Request Body**:
```json
{
  "platform": "youtube",
  "target_url": "https://youtube.com/watch?v=sample123",
  "category": "Synthetic Impersonation",
  "confidence_score": 0.982,
  "analyst_notes": "Deepfake face-swap detected on frame 142."
}
```

### Validation Rules
1. Body must be a valid JSON object.
2. `platform` is required and must be one of: `["youtube", "x", "meta", "custom"]` (case-insensitive).
3. `target_url` is required and must not be empty.
4. `confidence_score` defaults to 0.95 if omitted.
5. `category` defaults to `"Synthetic Impersonation & Manipulated Media"` if omitted.

### Success Response (`201 Created`)
```json
{
  "success": true,
  "message": "Abuse dossier successfully generated and dispatched.",
  "data": {
    "report_id": "VM-REP-B28C3807",
    "status": "DISPATCHED",
    "dispatch_timestamp": "2026-09-04T00:05:05Z",
    "platform_destination": {
      "platform": "Youtube",
      "channel": "Google Trust & Safety Abuse API",
      "target_url": "https://youtube.com/watch?v=sample123"
    },
    "forensic_evidence": {
      "category": "Synthetic Impersonation",
      "confidence_score": 0.982,
      "sha256_fingerprint": "7d9b936d90a786c2e2764bfa1e94474943018240ef48ff114dca2e6c464efc52",
      "analyst_notes": "Deepfake face-swap detected on frame 142.",
      "standards_compliance": ["C2PA-Authenticity", "NIST-AI-100-2"]
    },
    "dispatch_receipt": {
      "acknowledgment_code": "ACK-A17DF5",
      "estimated_review_hours": 24
    }
  },
  "error_code": null
}
```

### Error Responses
- **Unsupported platform e.g. tiktok (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Unsupported platform 'tiktok'. Allowed: custom, meta, x, youtube",
    "data": null,
    "error_code": "VALIDATION_ERROR"
  }
  ```
- **Missing `target_url` (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Target URL or content link is required.",
    "data": null,
    "error_code": "VALIDATION_ERROR"
  }
  ```
- **Invalid JSON payload (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Request body must be valid JSON.",
    "data": null,
    "error_code": "INVALID_JSON"
  }
  ```

---

## 7. User Registration

- **Method**: `POST`
- **Path**: `/api/auth/register`
- **Authentication**: None (Public)
- **Service Called**: `AuthService.register_user`
- **Request Headers**: `Content-Type: application/json`
- **Request Body**:
```json
{
  "name": "Alice Smith",
  "email": "alice@example.com",
  "password": "StrongPassword123"
}
```

### Validation Rules
1. Request body must be a valid JSON object.
2. `name`: Required, non-empty string.
3. `email`: Required, valid email format (e.g. `user@domain.com`). Automatically normalized to lowercase and trimmed of leading/trailing whitespace.
4. `password`:
   - Length: Minimum 12 characters, maximum 128 characters.
   - Composition: No mandatory uppercase, lowercase, digits, or special characters. Passphrases, spaces, and Unicode characters are fully allowed and preserved.
   - Design rationale: Prioritizes password length and weak-password blocking rather than arbitrary character-composition rules (aligning with NIST SP 800-63B guidelines).
   - Weak password protection: Obvious/common weak passwords (e.g. `password`, `123456789012`, `admin123`) are rejected via an internal blocklist (evaluated case-insensitively and ignoring surrounding whitespace).
   - *Note on Breached Passwords*: The service currently relies on an internal local weak-password blocklist; it does **not** query external breached-password databases (e.g., HaveIBeenPwned). Full breached-password detection may be integrated in future security phases.
5. Unique email: Registration is rejected if an account with the normalized email already exists.
6. Security: Plaintext password is never stored or logged. Encrypted with Werkzeug `scrypt` hash (surrounding and internal whitespace preserved). Response never exposes `password_hash`.

### Success Response (`201 Created`)
```json
{
  "success": true,
  "message": "User registered successfully.",
  "data": {
    "id": 1,
    "name": "Alice Smith",
    "email": "alice@example.com"
  },
  "error_code": null
}
```

### Error Responses
- **Missing or empty required field (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Field 'name' is required.",
    "data": null,
    "error_code": "MISSING_FIELD"
  }
  ```
- **Invalid email format (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Invalid email address format.",
    "data": null,
    "error_code": "INVALID_EMAIL"
  }
  ```
- **Password too short (< 12 characters) (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Password must be at least 12 characters long.",
    "data": null,
    "error_code": "PASSWORD_TOO_SHORT"
  }
  ```
- **Password too long (> 128 characters) (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Password must not exceed 128 characters.",
    "data": null,
    "error_code": "PASSWORD_TOO_LONG"
  }
  ```
- **Weak / Common password rejected (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "The password provided is too common or easily guessable.",
    "data": null,
    "error_code": "WEAK_PASSWORD"
  }
  ```
- **Duplicate email address (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "An account with this email already exists.",
    "data": null,
    "error_code": "EMAIL_ALREADY_REGISTERED"
  }
  ```
- **Malformed / Non-JSON payload (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Request body must be valid JSON.",
    "data": null,
    "error_code": "INVALID_JSON"
  }
  ```

---

## 8. User Login & JWT Authentication

- **Method**: `POST`
- **Path**: `/api/auth/login`
- **Authentication**: None (Public)
- **Service Called**: `AuthService.login_user`
- **Request Headers**: `Content-Type: application/json`
- **Request Body**:
```json
{
  "email": "alice@example.com",
  "password": "StrongPassword123"
}
```

### Validation & Authentication Rules
1. Request body must be a valid JSON object.
2. `email`: Required, non-empty string. Automatically normalized via `.strip().lower()`.
3. `password`: Required, non-empty string.
4. Credential verification: Cryptographically checked against the stored hash using Werkzeug `check_password_hash()`. Requires user account `is_active == True`.
5. Anti-enumeration security: If the user does not exist, the password is wrong, or the account is inactive, the endpoint returns an identical HTTP 401 generic error (`INVALID_CREDENTIALS`), preventing email harvesting.
6. JWT token generation: Returns a signed HS256 JWT access token with minimal claims (`sub`, `iat`, `exp`). The token contains no sensitive credentials or hashes.

### Success Response (`200 OK`)
```json
{
  "success": true,
  "message": "Login successful.",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 86400
  },
  "error_code": null
}
```

### Error Responses
- **Missing or non-string required field (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Field 'email' is required.",
    "data": null,
    "error_code": "MISSING_FIELD"
  }
  ```
- **Malformed / Non-JSON payload (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Request body must be valid JSON.",
    "data": null,
    "error_code": "INVALID_JSON"
  }
  ```
- **Invalid credentials / Account inactive (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Invalid email or password.",
    "data": null,
    "error_code": "INVALID_CREDENTIALS"
  }
  ```

---

## 9. Authenticated User Identity Verification

- **Method**: `GET`
- **Path**: `/api/auth/me`
- **Authentication**: Required (`Authorization: Bearer <JWT>`)
- **Service Called**: Controller decorated with `@require_auth`
- **Request Headers**:
  - `Authorization`: `Bearer <access_token>`
- **Request Body**: None

### Authorization Rules
1. Client must send HTTP `Authorization` header in format `Bearer <access_token>`.
2. Missing, empty, or non-Bearer headers return HTTP 401 with `AUTHENTICATION_REQUIRED`.
3. Expired tokens return HTTP 401 with `TOKEN_EXPIRED`.
4. Tampered, bad signature, malformed, or tokens missing required standard claims (`sub`, `iat`, `exp`) return HTTP 401 with `INVALID_TOKEN`.
5. Authenticated user ID is extracted from `sub` and bound to `g.current_user_id`.
6. Does not query database per request; operates statelessly.
7. Does not expose `password_hash`, `password`, or sensitive system secrets.

### Success Response (`200 OK`)
```json
{
  "success": true,
  "message": "Authenticated user.",
  "data": {
    "user_id": 1
  },
  "error_code": null
}
```

### Error Responses
- **Missing or malformed Authorization header (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Authentication required.",
    "data": null,
    "error_code": "AUTHENTICATION_REQUIRED"
  }
  ```
- **Expired token (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Authentication token has expired.",
    "data": null,
    "error_code": "TOKEN_EXPIRED"
  }
  ```
- **Invalid token / Tampered signature / Missing claims (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Invalid authentication token.",
    "data": null,
    "error_code": "INVALID_TOKEN"
  }
  ```

---

## 10. User Scan History Listing

- **Method**: `GET`
- **Path**: `/api/scans`
- **Authentication**: Required (`Authorization: Bearer <access_token>`) via `@require_auth`
- **Service Called**: `ScanService.get_user_scans`
- **Ownership**: Strictly scoped to `g.current_user_id`. Users can only retrieve their own scans.
- **Request Headers**:
  - `Authorization`: `Bearer <token>`
- **Query Parameters**:
  - `page` (integer, optional, default `1`): Page number, must be >= 1.
  - `per_page` (integer, optional, default `10`): Items per page, must be >= 1 and <= 100.
  - `media_type` (string, optional): Filter by modality: `text`, `image`, `video`, or `audio` (case-insensitive).
- **Request Body**: None

### Validation Rules
1. Must contain valid Bearer JWT in `Authorization` header.
2. `page` must be an integer >= 1. Non-integer or < 1 returns HTTP 400 with `INVALID_PAGE`.
3. `per_page` must be an integer between 1 and 100. Values < 1 or > 100 return HTTP 400 with `INVALID_PER_PAGE`.
4. `media_type`, if supplied, must be one of `{"text", "image", "video", "audio"}`. Other values return HTTP 400 with `INVALID_MEDIA_TYPE`.

### Payload Discipline
- Returns lightweight scan summary items.
- Eagerly loads `ScanResult` summary fields: `id`, `prediction`, `confidence`, `risk_level`.
- **`result_data` is strictly excluded** from the list response to prevent bandwidth inflation from Base64 heatmaps.
- `Scan.user`, `password_hash`, and raw media are never serialized.

### Success Response (`200 OK`)
```json
{
  "success": true,
  "message": "Scans retrieved successfully.",
  "data": {
    "items": [
      {
        "id": 14,
        "media_type": "video",
        "filename": "interview_clip.mp4",
        "status": "COMPLETED",
        "created_at": "2026-09-08T16:30:15Z",
        "completed_at": "2026-09-08T16:30:18Z",
        "result": {
          "id": 12,
          "prediction": "DEEPFAKE",
          "confidence": 0.842,
          "risk_level": "HIGH"
        }
      }
    ],
    "pagination": {
      "page": 1,
      "per_page": 10,
      "total_items": 1,
      "total_pages": 1,
      "has_next": false,
      "has_prev": false
    }
  },
  "error_code": null
}
```

### Empty List Response (`200 OK`)
```json
{
  "success": true,
  "message": "Scans retrieved successfully.",
  "data": {
    "items": [],
    "pagination": {
      "page": 1,
      "per_page": 10,
      "total_items": 0,
      "total_pages": 0,
      "has_next": false,
      "has_prev": false
    }
  },
  "error_code": null
}
```

### Error Responses
- **Missing or non-Bearer `Authorization` header (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Authentication required.",
    "data": null,
    "error_code": "AUTHENTICATION_REQUIRED"
  }
  ```
- **Expired JWT access token (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Authentication token has expired.",
    "data": null,
    "error_code": "TOKEN_EXPIRED"
  }
  ```
- **Invalid or malformed JWT token (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Invalid authentication token.",
    "data": null,
    "error_code": "INVALID_TOKEN"
  }
  ```
- **Invalid page parameter (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Query parameter 'page' must be an integer greater than or equal to 1.",
    "data": null,
    "error_code": "INVALID_PAGE"
  }
  ```
- **Invalid per_page parameter (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Query parameter 'per_page' must be an integer between 1 and 100.",
    "data": null,
    "error_code": "INVALID_PER_PAGE"
  }
  ```
- **Invalid media_type parameter (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Invalid media_type 'hologram'. Allowed values are: audio, image, text, video.",
    "data": null,
    "error_code": "INVALID_MEDIA_TYPE"
  }
  ```
- **Internal Database Error (`500 Internal Server Error`)**:
  ```json
  {
    "success": false,
    "message": "An error occurred while retrieving scans.",
    "data": null,
    "error_code": "INTERNAL_SERVER_ERROR"
  }
  ```

---

## 11. Individual Scan Forensic Detail

- **Method**: `GET`
- **Path**: `/api/scans/<int:scan_id>`
- **Authentication**: Required (`Authorization: Bearer <access_token>`) via `@require_auth`
- **Service Called**: `ScanService.get_user_scan_by_id`
- **Ownership & IDOR Protection**: Scoped to both `Scan.id == scan_id` AND `Scan.user_id == g.current_user_id`.
- **Anti-Enumeration Invariant**: If `scan_id` does not exist OR belongs to another user, returns HTTP 404 (`SCAN_NOT_FOUND`). It never returns 403.
- **Request Headers**:
  - `Authorization`: `Bearer <token>`
- **Request Body**: None

### Success Response (`200 OK`)
```json
{
  "success": true,
  "message": "Scan details retrieved successfully.",
  "data": {
    "id": 14,
    "user_id": 1,
    "media_type": "image",
    "filename": "suspect_profile.jpg",
    "status": "COMPLETED",
    "created_at": "2026-09-08T16:30:15Z",
    "completed_at": "2026-09-08T16:30:18Z",
    "result": {
      "id": 12,
      "scan_id": 14,
      "prediction": "DEEPFAKE",
      "confidence": 0.842,
      "risk_level": "HIGH",
      "created_at": "2026-09-08T16:30:18Z",
      "result_data": {
        "is_deepfake": true,
        "confidence_score": 0.842,
        "manipulation_type": "Face-Swap / Boundary Anomaly",
        "image_dimensions": { "width": 640, "height": 480 },
        "heatmap_preview": "data:image/jpeg;base64,..."
      }
    }
  },
  "error_code": null
}
```

### Error Responses
- **Scan Not Found or Belongs to Another User (`404 Not Found`)**:
  ```json
  {
    "success": false,
    "message": "Scan not found.",
    "data": null,
    "error_code": "SCAN_NOT_FOUND"
  }
  ```
- **Missing or non-Bearer `Authorization` header (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Authentication required.",
    "data": null,
    "error_code": "AUTHENTICATION_REQUIRED"
  }
  ```
- **Expired JWT access token (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Authentication token has expired.",
    "data": null,
    "error_code": "TOKEN_EXPIRED"
  }
  ```
- **Invalid or malformed JWT token (`401 Unauthorized`)**:
  ```json
  {
    "success": false,
    "message": "Invalid authentication token.",
    "data": null,
    "error_code": "INVALID_TOKEN"
  }
  ```
- **Internal Database Error (`500 Internal Server Error`)**:
  ```json
  {
    "success": false,
    "message": "An error occurred while retrieving scan details.",
    "data": null,
    "error_code": "INTERNAL_SERVER_ERROR"
  }
  ```

---

## 12. Global Framework Errors

| HTTP Status | Error Code | Example Trigger | Message |
| :--- | :--- | :--- | :--- |
| `400 Bad Request` | `BAD_REQUEST` | Malformed multipart/form-data | `"Bad request or malformed payload."` |
| `401 Unauthorized` | `AUTHENTICATION_REQUIRED` / `INVALID_TOKEN` / `TOKEN_EXPIRED` | Protected route missing or invalid token | `"Authentication required."` / `"Invalid authentication token."` |
| `404 Not Found` | `NOT_FOUND` | `GET /api/unknown-endpoint` | `"The requested resource was not found on this server."` |
| `405 Method Not Allowed` | `METHOD_NOT_ALLOWED` | `GET /api/detect/text` | `"The HTTP method is not allowed for this endpoint."` |
| `413 Payload Too Large` | `PAYLOAD_TOO_LARGE` | File upload > 50 MB | `"Request payload exceeds maximum permitted file size."` |
| `500 Internal Server Error` | `INTERNAL_SERVER_ERROR` | Unhandled server exception | `"An unexpected internal server error occurred."` |



