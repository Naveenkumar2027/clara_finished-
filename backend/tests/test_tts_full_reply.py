import base64
import hashlib
import io
import unittest
import wave
from unittest.mock import AsyncMock, patch

from backend.app import main


def _empty_rag_context(*_args, **_kwargs) -> str:
    return ""


class _FakeWebSocket:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.events.append(payload)


class TestTtsFullReply(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _silent_wav_base64(duration_s: float = 2.2, sample_rate: int = 16000) -> str:
        frames = int(duration_s * sample_rate)
        pcm = b"\x00\x00" * frames
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    async def test_first_sentence_and_remainder_are_non_overlapping(self) -> None:
        session = {"messages": []}
        ws = _FakeWebSocket()
        timing = main.TurnTiming()
        full_reply = (
            "Our library is open from 8 AM to 8 PM on weekdays. "
            "On Saturdays it is open from 9 AM to 5 PM."
        )
        first_sentence = "Our library is open from 8 AM to 8 PM on weekdays."
        tts_calls: list[dict] = []
        fake_first_audio = self._silent_wav_base64(duration_s=1.0)
        fake_remaining_audio = self._silent_wav_base64(duration_s=1.2)

        async def _fake_tts(text: str, language_code: str, **kwargs):
            tts_calls.append({"text": text, "language_code": language_code, **kwargs})
            kind = kwargs.get("utterance_kind")
            if kind == "assistant_first_sentence":
                return fake_first_audio, False
            if kind == "assistant_remaining_reply":
                return fake_remaining_audio, False
            return self._silent_wav_base64(duration_s=0.5), False

        with patch.object(main, "LOW_LATENCY_VOICE_MODE", False), patch.object(
            main, "FORCE_FINAL_TTS_ONLY", False
        ), patch.object(main, "ENABLE_FIRST_SENTENCE_TTS", True), patch.object(
            main, "ENABLE_TTS_PIPELINING", False
        ), patch.object(
            main, "ENABLE_ONCE_ONLY_TTS_SEGMENTS", True
        ), patch.object(
            main, "maybe_auto_detect_session_language", new=AsyncMock(return_value=None)
        ), patch.object(
            main, "get_relevant_context", new=_empty_rag_context
        ), patch.object(
            main, "_load_svit_json_context", new=lambda _k: ""
        ), patch.object(
            main, "_load_answer_locale_evidence", new=lambda _k: ""
        ), patch.object(
            main, "_stream_groq_reply", new=AsyncMock(return_value=(full_reply, first_sentence))
        ), patch.object(
            main, "tts_to_base64_cached", new=AsyncMock(side_effect=_fake_tts)
        ), patch.object(
            main, "_log_turn_metrics", new=lambda *args, **kwargs: None
        ):
            await main.process_user_text_and_reply(session, "What are library timings?", ws, timing, stt_meta=None)

        self.assertEqual(len(tts_calls), 2, "TTS should be called for first sentence and remainder only")
        self.assertEqual(tts_calls[0]["text"], first_sentence)
        self.assertEqual(tts_calls[0].get("utterance_kind"), "assistant_first_sentence")
        self.assertEqual(tts_calls[1]["text"], "On Saturdays it is open from 9 AM to 5 PM.")
        self.assertEqual(tts_calls[1].get("utterance_kind"), "assistant_remaining_reply")

        payloads = [e.get("payload", {}) for e in ws.events if isinstance(e, dict)]
        first_payloads = [p for p in payloads if p.get("type") == "assistant_first_sentence_audio"]
        self.assertEqual(len(first_payloads), 1)
        self.assertEqual(first_payloads[0].get("audioBase64"), fake_first_audio)
        self.assertEqual(first_payloads[0].get("utterance_kind"), "assistant_first_sentence")
        self.assertEqual(first_payloads[0].get("segment_index"), 0)
        final_payload = payloads[-1]
        self.assertEqual(final_payload.get("audioBase64"), fake_remaining_audio)
        self.assertEqual(final_payload.get("utterance_kind"), "assistant_remaining_reply")
        self.assertEqual(final_payload.get("segment_index"), 1)
        self.assertTrue(final_payload.get("is_final_segment"))
        self.assertEqual(final_payload.get("assistantText"), full_reply)
        self.assertEqual(final_payload.get("spokenText"), "On Saturdays it is open from 9 AM to 5 PM.")
        self.assertFalse(final_payload.get("audioUnavailable"))
        self.assertEqual(final_payload.get("messages", [])[-1].get("text"), full_reply)
        play_ms = timing.summary_ms().get("play_ms")
        self.assertIsNotNone(play_ms)

    async def test_single_sentence_reply_emits_single_final_segment(self) -> None:
        session = {"messages": []}
        ws = _FakeWebSocket()
        timing = main.TurnTiming()
        full_reply = "Admissions are currently open."
        tts_calls: list[dict] = []
        fake_audio = self._silent_wav_base64(duration_s=1.0)

        async def _fake_tts(text: str, language_code: str, **kwargs):
            tts_calls.append({"text": text, "language_code": language_code, **kwargs})
            return fake_audio, False

        with patch.object(main, "LOW_LATENCY_VOICE_MODE", False), patch.object(
            main, "FORCE_FINAL_TTS_ONLY", False
        ), patch.object(main, "ENABLE_FIRST_SENTENCE_TTS", True), patch.object(
            main, "ENABLE_TTS_PIPELINING", False
        ), patch.object(
            main, "ENABLE_ONCE_ONLY_TTS_SEGMENTS", True
        ), patch.object(
            main, "maybe_auto_detect_session_language", new=AsyncMock(return_value=None)
        ), patch.object(
            main, "get_relevant_context", new=_empty_rag_context
        ), patch.object(
            main, "_load_svit_json_context", new=lambda _k: ""
        ), patch.object(
            main, "_load_answer_locale_evidence", new=lambda _k: ""
        ), patch.object(
            main, "_stream_groq_reply", new=AsyncMock(return_value=(full_reply, full_reply))
        ), patch.object(
            main, "tts_to_base64_cached", new=AsyncMock(side_effect=_fake_tts)
        ), patch.object(
            main, "_log_turn_metrics", new=lambda *args, **kwargs: None
        ):
            await main.process_user_text_and_reply(
                session, "Is SVIT a private college?", ws, timing, stt_meta=None
            )

        self.assertEqual(len(tts_calls), 1)
        self.assertEqual(tts_calls[0].get("utterance_kind"), "assistant_full_reply")
        final_payload = [e.get("payload", {}) for e in ws.events][-1]
        self.assertEqual(final_payload.get("segment_index"), 0)
        self.assertTrue(final_payload.get("is_final_segment"))
        assistant_text = final_payload.get("assistantText")
        self.assertEqual(assistant_text, final_payload.get("messages", [])[-1].get("text"))
        self.assertEqual(final_payload.get("spokenText"), assistant_text)
        self.assertFalse(final_payload.get("audioUnavailable"))

    async def test_cache_hit_path_still_segments_without_overlap(self) -> None:
        session = {"messages": []}
        ws = _FakeWebSocket()
        timing = main.TurnTiming()
        user_text = "Tell me library timings."
        full_reply = (
            "Our library is open from 8 AM to 8 PM on weekdays. "
            "On Saturdays it is open from 9 AM to 5 PM."
        )
        context_sig = hashlib.sha256(b"").hexdigest()[:12]
        cache_key = (
            f"v2-direct|{main.INTENT_NORMAL_QUERY}|en|"
            f"{main._normalized_cache_text(user_text)}|{context_sig}"
        )
        main.LLM_REPLY_CACHE.set(cache_key, full_reply)
        tts_calls: list[dict] = []

        async def _fake_tts(text: str, language_code: str, **kwargs):
            tts_calls.append({"text": text, "language_code": language_code, **kwargs})
            return self._silent_wav_base64(duration_s=0.8), False

        with patch.object(main, "LOW_LATENCY_VOICE_MODE", False), patch.object(
            main, "FORCE_FINAL_TTS_ONLY", False
        ), patch.object(main, "ENABLE_FIRST_SENTENCE_TTS", True), patch.object(
            main, "ENABLE_TTS_PIPELINING", False
        ), patch.object(
            main, "ENABLE_ONCE_ONLY_TTS_SEGMENTS", True
        ), patch.object(
            main, "maybe_auto_detect_session_language", new=AsyncMock(return_value=None)
        ), patch.object(
            main, "get_relevant_context", new=_empty_rag_context
        ), patch.object(
            main, "_load_svit_json_context", new=lambda _k: ""
        ), patch.object(
            main, "_load_answer_locale_evidence", new=lambda _k: ""
        ), patch.object(
            main, "_stream_groq_reply", new=AsyncMock(return_value=("", ""))
        ), patch.object(
            main, "tts_to_base64_cached", new=AsyncMock(side_effect=_fake_tts)
        ), patch.object(
            main, "_log_turn_metrics", new=lambda *args, **kwargs: None
        ):
            await main.process_user_text_and_reply(session, user_text, ws, timing, stt_meta=None)

        self.assertEqual([c.get("utterance_kind") for c in tts_calls], ["assistant_first_sentence", "assistant_remaining_reply"])


if __name__ == "__main__":
    unittest.main()
