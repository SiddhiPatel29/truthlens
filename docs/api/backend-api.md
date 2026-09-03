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
- **Authentication**: None (Public in Phase 1)
- **Service Called**: `TextDetectionService.analyze_text`
- **Request Headers**: `Content-Type: application/json`
- **Request Body**:
```json
{
  "text": "The investigative report confirmed that generative text tools exhibit uniform sentence lengths."
}
```

### Validation Rules
1. Body must be valid JSON object containing key `"text"`.
2. `"text"` must be a string.
3. `len(text.strip()) >= 20` characters.

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

---

## 3. Image Tamper & Deepfake Detection

- **Method**: `POST`
- **Path**: `/api/detect/image`
- **Authentication**: None (Public in Phase 1)
- **Service Called**: `ImageDetectionService.analyze_image`
- **Request Headers**: `Content-Type: multipart/form-data`
- **Request Body**:
  - `image` (binary file): Supported formats: `.png`, `.jpg`, `.jpeg`, `.webp`.

### Validation Rules
1. Request must be `multipart/form-data` with form field name `image`.
2. File must be present and filename non-empty.
3. Extension must be in `{"png", "jpg", "jpeg", "webp"}`.
4. Total payload must not exceed `MAX_CONTENT_LENGTH` (50 MB).

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
- **Missing `image` field (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "No 'image' file field found in request.",
    "data": null,
    "error_code": "MISSING_FILE"
  }
  ```
- **Disallowed extension or empty file (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Invalid image format. Allowed: jpeg, jpg, png, webp",
    "data": null,
    "error_code": "INVALID_FILE"
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

---

## 4. Video Temporal Deepfake Detection

- **Method**: `POST`
- **Path**: `/api/detect/video`
- **Authentication**: None (Public in Phase 1)
- **Service Called**: `VideoDetectionService.analyze_video`
- **Request Headers**: `Content-Type: multipart/form-data`
- **Request Body**:
  - `video` (binary file): Supported formats: `.mp4`, `.mov`, `.avi`, `.mkv`.

### Validation Rules
1. Form field name must be `video`.
2. File must be present and non-empty.
3. Extension must be in `{"mp4", "mov", "avi", "mkv"}`.
4. Video file must have at least 1 readable frame.
5. Max payload size: 50 MB.

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
- **Missing `video` field (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "No 'video' file field found in request.",
    "data": null,
    "error_code": "MISSING_FILE"
  }
  ```
- **Empty file (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "No video file selected.",
    "data": null,
    "error_code": "INVALID_FILE"
  }
  ```
- **Unsupported format (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Invalid video format. Allowed: avi, mkv, mov, mp4",
    "data": null,
    "error_code": "INVALID_FORMAT"
  }
  ```

---

## 5. Audio Synthetic Voice & Lip-Sync Analysis

- **Method**: `POST`
- **Path**: `/api/detect/audio`
- **Authentication**: None (Public in Phase 1)
- **Service Called**: `AudioDetectionService.analyze_audio`
- **Request Headers**: `Content-Type: multipart/form-data`
- **Request Body**:
  - `audio` (binary file): Supported formats: `.wav`, `.mp3`, `.m4a`, `.flac`.

### Validation Rules
1. Form field name must be `audio`.
2. File must be present and non-empty.
3. Extension must be in `{"wav", "mp3", "m4a", "flac"}`.
4. Max payload size: 50 MB.

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
- **Missing `audio` field (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "No 'audio' file field found in request.",
    "data": null,
    "error_code": "MISSING_FILE"
  }
  ```
- **Unsupported format (`400 Bad Request`)**:
  ```json
  {
    "success": false,
    "message": "Invalid audio format. Allowed: flac, m4a, mp3, wav",
    "data": null,
    "error_code": "INVALID_FORMAT"
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

## 7. Global Framework Errors

| HTTP Status | Error Code | Example Trigger | Message |
| :--- | :--- | :--- | :--- |
| `400 Bad Request` | `BAD_REQUEST` | Malformed multipart/form-data | `"Bad request or malformed payload."` |
| `404 Not Found` | `NOT_FOUND` | `GET /api/unknown-endpoint` | `"The requested resource was not found on this server."` |
| `405 Method Not Allowed` | `METHOD_NOT_ALLOWED` | `GET /api/detect/text` | `"The HTTP method is not allowed for this endpoint."` |
| `413 Payload Too Large` | `PAYLOAD_TOO_LARGE` | File upload > 50 MB | `"Request payload exceeds maximum permitted file size."` |
| `500 Internal Server Error` | `INTERNAL_SERVER_ERROR` | Unhandled server exception | `"An unexpected internal server error occurred."` |
