"""M5.8 TTS orchestrator: short-answer economy, ordered long answers, six languages."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from backend.app import main
from backend.services.tts_orchestrator import (
    PLAN_ANSWER_LONG,
    PLAN_ANSWER_SHORT,
    PLAN_CARD,
    needs_full_reply_backup,
    plan_response_tts,
)

WAV = "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA="
LANGS = (
    ("en", "English", "en-IN", "Faculty here are supportive and experienced."),
    ("kn", "Kannada", "kn-IN", "ಇಲ್ಲಿನ ಅಧ್ಯಾಪಕರು ಬೆಂಬಲ ನೀಡುತ್ತಾರೆ."),
    ("hi", "Hindi", "hi-IN", "यहाँ के शिक्षक सहायक और अनुभवी हैं।"),
    ("ta", "Tamil", "ta-IN", "இங்கே ஆசிரியர்கள் ஆதரவாக இருக்காங்க."),
    ("te", "Telugu", "te-IN", "ఇక్కడ ఉపాధ్యాయులు సహాయకారులు."),
    ("ml", "Malayalam", "ml-IN", "ഇവിടുത്തെ അധ്യാപകർ പിന്തുണ നൽകുന്നു."),
)
MIXED = (
    "teachers hegiddare?",
    "CSE Data Science fee eshtu?",
    "AIML HOD yaaru?",
    "teachers kaise hain?",
    "CSE Data Science fee evlo?",
)
LONG_ANSWER = (
    "Yes, SVIT has several technical clubs and students can participate in hackathons, coding nights and open project labs. "
    "The campus also hosts project exhibitions every semester so every department can show student work to industry guests. "
    "Faculty mentors help students prepare for competitions, internships and campus placement interviews throughout the year. "
    "You can join a club during orientation week or later through the student council desk and the department coordinators. "
    "There are also cultural clubs, sports teams and community outreach groups if you want a balanced campus life besides academics. "
    "Ask me about a specific club, department or event and I will share the current details from the college information we have."
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


def _streaming(payloads: list[dict]) -> list[dict]:
    return [p for p in payloads if p.get("type") == "assistant_audio_update" and p.get("tts_streaming") is True]


def _final(payloads: list[dict]) -> dict:
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


class TestTtsOrchestratorPlanner(unittest.TestCase):
    def test_short_english_is_one_segment(self) -> None:
        plan = plan_response_tts(
            source_text="Yes, SVIT has several technical clubs and students can participate.",
            short_answer_max_chars=480,
            chunk_max_chars=220,
        )
        self.assertEqual(plan.mode, PLAN_ANSWER_SHORT)
        self.assertEqual(plan.clip_count, 1)

    def test_six_language_short_answers_are_one_segment(self) -> None:
        for _key, _name, _code, text in LANGS:
            with self.subTest(text=text[:20]):
                plan = plan_response_tts(source_text=text, short_answer_max_chars=480)
                self.assertEqual(plan.mode, PLAN_ANSWER_SHORT)
                self.assertEqual(plan.segments, [text])

    def test_long_answer_is_ordered_sentence_segments(self) -> None:
        plan = plan_response_tts(
            source_text=LONG_ANSWER,
            short_answer_max_chars=480,
            chunk_max_chars=220,
        )
        self.assertEqual(plan.mode, PLAN_ANSWER_LONG)
        self.assertGreaterEqual(plan.clip_count, 2)
        self.assertTrue("".join(plan.segments).replace(" ", "").startswith(LONG_ANSWER[:40].replace(" ", "")))

    def test_card_plan_preserves_n_units(self) -> None:
        cards = [f"clip-{i}" for i in range(5)]
        plan = plan_response_tts(source_text="ignored", card_segments=cards)
        self.assertEqual(plan.mode, PLAN_CARD)
        self.assertEqual(plan.segments, cards)

    def test_backup_only_when_zero_successful_clips(self) -> None:
        self.assertFalse(needs_full_reply_backup(used_bundle_plan=False, successful_clip_count=1))
        self.assertFalse(needs_full_reply_backup(used_bundle_plan=True, successful_clip_count=0))
        self.assertTrue(needs_full_reply_backup(used_bundle_plan=False, successful_clip_count=0))


class TestM58ResponseTts(unittest.IsolatedAsyncioTestCase):
    async def _run_answer(
        self,
        *,
        reply: str,
        user_text: str = "How good are the teachers here?",
        lang: tuple[str, str, str] = ("en", "English", "en-IN"),
        complete: bool = False,
        hold: bool = True,
        short_max: int = 480,
        tts_side_effect=None,
    ) -> tuple[list[dict], list[dict]]:
        session = _session(*lang)
        ws = _FakeWebSocket()
        timing = main.TurnTiming()
        calls: list[dict] = []

        async def _fake_tts(text: str, language_code: str, **kwargs):
            rec = {"text": text, "language_code": language_code, **kwargs}
            calls.append(rec)
            if tts_side_effect is not None:
                return await tts_side_effect(text, language_code, **kwargs)
            return WAV, False

        with patch.object(main, "LOW_LATENCY_VOICE_MODE", True), patch.object(
            main, "KIOSK_COMPLETE_RESPONSE_TTS", complete
        ), patch.object(main, "KIOSK_HOLD_THINKING_UNTIL_FIRST_AUDIO", hold), patch.object(
            main, "TTS_SHORT_ANSWER_MAX_CHARS", short_max
        ), patch.object(main, "ENABLE_ACK_EARCON", False), patch.object(
            main, "ENABLE_EARLY_PARTIAL_TEXT", False
        ), patch.object(
            main, "maybe_auto_detect_session_language", new=AsyncMock(side_effect=_no_auto_language)
        ), patch.object(
            main, "_stream_groq_reply", new=AsyncMock(return_value=(reply, reply))
        ), patch.object(main, "get_faq_answer_for_question", return_value=None), patch.object(
            main, "get_relevant_context", return_value="faculty context"
        ), patch.object(
            main, "govern_answer_length", side_effect=lambda text, kind="normal": text
        ), patch.object(
            main, "tts_to_base64_cached", new=AsyncMock(side_effect=_fake_tts)
        ):
            await main.process_user_text_and_reply(session, user_text, ws, timing)
            task = session.get("_thinking_tts_task")
            if task is not None:
                await task
        return _unwrap(ws.events), calls

    async def test_short_answer_is_one_tts_request_per_language(self) -> None:
        for lang_key, lang_name, lang_code, reply in LANGS:
            with self.subTest(lang=lang_key):
                payloads, calls = await self._run_answer(
                    reply=reply,
                    lang=(lang_key, lang_name, lang_code),
                )
                chunk_calls = [c for c in calls if str(c.get("utterance_kind", "")).endswith("_chunk_0")]
                self.assertEqual(len(chunk_calls), 1, calls)
                self.assertEqual(chunk_calls[0]["language_code"], lang_code)
                self.assertNotIn("assistant_full_reply_backup", [c.get("utterance_kind") for c in calls])
                streams = _streaming(payloads)
                self.assertGreaterEqual(len(streams), 1)
                self.assertEqual(streams[0].get("tts_expected_clip_count"), 1)
                self.assertEqual(streams[0].get("tts_plan_mode"), PLAN_ANSWER_SHORT)
                self.assertFalse(any(p.get("audioPending") is True and p.get("isProcessing") is False for p in payloads))
                metrics = _final(payloads).get("tts_metrics") or {}
                self.assertEqual(metrics.get("tts_chunks_per_turn"), 1)

    async def test_mixed_language_queries_keep_session_tts_code(self) -> None:
        for query in MIXED:
            with self.subTest(query=query):
                payloads, calls = await self._run_answer(
                    reply="Faculty here are supportive and experienced.",
                    user_text=query,
                    lang=("kn", "Kannada", "kn-IN"),
                )
                self.assertTrue(calls)
                answer_calls = [c for c in calls if c.get("utterance_kind") != "thinking_bridge"]
                self.assertTrue(answer_calls)
                self.assertEqual(answer_calls[0]["language_code"], "kn-IN")
                self.assertTrue(_final(payloads)["messages"][-1]["text"])

    async def test_long_answer_streams_first_clip_before_later_clips(self) -> None:
        order: list[int] = []

        async def _fake(text: str, language_code: str, **kwargs):
            kind = str(kwargs.get("utterance_kind") or "")
            if kind.endswith("_chunk_0"):
                order.append(0)
            elif kind.endswith("_chunk_1"):
                order.append(1)
            elif kind.endswith("_chunk_2"):
                order.append(2)
            return WAV, False

        payloads, calls = await self._run_answer(
            reply=LONG_ANSWER,
            user_text="Tell me everything about student clubs and campus life at SVIT in detail.",
            short_max=120,
            tts_side_effect=_fake,
        )
        streams = _streaming(payloads)
        self.assertGreaterEqual(
            len(streams),
            2,
            msg=f"kinds={[c.get('utterance_kind') for c in calls]} lens={[len(c.get('text') or '') for c in calls]}",
        )
        self.assertEqual(streams[0].get("tts_chunk_index"), 0)
        self.assertEqual(streams[0].get("tts_plan_mode"), PLAN_ANSWER_LONG)
        self.assertTrue(streams[0].get("messages"))
        self.assertFalse(streams[0].get("isProcessing"))
        self.assertFalse(any(p.get("audioPending") is True and "audioBase64" not in p for p in payloads if p.get("type") == "assistant_audio_update"))
        chunk_kinds = [c.get("utterance_kind") for c in calls if "chunk_" in str(c.get("utterance_kind"))]
        self.assertGreaterEqual(len(chunk_kinds), 2)
        self.assertEqual(order[0], 0)
        self.assertNotIn("assistant_full_reply_backup", [c.get("utterance_kind") for c in calls])

    async def test_partial_failure_does_not_regenerate_successful_clips(self) -> None:
        async def _fake(text: str, language_code: str, **kwargs):
            kind = str(kwargs.get("utterance_kind") or "")
            if kind.endswith("_chunk_1"):
                return None, False
            if kind == "assistant_full_reply_backup":
                raise AssertionError("backup should not run when primary already has audio")
            return WAV, False

        payloads, calls = await self._run_answer(
            reply=LONG_ANSWER,
            short_max=120,
            tts_side_effect=_fake,
        )
        kinds = [c.get("utterance_kind") for c in calls]
        self.assertNotIn("assistant_full_reply_backup", kinds)
        final = _final(payloads)
        self.assertFalse(final["audioUnavailable"])
        self.assertGreaterEqual(len(final.get("tts_audio_queue") or []), 1)

    async def test_total_failure_releases_thinking_and_commits_text(self) -> None:
        async def _fake(*_a, **_k):
            return None, False

        payloads, _calls = await self._run_answer(
            reply="Campus life is vibrant.",
            tts_side_effect=_fake,
        )
        final = _final(payloads)
        self.assertTrue(final["audioUnavailable"])
        self.assertFalse(final["audioPending"])
        self.assertFalse(final["isProcessing"])
        self.assertTrue(final["messages"][-1]["text"])

    async def test_hold_thinking_skips_premature_visible_payload(self) -> None:
        payloads, _calls = await self._run_answer(reply="Campus life is vibrant.")
        premature = [
            p
            for p in payloads
            if p.get("audioPending") is True and p.get("isProcessing") is False and not p.get("audioBase64")
        ]
        self.assertEqual(premature, [])
        streams = _streaming(payloads)
        self.assertTrue(streams)
        self.assertTrue(streams[0].get("messages"))


if __name__ == "__main__":
    unittest.main()
