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
Headers: Content-Type: application/json
Body: { "text": "Artificial intelligence synthesis has progressed rapidly..." }
  │
  ▼
[backend/app.py: create_app]
  Flask WSGI router matches prefix '/api' and routes to text_bp
  │
  ▼
[backend/routes/text_routes.py: detect_text()]
  1. Calls request.get_json(silent=True)
     - If body is None or not dict or 'text' not in body:
       Calls api_response(False, "Request body must contain a 'text' field.", None, "INVALID_INPUT", 400)
  2. Type validation: verifies isinstance(input_text, str)
  3. Length validation: verifies len(input_text.strip()) >= 20
     - If < 20 chars:
       Calls api_response(False, "Text is too short...", None, "TEXT_TOO_SHORT", 400)
  │
  ▼
[backend/services/text_service.py: TextDetectionService.analyze_text(input_text)]
  1. Cleans text, splits into sentence list using regex: r'(?<=[.!?]) +'
  2. Calculates sentence length variance and burstiness_score
  3. Calculates vocabulary repetition and type_token_ratio
  4. Computes aggregate ai_probability: round((burstiness * 0.6) + ((1 - ttr) * 0.4), 3)
  5. Computes sentence_breakdown with per-sentence suspicious flag
  6. Returns dictionary { is_ai_generated, ai_confidence_score, metrics, sentence_breakdown }
  │
  ▼
[backend/routes/text_routes.py: detect_text()]
  Catches ValueError -> returns api_response(False, str(e), None, "PROCESSING_ERROR", 400)
  Catches Exception  -> logs via logger.exception(), returns api_response(False, "...", None, "INTERNAL_SERVER_ERROR", 500)
  On success:
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
Headers: Content-Type: multipart/form-data
Body: file field 'image' containing image binary (e.g. test.jpg)
  │
  ▼
[backend/app.py: create_app]
  Flask WSGI router matches prefix '/api' and routes to image_bp
  │
  ▼
[backend/routes/image_routes.py: detect_image()]
  1. Checks if "image" in request.files
     - If missing: calls api_response(False, "...", None, "MISSING_FILE", 400)
  2. Extracts file = request.files["image"]
  3. Validates file via [backend/utils/file_validator.py: validate_image_file(file)]
     - Checks file.filename != ""
     - Checks extension against ALLOWED_IMAGE_EXTENSIONS ("png", "jpg", "jpeg", "webp")
     - If invalid: calls api_response(False, err_msg, None, err_code, 400)
  4. Reads raw bytes: file_bytes = file.read()
  │
  ▼
[backend/services/image_service.py: ImageDetectionService.analyze_image(file_bytes)]
  1. Decodes raw bytes to OpenCV BGR matrix: np.frombuffer + cv2.imdecode
     - If img is None: raises ValueError("Failed to decode image...")
  2. Converts to grayscale: cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
  3. Computes Laplacian edge/texture variance: cv2.Laplacian(gray, cv2.CV_64F).var()
  4. Constructs Gaussian activation mask: cv2.circle + cv2.GaussianBlur
  5. Renders color heatmap: cv2.applyColorMap(..., cv2.COLORMAP_JET)
  6. Blends heatmap overlay: cv2.addWeighted(img, 0.6, heatmap_color, 0.4, 0)
  7. Encodes overlay to JPEG: cv2.imencode(".jpg", overlay)
  8. Base64 encodes preview: base64.b64encode(...) -> "data:image/jpeg;base64,..."
  9. Calculates confidence_score and is_deepfake boolean flag
  10. Returns analysis dict
  │
  ▼
[backend/routes/image_routes.py: detect_image()]
  Catches ValueError -> logs warning, returns api_response(False, str(e), None, "PROCESSING_ERROR", 400)
  Catches Exception  -> logs traceback via logger.exception(), returns sanitized 500 error
  On success:
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
Headers: Content-Type: multipart/form-data
Body: file field 'video' containing video binary (e.g. test.mp4)
  │
  ▼
[backend/app.py: create_app]
  Routes to video_bp
  │
  ▼
[backend/routes/video_routes.py: detect_video()]
  1. Checks "video" in request.files
     - If missing: returns api_response(False, "...", None, "MISSING_FILE", 400)
  2. Validates file via [backend/utils/file_validator.py: validate_video_file(file)]
     - Verifies filename not empty and extension in {"mp4", "mov", "avi", "mkv"}
     - If invalid: returns api_response(False, err_msg, None, err_code, 400)
  │
  ▼
[backend/services/video_service.py: VideoDetectionService.analyze_video(file)]
  1. Creates temporary file on disk: tempfile.mkstemp(suffix=".mp4")
  2. Streams file.save(temp_path)
  3. try...finally ensures os.remove(temp_path) executes even if errors occur
  4. Opens cv2.VideoCapture(temp_path)
  5. Uniformly samples up to 16 keyframes across duration: np.linspace(...)
  6. Reads sampled frames, computes Laplacian variance and anomaly score per frame
  7. Tracks peak anomaly frame (suspicious_frame)
  8. Calculates overall sequence confidence mean and temporal instability standard deviation
  9. Renders Grad-CAM++ heatmap overlay on peak suspicious frame and encodes to Base64 data URL
  10. Returns analysis dictionary
  │
  ▼
[backend/routes/video_routes.py: detect_video()]
  Catches ValueError -> returns api_response(False, str(e), None, "PROCESSING_ERROR", 400)
  Catches Exception  -> logs traceback via logger.exception(), returns sanitized 500 error
  On success:
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
Headers: Content-Type: multipart/form-data
Body: file field 'audio' containing audio binary (e.g. test.wav)
  │
  ▼
[backend/app.py: create_app]
  Routes to audio_bp
  │
  ▼
[backend/routes/audio_routes.py: detect_audio()]
  1. Checks "audio" in request.files
     - If missing: returns api_response(False, "...", None, "MISSING_FILE", 400)
  2. Validates file via [backend/utils/file_validator.py: validate_audio_file(file)]
     - Verifies filename not empty and extension in {"wav", "mp3", "m4a", "flac"}
     - If invalid: returns api_response(False, err_msg, None, err_code, 400)
  │
  ▼
[backend/services/audio_service.py: AudioDetectionService.analyze_audio(file)]
  1. Saves stream to temporary file: tempfile.mkstemp(suffix=".wav")
  2. try...finally guarantees os.remove(temp_path) is called
  3. Decodes WAV stream: scipy.io.wavfile.read(temp_path)
  4. Converts stereo to mono if multi-channel (data.mean(axis=1))
  5. Computes Zero Crossing Rate (ZCR): np.sum(np.diff(data > 0) != 0) / len(data)
  6. Computes spectral energy variance: np.var(data)
  7. Estimates synthetic vocal confidence score
  8. Flags temporal lip-sync discrepancy window intervals
  9. Returns analysis dictionary
  │
  ▼
[backend/routes/audio_routes.py: detect_audio()]
  Catches ValueError -> returns api_response(False, str(e), None, "PROCESSING_ERROR", 400)
  Catches Exception  -> logs traceback via logger.exception(), returns sanitized 500 error
  On success:
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
  1. Checks request.get_json(silent=True)
     - If body is None or not dict:
       Returns api_response(False, "Request body must be valid JSON.", None, "INVALID_JSON", 400)
  │
  ▼
[backend/services/auth_service.py: AuthService.register_user(body)]
  1. Name Validation:
     - Verifies name is non-empty string; strips surrounding whitespace
     - If invalid: raises AuthValidationError("Field 'name' is required.", "MISSING_FIELD")
  2. Email Validation & Normalization:
     - Verifies email is non-empty string
     - Normalizes: raw_email.strip().lower() -> "alice.smith@example.com"
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
  4. Claim Validation & Context Binding:
     - If jwt.ExpiredSignatureError: returns api_response(False, "Authentication token has expired.", None, "TOKEN_EXPIRED", 401)
     - If jwt.InvalidTokenError: returns api_response(False, "Invalid authentication token.", None, "INVALID_TOKEN", 401)
     - Validates payload["sub"] as positive integer
     - Binds user ID to request context: g.current_user_id = int(payload["sub"])
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

## 10. Database Initialization & Session Lifecycle Flow

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

## 11. Migration Execution Flow (Flask-Migrate + Alembic)

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

## 12. Centralized Error Execution Flow (400, 401, 404, 405, 413, 500)

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
  - Exception: handle_unhandled_exception ->
      logger.exception("Unhandled server exception: %s", str(e))
      api_response(False, "An unexpected internal server error occurred.", None, "INTERNAL_SERVER_ERROR", 500)
  │
  ▼
Client receives uniform JSON envelope with exact status code and zero internal info leakage
```

