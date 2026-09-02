"""Campus navigation: WebSocket handling for spoken walking directions (TTS)."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Awaitable, Callable, Tuple

from backend.config.settings import LANGUAGE_NAME_TO_CODE_KEY, TARGET_LANGUAGE_CODES

logger = logging.getLogger(__name__)

CAMPUS_NAVIGATION_TTS_ACTION = "campus_navigation_tts"
_VALID_LANGUAGES = frozenset(LANGUAGE_NAME_TO_CODE_KEY.keys())

TtsToBase64Cached = Callable[..., Awaitable[Tuple[str | None, bool]]]


async def handle_campus_navigation_tts(
    msg: dict[str, Any],
    session: dict[str, Any],
    *,
    tts_to_base64_cached: TtsToBase64Cached,
) -> dict[str, Any]:
    """Build state-5 payload with Sarvam TTS audio for campus direction readout."""
    text = (msg.get("text") or "").strip()
    language = msg.get("language") or session.get("language_name") or "English"
    if language not in _VALID_LANGUAGES:
        language = "English"
    code_key = LANGUAGE_NAME_TO_CODE_KEY[language]
    lang_code = TARGET_LANGUAGE_CODES[code_key]
    turn_id = (msg.get("turn_id") or f"campus-nav-{uuid.uuid4().hex[:12]}").strip()
    audio_b64: str | None = None
    try:
        audio_b64, _ = await tts_to_base64_cached(
            text,
            lang_code,
            turn_id=turn_id,
            utterance_kind=CAMPUS_NAVIGATION_TTS_ACTION,
        )
    except Exception as exc:
        logger.exception("Campus navigation TTS failed: %s", exc)
    payload: dict[str, Any] = {
        "type": CAMPUS_NAVIGATION_TTS_ACTION,
        "isSpeaking": bool(audio_b64),
        "isProcessing": False,
        "turn_id": turn_id,
        "utterance_kind": CAMPUS_NAVIGATION_TTS_ACTION,
        "languageName": language,
        "languageCodeKey": code_key,
        "ttsCode": lang_code,
    }
    if audio_b64:
        payload["audioBase64"] = audio_b64
    else:
        payload["error"] = "Could not generate campus navigation audio."
    return payload
