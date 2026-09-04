from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from backend.app import main
from backend.tests.test_low_latency_response import (
    ANSWER_REPLY,
    _FakeWebSocket,
    _low_latency_test_session,
    _no_auto_language,
    _partition_tts_chunks,
    _unwrap_payloads,
)


class ThinkingInterludeWsTests(unittest.IsolatedAsyncioTestCase):
    async def test_thinking_interlude_is_emitted_before_answer(self) -> None:
        session = _low_latency_test_session()
        session["guest_name"] = "Rahul"
        ws = _FakeWebSocket()
        timing = main.TurnTiming()
        fake_audio = "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA="

        async def _fake_tts(text: str, language_code: str, **kwargs):
            return fake_audio, False

        with patch.object(main, "LOW_LATENCY_VOICE_MODE", True), patch.object(
            main, "KIOSK_COMPLETE_RESPONSE_TTS", True
        ), patch.object(main, "ENABLE_ACK_EARCON", True), patch.object(
            main, "ENABLE_EARLY_PARTIAL_TEXT", False
        ), patch.object(
            main, "maybe_auto_detect_session_language", new=AsyncMock(side_effect=_no_auto_language)
        ), patch.object(
            main,
            "_stream_groq_reply",
            new=AsyncMock(return_value=(ANSWER_REPLY, ANSWER_REPLY)),
        ), patch.object(main, "get_relevant_context", return_value="faculty context"), patch.object(
            main, "split_tts_chunks", side_effect=_partition_tts_chunks
        ), patch.object(main, "tts_to_base64_cached", new=AsyncMock(side_effect=_fake_tts)):
            await main.process_user_text_and_reply(session, "Who is the principal?", ws, timing)
            task = session.get("_thinking_tts_task")
            if task is not None:
                await task

        payloads = _unwrap_payloads(ws.events)
        types = [p.get("type") for p in payloads]
        self.assertIn("thinking_interlude", types)
        interlude = next(p for p in payloads if p.get("type") == "thinking_interlude")
        thinking_text = (interlude.get("thinking_text") or "").lower()
        self.assertIn("principal", thinking_text)
        self.assertNotIn("department head", thinking_text)
        self.assertEqual(interlude.get("language_code_key"), "en")
        self.assertEqual(types[0], "thinking_interlude")
        self.assertIn("thinking_audio", types)
        # Thinking turns must not emit ACK (prevents first-word clip race).
        self.assertNotIn("assistant_ack_audio", types)
