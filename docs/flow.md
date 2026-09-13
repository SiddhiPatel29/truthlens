# End-to-End Execution Flow Specification

This document traces the exact execution paths through the VeraMedia AI backend for each supported operation, utilizing actual filenames and function names.

---

## 1. System Health Check (`GET /api/health`)

```
Client HTTP Request: GET /api/health
  │
  ▼
[backend/app.py: create_app]
  Flask WSGI dispatcher matches route prefix '/api' to health_bp
  │
  ▼
[backend/routes/health_routes.py: health_check()]
  Route: @health_bp.route("/health", methods=["GET"])
  Decorator: @limiter.exempt (Explicitly exempt from rate limiting for monitoring/load-balancers)
  Constructs static status dictionary:
    {
      "service": "VeraMedia AI Backend",
      "status": "OPERATIONAL",
      "version": "1.0.0",
      "supported_modalities": ["video", "audio", "image", "text"]
    }
  │
  ▼
[backend/utils/response.py: api_response()]
  Wraps payload into envelope:
    { "success": True, "message": "...", "data": {...}, "error_code": None }
  Calls flask.jsonify(payload), returns with HTTP status code 200
  │
  ▼
Client receives HTTP 200 JSON Response
```

---

## 2. Text Detection Flow (`POST /api/detect/text`)

```
Client HTTP Request: POST /api/detect/text
Headers:
  Content-Type: application/json
  Authorization: Bearer <access_token>
Body: { "text": "Artificial intelligence synthesis has progressed rapidly..." }
  │
  ▼
[backend/app.py: create_app]
  Flask WSGI router matches prefix '/api' and routes to text_bp
  │
  ▼
[backend/utils/auth.py: @require_auth]
  1. Inspects request.headers.get("Authorization")
     - Missing or non-Bearer: returns 401 AUTHENTICATION_REQUIRED
  2. Extracts token and calls AuthService.verify_token(token)
     - Expired: returns 401 TOKEN_EXPIRED
     - Invalid signature/claims: returns 401 INVALID_TOKEN
  3. Validates positive integer sub claim: user_id = int(payload["sub"])
  4. Database User & Active Verification:
     - Queries User via db.session.get(User, user_id, populate_existing=True)
     - If user is None or not user.is_active: returns 401 INVALID_TOKEN ("Invalid authentication token.")
  5. Context Binding: binds g.current_user_id = user_id and g.current_user = user
  │
  ▼
[backend/utils/limiter.py: @limiter.limit (Authenticated User Keyed Rate Limiting)]
  1. Key resolution: get_user_rate_limit_key() -> f"user:{g.current_user_id}"
  2. Quota evaluation: checks quota against RATELIMIT_DETECT_TEXT (default: 30/min, 200/hr)
  3. If quota exceeded:
     - Raises RateLimitExceeded (HTTP 429)
     - Centralized error handler in backend/utils/errors.py catches 429
     - Flask-Limiter injects Retry-After, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset headers (when RATELIMIT_HEADERS_ENABLED=True / headers_enabled=True)
     - Returns 429 {"success": false, "message": "Rate limit exceeded. Please try again later.", "data": null, "error_code": "RATE_LIMIT_EXCEEDED"}
     - Guarantees ZERO text analysis, ZERO Scan records, and ZERO ScanResult records created
  4. If within quota: decrements user quota and proceeds to route handler
  │
  ▼
[backend/routes/text_routes.py: detect_text()]
  1. Calls request.get_json(silent=True)
     - If body is None or not dict or 'text' not in body:
       Calls api_response(False, "Request body must contain a 'text' field.", None, "INVALID_INPUT", 400)
  2. Type validation: verifies isinstance(input_text, str)
  3. Minimum length validation: verifies len(input_text.strip()) >= 20
     - If < 20 chars:
       Calls api_response(False, "Text is too short...", None, "TEXT_TOO_SHORT", 400)
  4. Maximum length validation: verifies len(input_text.strip()) <= MAX_TEXT_LENGTH (25,000)
     - If > 25,000 chars:
       Calls api_response(False, "Text exceeds maximum permitted length of 25000 characters.", None, "TEXT_TOO_LONG", 400) (zero DB persistence)
  │
  ▼
[backend/services/text_service.py: TextDetectionService.analyze_text(input_text)]
  1. Cleans text, verifies len(cleaned_text) <= MAX_TEXT_LENGTH (25,000), splits into sentence list using regex: r'(?<=[.!?]) +'
  2. Calculates sentence length variance and burstiness_score over complete accepted text
  3. Calculates vocabulary repetition and type_token_ratio over complete accepted text
  4. Computes aggregate ai_probability: round((burstiness * 0.6) + ((1 - ttr) * 0.4), 3)
  5. Computes sentence_breakdown with per-sentence suspicious flag, capped at MAX_SENTENCE_BREAKDOWN_ITEMS (100) entries to prevent DB payload bloat
  6. Returns dictionary { is_ai_generated, ai_confidence_score, metrics: { total_sentences, total_words, burstiness_index, lexical_diversity }, sentence_breakdown }
  │
  ▼
[backend/routes/text_routes.py: detect_text()]
  Catches ValueError -> returns api_response(False, str(e), None, "PROCESSING_ERROR", 400)
  Catches Exception  -> logs via logger.exception(), returns api_response(False, "...", None, "INTERNAL_SERVER_ERROR", 500)
  │
  ▼
[backend/services/scan_service.py: ScanService.create_scan()]
  1. Validates user_id=g.current_user_id, media_type="text", filename=None
  2. Inserts Scan record with status="PENDING" and created_at=utc_now()
  3. Commits transaction and returns scan instance
  │
  ▼
[backend/services/scan_service.py: ScanService.save_scan_result()]
  1. Maps detector output:
     - prediction = "AI_GENERATED" if is_ai_generated else "AUTHENTIC"
     - confidence = ai_confidence_score
     - risk_level = "HIGH" if confidence >= 0.7 else ("MEDIUM" if confidence >= 0.4 else "LOW")
     - result_data = result dictionary
  2. Inserts ScanResult record linked to scan.id
  3. Atomically updates parent scan status="COMPLETED", completed_at=utc_now()
  4. Commits atomic transaction
  (If persistence fails: route catches ScanServiceError, logs exception, returns 500 INTERNAL_SERVER_ERROR)
  │
  ▼
[backend/utils/response.py: api_response()]
  Returns jsonify({ "success": True, "message": "Text analyzed successfully.", "data": result, "error_code": None }), 200
  │
  ▼
Client receives HTTP 200 JSON Response
```

---

## 3. Image Detection Flow (`POST /api/detect/image`)

```
Client HTTP Request: POST /api/detect/image
Headers:
  Content-Type: multipart/form-data
  Authorization: Bearer <access_token>
Body: file field 'image' containing image binary (e.g. test.jpg)
  │
  ▼
[backend/app.py: create_app]
  Flask WSGI router matches prefix '/api' and routes to image_bp
  │
  ▼
[backend/utils/auth.py: @require_auth]
  1. Inspects request.headers.get("Authorization")
     - Missing or non-Bearer: returns 401 AUTHENTICATION_REQUIRED
  2. Extracts token and calls AuthService.verify_token(token)
     - Expired: returns 401 TOKEN_EXPIRED
     - Invalid signature/claims: returns 401 INVALID_TOKEN
  3. Validates positive integer sub claim: user_id = int(payload["sub"])
  4. Database User & Active Verification:
     - Queries User via db.session.get(User, user_id, populate_existing=True)
     - If user is None or not user.is_active: returns 401 INVALID_TOKEN ("Invalid authentication token.")
  5. Context Binding: binds g.current_user_id = user_id and g.current_user = user
  │
  ▼
[backend/utils/limiter.py: @limiter.limit (Authenticated User Keyed Rate Limiting)]
  1. Key resolution: get_user_rate_limit_key() -> f"user:{g.current_user_id}"
  2. Quota evaluation: checks quota against RATELIMIT_DETECT_IMAGE (default: 15/min, 100/hr)
  3. If quota exceeded:
     - Raises RateLimitExceeded (HTTP 429) -> returns 429 RATE_LIMIT_EXCEEDED with Retry-After header
     - Guarantees ZERO image reading, ZERO OpenCV analysis, and ZERO Scan/ScanResult records created
  4. If within quota: decrements user quota and proceeds to route handler
  │
  ▼
[backend/routes/image_routes.py: detect_image()]
  1. Checks if "image" in request.files
     - If missing: calls api_response(False, "...", None, "MISSING_FILE", 400)
  2. Extracts file = request.files["image"]
  3. Validates file via [backend/utils/file_validator.py: validate_image_file(file)]
     - File presence and non-empty filename check (returns 400 INVALID_FILE)
     - Filename safety check: is_safe_filename(file.filename) verifies length <= 255, no control/null chars, no path separators (/ or \), no colons/drive letters, no dot directory navigation, no dot prefixes/suffixes (returns 400 INVALID_FILE)
     - Extension check: verifies extension in ALLOWED_IMAGE_EXTENSIONS ("png", "jpg", "jpeg", "webp") (returns 400 INVALID_FORMAT)
     - Bounded magic-byte check: read_file_prefix reads 32 bytes and deterministically rewinds stream; validate_image_signature validates JPEG (\xff\xd8\xff), PNG (\x89PNG\r\n\x1a\n), or WebP (RIFF....WEBP) (returns 400 INVALID_FORMAT)
     - If invalid: calls api_response(False, err_msg, None, err_code, 400)
  4. Reads raw bytes: file_bytes = file.read()
  │
  ▼
[backend/services/image_service.py: ImageDetectionService.analyze_image(file_bytes)]
  1. Decodes raw bytes to OpenCV BGR matrix: np.frombuffer + cv2.imdecode
     - If img is None: raises ValueError("Failed to decode image...")
  2. Enforces Dimension & Pixel Limits:
     - Checks w <= 0 or h <= 0 or w > MAX_IMAGE_WIDTH (4096) or h > MAX_IMAGE_HEIGHT (4096) or (w * h) > MAX_IMAGE_PIXELS (16,777,216)
     - If exceeded: raises ValueError("Image dimensions ... exceed maximum permitted limits...")
     - Fails fast before allocating full-resolution float32 masks or running 2D convolutions
  3. Converts to grayscale: cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
  4. Computes Laplacian edge/texture variance: cv2.Laplacian(gray, cv2.CV_64F).var()
  5. Constructs Gaussian activation mask: cv2.circle + cv2.GaussianBlur
  6. Renders color heatmap: cv2.applyColorMap(..., cv2.COLORMAP_JET)
  7. Blends heatmap overlay: cv2.addWeighted(img, 0.6, heatmap_color, 0.4, 0)
  8. Calculates confidence_score and is_deepfake boolean flag
  9. Downscales Heatmap Overlay to Thumbnail Preview:
     - If max(h, w) > MAX_PREVIEW_DIMENSION (512): resizes overlay using cv2.INTER_AREA decimation
     - If max(h, w) <= 512: preserves original overlay size without upscaling
  10. Encodes thumbnail overlay to JPEG: cv2.imencode(".jpg", preview_overlay)
  11. Base64 encodes preview: base64.b64encode(...) -> "data:image/jpeg;base64,..."
  12. Returns analysis dict { is_deepfake, confidence_score, manipulation_type, image_dimensions: {width: w, height: h}, heatmap_preview }
  │
  ▼
[backend/routes/image_routes.py: detect_image()]
  Catches ValueError -> logs warning, returns api_response(False, str(e), None, "PROCESSING_ERROR", 400)
  Catches Exception  -> logs traceback via logger.exception(), returns sanitized 500 error
  │
  ▼
[backend/services/scan_service.py: ScanService.create_scan()]
  1. Validates user_id=g.current_user_id, media_type="image", filename=file.filename
  2. Inserts Scan record with status="PENDING" and created_at=utc_now()
  3. Commits transaction and returns scan instance
  │
  ▼
[backend/services/scan_service.py: ScanService.save_scan_result()]
  1. Maps detector output:
     - prediction = "DEEPFAKE" if is_deepfake else "AUTHENTIC"
     - confidence = confidence_score
     - risk_level = "HIGH" if confidence >= 0.7 else ("MEDIUM" if confidence >= 0.4 else "LOW")
     - result_data = result dictionary (metadata + preview data URL; no raw image bytes)
  2. Inserts ScanResult record linked to scan.id
  3. Atomically updates parent scan status="COMPLETED", completed_at=utc_now()
  4. Commits atomic transaction
  (If persistence fails: route catches ScanServiceError, logs exception, returns 500 INTERNAL_SERVER_ERROR)
  │
  ▼
[backend/utils/response.py: api_response()]
  Returns jsonify({ "success": True, "message": "Image analyzed successfully.", "data": result, "error_code": None }), 200
  │
  ▼
Client receives HTTP 200 JSON Response
```

---

## 4. Video Detection Flow (`POST /api/detect/video`)

```
Client HTTP Request: POST /api/detect/video
Headers:
  Content-Type: multipart/form-data
  Authorization: Bearer <access_token>
Body: file field 'video' containing video binary (e.g. test.mp4)
  │
  ▼
[backend/app.py: create_app]
  Flask WSGI router matches prefix '/api' and routes to video_bp
  │
  ▼
[backend/utils/auth.py: @require_auth]
  1. Inspects request.headers.get("Authorization")
     - Missing or non-Bearer: returns 401 AUTHENTICATION_REQUIRED
  2. Extracts token and calls AuthService.verify_token(token)
     - Expired: returns 401 TOKEN_EXPIRED
     - Invalid signature/claims: returns 401 INVALID_TOKEN
  3. Validates positive integer sub claim: user_id = int(payload["sub"])
  4. Database User & Active Verification:
     - Queries User via db.session.get(User, user_id, populate_existing=True)
     - If user is None or not user.is_active: returns 401 INVALID_TOKEN ("Invalid authentication token.")
  5. Context Binding: binds g.current_user_id = user_id and g.current_user = user
  │
  ▼
[backend/utils/limiter.py: @limiter.limit (Authenticated User Keyed Rate Limiting)]
  1. Key resolution: get_user_rate_limit_key() -> f"user:{g.current_user_id}"
  2. Quota evaluation: checks quota against RATELIMIT_DETECT_VIDEO (default: 5/min, 30/hr)
  3. If quota exceeded:
     - Raises RateLimitExceeded (HTTP 429) -> returns 429 RATE_LIMIT_EXCEEDED with Retry-After header
     - Guarantees ZERO video file saving, ZERO OpenCV frame decoding, and ZERO Scan/ScanResult records created
  4. If within quota: decrements user quota and proceeds to route handler
  │
  ▼
[backend/routes/video_routes.py: detect_video()]
  1. Checks "video" in request.files
     - If missing: returns api_response(False, "...", None, "MISSING_FILE", 400)
  2. Validates file via [backend/utils/file_validator.py: validate_video_file(file)]
     - File presence and non-empty filename check (returns 400 INVALID_FILE)
     - Filename safety check: is_safe_filename(file.filename) verifies length <= 255, no control/null chars, no path separators (/ or \), no colons/drive letters, no dot directory navigation, no dot prefixes/suffixes (returns 400 INVALID_FILE)
     - Extension check: verifies extension in ALLOWED_VIDEO_EXTENSIONS ("mp4", "mov", "avi", "mkv") (returns 400 INVALID_FORMAT)
     - Bounded magic-byte check: read_file_prefix reads 32 bytes and rewinds stream; validate_video_signature validates MP4 (ftyp at 4..8), MOV (conservative ftyp at 4..8), AVI (RIFF....AVI / AVIX), or MKV (1A 45 DF A3) (returns 400 INVALID_FORMAT)
     - If invalid: returns api_response(False, err_msg, None, err_code, 400)
  │
  ▼
[backend/services/video_service.py: VideoDetectionService.analyze_video(file)]
  1. Derives dynamic extension suffix (.mp4, .mov, .avi, .mkv) from validated upload
  2. Creates temporary file on disk: tempfile.mkstemp(suffix=f".{ext}")
  3. Streams file.save(temp_path)
  4. Opens cv2.VideoCapture(temp_path)
  5. Validates video duration against policy (MAX_VIDEO_DURATION_SECONDS = 120):
     - If total_frames / fps > 120: raises ValueError (rejected as 400 PROCESSING_ERROR)
  6. Validates container resolution metadata (MAX_VIDEO_WIDTH=4096, MAX_VIDEO_HEIGHT=4096, MAX_PIXELS=16_777_216):
     - If meta_w, meta_h exceed limits: raises ValueError (rejected as 400 PROCESSING_ERROR)
  7. Uniformly samples up to 16 keyframes across duration: np.linspace(...)
  8. For each sampled frame:
     - Validates actual decoded frame.shape[:2] against width/height/pixel bounds
     - Computes Laplacian variance and anomaly score per frame
  9. Tracks peak anomaly frame (suspicious_frame)
  10. Calculates overall sequence confidence mean and temporal instability standard deviation
  11. Renders Grad-CAM++ heatmap overlay on peak suspicious frame; downscales overlay to thumbnail representation (MAX_PREVIEW_DIMENSION = 512) using cv2.INTER_AREA, and encodes to Base64 data URL
  12. finally block guarantees deterministic cleanup order:
     - cap.release() executes strictly BEFORE os.remove(temp_path)
     - On Windows, this prevents PermissionError [WinError 32] file handle lock leaks
  13. Returns analysis dictionary
  │
  ▼
[backend/routes/video_routes.py: detect_video()]
  Catches ValueError -> returns api_response(False, str(e), None, "PROCESSING_ERROR", 400)
  Catches Exception  -> logs traceback via logger.exception(), returns sanitized 500 error
  │
  ▼
[backend/services/scan_service.py: ScanService.create_scan()]
  1. Validates user_id=g.current_user_id, media_type="video", filename=file.filename
  2. Inserts Scan record with status="PENDING" and created_at=utc_now()
  3. Commits transaction and returns scan instance
  │
  ▼
[backend/services/scan_service.py: ScanService.save_scan_result()]
  1. Maps detector output:
     - prediction = "DEEPFAKE" if is_deepfake else "AUTHENTIC"
     - confidence = confidence_score
     - risk_level = "HIGH" if confidence >= 0.7 else ("MEDIUM" if confidence >= 0.4 else "LOW")
     - result_data = deliberately constructed dictionary (metrics + keyframe thumbnail; no raw video bytes)
  2. Inserts ScanResult record linked to scan.id
  3. Atomically updates parent scan status="COMPLETED", completed_at=utc_now()
  4. Commits atomic transaction
  (If persistence fails: route catches ScanServiceError, logs exception, returns 500 INTERNAL_SERVER_ERROR)
  │
  ▼
[backend/utils/response.py: api_response()]
  Returns jsonify({ "success": True, "message": "Video analyzed successfully.", "data": result, "error_code": None }), 200
  │
  ▼
Client receives HTTP 200 JSON Response
```

---

## 5. Audio Detection Flow (`POST /api/detect/audio`)

```
Client HTTP Request: POST /api/detect/audio
Headers:
  Content-Type: multipart/form-data
  Authorization: Bearer <access_token>
Body: file field 'audio' containing audio binary (e.g. test.wav)
  │
  ▼
[backend/app.py: create_app]
  Flask WSGI router matches prefix '/api' and routes to audio_bp
  │
  ▼
[backend/utils/auth.py: @require_auth]
  1. Inspects request.headers.get("Authorization")
     - Missing or non-Bearer: returns 401 AUTHENTICATION_REQUIRED
  2. Extracts token and calls AuthService.verify_token(token)
     - Expired: returns 401 TOKEN_EXPIRED
     - Invalid signature/claims: returns 401 INVALID_TOKEN
  3. Validates positive integer sub claim: user_id = int(payload["sub"])
  4. Database User & Active Verification:
     - Queries User via db.session.get(User, user_id, populate_existing=True)
     - If user is None or not user.is_active: returns 401 INVALID_TOKEN ("Invalid authentication token.")
  5. Context Binding: binds g.current_user_id = user_id and g.current_user = user
  │
  ▼
[backend/utils/limiter.py: @limiter.limit (Authenticated User Keyed Rate Limiting)]
  1. Key resolution: get_user_rate_limit_key() -> f"user:{g.current_user_id}"
  2. Quota evaluation: checks quota against RATELIMIT_DETECT_AUDIO (default: 10/min, 60/hr)
  3. If quota exceeded:
     - Raises RateLimitExceeded (HTTP 429) -> returns 429 RATE_LIMIT_EXCEEDED with Retry-After header
     - Guarantees ZERO audio tempfile saving, ZERO scipy decoding, and ZERO Scan/ScanResult records created
  4. If within quota: decrements user quota and proceeds to route handler
  │
  ▼
[backend/routes/audio_routes.py: detect_audio()]
  1. Checks "audio" in request.files
     - If missing: returns api_response(False, "...", None, "MISSING_FILE", 400)
  2. Validates file via [backend/utils/file_validator.py: validate_audio_file(file)]
     - File presence and non-empty filename check (returns 400 INVALID_FILE)
     - Filename safety check: is_safe_filename(file.filename) verifies length <= 255, no control/null chars, no path separators (/ or \), no colons/drive letters, no dot directory navigation, no dot prefixes/suffixes (returns 400 INVALID_FILE)
     - Extension check: verifies extension in ALLOWED_AUDIO_EXTENSIONS ("wav") (Option A: WAV-only policy for scipy decoder) (returns 400 INVALID_FORMAT)
     - Bounded magic-byte check: read_file_prefix reads 32 bytes and rewinds stream; validate_audio_signature validates WAV (RIFF....WAVE or RIFX....WAVE) (returns 400 INVALID_FORMAT)
     - If invalid: returns api_response(False, err_msg, None, err_code, 400)
  │
  ▼
[backend/services/audio_service.py: AudioDetectionService.analyze_audio(file)]
  1. Saves stream to temporary file: tempfile.mkstemp(suffix=".wav")
  2. Decodes WAV stream: scipy.io.wavfile.read(temp_path)
     - If decoding fails: raises ValueError (propagates clean error; NO synthetic random noise fallback)
  3. Validates decoded buffer:
     - If data.size == 0: raises ValueError ("Uploaded audio contains zero readable audio samples.")
     - If sample_rate <= 0: raises ValueError ("Uploaded audio has an invalid sample rate.")
  4. Converts stereo to mono if multi-channel (data.mean(axis=1))
  5. Computes duration_sec = round(len(data) / float(sample_rate), 2)
     - If duration_sec > MAX_AUDIO_DURATION_SECONDS (120): raises ValueError("Audio duration ... exceeds maximum permitted limit (120s).") (returns 400 PROCESSING_ERROR, 0 scans)
  6. Computes Zero Crossing Rate (ZCR): np.sum(np.diff(data > 0) != 0) / len(data)
  7. Computes spectral energy variance: np.var(data)
  8. Estimates synthetic vocal confidence score
  9. Flags temporal lip-sync discrepancy window intervals
  10. finally block guarantees deterministic cleanup:
     - os.remove(temp_path) executes on success, decoder failure, limit violation, or processing exception
     - Cleanup failures log a warning without crashing the response
  11. Returns analysis dictionary
  │
  ▼
[backend/routes/audio_routes.py: detect_audio()]
  Catches ValueError -> returns api_response(False, str(e), None, "PROCESSING_ERROR", 400) (zero DB persistence)
  Catches Exception  -> logs traceback via logger.exception(), returns sanitized 500 error
  │
  ▼
[backend/services/scan_service.py: ScanService.create_scan()]
  1. Validates user_id=g.current_user_id, media_type="audio", filename=file.filename
  2. Inserts Scan record with status="PENDING" and created_at=utc_now()
  3. Commits transaction and returns scan instance
  │
  ▼
[backend/services/scan_service.py: ScanService.save_scan_result()]
  1. Maps detector output:
     - prediction = "SYNTHETIC" if is_synthetic_audio else "AUTHENTIC"
     - confidence = confidence_score
     - risk_level = "HIGH" if confidence >= 0.7 else ("MEDIUM" if confidence >= 0.4 else "LOW")
     - result_data = deliberately constructed dictionary (metrics + lip_sync_discrepancies; no raw audio bytes)
  2. Inserts ScanResult record linked to scan.id
  3. Atomically updates parent scan status="COMPLETED", completed_at=utc_now()
  4. Commits atomic transaction
  (If persistence fails: route catches ScanServiceError, logs exception, returns 500 INTERNAL_SERVER_ERROR)
  │
  ▼
[backend/utils/response.py: api_response()]
  Returns jsonify({ "success": True, "message": "Audio analyzed successfully.", "data": result, "error_code": None }), 200
  │
  ▼
Client receives HTTP 200 JSON Response
```

---

## 6. Abuse Report Dispatcher Flow (`POST /api/report/abuse`)

```
Client HTTP Request: POST /api/report/abuse
Headers: Content-Type: application/json
Body:
{
  "platform": "youtube",
  "target_url": "https://youtube.com/watch?v=sample123",
  "category": "Synthetic Impersonation",
  "confidence_score": 0.982,
  "analyst_notes": "Deepfake face-swap detected."
}
  │
  ▼
[backend/app.py: create_app]
  Routes to abuse_bp
  │
  ▼
[backend/routes/abuse_routes.py: dispatch_abuse_report()]
  Decorator: @limiter.limit(DEFAULT_LIMIT_REPORT_ABUSE) (Key: client IP request.remote_addr, 10/min, 60/hr)
  - If IP exceeded quota: raises RateLimitExceeded (HTTP 429), returns standard RATE_LIMIT_EXCEEDED response with Retry-After header
  1. Checks request.get_json(silent=True)
     - If not dict: returns api_response(False, "Request body must be valid JSON.", None, "INVALID_JSON", 400)
  │
  ▼
[backend/services/abuse_service.py: AbuseDispatcherService.generate_dossier(body)]
  1. Normalizes platform: payload.get("platform", "").lower().strip()
  2. Validates platform against SUPPORTED_PLATFORMS ("youtube", "x", "meta", "custom")
     - If unsupported (e.g. tiktok): raises ValueError("Unsupported platform 'tiktok'...")
  3. Validates target_url is present and non-empty
     - If missing: raises ValueError("Target URL or content link is required.")
  4. Generates unique report ID: "VM-REP-" + uuid.uuid4().hex[:8].upper()
  5. Computes deterministic SHA-256 fingerprint from canonical JSON manifest:
     json.dumps(raw_manifest, sort_keys=True) -> hashlib.sha256().hexdigest()
  6. Maps destination routing channel:
     - "youtube" -> "Google Trust & Safety Abuse API"
     - "x"       -> "X Security Policy Escalation Relay"
     - "meta"    -> "Meta Oversight & Safety Enforcement"
     - "custom"  -> "Enterprise Webhook Dispatcher"
  7. Formats dossier dictionary with forensic evidence, standards compliance (C2PA, NIST), and receipt acknowledgment code
  │
  ▼
[backend/routes/abuse_routes.py: dispatch_abuse_report()]
  Catches ValueError -> returns api_response(False, str(e), None, "VALIDATION_ERROR", 400)
  Catches Exception  -> logs traceback via logger.exception(), returns sanitized 500 error
  On success:
  │
  ▼
[backend/utils/response.py: api_response()]
  Returns jsonify({ "success": True, "message": "Abuse dossier successfully generated and dispatched.", "data": dossier, "error_code": None }), 201
  │
  ▼
Client receives HTTP 201 Created JSON Response
---

## 7. User Registration Flow (`POST /api/auth/register`)

```
Client HTTP Request: POST /api/auth/register
Headers: Content-Type: application/json
Body:
{
  "name": "Alice Smith",
  "email": "Alice.Smith@example.com",
  "password": "StrongPassword123"
}
  │
  ▼
[backend/app.py: create_app]
  Routes to auth_bp
  │
  ▼
[backend/routes/auth_routes.py: register()]
  Decorator: @limiter.limit(DEFAULT_LIMIT_AUTH_REGISTER) (Key: client IP request.remote_addr, 3/min, 10/hr)
  - If IP exceeded quota: raises RateLimitExceeded (HTTP 429), returns standard RATE_LIMIT_EXCEEDED response with Retry-After header. Zero user records created.
  1. Checks request.get_json(silent=True)
     - If body is None or not dict:
       Returns api_response(False, "Request body must be valid JSON.", None, "INVALID_JSON", 400)
  │
  ▼
[backend/services/auth_service.py: AuthService.register_user(body)]
  1. Name Validation:
     - Verifies name is non-empty string; strips surrounding whitespace: clean_name = raw_name.strip()
     - Enforces maximum length: len(clean_name) <= MAX_NAME_LENGTH (120)
       (raises AuthValidationError("Name must not exceed 120 characters.", "NAME_TOO_LONG") if > 120)
     - If empty or invalid: raises AuthValidationError("Field 'name' is required.", "MISSING_FIELD")
  2. Email Validation & Normalization:
     - Verifies email is non-empty string
     - Normalizes: raw_email.strip().lower() -> "alice.smith@example.com"
     - Enforces maximum length: len(normalized_email) <= MAX_EMAIL_LENGTH (255)
       (raises AuthValidationError("Email must not exceed 255 characters.", "EMAIL_TOO_LONG") if > 255)
     - Validates against regex: r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
     - If invalid: raises AuthValidationError("Invalid email address format.", "INVALID_EMAIL")
  3. Password Validation:
     - Verifies password is a non-empty string
     - Checks minimum length: len(password) >= 12 (raises AuthValidationError with "PASSWORD_TOO_SHORT" if < 12)
     - Checks maximum length: len(password) <= 128 (raises AuthValidationError with "PASSWORD_TOO_LONG" if > 128)
     - Checks weak-password blocklist: evaluates password.strip().lower() against local blocklist (raises AuthValidationError with "WEAK_PASSWORD" if matched)
     - No arbitrary composition constraints; spaces and Unicode are accepted and preserved
  4. Duplicate Check:
     - Queries User.query.filter_by(email=normalized_email).first()
     - If user exists: raises AuthValidationError("An account with this email already exists.", "EMAIL_ALREADY_REGISTERED")
  5. Password Hashing:
     - Generates hash: werkzeug.security.generate_password_hash(password) preserving raw unstripped password
     - Plaintext password is never stored or logged
  6. Persistence:
     - Instantiates User(name=clean_name, email=normalized_email, password_hash=password_hash, is_active=True)
     - Calls db.session.add(user) and db.session.commit()
  7. Returns safe user dictionary: { "id": user.id, "name": user.name, "email": user.email }
  │
  ▼
[backend/routes/auth_routes.py: register()]
  Catches AuthValidationError -> returns api_response(False, e.message, None, e.error_code, 400)
  Catches Exception           -> logs traceback via logger.exception(), returns sanitized 500 error
  On success:
  │
  ▼
[backend/utils/response.py: api_response()]
  Returns jsonify({
    "success": True,
    "message": "User registered successfully.",
    "data": { "id": 1, "name": "Alice Smith", "email": "alice.smith@example.com" },
    "error_code": None
  }), 201
  │
  ▼
Client receives HTTP 201 Created JSON Response
```

---

## 8. User Login Flow (`POST /api/auth/login`)

```
Client HTTP Request: POST /api/auth/login
Header: Content-Type: application/json
Body: { "email": "  Alice.Smith@Example.COM  ", "password": "StrongPassword123" }
  │
  ▼
[backend/app.py: Flask WSGI dispatch]
  Routes to auth_bp
  │
  ▼
[backend/routes/auth_routes.py: login()]
  Decorator: @limiter.limit(DEFAULT_LIMIT_AUTH_LOGIN) (Key: client IP request.remote_addr, 5/min, 20/hr)
  - If IP exceeded quota: raises RateLimitExceeded (HTTP 429), returns standard RATE_LIMIT_EXCEEDED response with Retry-After header.
  - Critical invariant: rate limiting occurs BEFORE password verification / scrypt execution, preventing CPU exhaustion attacks.
  1. Validation: Checks request.get_json(silent=True)
     - If body is None or not dict:
       Returns api_response(False, "Request body must be valid JSON.", None, "INVALID_JSON", 400)
  │
  ▼
[backend/services/auth_service.py: AuthService.login_user(body)]
  1. Input Validation:
     - Verifies 'email' is present and is a non-empty string (raises AuthValidationError("MISSING_FIELD") if missing)
     - Verifies 'password' is present and is a string (raises AuthValidationError("MISSING_FIELD") if missing)
  2. Email Normalization:
     - Normalizes: raw_email.strip().lower() -> "alice.smith@example.com"
  3. User Lookup:
     - Queries User.query.filter_by(email=normalized_email).first()
  4. Active-User & Password Verification (Anti-Enumeration):
     - If user is None:
       Raises AuthCredentialsError("Invalid email or password.", "INVALID_CREDENTIALS")
     - If not check_password_hash(user.password_hash, password):
       Raises AuthCredentialsError("Invalid email or password.", "INVALID_CREDENTIALS")
     - If not user.is_active:
       Raises AuthCredentialsError("Invalid email or password.", "INVALID_CREDENTIALS")
     (All three failures produce identical generic 401 response)
  5. JWT Generation:
     - Calculates iat (now) and exp (now + timedelta(hours=JWT_EXPIRATION_HOURS))
     - Constructs minimal claims payload: { "sub": str(user.id), "iat": iat, "exp": exp }
     - Signs token with PyJWT: jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
  6. Returns login payload:
     {
       "access_token": access_token,
       "token_type": "Bearer",
       "expires_in": expires_in_seconds
     }
  │
  ▼
[backend/routes/auth_routes.py: login()]
  Catches AuthValidationError  -> returns api_response(False, e.message, None, e.error_code, 400)
  Catches AuthCredentialsError -> returns api_response(False, e.message, None, e.error_code, 401)
  Catches Exception            -> logs traceback via logger.exception(), returns sanitized 500 error
  On success:
  │
  ▼
[backend/utils/response.py: api_response()]
  Returns jsonify({
    "success": True,
    "message": "Login successful.",
    "data": {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "Bearer",
      "expires_in": 86400
    },
    "error_code": None
  }), 200
  │
  ▼
Client receives HTTP 200 OK with Bearer access token
```

---

## 9. Protected Route Authorization Flow (`GET /api/auth/me`)

```
Client HTTP Request: GET /api/auth/me
Headers: Authorization: Bearer <access_token>
  │
  ▼
[backend/app.py: create_app]
  Routes to auth_bp
  │
  ▼
[backend/utils/auth.py: @require_auth decorator]
  1. Authorization Header Extraction:
     - Extracts request.headers.get("Authorization")
     - If missing or empty: returns api_response(False, "Authentication required.", None, "AUTHENTICATION_REQUIRED", 401)
  │
  ▼
  2. Bearer Scheme Validation:
     - Splits header into parts: split(None, 1)
     - Validates format matches "Bearer <token>"
     - If not Bearer or empty token: returns api_response(False, "Authentication required.", None, "AUTHENTICATION_REQUIRED", 401)
  │
  ▼
  3. Token Verification via AuthService:
     [backend/services/auth_service.py: AuthService.verify_token(token)]
     - Decodes JWT using configured JWT_SECRET_KEY and HS256
     - Enforces standard claims requirement: options={"require": ["sub", "iat", "exp"]}
     - Checks expiration: raises jwt.ExpiredSignatureError if exp < now
     - Checks signature and claim integrity: raises jwt.InvalidTokenError if tampered or missing
  │
  ▼
  4. Claim Validation:
     - If jwt.ExpiredSignatureError: returns api_response(False, "Authentication token has expired.", None, "TOKEN_EXPIRED", 401)
     - If jwt.InvalidTokenError: returns api_response(False, "Invalid authentication token.", None, "INVALID_TOKEN", 401)
     - Validates payload["sub"] as positive integer; extracts user_id = int(payload["sub"])
  │
  ▼
  5. Database User & Active Status Verification:
     - Queries User record: user = db.session.get(User, user_id, populate_existing=True)
     - If user is None (deleted/nonexistent): returns api_response(False, "Invalid authentication token.", None, "INVALID_TOKEN", 401)
     - If not user.is_active (deactivated/suspended): returns api_response(False, "Invalid authentication token.", None, "INVALID_TOKEN", 401)
     - Anti-enumeration: returns identical generic 401 INVALID_TOKEN for nonexistent and inactive accounts
  │
  ▼
  6. Context Binding:
     - Binds verified context:
         g.current_user_id = user_id
         g.current_user = user
  │
  ▼
[backend/utils/limiter.py: @limiter.limit (Key: f"user:{g.current_user_id}", 60/min)]
  - Evaluates user quota. If exceeded: returns 429 RATE_LIMIT_EXCEEDED.
  │
  ▼
[backend/routes/auth_routes.py: get_current_user()]
  - Invokes protected route function
  - Accesses g.current_user_id
  - Wraps response via api_response(True, "Authenticated user.", {"user_id": g.current_user_id}, None, 200)
  │
  ▼
[backend/utils/response.py: api_response()]
  Returns jsonify({
    "success": True,
    "message": "Authenticated user.",
    "data": {
      "user_id": 1
    },
    "error_code": None
  }), 200
  │
  ▼
Client receives HTTP 200 OK with authenticated user_id
```

---

## 10. Scan Persistence Service Flow (`create_scan` & `save_scan_result`)

### A. Scan Creation Flow (`create_scan`)
```
Caller (e.g. Detection Service / Route in future steps)
  │
  ▼
[backend/services/scan_service.py: ScanService.create_scan()]
  1. Input Validation:
     - Validates user_id: positive integer or None
     - Validates media_type: non-empty string, normalized via .strip().lower()
     - Validates filename: optional string or None
  │
  ▼
  2. Model Instantiation:
     - Instantiates Scan(user_id=user_id, media_type=media_type, filename=filename, status="PENDING", created_at=now)
  │
  ▼
  3. Database Transaction:
     - db.session.add(scan)
     - db.session.commit()
     - If SQLAlchemyError: db.session.rollback(), raises ScanDatabaseError
  │
  ▼
Returns Persisted Scan Model Instance
```

### B. Scan Result Persistence Flow (`save_scan_result`)
```
Caller (e.g. Analysis Completion Handler)
  │
  ▼
[backend/services/scan_service.py: ScanService.save_scan_result()]
  1. Target Scan Lookup & Integrity Checks:
     - Validates scan_id is positive integer
     - Resolves Scan via db.session.get(Scan, scan_id)
     - If not found: raises ScanNotFoundError
     - Checks if scan.result already exists (one-to-one constraint)
     - If exists: raises ScanConflictError
  │
  ▼
  2. Outcome Validation:
     - Validates prediction: non-empty string
     - Validates confidence: float in [0.0, 1.0]
     - Validates risk_level: non-empty string
     - Validates result_data: dict or defaults to {}
  │
  ▼
  3. Single Atomic Transaction:
     - Instantiates ScanResult(scan_id=scan.id, prediction=..., confidence=..., risk_level=..., result_data=..., created_at=now)
     - Updates parent Scan:
         scan.status = "COMPLETED"
         scan.completed_at = now
     - db.session.add(scan_result)
     - db.session.commit()
     - If SQLAlchemyError: db.session.rollback(), raises ScanDatabaseError
  │
  ▼
Returns Persisted ScanResult Model Instance (Parent Scan status is COMPLETED)
```

---

## 11. Database Initialization & Session Lifecycle Flow

```
Application Startup / Test Context:
  │
  ▼
[backend/app.py: create_app()]
  1. Reads SQLALCHEMY_DATABASE_URI from Config (defaults to sqlite:///truthlens.db)
  2. Calls db.init_app(app)
  3. Calls migrate.init_app(app, db)
  │
  ▼
[backend/database/db.py: enforce_sqlite_foreign_keys()]
  On SQLite connection:
  Executes "PRAGMA foreign_keys=ON;"
  │
  ▼
[backend/database/models.py]
  Declarative models registered:
  - User (users table)
  - Scan (scans table, user_id nullable foreign key)
  - ScanResult (scan_results table, scan_id unique foreign key)
  - AbuseReport (abuse_reports table, user_id and scan_id foreign keys)
  │
  ▼
Session Lifecycle:
  - Scoped sessions managed via db.session
  - Unit tests use in-memory SQLite (sqlite:///:memory:) with automatic rollback
  - Production/Dev uses instance/truthlens.db (or PostgreSQL in staging/production)
```

---

## 12. Migration Execution Flow (Flask-Migrate + Alembic)

```
CLI Command: flask db upgrade
  │
  ▼
[Flask-Migrate / Alembic Engine]
  1. Inspects Alembic configuration in migrations/alembic.ini & migrations/env.py
  2. Binds to app.config['SQLALCHEMY_DATABASE_URI']
  3. Checks 'alembic_version' table in target database
  4. Identifies pending revision: f3e901358e24 ("Initial database schema")
  │
  ▼
[migrations/versions/f3e901358e24_initial_database_schema_users_scans_.py]
  Executes upgrade():
  - Creates table 'users' with unique index on 'email'
  - Creates table 'scans' with index on 'user_id' and FK users.id (ON DELETE CASCADE)
  - Creates table 'abuse_reports' with indexes on 'scan_id', 'user_id'
  - Creates table 'scan_results' with unique index on 'scan_id' and FK scans.id (ON DELETE CASCADE)
  - Records revision ID into 'alembic_version'
  │
  ▼
Database is upgraded and schema matches SQLAlchemy declarative models
```

---

## 13. Centralized Error Execution Flow (400, 401, 404, 405, 413, 500)

```
Client sends invalid or unhandled request:
- Request unknown route (e.g. GET /api/unknown)
- Request incorrect method (e.g. GET /api/detect/text)
- Request exceeding MAX_CONTENT_LENGTH (> 50 MB)
- Unhandled server exception thrown outside try/catch
  │
  ▼
[Flask Core Engine]
  Traps exception and checks registered @app.errorhandler handlers
  │
  ▼
[backend/utils/errors.py]
  - 400: handle_bad_request -> api_response(False, description, None, "BAD_REQUEST", 400)
  - 404: handle_not_found   -> api_response(False, "Resource was not found...", None, "NOT_FOUND", 404)
  - 405: handle_method_not_allowed -> api_response(False, "Method is not allowed...", None, "METHOD_NOT_ALLOWED", 405)
  - 413: handle_payload_too_large  -> api_response(False, "Payload exceeds maximum...", None, "PAYLOAD_TOO_LARGE", 413)
  - 429: handle_rate_limit_exceeded -> api_response(False, "Rate limit exceeded. Please try again later.", None, "RATE_LIMIT_EXCEEDED", 429) (with Retry-After and X-RateLimit-* headers emitted by Flask-Limiter when RATELIMIT_HEADERS_ENABLED=True / headers_enabled=True)
  - Exception: handle_unhandled_exception ->
      logger.exception("Unhandled server exception: %s", str(e))
      api_response(False, "An unexpected internal server error occurred.", None, "INTERNAL_SERVER_ERROR", 500)
  │
  ▼
Client receives uniform JSON envelope with exact status code and zero internal info leakage
```

---

## 14. Scan History Listing Flow (`GET /api/scans`)

```
Client HTTP Request: GET /api/scans?page=1&per_page=10&media_type=video
Headers:
  Authorization: Bearer <access_token>
  │
  ▼
[backend/app.py: create_app]
  Flask WSGI router matches prefix '/api' and routes to scan_bp
  │
  ▼
[backend/utils/auth.py: @require_auth]
  1. Validates Authorization: Bearer <token>
  2. Verifies signature, expiration, and required claims via AuthService.verify_token()
  3. Verifies user exists and user.is_active is True via db.session.get(User, user_id, populate_existing=True)
  4. Binds authenticated user context: g.current_user_id = user_id, g.current_user = user
  │
  ▼
[backend/utils/limiter.py: @limiter.limit (Key: f"user:{g.current_user_id}", 60/min)]
  - Evaluates user quota. If exceeded: returns 429 RATE_LIMIT_EXCEEDED.
  │
  ▼
[backend/routes/scan_routes.py: list_scans()]
  1. Parses & validates 'page' (int >= 1; else 400 INVALID_PAGE)
  2. Parses & validates 'per_page' (int 1-100; else 400 INVALID_PER_PAGE)
  3. Parses & validates optional 'media_type' against ALLOWED_MEDIA_TYPES (else 400 INVALID_MEDIA_TYPE)
  │
  ▼
[backend/services/scan_service.py: ScanService.get_user_scans()]
  1. Scopes query strictly to user_id == g.current_user_id
  2. Eagerly loads 1-to-1 result via joinedload(Scan.result) to avoid N+1 queries
  3. Applies optional media_type filter
  4. Calculates total_items and total_pages
  5. Applies deterministic order_by(Scan.created_at.desc(), Scan.id.desc())
  6. Applies offset and limit pagination
  7. Returns { items, pagination: { page, per_page, total_items, total_pages, has_next, has_prev } }
  │
  ▼
[backend/routes/scan_routes.py: list_scans()]
  Serializes lightweight items:
  - id, media_type, filename, status, created_at, completed_at
  - summary result: { id, prediction, confidence, risk_level }
  - strictly excludes result_data to prevent large Base64 transmission
  - strictly excludes password_hash and user entity
  │
  ▼
[backend/utils/response.py: api_response()]
  Returns jsonify({ "success": True, "message": "Scans retrieved successfully.", "data": { "items": [...], "pagination": {...} }, "error_code": None }), 200
  │
  ▼
Client receives HTTP 200 JSON Response with paginated scan summary list
```

---

## 15. Individual Scan Forensic Detail Flow (`GET /api/scans/<int:scan_id>`)

```
Client HTTP Request: GET /api/scans/<scan_id>
Headers:
  Authorization: Bearer <access_token>
  │
  ▼
[backend/app.py: create_app]
  Routes to scan_bp
  │
  ▼
[backend/utils/auth.py: @require_auth]
  Validates Bearer token, verifies active database user, and binds g.current_user_id
  │
  ▼
[backend/utils/limiter.py: @limiter.limit (Key: f"user:{g.current_user_id}", 60/min)]
  - Evaluates user quota. If exceeded: returns 429 RATE_LIMIT_EXCEEDED.
  │
  ▼
[backend/routes/scan_routes.py: get_scan(scan_id)]
  Calls ScanService.get_user_scan_by_id(user_id=g.current_user_id, scan_id=scan_id)
  │
  ▼
[backend/services/scan_service.py: ScanService.get_user_scan_by_id()]
  Queries Scan.query.options(joinedload(Scan.result)).filter(Scan.id == scan_id, Scan.user_id == user_id).first()
  │
  ▼
Check Scan existence & ownership:
  - If scan is None (either does not exist OR belongs to another user):
      Returns api_response(False, "Scan not found.", None, "SCAN_NOT_FOUND", 404)
      (Anti-IDOR: never returns 403, preventing ID enumeration)
  - If scan exists and belongs to g.current_user_id:
      Serializes full detail payload including complete result_data (heatmap data URLs, breakdown metrics)
      Strictly omits password_hash and user entity
  │
  ▼
[backend/utils/response.py: api_response()]
  Returns jsonify({ "success": True, "message": "Scan details retrieved successfully.", "data": scan_detail, "error_code": None }), 200
  │
  ▼
Client receives HTTP 200 JSON Response with full forensic analysis details
```



