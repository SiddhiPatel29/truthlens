# Backend Engineering Constraints & Guidelines

This document specifies immutable rules and constraints that developers and AI assistants must NOT modify blindly.

---

## 1. Frontend Boundary
- **DO NOT modify frontend code.**
- The frontend is independently developed by other team members.
- Do not edit frontend components, styling, routing, mockups, or state management.
- Backend changes must communicate exclusively through documented REST API contracts.

---

## 2. Architecture Stability
- **DO NOT rewrite working backend architecture without concrete justification.**
- Preserve the Flask application factory pattern (`create_app`), modular Blueprints in `backend/routes/`, isolated services in `backend/services/`, and utilities in `backend/utils/`.
- Do not introduce unnecessary design patterns, microservices, message brokers (Celery, RabbitMQ), distributed caches (Redis), Docker, or Kubernetes unless explicitly requested.

---

## 3. Secret & Credential Management
- **DO NOT expose secrets or credentials in source code or version control.**
- **DO NOT commit `.env` files.**
- Never hardcode API keys, database credentials, or secret keys in Python files.
- All secrets must be loaded dynamically via environment variables with safe defaults for local development only.
- In production (`FLASK_ENV=production`), application startup must fail if fallback development secrets are detected.
- Never log passwords, API tokens, session cookies, or raw authorization headers in server logs.

---

## 4. Error Sanitization & Information Leakage Prevention
- **DO NOT expose internal exceptions, tracebacks, filesystem paths, or library errors to API clients.**
- All client error responses must use the uniform JSON envelope:
  ```json
  {
      "success": false,
      "message": "Sanitized, safe human-readable message",
      "data": null,
      "error_code": "SPECIFIC_ERROR_CODE"
  }
  ```
- Detailed stack traces must be captured strictly in server-side logs via `logger.exception()`.

---

## 5. API Contract Integrity
- **DO NOT invent API endpoints.**
- **DO NOT silently change existing API contracts.**
- The existing endpoints (`GET /api/health`, `POST /api/detect/text`, `POST /api/detect/image`, `POST /api/detect/video`, `POST /api/detect/audio`, `POST /api/report/abuse`) represent an agreed-upon contract with the frontend team.
- Field names, response structures, status codes, and error codes must remain stable. If a breaking change is unavoidable, it must be documented, reviewed, and approved before modification.

---

## 6. Detection Honesty & Transparency
- **DO NOT claim heuristic signal detection is genuine deep-learning / ML detection.**
- The current backend uses mathematical and signal-processing heuristics (Laplacian variance, Zero Crossing Rate, sentence burstiness, Grad-CAM++ simulated activation masks).
- Clearly document these algorithms as signal heuristics. Do not misrepresent them as trained transformer or convolutional deep neural networks until genuine models are integrated in a future phase.

---

## 7. Security Controls
- **DO NOT disable security controls merely to make development easier.**
- Do not set `CORS` origins to wildcard `*` with `supports_credentials=True` in production.
- Do not disable file extension checks or request payload size limits (`MAX_CONTENT_LENGTH`).
- Do not disable debug sanitization in production environments.

---

## 8. Database & Authentication Boundaries (Phase-Specific)
- **DO NOT implement database persistence, user registration, JWT login, or password resets in Phase 1.**
- Phase 1 is strictly dedicated to stabilizing the clean, testable, secure foundation. Database models, migrations, and authentication mechanisms belong exclusively to Phase 2.
