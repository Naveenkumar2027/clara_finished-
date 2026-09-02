"""M5.7 complete-response TTS: hold presentation until validated speech is ready."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from backend.app import main

WAV = "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA="
LANGS = (
    ("en", "English", "en-IN"),
    ("kn", "Kannada", "kn-IN"),
    ("hi", "Hindi", "hi-IN"),
    ("ta", "Tamil", "ta-IN"),
    ("te", "Telugu", "te-IN"),
    ("ml", "Malayalam", "ml-IN"),
)


class _FakeWebSocket:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.events.append(payload)


def _session(lang_key: str = "en", lang_name: str = "English", lang_code: str = "en-IN") -> dict:
    return {
        "messages": [],
        "language_code_key": lang_key,
        "language_name": lang_name,
        "language_code": lang_code,
        "session_generation": 0,
        "wire_seq": 0,
        "ws_send_lock": asyncio.Lock(),
        "awaiting_guest_name": False,
    }


def _unwrap(events: list[dict]) -> list[dict]:
    return [e["payload"] for e in events if isinstance(e.get("payload"), dict)]


def _final_audio(payloads: list[dict]) -> dict:
    finals = [
        p
        for p in payloads
        if p.get("type") == "assistant_audio_update" and p.get("tts_streaming") is False
    ]
    if not finals:
        raise AssertionError("expected a final assistant_audio_update")
    return finals[-1]


async def _no_auto_language(*_a, **_k) -> None:
    return None


class TestM57CompleteResponseTts(unittest.IsolatedAsyncioTestCase):
    async def test_successful_chunks_skip_backup_and_omit_streaming(self) -> None:
        session = _session()
        ws = _FakeWebSocket()
        timing = main.TurnTiming()
        kinds: list[str] = []

        async def _fake_tts(text: str, language_code: str, **kwargs):
            kinds.append(str(kwargs.get("utterance_kind") or ""))
            return WAV, False

        with patch.object(main, "LOW_LATENCY_VOICE_MODE", True), patch.object(
            main, "KIOSK_COMPLETE_RESPONSE_TTS", True
        ), patch.object(main, "TTS_SHORT_ANSWER_MAX_CHARS", 0), patch.object(
            main, "ENABLE_ACK_EARCON", False
        ), patch.object(
            main, "ENABLE_EARLY_PARTIAL_TEXT", False
        ), patch.object(
            main, "maybe_auto_detect_session_language", new=AsyncMock(side_effect=_no_auto_language)
        ), patch.object(
            main,
            "_stream_groq_reply",
            new=AsyncMock(return_value=("Faculty here are supportive and experienced.", "Faculty here are supportive and experienced.")),
        ), patch.object(main, "get_relevant_context", return_value="faculty context"), patch.object(
            main,
            "split_tts_chunks",
            side_effect=lambda text, max_chars=220: (
                [text[: max(1, len(text) // 2)], text[max(1, len(text) // 2) :]] if text else []
            ),
        ), patch.object(
            main, "tts_to_base64_cached", new=AsyncMock(side_effect=_fake_tts)
        ):
            await main.process_user_text_and_reply(session, "How good are the teachers here?", ws, timing)

        payloads = _unwrap(ws.events)
        final = _final_audio(payloads)
        self.assertEqual(
            [p for p in payloads if p.get("tts_streaming") is True],
            [],
        )
        self.assertEqual(final.get("tts_audio_queue"), [WAV, WAV])
        self.assertFalse(final["audioPending"])
        self.assertFalse(final["audioUnavailable"])
        self.assertFalse(final["isProcessing"])
        self.assertNotIn("assistant_full_reply_backup", kinds)

    async def test_empty_audio_is_not_marked_ready(self) -> None:
        session = _session()
        ws = _FakeWebSocket()
        timing = main.TurnTiming()

        async def _fake_tts(*_a, **_k):
            return "", False

        with patch.object(main, "LOW_LATENCY_VOICE_MODE", True), patch.object(
            main, "KIOSK_COMPLETE_RESPONSE_TTS", True
        ), patch.object(main, "ENABLE_ACK_EARCON", False), patch.object(
            main, "ENABLE_EARLY_PARTIAL_TEXT", False
        ), patch.object(
            main, "maybe_auto_detect_session_language", new=AsyncMock(side_effect=_no_auto_language)
        ), patch.object(
            main,
            "_stream_groq_reply",
            new=AsyncMock(return_value=("Campus life is vibrant.", "Campus life is vibrant.")),
        ), patch.object(main, "get_relevant_context", return_value="campus context"), patch.object(main, "split_tts_chunks", side_effect=lambda text, max_chars=220: [text.strip() or "ok"]), patch.object(
            main, "tts_to_base64_cached", new=AsyncMock(side_effect=_fake_tts)
        ):
            await main.process_user_text_and_reply(session, "How is campus life?", ws, timing)

        final = _final_audio(_unwrap(ws.events))
        self.assertTrue(final["audioUnavailable"])
        self.assertFalse(final["audioPending"])
        self.assertTrue(final["messages"][-1]["text"])

    async def test_six_languages_receive_complete_final_audio(self) -> None:
        for lang_key, lang_name, lang_code in LANGS:
            with self.subTest(lang=lang_key):
                session = _session(lang_key, lang_name, lang_code)
                ws = _FakeWebSocket()
                timing = main.TurnTiming()
                seen_codes: list[str] = []

                async def _fake_tts(text: str, language_code: str, **kwargs):
                    seen_codes.append(language_code)
                    return WAV, False

                with patch.object(main, "LOW_LATENCY_VOICE_MODE", True), patch.object(
                    main, "KIOSK_COMPLETE_RESPONSE_TTS", True
                ), patch.object(main, "ENABLE_ACK_EARCON", False), patch.object(
                    main, "ENABLE_EARLY_PARTIAL_TEXT", False
                ), patch.object(
                    main, "maybe_auto_detect_session_language", new=AsyncMock(side_effect=_no_auto_language)
                ), patch.object(
                    main,
                    "_stream_groq_reply",
                    new=AsyncMock(return_value=("Labs are well equipped.", "Labs are well equipped.")),
                ), patch.object(main, "get_relevant_context", return_value="labs context"), patch.object(main, "split_tts_chunks", side_effect=lambda text, max_chars=220: [text.strip() or "ok"]), patch.object(
                    main, "tts_to_base64_cached", new=AsyncMock(side_effect=_fake_tts)
                ):
                    await main.process_user_text_and_reply(session, "Are there good labs?", ws, timing)

                final = _final_audio(_unwrap(ws.events))
                # Verify language metadata
                self.assertEqual(final.get("languageCodeKey"), lang_key)
                self.assertEqual(final.get("languageName"), lang_name)
                self.assertEqual(final.get("ttsCode"), lang_code)
                self.assertIn(lang_code, seen_codes)
                self.assertEqual(final.get("tts_audio_queue"), [WAV])
                self.assertFalse(final["audioUnavailable"])


if __name__ == "__main__":
    unittest.main()
