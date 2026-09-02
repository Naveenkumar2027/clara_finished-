# CLARA Project Memory (Persistent Context)

Coding agents should pair this document with **`AGENTS.md`** at the repo root (read both fully at task start).

## Project Identity

- **Project:** CLARA - AI Receptionist Kiosk System
- **Type:** Full-stack kiosk app (React frontend + FastAPI backend)
- **Primary behavior:** Multilingual conversational assistant with voice I/O, WebSocket state sync, RAG-backed answers, and rich department/cards UX
- **Languages supported:** English, Kannada, Hindi, Tamil, Telugu, Malayalam
- **Current readiness:** Repo-side production checks are strong; final production approval still requires target kiosk hardware voice validation.

## Architecture Overview

- `frontend/`: React 19 + Vite + TypeScript kiosk UI.
- `backend/`: FastAPI app with WebSocket endpoint `/ws/clara`.
- `backend/services/answer_generation.py`: core intent and response pipeline.
- `backend/services/greetings.py`: wake and greeting copy, greeting style token.
- `backend/core/`: audio pipeline, language detection, RAG retrieval.
- `backend/clients/provider_clients.py`: Groq + Sarvam API clients, retries/fallbacks.
- `backend/clients/database.py`: PostgreSQL/pgvector pooling and resilient fallback mode.
- `backend/tests/test_health_endpoints.py`: coverage for health/readiness endpoints.
- `backend/tests/test_provider_failure_paths.py`: mocked failure-path coverage for STT, TTS, Groq, and RAG fallback behavior.
- `backend/tests/test_golden_query_matrix.py`: deterministic receptionist intent/query matrix.
- `frontend/e2e/chat-flow.spec.ts`: mocked E2E kiosk flow for sleep, wake/language gate, query response, reset, and all six language selections.
- `docs/`: ops/troubleshooting/latency references.
- `scripts/`: dev/startup and local utility scripts.

## Runtime Flow (High-Level)

1. Frontend starts in sleep state and connects to backend WebSocket.
2. Wake action transitions kiosk into chat/language gate.
3. User selects language (or backend auto-detects from first meaningful transcript).
4. User input comes from browser speech recognition or backend mic capture.
5. Backend normalizes query, detects intent/entities, fetches context (RAG when DB available), and generates reply.
6. For low-latency turns, backend sends visible text/card output first, then sends audio later with `type="assistant_audio_update"` on the same `turn_id`.
7. Frontend renders messages/cards immediately, merges later audio updates into the active assistant turn, and plays audio when available.

## Backend Core Responsibilities

### `backend/app/main.py`

- Owns FastAPI lifecycle and WebSocket action loop.
- Handles actions like `wake`, `language_selected`, `conversation_started`, `user_message`, `mic_start`, `menu_select`, etc.
- Runs turn processing pipeline and emits payloads containing UI state, messages, optional audio, and debug timing fields.
- Includes TTS caching/singleflight behavior and fallback handling.
- Supports low-latency visible-answer/audio-update split when `LOW_LATENCY_VOICE_MODE=true`.
- Uses deterministic fast paths for common receptionist intents when local data is enough.
- Exposes `GET /health` for process liveness and `GET /ready` for dependency readiness.

### `backend/app/ws_schemas.py`

- Strict validation for inbound WebSocket actions and payload shape.
- Allowed actions are explicitly whitelisted and parsed into typed models.

### `backend/services/answer_generation.py`

- Contains intent detection, department matching, entity extraction, and card-routing hints.
- Builds prompts for LLM calls and shapes structured overview responses.
- Handles multilingual normalization and translation-preserving structure logic.
- Provides fallback/off-topic/unavailable responses.

### `backend/services/greetings.py`

- Time-aware greeting text for wake/opening and language-gate nudge text.
- Returns greeting font family stack for frontend display styling (`greetingFontFamily` payload field).

### `backend/core/audio_pipeline.py`

- Microphone device resolution and validation.
- Fixed-duration and VAD-based recording modes.
- Audio capture metadata for diagnostics.

### `backend/core/language_detection.py`

- Language detection from STT metadata plus script heuristics.
- Constrained to CLARA supported language set and threshold fallback behavior.

### `backend/core/rag.py` + `backend/clients/database.py`

- Generates embeddings and retrieves top-k context from `college_knowledge`.
- Uses PostgreSQL + pgvector when available.
- If DB is unavailable, backend remains operational in LLM-only fallback mode.
- Current verified local state: `575` documents ingested and multilingual RAG smoke returns context for `en`, `hi`, `kn`, `ta`, `te`, `ml`.

### `backend/clients/provider_clients.py`

- Shared HTTP client with tuned timeouts/limits.
- Groq async client setup.
- Sarvam STT/TTS with retry and endpoint fallbacks.
- Warmup helpers to reduce first-turn latency.

## Frontend Core Responsibilities

### `frontend/src/App.tsx`

- Main kiosk shell and state routing between Sleep and Chat.
- Initializes WebSocket hook and orchestrates hard reset flow.
- Applies runtime remount/reset semantics for robust kiosk session recovery.

### `frontend/src/hooks/useWebSocket.ts`

- Singleton connection per URL, reconnect/backoff behavior.
- Tracks phase (`initial_connecting`, `connected`, `reconnecting`, `offline`).
- Drops stale payloads using `session_gen` and `wire_seq` guards.
- Exposes diagnostics and reset generation floor helpers.

### `frontend/src/screens/ChatScreen.tsx`

- Primary conversation UI renderer.
- Applies backend-provided `greetingFontFamily` style to greeting bubble.
- Coordinates message rendering, card panels, speaking/listening indicators, and audio playback UX.
- Treats `audioPending` as processing, not true speaking, and clears the orb on audio timeout/unavailable states.

### `frontend/src/hooks/useSpeechRecognition.ts`

- Browser speech-recognition path with per-language BCP47 mapping.
- Sends recognized transcript as `user_message` WebSocket action.

### `frontend/src/store/kiosk/*`

- Semantic kiosk state model and transition guard matrix.
- Maps backend numeric app states to semantic UI states.

### `frontend/src/context/LanguageContext.tsx`

- UI translation dictionary and language selection context.
- Provides default language reset behavior.
- Chat greeting text itself is backend-driven via WebSocket payload.

## WebSocket Contract Snapshot

Inbound actions currently include:

- `wake`
- `reset_session`, `home`
- `language_selected`
- `language_gate_prompt`
- `conversation_started`
- `user_message`
- `campus_navigation_tts`
- `toggle_mic`, `mic_start`, `mic_stop`, `mic_cancel`
- `menu_select`

## Critical Features to Preserve

- Wake -> language-gate -> conversation sequence.
- Multilingual support and language persistence per session.
- Auto language detection fallback behavior.
- STT/TTS pipeline and graceful fallback when providers are slow/unavailable.
- WebSocket session staleness protections (`session_gen`, `wire_seq`).
- RAG retrieval path with non-fatal DB fallback mode.
- Existing cards/menu behavior and department-specific response paths.
- Hard reset behavior returning kiosk cleanly to sleep defaults.

## Configuration Sources

- Backend env template: `.env.example`
- Backend config parser/constants: `backend/config/settings.py`
- Frontend env (optional local): `frontend/.env.local`
- Key runtime knobs: voice timeouts, streaming toggles, WS auth, DB credentials, model IDs
- Production WebSocket auth uses `WS_AUTH_REQUIRED=true` plus `WS_TOKEN_SIGNING_SECRET`; browsers fetch a short-lived credential from `POST /api/ws-token` and do not embed a permanent token.
- Production monitors should call `/health` and `/ready`.
- `PRODUCTION_STRICT_READY=true` makes `/ready` enforce provider keys, RAG availability, `RAG_MIN_DOCUMENTS`, WebSocket auth when required, and non-broad `WS_ALLOWED_ORIGINS`.
- Default readiness thresholds: `RAG_MIN_DOCUMENTS=500`, `REQUIRE_WS_AUTH_IN_PRODUCTION=true`.
- Low-latency defaults: `LOW_LATENCY_VOICE_MODE=true`, `FIRST_SENTENCE_TTS_MAX_CHARS=160`, `AUDIO_UPDATE_TIMEOUT_S=3.0`.

## Infra and Data

- `docker-compose.yml`: local PostgreSQL + pgvector service.
- `scripts/db/init_pgvector.sql`: DB/schema bootstrap.
- `scripts/db/init-rag-db.ps1`: Windows helper that starts/repairs Postgres, aligns role password with `.env`, creates the configured DB, and applies schema.
- Ingestion script: `python -m backend.tools.ingest_college_knowledge_pg`
- RAG verification scripts:
  - `python backend/tools/test_db_rag.py`
  - `python -m backend.tools.rag_multilingual_check`
- RAG table expected: `college_knowledge`

## Dev Commands (Reference)

- Backend start: `python -m backend.main`
- Frontend start: `npm run dev` (inside `frontend/`)
- Full deps backend install: `pip install -r backend/requirements/requirements.txt`
- RAG DB init/repair: `powershell -ExecutionPolicy Bypass -File scripts\db\init-rag-db.ps1`
- Production check bundle: `powershell -ExecutionPolicy Bypass -File scripts\production-check.ps1`
- Optional latency gate: `powershell -ExecutionPolicy Bypass -File scripts\production-check.ps1 -RunLatencyGate`
- Receptionist latency benchmark: `python -m backend.tools.latency_benchmark --turns 20 --label low-latency-receptionist`
- Frontend E2E after backend/frontend are running: `cd frontend && npm run test:e2e`
- Optional diagnostics scripts live under `backend/tools/`

## Current Production Verification Snapshot

Last verified locally on 2026-05-02:

- Backend tests: `56 passed, 49 subtests passed`.
- RAG DB smoke: passing.
- RAG document count: `575`.
- Multilingual RAG smoke: passing for all six supported languages.
- Frontend typecheck: passing.
- Frontend production build: passing.
- Frontend E2E kiosk flow: `10 passed` using mocked local-safe WebSocket behavior.
- Frontend audit: `0 vulnerabilities`.
- Python installed-environment audit: no known vulnerabilities.
- Frontend main app JS chunk reduced from about `1.28 MB` to about `442 kB` using Vite vendor chunks.
- Low-latency receptionist benchmark: visible answer p95 `242ms`; first audio-ready p95 `3,000ms`.
- Last production-check result: `DEGRADED` only because git working tree is dirty; all software gates passed.
- Current readiness: software `90-92%`, overall production `88-90%` until real kiosk hardware voice validation passes.

Known non-blocking warnings:

- Vite duplicate static/dynamic import warning for `college-logo.png`.
- Hugging Face unauthenticated download warning unless `HF_TOKEN` is set.
- TTS may still take up to the configured `AUDIO_UPDATE_TIMEOUT_S` cap, but the UI now shows the answer first and releases pending/speaking state cleanly.

## Remaining Production Gates

- Full hardware kiosk smoke: sleep -> wake -> language -> chat -> voice answer -> reset.
- Real microphone and speaker validation on the target kiosk.
- STT/TTS quality and latency validation with real Groq/Sarvam provider keys.
- Spoken checks in English, Kannada, Hindi, Tamil, Telugu, and Malayalam.
- Confirm `/ready` returns `status: ready` in the production environment.
- Ensure release is cut from a clean git state with only intentional files committed.

## Editing Safety Guidelines for Future Agents

- Make minimal, focused changes.
- Preserve existing UX/voice/state semantics unless explicitly asked to change them.
- Do not silently alter WebSocket contracts.
- Keep fallback behavior intact (voice provider failures, DB unavailable paths).
- Prefer additive documentation and targeted fixes over broad refactors.
- Validate with lint/tests/smoke checks relevant to touched area.
- For production-related changes, run `scripts\production-check.ps1` when feasible.

## UI Notes (Full-text chat)

- Full-text replies render in the scroll container `.text-container` (see `frontend/src/styles/cinematic-light.css`) and are orchestrated in `frontend/src/screens/ChatScreen.tsx`.
- Keep the bottom of the text viewport above the FAQ suggestions + orb stack in full-text layout.
- Short replies should remain visually centered; only long/overflowing replies should start at the top (optionally with gentle auto-scroll).

## Kiosk Inactivity Timer Notes

- The chat inactivity timer is owned by `frontend/src/App.tsx` (`CHAT_USER_INACTIVITY_MS`).
- The inactivity timer must **never** hard-reset the session while CLARA is mid-turn (processing) or playing TTS audio. When the timer fires during speaking/processing, it should reschedule itself instead of resetting.

## Facial Display Notes (eyes)

- Facial UI eye shapes live in `facial-display/src/components/RobotFace.tsx`.
- Eyes should visually occupy ~60% of the upper face region (bigger rounded-rect forms) while preserving blink/wink and gaze drift.
- If eyes feel too small on the kiosk display, increase both the eye container sizing (Tailwind width/height + max sizes) and expand the eye SVG viewBox/path extents together so glow + gaze remain proportional.
- Eye sizing can be tuned aggressively for distant viewing (external monitor): prefer larger eye containers over increasing face scale globally so mouth/eyes maintain proportions.

## Facial Display Notes (mouth placement)

- Mouth layout is in `facial-display/src/components/RobotFace.tsx` under the lower face container.
- Keep the mouth centered between the two eyes (horizontally) and sized proportionally to the eye scale so it remains readable from a distance.

## Quick "Where to Change What"

- Greeting copy/styling token: `backend/services/greetings.py`
- WebSocket behavior/state payloads: `backend/app/main.py`
- WS message schema validation: `backend/app/ws_schemas.py`
- Intent and card logic: `backend/services/answer_generation.py`
- STT/TTS providers: `backend/clients/provider_clients.py`
- Audio capture details: `backend/core/audio_pipeline.py`
- RAG retrieval: `backend/core/rag.py`, `backend/clients/database.py`
- RAG DB repair/init: `scripts/db/init-rag-db.ps1`
- Production verification: `scripts/production-check.ps1`
- Latency benchmark/gate: `backend/tools/latency_benchmark.py`, `scripts/production-check.ps1 -RunLatencyGate`
- Health/readiness endpoints: `backend/app/main.py`, `backend/tests/test_health_endpoints.py`
- Frontend WS lifecycle: `frontend/src/hooks/useWebSocket.ts`
- Chat UI rendering: `frontend/src/screens/ChatScreen.tsx`
- Kiosk shell/reset flow: `frontend/src/App.tsx`

## Session Update Log (2026-05-05)

### 1) Bus Routes Feature (Backend + Frontend)

- Added deterministic bus intent detection and routing:
  - `INTENT_BUS_ROUTES`, multilingual cue detection, and card hints in `backend/services/answer_generation.py`.
  - Backend WebSocket flow now maps bus trigger to `showCard="bus_routes"` in `backend/app/main.py`.
- Added backend test coverage:
  - `backend/tests/test_bus_routes_intent.py`.
- Added frontend bus routes module set:
  - Data: `frontend/src/data/collegeBusRoutes.json`, `frontend/src/data/collegeBusRoutes.types.ts`
  - Intent helpers: `frontend/src/lib/busRoutesIntent.ts`, `frontend/src/lib/busRoutesMatch.ts`
  - UI: `frontend/src/components/bus/BusRoutesFullscreen.tsx`

### 2) Single-Surface Chat Screen State + Unmount Semantics

- Introduced single-surface state model for mutually exclusive fullscreen content:
  - `frontend/src/types/chatSurface.ts`.
- Updated `frontend/src/screens/ChatScreen.tsx` to render one active surface at a time (`chat`, `department_comparison`, `brochure`, `bus_routes`), preventing overlay/ghost stacking.
- Bus routes close now returns to chat with surface reset and fresh remount behavior.

### 3) Comparison Table Readability + Narration Sync

- Increased comparison panel readability and usable area in:
  - `frontend/src/styles/cinematic-light.css`
  - `frontend/src/components/comparison/DepartmentComparisonCinema.tsx`
- Improved comparison TTS alignment logic in `frontend/src/screens/ChatScreen.tsx`:
  - narration-plan aware section application,
  - safer final section settling for streamed audio completion paths.

### 4) Chat Full-Text Bottom Alignment

- Rebalanced FAQ/orb/tap-to-speak stack in:
  - `frontend/src/styles/cinematic-light.css`
  - `frontend/src/screens/ChatScreen.tsx`
  - `frontend/src/screens/chat/ChatOrbControl.tsx`
- Goal achieved: cleaner bottom anchoring and reduced tap-text clipping risk.

### 5) Trustees / Founders Card System Upgrade

- Replaced passive slideshow with explicit interactive navigation:
  - prev/next controls, disabled edge states, dot indicators in `frontend/src/components/chat/cards/Trustees/Trustees.tsx`.
- Upgraded card visual hierarchy and dimensions (premium scale, no truncation) in:
  - `frontend/src/components/chat/cards/Trustees/TrusteeCard.tsx`
  - `frontend/src/styles/cinematic-light.css`
- Added per-card concise `tts_summary` metadata and auto-play-on-index-change backend narration trigger via `ChatScreen` callbacks (backend TTS path reused).

### 6) Repo Sync and Merge Notes

- Local branch was synchronized with upstream `origin/main` during this session and merge conflicts were resolved in:
  - `frontend/src/screens/ChatScreen.tsx`
  - `frontend/src/styles/cinematic-light.css`
  - `frontend/src/components/comparison/DepartmentComparisonCinema.tsx`
- Frontend typecheck (`npm run lint`, TypeScript noEmit) passed after each major conflict/feature integration step.
