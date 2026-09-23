# TruthLens / VeraMedia AI

> **Multimodal Synthetic Media & Forensic Analysis Platform**

TruthLens (also referred to as VeraMedia AI) is an end-to-end web platform designed to analyze digital media (text, images, video, and audio) for indicators of synthetic generation and manipulation. The platform provides automated forensic heuristics, artifact visualization, persistent audit logging, authenticated scan history, and abuse takedown report generation.

---

## Table of Contents

- [Overview](#overview)
- [Current Implementation](#current-implementation)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Repository Structure](#repository-structure)
- [Detection Methods](#detection-methods)
- [Authentication and Security](#authentication-and-security)
- [Supported Media and Limits](#supported-media-and-limits)
- [API Overview](#api-overview)
- [Technology Stack](#technology-stack)
- [Environment Configuration](#environment-configuration)
- [Local Setup](#local-setup)
- [Running Backend](#running-backend)
- [Running Frontend](#running-frontend)
- [Running Tests](#running-tests)
- [Database Migrations](#database-migrations)
- [Current Limitations](#current-limitations)
- [Future Work](#future-work)
- [Development Notes](#development-notes)

---

## Overview

With the rapid emergence of generative artificial intelligence, manipulated digital assets (deepfakes, voice clones, synthetic imagery, and AI-generated text) pose significant trust, security, and verification challenges.

TruthLens provides an operational dashboard and API service for forensic examiners, trust and safety analysts, and researchers to:
- Inspect digital media across four modalities: **Text**, **Image**, **Video**, and **Audio**.
- Detect algorithmic and statistical manipulation indicators without sending media to external cloud APIs.
- Generate cryptographic SHA-256 evidence digests and persistent audit records.
- Export structured abuse dossiers to support manual platform abuse or takedown reporting.

---

## Current Implementation

This repository contains a functional, self-contained implementation with a Python/Flask backend and a React/TypeScript frontend.

> **Important Technical Note**:
> The detection engine in this codebase utilizes **statistical, mathematical, signal-processing, and computer-vision heuristics** (implemented via NumPy, SciPy, and OpenCV).
>
> The current codebase does **not** execute heavy deep-learning model checkpoints (such as ResNet-50, EfficientNet, CNN-LSTM, SyncNet, Wav2Vec, RoBERTa, or true GPU-based neural Grad-CAM++). While earlier design concepts and architectural roadmaps proposed those deep-learning models, the active system is engineered as an efficient, deterministic, CPU-compatible forensic pipeline.

### Active vs. Proposed Capabilities Summary

| Capability | Current Repository Implementation | Proposed / Future Roadmap |
| :--- | :--- | :--- |
| **Backend Framework** | Flask 3.0.3 application factory | FastAPI / Distributed Microservices |
| **Image Analysis** | OpenCV Laplacian variance, spatial artifact heatmaps, dimension & pixel bounds | Deep ResNet-50 / EfficientNet / Vision Transformers |
| **Video Analysis** | Frame sampling, temporal variance, inter-frame anomaly tracking | Spatial-temporal 3D CNN / Bi-LSTM |
| **Audio Analysis** | SciPy WAV signal analysis, Zero-Crossing Rate (ZCR), energy variance | SyncNet cross-modal lip synchronization, Wav2Vec |
| **Text Analysis** | Sentence burstiness variance, Type-Token Ratio (TTR), linguistic predictability | RoBERTa / DeBERTa fine-tuned transformer classification |
| **Database** | SQLite via SQLAlchemy 2.0 / Alembic migrations | PostgreSQL / Distributed cluster |
| **Authentication** | PBKDF2/scrypt password hashing, PyJWT tokens, role metadata | OAuth2 / SSO / Hardware token MFA |
| **Evidence Verification** | SHA-256 cryptographic digest matching & local scan records | Distributed ledger / Public C2PA PKI signing |
| **Rate Limiting** | Flask-Limiter (in-memory for local development; Redis-compatible) | Distributed Redis Cluster with dynamic IP reputation |

---

## Key Features

- **Multimodal Forensic Analysis**: Specialized endpoints and analysis pipelines for text documents, raster images, containerized video, and uncompressed audio.
- **Interactive Visualizations**:
  - **Forensic Anomaly Heatmaps**: Visualizes regions associated with the implemented spatial artifact analysis.
  - **Temporal Frame Sampling**: Inspects keyframes across video timelines for visual inconsistencies.
  - **Acoustic Waveform Telemetry**: Displays Zero-Crossing Rate (ZCR) and spectral energy indicators.
  - **Linguistic Metrics**: Displays sentence length variance (burstiness) and vocabulary richness (Type-Token Ratio).
- **Persistent Scan History**: Every authenticated scan is recorded in SQLite with its analysis verdict, confidence score, risk categorization, and detailed telemetry metadata.
- **Cryptographic Evidence Hashing**: Every analyzed asset is hashed with SHA-256 to provide a cryptographic integrity fingerprint that can be referenced during evidence verification.
- **Abuse Evidence Dossiers**: Generates structured evidence dossiers that can be used to support manual platform abuse or takedown reporting.
- **Defensive Resource Bounding**: Strict file validation guards against path traversal, control characters, decompression bombs (16 MP limit), and oversized media.
- **Rate Limiting & Anti-Enumeration**: Per-endpoint and per-user throttling prevents denial-of-service and credential brute-forcing.

---

## Architecture

TruthLens follows a decoupled client-server architecture:

```
+------------------------------------------------------------------+
|                   TruthLens Frontend (React / Vite)              |
|   - Operational Dashboard      - Modality Upload Console         |
|   - Interactive Forensics      - Evidentiary Vault & QR Modal    |
|   - Abuse Dispatcher           - System Health Monitor           |
+---------------------------------+--------------------------------+
                                  |
                   HTTP / REST    |  JSON + Multipart Uploads
                   Bearer JWT     |  CORS Whitelisted
                                  v
+------------------------------------------------------------------+
|                   TruthLens Backend (Flask 3.0.3)                |
|   +----------------------------------------------------------+   |
|   | App Factory (create_app) & Central Error Handling        |   |
|   +----------------------------------------------------------+   |
|   | Middleware: Flask-Limiter, CORS, JWT Verification        |   |
|   +----------------------------------------------------------+   |
|   | Route Blueprints:                                        |   |
|   |   /api/auth     /api/detect/text     /api/detect/image   |   |
|   |   /api/health   /api/detect/audio    /api/detect/video   |   |
|   |   /api/scans    /api/report/abuse                        |   |
|   +----------------------------------------------------------+   |
|   | Service Layer:                                           |   |
|   |   TextService   ImageService   VideoService  AudioService|   |
|   |   ScanService   AuthService    AbuseService              |   |
|   +----------------------------------------------------------+   |
|   | Data Layer: SQLAlchemy 2.0 ORM + Alembic Migrations      |   |
+---------------------------------+--------------------------------+
                                  |
                                  v
               +--------------------------------------+
               |      SQLite Database (truthlens.db)  |
               |  - users            - scans          |
               |  - scan_results     - abuse_reports  |
               +--------------------------------------+
```

---

## Repository Structure

```text
truthlens/
├── backend/                        # Python/Flask server package
│   ├── database/                   # Database engine, models, and initialization
│   │   ├── db.py                   # SQLAlchemy instance and migrate extension
│   │   └── models.py               # User, Scan, ScanResult, AbuseReport models
│   ├── routes/                     # Blueprint API route controllers
│   │   ├── abuse_routes.py         # Abuse report submission and persistence
│   │   ├── audio_routes.py         # Audio file upload and analysis
│   │   ├── auth_routes.py          # User registration, login, and profile (/me)
│   │   ├── health_routes.py        # System health and operational check
│   │   ├── image_routes.py         # Image file upload and analysis
│   │   ├── scan_routes.py          # Paginated scan history and detail retrieval
│   │   ├── text_routes.py          # Text document analysis
│   │   └── video_routes.py         # Video upload, duration check, and analysis
│   ├── services/                   # Core business logic and forensic algorithms
│   │   ├── abuse_service.py        # Dossier generation and database persistence
│   │   ├── audio_service.py        # WAV decoding, ZCR, and energy calculations
│   │   ├── auth_service.py         # Password hashing, token generation, credential check
│   │   ├── image_service.py        # Laplacian variance, spatial heatmap overlays
│   │   ├── scan_service.py         # Query pagination, scan detail serialization
│   │   ├── text_service.py         # Sentence burstiness, lexical diversity
│   │   └── video_service.py        # OpenCV frame sampling, temporal jitter tracking
│   ├── utils/                      # Cross-cutting utilities and security helpers
│   │   ├── auth.py                 # @require_auth JWT decorator and token parser
│   │   ├── errors.py               # Centralized HTTP error handler mapping
│   │   ├── file_validator.py       # Filename sanitization and magic-byte validation
│   │   ├── limiter.py              # Flask-Limiter configuration and key functions
│   │   └── response.py             # Standard JSON envelope helper (api_response)
│   ├── app.py                      # Application factory (create_app)
│   └── config.py                   # Environment settings and security validators
├── frontend/                       # React / TypeScript / Vite client application
│   ├── src/
│   │   ├── api/                    # Typed API client and endpoint bindings
│   │   │   ├── abuse.ts            # Abuse reporting endpoint calls
│   │   │   ├── auth.ts             # Login, register, and getCurrentUser calls
│   │   │   ├── client.ts           # Fetch wrapper with Bearer token injection
│   │   │   ├── detection.ts        # Multipart file and text detection calls
│   │   │   ├── health.ts           # Health check API call
│   │   │   └── scans.ts            # Scan listing and scan detail fetchers
│   │   ├── components/             # Reusable UI component modules
│   │   │   ├── analyze/            # Upload zones, progress indicators, results
│   │   │   ├── common/             # Modals (e.g. LedgerQrModal)
│   │   │   ├── forensics/          # HeatmapViewer, VideoForensics, Audio, Text
│   │   │   ├── investigation/      # ChainOfCustody, RiskAssessment, HumanReview
│   │   │   └── layout/             # AppLayout (top header & dropdowns), Sidebar
│   │   ├── context/                # React context providers (AuthContext)
│   │   ├── pages/                  # Top-level view pages
│   │   │   ├── AbuseDispatcher.tsx # Takedown dossier compilation page
│   │   │   ├── Analyze.tsx         # Multimodal media upload and analysis
│   │   │   ├── Dashboard.tsx       # Telemetry stats, charts, and scan feed
│   │   │   ├── DetectionHistory.tsx# Filterable historical scan records
│   │   │   ├── EvidenceVault.tsx   # Cryptographic asset vault and verification modal
│   │   │   ├── Investigations.tsx  # Deep forensic case examination view
│   │   │   ├── Login.tsx           # Authentication and registration forms
│   │   │   ├── ReportGeneration.tsx# Printable case dossiers and manifests
│   │   │   ├── Settings.tsx        # Analyst preferences and security profile
│   │   │   └── SystemHealth.tsx    # Pipeline status and engine telemetry
│   │   ├── types/                  # TypeScript interface definitions
│   │   ├── utils/                  # Client state helpers (scanManager)
│   │   ├── App.tsx                 # Route declarations and protected route guards
│   │   ├── index.css               # Global theme tokens, typography, utilities
│   │   └── main.tsx                # React DOM root entry
│   ├── package.json                # Frontend package dependencies and scripts
│   ├── tsconfig.json               # TypeScript compiler configuration
│   └── vite.config.ts              # Vite bundler configuration
├── migrations/                     # Alembic database migration scripts
│   ├── versions/                   # Versioned migration schemas
│   ├── alembic.ini                 # Alembic configuration
│   └── env.py                      # Migration runtime environment
├── tests/                          # Automated backend test suite (Pytest)
│   ├── conftest.py                 # Test fixtures, mock database, test client
│   ├── test_abuse_report.py        # Abuse report validation & persistence tests
│   ├── test_audio_detection.py     # Audio signal processing & limits tests
│   ├── test_audio_persistence.py   # Audio scan database lifecycle tests
│   ├── test_auth_authorization.py  # JWT protection & bearer token tests
│   ├── test_auth_login.py          # Login credential verification tests
│   ├── test_auth_registration.py   # User registration & password policy tests
│   ├── test_database.py            # Model constraints and cascade tests
│   ├── test_error_handling.py      # Standard JSON error envelope tests
│   ├── test_file_validator.py      # Magic-byte and filename security tests
│   ├── test_image_detection.py     # Image decoding, Laplacian variance tests
│   ├── test_image_persistence.py   # Image scan database lifecycle tests
│   ├── test_rate_limiting.py       # Rate limiter and DoS protection tests
│   ├── test_scan_history.py        # Scan history pagination and query tests
│   ├── test_scan_service.py        # Scan service logic tests
│   ├── test_startup_and_health.py  # App factory, health endpoint tests
│   ├── test_text_detection.py      # Text burstiness and lexical diversity tests
│   ├── test_text_persistence.py    # Text scan database lifecycle tests
│   ├── test_video_detection.py     # Video duration, OpenCV decoding tests
│   └── test_video_persistence.py   # Video scan database lifecycle tests
├── docs/                           # Project documentation and test checklists
├── instance/                       # Local instance storage (e.g. SQLite database)
├── scratch/                        # Temporary verification and validation scripts
├── .env.example                    # Safe environment variable template
├── requirements.txt                # Python backend dependencies
├── run.py                          # Minimal local server entry point
├── test.jpg                        # Root image test fixture
├── test.mp4                        # Root video test fixture
├── test.wav                        # Root audio test fixture
└── README.md                       # Repository documentation
```

---

## Detection Methods

TruthLens analyzes media using reproducible, explainable algorithmic methods:

### Text Analysis (`backend/services/text_service.py`)
- **Sentence Burstiness Variance**: Measures the standard deviation of sentence lengths. Natural human writing exhibits rhythmic variation (high burstiness), whereas synthetic text generated by large language models frequently exhibits uniform sentence lengths (low burstiness).
- **Type-Token Ratio (TTR)**: Calculates the ratio of unique words to total words to detect vocabulary repetition and lexical diversity anomalies.
- **Predictability & Scoring**: Combines burstiness and vocabulary uniformity into an aggregated AI generation score between `0.05` and `0.98`.
- **Payload Safety**: Analyzes the entire text (up to 25,000 characters) while capping the serialized sentence breakdown at 100 entries to prevent database bloat.

### Image Analysis (`backend/services/image_service.py`)
- **Spatial Variance (Laplacian)**: Converts the image to grayscale and computes the variance of the Laplacian matrix ($\nabla^2 f$) to quantify edge sharpness, high-frequency noise, and blur anomalies.
- **Visual Artifact Heatmap**: Computes an activation mask across spatial regions and generates a blended pseudo-color JET heatmap overlay indicating potential synthetic boundary seams.
- **Resource Protection**: Validates that dimensions do not exceed $4096 \times 4096$ and total pixel count does not exceed $16,777,216$ pixels (16 Megapixels), preventing decompression bombs.

### Video Analysis (`backend/services/video_service.py`)
- **Frame Sampling**: Extracts keyframes sequentially across the video duration using OpenCV.
- **Temporal Consistency**: Calculates frame-to-frame pixel residual differences and standard deviations to detect temporal flickering, unnatural jitter, and frame discontinuities.
- **Keyframe Visualization**: Identifies the frame with peak anomaly scores and renders a heatmap preview.
- **Resource Protection**: Enforces a strict 120-second duration maximum and 16 Megapixel resolution cap per frame.

### Audio Analysis (`backend/services/audio_service.py`)
- **Zero-Crossing Rate (ZCR)**: Measures the rate at which the audio signal changes algebraic sign. Synthetic voices and vocoders often exhibit abnormal zero-crossing densities compared to natural human speech.
- **Energy Variance & RMS**: Evaluates spectral energy distribution and root-mean-square amplitude variance across signal windows.
- **Format Constraint**: Requires uncompressed 16-bit or 24-bit PCM WAV containers to avoid lossy MP3/AAC compression artifacts corrupting signal calculations.
- **Resource Protection**: Enforces a strict 120-second duration maximum.

---

## Authentication and Security

### Password Security
- Passwords must be at least **12 characters** in length.
- Passwords are hashed using Werkzeug's secure hashing algorithms (`scrypt` or `pbkdf2:sha256`) with unique per-user salts. Raw passwords are never logged or stored.

### JWT Authorization
- Issues standard JSON Web Tokens signed with HMAC-SHA256 (`PyJWT`).
- Default token validity is **24 hours** (`JWT_EXPIRATION_HOURS=24`).
- Protected endpoints require an `Authorization: Bearer <token>` header.
- Invalid or expired tokens return an explicit `401 Unauthorized` with auto-session clearance on the frontend.

### Rate Limiting & DoS Mitigation
Rate limiting is enforced globally and on sensitive endpoints via `Flask-Limiter`:
- `POST /api/auth/register`: 3 per minute; 10 per hour
- `POST /api/auth/login`: 5 per minute; 20 per hour
- `POST /api/report/abuse`: 10 per minute; 60 per hour
- `POST /api/detect/video`: 5 per minute; 30 per hour
- `POST /api/detect/audio`: 10 per minute; 60 per hour
- `POST /api/detect/image`: 15 per minute; 100 per hour
- `POST /api/detect/text`: 30 per minute; 200 per hour
- `GET /api/scans`: 60 per minute
- `GET /api/auth/me`: 60 per minute

Responses return standard `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `Retry-After` headers. Rate limit violations return `429 Too Many Requests`.

### File & Upload Security
- **Magic-Byte Signature Inspection**: Inspects the first 32 bytes of uploaded streams to verify true file format signatures, preventing file-extension spoofing (e.g., verifying `FF D8 FF` for JPEG, `\x89PNG` for PNG, `RIFF....WEBP` for WebP, `ftyp` for MP4, `RIFF....WAVE` for WAV).
- **Filename Sanitization**: Rejects path traversal attempts (`../`, `..\\`), absolute paths, Windows drive letters (`C:`), control characters (ASCII 0–31, 127), and filenames longer than 255 characters.
- **Payload Limits**: Requests exceeding `MAX_CONTENT_LENGTH` (50 MB by default) are terminated by the web server with `413 Request Entity Too Large`.

---

## Supported Media and Limits

| Modality | Allowed Extensions | Magic Byte Signature Check | Dimensional & Duration Limits | Character / Size Bounds |
| :--- | :--- | :--- | :--- | :--- |
| **Text** | Raw JSON text field | N/A | N/A | Min 20 characters, Max 25,000 characters |
| **Image** | `.jpg`, `.jpeg`, `.png`, `.webp` | JPEG (`FF D8 FF`), PNG (`89 50 4E 47`), WebP (`RIFF....WEBP`) | Max $4096 \times 4096$ px; Max 16,777,216 pixels | Max 50 MB request payload |
| **Video** | `.mp4`, `.mov`, `.avi`, `.mkv` | MP4/MOV (`ftyp`), AVI (`RIFF....AVI`), MKV (`1A 45 DF A3`) | Max duration 120 seconds; Max $4096 \times 4096$ px | Max 50 MB request payload |
| **Audio** | `.wav` | WAV (`RIFF....WAVE` or `RIFX....WAVE`) | Max duration 120 seconds | Max 50 MB request payload |

---

## API Overview

All API responses follow a consistent JSON response envelope:

```json
{
  "success": true,
  "message": "Human-readable description.",
  "data": { ... },
  "error_code": null
}
```

When an error occurs, `success` is `false`, `data` is `null`, and `error_code` contains a machine-readable string (e.g., `INVALID_INPUT`, `UNAUTHORIZED`, `RATE_LIMIT_EXCEEDED`).

### System & Health

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | No | Returns system operational status and supported modalities. |

### Authentication

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/register` | No | Registers a new analyst user account. Requires `name`, `email`, `password`. |
| `POST` | `/api/auth/login` | No | Authenticates user credentials and returns a Bearer JWT access token. |
| `GET` | `/api/auth/me` | **Yes** | Returns profile information (`user_id`, `name`, `email`) for the authenticated user. |

### Detection & Analysis

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/detect/text` | **Yes** | Analyzes text for AI generation markers. Body: `{ "text": "..." }`. |
| `POST` | `/api/detect/image` | **Yes** | Analyzes an image file for artifacts. Multipart field: `image`. |
| `POST` | `/api/detect/video` | **Yes** | Analyzes video frames for temporal inconsistencies. Multipart field: `video`. |
| `POST` | `/api/detect/audio` | **Yes** | Analyzes audio waveforms for vocal synthesis cues. Multipart field: `audio`. |

All successful detection responses return a persistent `scan_id` referencing the saved database record.

### Scans & History

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/scans` | **Yes** | Lists paginated scan records owned by the user. Query params: `page`, `per_page`, `media_type`. |
| `GET` | `/api/scans/<scan_id>` | **Yes** | Retrieves full forensic result telemetry for a specific scan owned by the user. |

### Abuse & Reporting

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/report/abuse` | Optional | Generates a structured abuse dossier and persists it to the database. Supports optional `scan_id`. |

---

## Technology Stack

### Backend
- **Language**: Python 3.10+
- **Web Framework**: Flask 3.0.3
- **ORM & Database**: SQLAlchemy 2.0.52, Flask-SQLAlchemy 3.1.1
- **Database Migrations**: Alembic 1.19.2, Flask-Migrate 4.1.0
- **Security & Tokens**: PyJWT 2.10.1, Werkzeug 3.1.8
- **Rate Limiting**: Flask-Limiter 4.1.1
- **CORS Handling**: flask-cors 4.0.1
- **Computer Vision & Signal Processing**: OpenCV (`opencv-python 4.11.0.86`), NumPy 2.2.3, SciPy 1.15.2
- **Testing**: Pytest 8.3.4
- **WSGI Production Server**: Gunicorn 22.0.0

### Frontend
- **Framework**: React 18.3.1
- **Language**: TypeScript 5.6.3
- **Bundler & Dev Server**: Vite 6.0.1
- **Routing**: React Router 6.28.0
- **Icons**: Lucide React 0.468.0
- **QR Generation**: QRCode 1.5.4

---

## Environment Configuration

Configuration is managed via environment variables. Copy the safe template:

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# macOS / Linux
cp .env.example .env
```

### Key Environment Variables

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `FLASK_ENV` | `development` | Environment mode (`development`, `testing`, `production`). |
| `FLASK_DEBUG` | `1` | Enables Flask interactive debug mode (set to `0` in production). |
| `PORT` | `5000` | Port the backend server listens on. |
| `SECRET_KEY` | `dev_insecure_secret...` | Cryptographic secret for session signing. **Must be changed in production.** |
| `CLIENT_ORIGIN` | `http://localhost:3000,http://localhost:5173` | Comma-separated list of allowed frontend origins for CORS. |
| `MAX_CONTENT_LENGTH_MB`| `50` | Maximum permitted request payload size in megabytes. |
| `DATABASE_URL` | `sqlite:///truthlens.db` | SQLAlchemy database URI (SQLite locally, PostgreSQL for production). |
| `JWT_SECRET_KEY` | `dev_jwt_secret...` | Secret key for signing JWT tokens. **Must be changed in production.** |
| `JWT_EXPIRATION_HOURS` | `24` | Token expiration time in hours. |
| `RATELIMIT_ENABLED` | `true` | Globally toggles rate limiting. |
| `RATELIMIT_STORAGE_URI`| `memory://` | Storage backend for rate limiting. **Use Redis in multi-worker production.** |
| `RATELIMIT_STRATEGY` | `fixed-window` | Rate limiting algorithm strategy (`fixed-window`, `moving-window`). |

> **Security Warning**:
> - Never commit `.env` or production credentials to version control.
> - When running with `FLASK_ENV=production`, `backend/config.py` enforces a safety check that terminates startup if default development keys are detected.

---

## Local Setup

### Prerequisites
- **Python**: 3.10, 3.11, or 3.12 installed
- **Node.js**: 18+ or 20+ LTS installed
- **Git**

### Step-by-Step Installation (Windows PowerShell)

```powershell
# 1. Clone repository
git clone https://github.com/SiddhiPatel29/truthlens.git
cd truthlens

# 2. Create and activate Python virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Upgrade pip and install backend dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Initialize environment variables
Copy-Item .env.example .env

# 5. Install frontend dependencies
cd frontend
npm install
cd ..
```

### Step-by-Step Installation (macOS / Linux)

```bash
# 1. Clone repository
git clone https://github.com/SiddhiPatel29/truthlens.git
cd truthlens

# 2. Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Upgrade pip and install backend dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Initialize environment variables
cp .env.example .env

# 5. Install frontend dependencies
cd frontend
npm install
cd ..
```

---

## Running Backend

Ensure your virtual environment is active:

### Windows PowerShell
```powershell
.venv\Scripts\Activate.ps1
python run.py
```

### macOS / Linux
```bash
source .venv/bin/activate
python run.py
```

The backend server starts at:
```text
[*] VeraMedia AI Backend starting on http://localhost:5000
```

Verify backend health by visiting [http://localhost:5000/api/health](http://localhost:5000/api/health) in your browser or running:
```powershell
curl http://localhost:5000/api/health
```

---

## Running Frontend

In a separate terminal window:

```bash
cd frontend
npm run dev
```

The Vite development server will start at:
```text
  VITE v6.0.1  ready in 350 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

Open [http://localhost:5173](http://localhost:5173) in your browser to access the TruthLens console.

### Production Frontend Build
To compile the optimized production bundle:
```bash
cd frontend
npm run build
```
Compiled artifacts are written to `frontend/dist/`.

---

## Running Tests

The test suite contains **360 automated tests** covering authentication, detection, persistence, rate limiting, and file validation.

Run the full test suite using Pytest:

### Windows PowerShell
```powershell
.venv\Scripts\python -m pytest
```

### macOS / Linux
```bash
pytest
```

Run with concise reporting:
```bash
pytest -q
```

Run specific test modules:
```bash
pytest tests/test_auth_login.py
pytest tests/test_image_detection.py
pytest tests/test_rate_limiting.py
```

---

## Database Migrations

TruthLens uses **Flask-Migrate** (built on Alembic) to track database schema evolutions.

### Applying Migrations
To upgrade your local SQLite database to the latest schema:

#### Windows PowerShell
```powershell
$env:FLASK_APP = "run.py"
flask db upgrade
```

#### macOS / Linux
```bash
export FLASK_APP=run.py
flask db upgrade
```

### Generating a New Migration
When modifying models in `backend/database/models.py`:

```powershell
$env:FLASK_APP = "run.py"
flask db migrate -m "Add new column or table"
flask db upgrade
```

### Checking Migration Status
```powershell
flask db current
flask db history
```

---

## Current Limitations

1. **Heuristic Analysis vs. Deep Learning**: The current analysis engines use algorithmic heuristics and statistical signal processing. They do not employ trained neural network models (e.g., deep weights from RoBERTa, SyncNet, or ResNet).
2. **Audio Format Limitation**: The audio detection service currently only supports uncompressed **WAV** format files to ensure clean signal processing. Lossy compressed formats (MP3, AAC, OGG) are intentionally rejected by validation.
3. **In-Memory Rate Limiting**: The default `memory://` rate-limiting backend stores counters in local process memory. For multi-worker production deployments (e.g. Gunicorn with multiple worker processes), a shared storage URI such as `redis://localhost:6379/0` must be configured.
4. **SQLite Concurrency**: The default SQLite database is suitable for development and demonstrations, but high-concurrency production deployments require PostgreSQL.
5. **Local Evidence Ledger**: QR verification checks the SHA-256 evidence fingerprint against local database records. It does not interface with a public blockchain or C2PA PKI certificate authority.

---

## Future Work

The following enhancements represent the architectural roadmap for future development phases:

- **Deep Learning Model Integration**:
  - **Vision**: Integrate pre-trained ResNet-50 / EfficientNet models for pixel-level face-swap and artifact detection.
  - **Video**: Implement 3D CNN / Bi-LSTM networks for frame sequence and temporal artifact analysis.
  - **Audio**: Integrate SyncNet for automated lip-to-speech cross-modal desynchronization detection.
  - **Text**: Deploy transformer-based perplexity models (e.g., RoBERTa/DeBERTa) for linguistic classification.
- **Asynchronous Processing Architecture**:
  - Implement task queues using **Celery** and **Redis** to process long videos and large media asynchronously.
  - Provide WebSocket progress updates to the frontend during multi-minute processing tasks.
- **Hardware Acceleration**:
  - Support GPU-accelerated inference (CUDA / TensorRT) for high-throughput batch detection.
- **Standardized C2PA Provenance**:
  - Integrate cryptographic C2PA manifest signing and validation using appropriate credential and trust infrastructure.
- **Enterprise Storage Connectors**:
  - Support AWS S3 / Google Cloud Storage for persistent evidentiary media vault storage.

---

## Development Notes

- **Code Formatting & Clean Diffs**: Verify clean diffs before committing:
  ```bash
  git diff --check
  ```
- **Virtual Environment**: Always ensure Python dependencies are installed and executed inside the virtual environment (`.venv`).
- **Source of Truth**: The active code in `backend/` and `frontend/` represents the ground truth of the system. Documentation and presentations should reflect the actual implemented capabilities.

---

*TruthLens / VeraMedia AI &copy; 2026. Built for research, evaluation, and forensic media analysis.*
