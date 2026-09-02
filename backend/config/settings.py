"""Configuration management for CLARA."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Base directory (project root containing .env)
BASE_DIR = Path(__file__).resolve().parents[2]

# Load environment variables from project root so PORT etc. are correct when run from any cwd
load_dotenv(BASE_DIR / ".env")

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
# Legacy support (fallback to separate keys if single key not provided)
if not SARVAM_API_KEY:
    SARVAM_API_KEY = os.getenv("SARVAM_ASR_API_KEY", "") or os.getenv("SARVAM_TTS_API_KEY", "")
# Sarvam STT language: "unknown" = auto-detect, or "hi", "en", etc. Empty = do not pass (API default).
_sarvam_language_raw = os.getenv("SARVAM_LANGUAGE_CODE", "unknown").strip().lower()
if "," in _sarvam_language_raw:
    # Some env files mistakenly use comma-separated values; Sarvam expects one code.
    _sarvam_language_raw = next((part.strip() for part in _sarvam_language_raw.split(",") if part.strip()), "unknown")
SARVAM_LANGUAGE_CODE = _sarvam_language_raw or None

# Sarvam TTS voice configuration (Bulbul v3)
_sarvam_speaker = os.getenv("SARVAM_TTS_SPEAKER", "simran").strip().lower()
SARVAM_TTS_SPEAKER = _sarvam_speaker or "simran"
try:
    _sarvam_tts_pace_raw = float(os.getenv("SARVAM_TTS_PACE", "1.25"))
except ValueError:
    _sarvam_tts_pace_raw = 1.25
# Clamp pace to a sensible range (0.5x – 2.0x)
SARVAM_TTS_PACE = max(0.5, min(2.0, _sarvam_tts_pace_raw))

# Auto language detection (text-level after first transcript)
AUTO_LANGUAGE_DETECT_ENABLED = os.getenv("AUTO_LANGUAGE_DETECT_ENABLED", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
AUTO_LANGUAGE_DETECT_CONFIDENCE_THRESHOLD = float(
    os.getenv("AUTO_LANGUAGE_DETECT_CONFIDENCE_THRESHOLD", "0.70")
)

# Hardware Configuration
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
# Legacy env key; retained for backward compatibility only.
MIC_DEVICE_INDEX = int(os.getenv("MIC_DEVICE_INDEX", "0")) if os.getenv("MIC_DEVICE_INDEX") else None
# Audio input device: by name substring (e.g. "ReSpeaker") or explicit index.
# If AUDIO_INPUT_DEVICE_INDEX is unset, fall back to legacy MIC_DEVICE_INDEX.
AUDIO_INPUT_DEVICE_NAME = os.getenv("AUDIO_INPUT_DEVICE_NAME", "").strip() or None
_audio_idx = os.getenv("AUDIO_INPUT_DEVICE_INDEX", "").strip()
if _audio_idx.isdigit():
    AUDIO_INPUT_DEVICE_INDEX = int(_audio_idx)
elif MIC_DEVICE_INDEX is not None:
    AUDIO_INPUT_DEVICE_INDEX = MIC_DEVICE_INDEX
else:
    AUDIO_INPUT_DEVICE_INDEX = None

# Audio output device (for playback in smoke test / backend playback)
AUDIO_OUTPUT_DEVICE_NAME = os.getenv("AUDIO_OUTPUT_DEVICE_NAME", "").strip() or None
_audio_out_idx = os.getenv("AUDIO_OUTPUT_DEVICE_INDEX", "").strip()  # separate from input
AUDIO_OUTPUT_DEVICE_INDEX = int(_audio_out_idx) if _audio_out_idx.isdigit() else None

# Paths
FACES_DB_PATH = os.getenv("FACES_DB_PATH", str(BASE_DIR / "config" / "faces.dat"))
UI_CONFIG_PATH = os.getenv("UI_CONFIG_PATH", str(BASE_DIR / "config" / "ui_config.json"))
TEMP_DIR = os.getenv("TEMP_DIR", str(BASE_DIR / "temp"))

# RAG Configuration
RAG_MAX_TOKENS = int(os.getenv("RAG_MAX_TOKENS", "6000"))
# Must be a valid Groq chat model id; if API returns 404, set in .env (see https://console.groq.com/docs/models)
# Groq decommissioned llama-3.1-8b-instant on 2026-08-16; openai/gpt-oss-20b is the documented successor.
RAG_MODEL = os.getenv("RAG_MODEL", "openai/gpt-oss-20b")
COLLEGE_KNOWLEDGE_PATH = os.getenv("COLLEGE_KNOWLEDGE_PATH", str(BASE_DIR / "college_knowledge.txt"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
RAG_MIN_DOCUMENTS = int(os.getenv("RAG_MIN_DOCUMENTS", "500"))
# Low-latency Groq model for mixed-language query normalization (Hinglish / regional + English).
MULTILINGUAL_PREPROCESSOR_MODEL = os.getenv("MULTILINGUAL_PREPROCESSOR_MODEL", "openai/gpt-oss-20b")
MULTILINGUAL_PREPROCESSOR_MAX_TOKENS = int(os.getenv("MULTILINGUAL_PREPROCESSOR_MAX_TOKENS", "320"))
MULTILINGUAL_PREPROCESSOR_TIMEOUT_S = float(os.getenv("MULTILINGUAL_PREPROCESSOR_TIMEOUT_S", "1.6"))

# M5.5 semantic-understanding proposal (not answer generation; not RAG_MODEL).
SEMANTIC_ROUTER_ENABLED = os.getenv("SEMANTIC_ROUTER_ENABLED", "false").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
SEMANTIC_ROUTER_MODEL = os.getenv("SEMANTIC_ROUTER_MODEL", "openai/gpt-oss-120b").strip() or "openai/gpt-oss-120b"
try:
    SEMANTIC_ROUTER_TIMEOUT_S = float(os.getenv("SEMANTIC_ROUTER_TIMEOUT_S", "6.0"))
except ValueError:
    SEMANTIC_ROUTER_TIMEOUT_S = 6.0

# PostgreSQL + pgvector (RAG storage)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "clara_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "clara_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

# State Machine Configuration
INACTIVITY_TIMEOUT = float(os.getenv("INACTIVITY_TIMEOUT", "20.0"))

# Audio Configuration
AUDIO_SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
AUDIO_CHANNELS = int(os.getenv("AUDIO_CHANNELS", "1"))
AUDIO_VAD_FRAME_MS = int(os.getenv("AUDIO_VAD_FRAME_MS", "20"))  # 10, 20, or 30 for webrtcvad
AUDIO_SILENCE_STOP_MS = int(os.getenv("AUDIO_SILENCE_STOP_MS", "800"))  # stop after this much silence
AUDIO_SPEECH_TIMEOUT_MS = int(os.getenv("AUDIO_SPEECH_TIMEOUT_MS", "10000"))  # max wait for speech to start
AUDIO_VAD_AGGRESSIVENESS = int(os.getenv("AUDIO_VAD_AGGRESSIVENESS", "2"))  # 0–3 for webrtcvad
AUDIO_PREROLL_BUFFER_MS = int(os.getenv("AUDIO_PREROLL_BUFFER_MS", "300"))  # ms of audio before speech start
AUDIO_MAX_UTTERANCE_MS = int(os.getenv("AUDIO_MAX_UTTERANCE_MS", "9000"))  # hard cap utterance length in VAD mode
# Record mode: "fixed" = record N seconds (proves capture on PC mic); "vad" = VAD start/stop
AUDIO_RECORD_MODE = (os.getenv("AUDIO_RECORD_MODE", "fixed").strip().lower() or "fixed")
if AUDIO_RECORD_MODE not in ("fixed", "vad"):
    AUDIO_RECORD_MODE = "fixed"
AUDIO_FIXED_RECORD_SECONDS = float(os.getenv("AUDIO_FIXED_RECORD_SECONDS", "4.0"))
AUDIO_SILENT_RMS_THRESHOLD = float(os.getenv("AUDIO_SILENT_RMS_THRESHOLD", "0.001"))

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "6969"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5176")
KIOSK_TIMEZONE = os.getenv("KIOSK_TIMEZONE", "Asia/Kolkata").strip() or "Asia/Kolkata"
# Shared secret for simple bearer token auth (minimum safe baseline).
WS_AUTH_TOKEN = os.getenv("WS_AUTH_TOKEN", "").strip()
# Optional HMAC secret for signed, short-lived ws tokens.
WS_TOKEN_SIGNING_SECRET = os.getenv("WS_TOKEN_SIGNING_SECRET", "").strip()
WS_TOKEN_TTL_SECONDS = max(60, min(120, int(os.getenv("WS_TOKEN_TTL_SECONDS", "90"))))
# If WS_AUTH_REQUIRED is unset: require auth only when a credential exists. This avoids a
# broken default (auth "on" but no token can ever verify) which breaks local WS connects.
_ws_auth_required_env = os.getenv("WS_AUTH_REQUIRED", "").strip()
_has_ws_credential = bool(WS_AUTH_TOKEN or WS_TOKEN_SIGNING_SECRET)
if _ws_auth_required_env:
    WS_AUTH_REQUIRED = _ws_auth_required_env.lower() in ("1", "true", "yes", "on")
else:
    WS_AUTH_REQUIRED = _has_ws_credential
_ws_allowed_origins_env = os.getenv("WS_ALLOWED_ORIGINS", "").strip()
_ws_allowed_origins_from_env = [
    origin.strip()
    for origin in (_ws_allowed_origins_env.split(",") if _ws_allowed_origins_env else [])
    if origin.strip()
]
# If WS_ALLOWED_ORIGINS is unset, default to FRONTEND_URL plus a localhost/127.0.0.1 twin when applicable.
_ws_default_origins: list[str] = [FRONTEND_URL]
try:
    from urllib.parse import urlparse

    parsed = urlparse(FRONTEND_URL)
    if parsed.hostname == "localhost" and parsed.port:
        alt = parsed._replace(netloc=f"127.0.0.1:{parsed.port}").geturl()
        if alt not in _ws_default_origins:
            _ws_default_origins.append(alt)
    elif parsed.hostname == "127.0.0.1" and parsed.port:
        alt = parsed._replace(netloc=f"localhost:{parsed.port}").geturl()
        if alt not in _ws_default_origins:
            _ws_default_origins.append(alt)
except Exception:
    pass
WS_ALLOWED_ORIGINS = _ws_allowed_origins_from_env or _ws_default_origins

# Production readiness validation. Strict mode is opt-in so local development remains smooth.
PRODUCTION_STRICT_READY = os.getenv("PRODUCTION_STRICT_READY", "false").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
# Permanent tokens are a development/test compatibility path only. Strict production
# always requires a short-lived token signed with WS_TOKEN_SIGNING_SECRET.
WS_STATIC_TOKEN_ALLOWED = (
    not PRODUCTION_STRICT_READY
    and os.getenv("WS_STATIC_TOKEN_ALLOWED", "true").strip().lower()
    in ("1", "true", "yes", "on")
)
REQUIRE_WS_AUTH_IN_PRODUCTION = os.getenv(
    "REQUIRE_WS_AUTH_IN_PRODUCTION", "true"
).strip().lower() in ("1", "true", "yes", "on")

# Performance/latency tuning
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "100"))
# Longer spoken comparison: full walkthrough of every section × every program on the card.
LLM_MAX_TOKENS_DEPARTMENT_COMPARISON = int(os.getenv("LLM_MAX_TOKENS_DEPARTMENT_COMPARISON", "900"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_STREAM_PARTIAL_DEBOUNCE_MS = int(os.getenv("LLM_STREAM_PARTIAL_DEBOUNCE_MS", "80"))
LLM_STREAM_TIMEOUT_S = float(os.getenv("LLM_STREAM_TIMEOUT_S", "8.0"))
ENABLE_LLM_STREAMING = os.getenv("ENABLE_LLM_STREAMING", "true").strip().lower() in ("1", "true", "yes", "on")
PERF_DEBUG_TIMINGS = os.getenv("PERF_DEBUG_TIMINGS", "true").strip().lower() in ("1", "true", "yes", "on")
# Conversation Intelligence Layer (Milestone 1)
try:
    INTENT_CONFIDENCE_THRESHOLD = float(os.getenv("INTENT_CONFIDENCE_THRESHOLD", "0.60"))
except ValueError:
    INTENT_CONFIDENCE_THRESHOLD = 0.60
INTENT_CONFIDENCE_THRESHOLD = max(0.0, min(1.0, INTENT_CONFIDENCE_THRESHOLD))
_conv_intel_dbg = os.getenv("CONVERSATION_INTEL_DEBUG", "").strip().lower()
if _conv_intel_dbg in ("1", "true", "yes", "on"):
    CONVERSATION_INTEL_DEBUG = True
elif _conv_intel_dbg in ("0", "false", "no", "off"):
    CONVERSATION_INTEL_DEBUG = False
else:
    # Default: follow PERF_DEBUG_TIMINGS so production can silence both together.
    CONVERSATION_INTEL_DEBUG = PERF_DEBUG_TIMINGS

# Milestone 2 — Runtime integrity / localization
_runtime_diag = os.getenv("RUNTIME_DIAGNOSTICS", "").strip().lower()
if _runtime_diag in ("1", "true", "yes", "on"):
    RUNTIME_DIAGNOSTICS = True
elif _runtime_diag in ("0", "false", "no", "off"):
    RUNTIME_DIAGNOSTICS = False
else:
    RUNTIME_DIAGNOSTICS = PERF_DEBUG_TIMINGS or CONVERSATION_INTEL_DEBUG
RUNTIME_OWNERSHIP_ENFORCE = os.getenv("RUNTIME_OWNERSHIP_ENFORCE", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
RUNTIME_STRICT_STARTUP = os.getenv("RUNTIME_STRICT_STARTUP", "false").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
try:
    RUNTIME_TIMELINE_MAX = int(os.getenv("RUNTIME_TIMELINE_MAX", "200"))
except ValueError:
    RUNTIME_TIMELINE_MAX = 200
RUNTIME_TIMELINE_MAX = max(20, min(2000, RUNTIME_TIMELINE_MAX))
LOCALIZATION_FREEZE_ENABLED = os.getenv("LOCALIZATION_FREEZE_ENABLED", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
LOCALIZATION_VERIFY_STRICT = os.getenv("LOCALIZATION_VERIFY_STRICT", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
PRESENTATION_CONTRACT_ENFORCED = os.getenv("PRESENTATION_CONTRACT_ENFORCED", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
try:
    TRANSLATION_CACHE_MAX = int(os.getenv("TRANSLATION_CACHE_MAX", "256"))
except ValueError:
    TRANSLATION_CACHE_MAX = 256
try:
    TRANSLATION_CACHE_TTL_S = float(os.getenv("TRANSLATION_CACHE_TTL_S", "900"))
except ValueError:
    TRANSLATION_CACHE_TTL_S = 900.0

RAG_CONTEXT_TIMEOUT_S = float(os.getenv("RAG_CONTEXT_TIMEOUT_S", "0.8"))
TTS_TIMEOUT_S = float(os.getenv("TTS_TIMEOUT_S", "10.0"))
STT_TIMEOUT_S = float(os.getenv("STT_TIMEOUT_S", "8.0"))
ENABLE_FIRST_SENTENCE_TTS = os.getenv("ENABLE_FIRST_SENTENCE_TTS", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
ENABLE_TTS_PIPELINING = os.getenv("ENABLE_TTS_PIPELINING", "true").strip().lower() in ("1", "true", "yes", "on")
# When enabled, never speak overlapping text spans in a single assistant turn.
ENABLE_ONCE_ONLY_TTS_SEGMENTS = os.getenv("ENABLE_ONCE_ONLY_TTS_SEGMENTS", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
# Narration segmented TTS aligned with kiosk cards / teleprompter (per-segment `segment_audio` frames).
ENABLE_NARRATION_PLAN = os.getenv("ENABLE_NARRATION_PLAN", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
try:
    NARRATION_SEGMENT_TTS_BUDGET_S = float(os.getenv("NARRATION_SEGMENT_TTS_BUDGET_S", "12.0"))
except ValueError:
    NARRATION_SEGMENT_TTS_BUDGET_S = 12.0
NARRATION_SEGMENT_TTS_BUDGET_S = max(3.0, min(120.0, NARRATION_SEGMENT_TTS_BUDGET_S))

ENABLE_ACK_EARCON = os.getenv("ENABLE_ACK_EARCON", "true").strip().lower() in ("1", "true", "yes", "on")
ENABLE_EARLY_PARTIAL_TEXT = os.getenv("ENABLE_EARLY_PARTIAL_TEXT", "true").strip().lower() in ("1", "true", "yes", "on")
LOW_LATENCY_VOICE_MODE = os.getenv("LOW_LATENCY_VOICE_MODE", "true").strip().lower() in ("1", "true", "yes", "on")
# Wait-for-all-clips before presenting. Off by default: M5.8 presents on first playable clip.
KIOSK_COMPLETE_RESPONSE_TTS = os.getenv("KIOSK_COMPLETE_RESPONSE_TTS", "false").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
# Hold THINKING until the first playable response clip is validated. Do not show text-first.
KIOSK_HOLD_THINKING_UNTIL_FIRST_AUDIO = os.getenv(
    "KIOSK_HOLD_THINKING_UNTIL_FIRST_AUDIO", "true"
).strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
FIRST_SENTENCE_TTS_MAX_CHARS = int(os.getenv("FIRST_SENTENCE_TTS_MAX_CHARS", "160"))
AUDIO_UPDATE_TIMEOUT_S = float(os.getenv("AUDIO_UPDATE_TIMEOUT_S", "3.0"))
# Short receptionist answers stay on one Sarvam call. Chunk only genuinely long replies.
try:
    TTS_SHORT_ANSWER_MAX_CHARS = int(os.getenv("TTS_SHORT_ANSWER_MAX_CHARS", "480"))
except ValueError:
    TTS_SHORT_ANSWER_MAX_CHARS = 480
TTS_SHORT_ANSWER_MAX_CHARS = max(0, min(4000, TTS_SHORT_ANSWER_MAX_CHARS))
try:
    TTS_CHUNK_MAX_ATTEMPTS = int(os.getenv("TTS_CHUNK_MAX_ATTEMPTS", "2"))
except ValueError:
    TTS_CHUNK_MAX_ATTEMPTS = 2
TTS_CHUNK_MAX_ATTEMPTS = max(1, min(4, TTS_CHUNK_MAX_ATTEMPTS))
# Chunked low-latency TTS: per-chapter budgets (full reply is never generated in one blocking call).
TTS_CHUNK_MAX_CHARS = int(os.getenv("TTS_CHUNK_MAX_CHARS", "220"))
TTS_CHUNK_MAX_CHARS_NARRATOR = int(os.getenv("TTS_CHUNK_MAX_CHARS_NARRATOR", "260"))
TTS_CHUNK_MAX_CHARS_COMPARISON = int(os.getenv("TTS_CHUNK_MAX_CHARS_COMPARISON", "340"))
TTS_CHUNK_FIRST_TIMEOUT_S = float(os.getenv("TTS_CHUNK_FIRST_TIMEOUT_S", "10.0"))
TTS_CHUNK_TIMEOUT_S = float(os.getenv("TTS_CHUNK_TIMEOUT_S", "5.0"))
FULL_TTS_FALLBACK_TIMEOUT = float(os.getenv("FULL_TTS_FALLBACK_TIMEOUT", "20.0"))

# Shared HTTP client configuration
HTTP_TIMEOUT_CONNECT_S = float(os.getenv("HTTP_TIMEOUT_CONNECT_S", "2.0"))
HTTP_TIMEOUT_READ_S = float(os.getenv("HTTP_TIMEOUT_READ_S", "15.0"))
HTTP_TIMEOUT_WRITE_S = float(os.getenv("HTTP_TIMEOUT_WRITE_S", "15.0"))
HTTP_TIMEOUT_POOL_S = float(os.getenv("HTTP_TIMEOUT_POOL_S", "2.0"))
HTTP_MAX_KEEPALIVE_CONNECTIONS = int(os.getenv("HTTP_MAX_KEEPALIVE_CONNECTIONS", "20"))
HTTP_MAX_CONNECTIONS = int(os.getenv("HTTP_MAX_CONNECTIONS", "50"))
HTTP_KEEPALIVE_EXPIRY_S = float(os.getenv("HTTP_KEEPALIVE_EXPIRY_S", "30.0"))
HTTP_RETRY_ATTEMPTS = int(os.getenv("HTTP_RETRY_ATTEMPTS", "1"))

# Language Code Mappings (for TTS target_language_code)
TARGET_LANGUAGE_CODES = {
    "en": "en-IN",
    "hi": "hi-IN",
    "kn": "kn-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "ml": "ml-IN",
}

# Frontend language display name -> config key (for TARGET_LANGUAGE_CODES)
LANGUAGE_NAME_TO_CODE_KEY = {
    "English": "en",
    "Kannada": "kn",
    "Hindi": "hi",
    "Tamil": "ta",
    "Telugu": "te",
    "Malayalam": "ml",
}
