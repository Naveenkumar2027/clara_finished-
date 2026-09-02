# CLARA - AI Receptionist Kiosk System

CLARA is a full-stack multilingual AI receptionist kiosk for SVIT. It uses a React/Vite frontend, a FastAPI backend, WebSocket state sync, optional PostgreSQL/pgvector RAG, and voice I/O through browser speech recognition or backend STT/TTS providers.

Repository: https://github.com/thequantumbugs-coder/FB-Clara

## Production Readiness Snapshot

Current automated gates expected before release:

- Frontend typecheck: `npm run lint`
- Frontend production build: `npm run build`
- Frontend security audit: `npm audit --audit-level=high`
- Frontend E2E kiosk flow: `npm run test:e2e`
- Backend tests: `python -m pytest backend/tests -q`
- RAG database smoke: `python backend/tools/test_db_rag.py`
- Multilingual RAG smoke: `python -m backend.tools.rag_multilingual_check`
- Optional latency benchmark: `python -m backend.tools.latency_benchmark --turns 20 --label low-latency-receptionist`

On Windows, run the release check bundle:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\production-check.ps1
```

To include the low-latency benchmark gate:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\production-check.ps1 -RunLatencyGate
```

Manual gates still required on target kiosk hardware:

- Microphone capture quality
- Speaker output quality
- STT/TTS provider latency
- Wake -> language -> chat -> voice reply -> reset flow
- All six supported languages

## Repository Structure

```text
backend/          FastAPI app, WebSocket endpoint, RAG, voice, tests
frontend/         React 19 + Vite + TypeScript kiosk UI
config/           Runtime UI configuration
scripts/          Startup, DB, and deployment helpers
docs/             Setup, status, latency, and troubleshooting notes
college_knowledge.txt
docker-compose.yml
.env.example      Backend environment template
```

## Prerequisites

- Node.js 20+
- Python 3.11 recommended
- Docker Desktop, for local PostgreSQL/pgvector
- Provider keys for production voice/LLM:
  - `GROQ_API_KEY`
  - `SARVAM_API_KEY`

## Environment Setup

Copy the backend environment template:

```powershell
Copy-Item .env.example .env
```

Set at least:

```text
GROQ_API_KEY=...
SARVAM_API_KEY=...
POSTGRES_PASSWORD=...
```

For production WebSocket auth, also set:

```text
WS_AUTH_REQUIRED=true
WS_TOKEN_SIGNING_SECRET=<strong-random-signing-secret>
WS_TOKEN_TTL_SECONDS=90
PRODUCTION_STRICT_READY=true
RAG_MIN_DOCUMENTS=500
REQUIRE_WS_AUTH_IN_PRODUCTION=true
```

For low-latency visible answers with audio attached after TTS completes, keep:

```text
LOW_LATENCY_VOICE_MODE=true
FIRST_SENTENCE_TTS_MAX_CHARS=160
AUDIO_UPDATE_TIMEOUT_S=3.0
ENABLE_FIRST_SENTENCE_TTS=true
ENABLE_TTS_PIPELINING=true
```

The browser obtains a short-lived token from `POST /api/ws-token`; no permanent
frontend token is configured. Set only the WebSocket address when needed:

```text
VITE_WS_URL=ws://localhost:6969/ws/clara
```

`WS_AUTH_TOKEN` is retained only for explicitly non-production development or
test clients. `PRODUCTION_STRICT_READY=true` always rejects it. Rate limits are
in-memory and process-local; multi-worker deployments need a shared limiter.

## Backend Setup

Create and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements\requirements.txt
```

Start or repair the local RAG database:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\db\init-rag-db.ps1
```

Ingest knowledge into PostgreSQL:

```powershell
.\.venv\Scripts\python.exe -m backend.tools.ingest_college_knowledge_pg
```

Verify RAG:

```powershell
.\.venv\Scripts\python.exe backend\tools\test_db_rag.py
.\.venv\Scripts\python.exe -m backend.tools.rag_multilingual_check
```

Run the backend:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-backend.ps1
```

Default backend URL: `http://localhost:6969`

Production monitor endpoints:

- `GET /health`: process liveness
- `GET /ready`: dependency readiness. In strict mode, it requires provider keys, RAG document count >= `RAG_MIN_DOCUMENTS`, WebSocket auth when required, and locked-down allowed origins.

## Frontend Setup

Install dependencies:

```powershell
Set-Location frontend
npm ci
```

Run development UI:

```powershell
npm run dev
```

Default frontend URL: `http://localhost:5176`

Build production UI:

```powershell
npm run build
```

Run mocked E2E kiosk flow after backend/frontend are running:

```powershell
npm run test:e2e
```

The E2E suite uses a local-safe mocked WebSocket and does not require microphone, Sarvam, or Groq access.

## Running Both Locally

Terminal 1:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-backend.ps1
```

Terminal 2:

```powershell
Set-Location frontend
npm run dev
```

If port `6969` is already in use:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\kill-backend-port.ps1
```

## Voice Modes

Recommended demo mode:

```text
VITE_VOICE_INPUT_MODE=browser
```

Backend microphone capture is supported, but should be validated on the exact kiosk hardware before demos or production use.

Supported languages:

- English
- Kannada
- Hindi
- Tamil
- Telugu
- Malayalam

Keep `SARVAM_LANGUAGE_CODE=unknown` or unset to allow STT auto-detection. Manual language selection from the UI overrides detection for that session.

Low-latency behavior:

- CLARA sends text/cards first and does not wait for TTS.
- Audio arrives later through an `assistant_audio_update` WebSocket payload on the same `turn_id`.
- Deterministic receptionist intents use local fast paths when data is available.
- The current software target is visible answer p95 <= 1,000ms and first audio-ready p95 <= 3,000ms for common receptionist questions.

## RAG Notes

The RAG path uses:

- Docker service: `clara-postgres`
- Database defaults: `clara_db`, `clara_user`
- Table: `college_knowledge`
- Schema: `scripts/db/init_pgvector.sql`
- Ingestion: `python -m backend.tools.ingest_college_knowledge_pg`

If `.env` was changed after the Docker volume was created, run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\db\init-rag-db.ps1
```

This aligns the running database role password with `.env`, creates the configured database if needed, and applies the pgvector schema.

## Production Checklist

Before declaring a release production-ready:

- `git status --short` contains only intentional release changes
- `.env` and `frontend/.env.local` are not committed
- `WS_AUTH_REQUIRED=true` is enabled for non-local deployments
- `WS_TOKEN_SIGNING_SECRET` is configured and `WS_AUTH_TOKEN` is not used by production
- `WS_ALLOWED_ORIGINS` is locked to the real frontend origin
- PostgreSQL is healthy and RAG returns non-empty context
- Knowledge ingestion has been run after content changes
- Backend tests pass
- Frontend typecheck/build pass
- Security audits pass
- Mocked Playwright kiosk E2E passes
- Optional latency gate passes with `scripts\production-check.ps1 -RunLatencyGate`
- Full kiosk hardware smoke passes
- Logs are collected for backend startup, WebSocket turns, provider failures, and latency metrics
- `/ready` reports `status: ready` on the production machine

## Useful Files

- Agent instructions (read first): `AGENTS.md` — then full project context in `docs/CLARA_PROJECT_MEMORY.md`
- Persistent project context: `docs/CLARA_PROJECT_MEMORY.md`
- Current status: `docs/CURRENT_STATUS.md`
- PostgreSQL setup: `docs/POSTGRES_SETUP.md`
- Voice latency runbook: `backend/tools/audio_latency_runbook.md`
- WebSocket schemas: `backend/app/ws_schemas.py`
- Main backend app: `backend/app/main.py`
- Main frontend app: `frontend/src/App.tsx`

## CI

GitHub Actions runs:

- Frontend install, typecheck, build, and `npm audit --audit-level=high`
- Backend dependency install, unit tests, and Python dependency audit

See `.github/workflows/ci.yml`.
