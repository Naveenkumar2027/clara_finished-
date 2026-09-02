"""M5.3 — typed WS narration_plan unitIds follow SemanticRequest (no M5.2 mock)."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from backend.app import main
from backend.services.content.semantic_request_parser import parse_semantic_request
from backend.services.content.unit_selector import select_content_units


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


def _unit_ids(plan: dict | None) -> list[str]:
    if not isinstance(plan, dict):
        return []
    out: list[str] = []
    for s in plan.get("segments") or []:
        if isinstance(s, dict) and isinstance(s.get("unitId"), str) and s["unitId"].strip():
            out.append(s["unitId"].strip())
    return out


async def _no_auto_language(*_a, **_k) -> None:
    return None


async def _empty_rag(*_a, **_k):
    return "", "none"


class TestM53WsUnitIdParity(unittest.IsolatedAsyncioTestCase):
    async def _run_card_turn(self, user_text: str, *, lang_key: str = "en") -> list[str]:
        names = {
            "en": ("English", "en-IN"),
            "kn": ("Kannada", "kn-IN"),
            "hi": ("Hindi", "hi-IN"),
            "ta": ("Tamil", "ta-IN"),
            "te": ("Telugu", "te-IN"),
            "ml": ("Malayalam", "ml-IN"),
        }
        lang_name, lang_code = names[lang_key]
        session = _session(lang_key, lang_name, lang_code)
        ws = _FakeWebSocket()
        timing = main.TurnTiming()
        fake_audio = "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA="

        async def _fake_tts(text: str, language_code: str, **kwargs):
            return fake_audio, False

        with patch.object(main, "LOW_LATENCY_VOICE_MODE", True), patch.object(
            main, "ENABLE_ACK_EARCON", False
        ), patch.object(main, "ENABLE_EARLY_PARTIAL_TEXT", False), patch.object(
            main, "ENABLE_FIRST_SENTENCE_TTS", False
        ), patch.object(main, "FORCE_FINAL_TTS_ONLY", False), patch.object(
            main, "maybe_auto_detect_session_language", new=AsyncMock(side_effect=_no_auto_language)
        ), patch.object(main, "get_relevant_context", new=AsyncMock(side_effect=_empty_rag)), patch.object(
            main, "_load_svit_json_context", new=lambda _k: ""
        ), patch.object(main, "tts_to_base64_cached", new=AsyncMock(side_effect=_fake_tts)), patch.object(
            main, "_log_turn_metrics", new=lambda *a, **k: None
        ):
            await main.process_user_text_and_reply(session, user_text, ws, timing)

        payloads = _unwrap(ws.events)
        audio_frames = [
            p
            for p in payloads
            if p.get("type") == "assistant_audio_update"
            and (p.get("tts_streaming") is True or p.get("tts_streaming") is False)
        ]
        if not audio_frames:
            return []
        streaming = [p for p in audio_frames if p.get("tts_streaming") is True]
        carrier = streaming[0] if streaming else audio_frames[-1]
        return _unit_ids(carrier.get("narration_plan") if isinstance(carrier.get("narration_plan"), dict) else None)

    async def _run_card_turn_plan(self, user_text: str, *, lang_key: str = "en") -> dict:
        names = {
            "en": ("English", "en-IN"),
            "kn": ("Kannada", "kn-IN"),
        }
        lang_name, lang_code = names[lang_key]
        session = _session(lang_key, lang_name, lang_code)
        ws = _FakeWebSocket()
        timing = main.TurnTiming()
        fake_audio = "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA="

        async def _fake_tts(text: str, language_code: str, **kwargs):
            return fake_audio, False

        with patch.object(main, "LOW_LATENCY_VOICE_MODE", True), patch.object(
            main, "ENABLE_ACK_EARCON", False
        ), patch.object(main, "ENABLE_EARLY_PARTIAL_TEXT", False), patch.object(
            main, "ENABLE_FIRST_SENTENCE_TTS", False
        ), patch.object(main, "FORCE_FINAL_TTS_ONLY", False), patch.object(
            main, "maybe_auto_detect_session_language", new=AsyncMock(side_effect=_no_auto_language)
        ), patch.object(main, "get_relevant_context", new=AsyncMock(side_effect=_empty_rag)), patch.object(
            main, "_load_svit_json_context", new=lambda _k: ""
        ), patch.object(main, "tts_to_base64_cached", new=AsyncMock(side_effect=_fake_tts)), patch.object(
            main, "_log_turn_metrics", new=lambda *a, **k: None
        ):
            await main.process_user_text_and_reply(session, user_text, ws, timing)

        payloads = _unwrap(ws.events)
        audio_frames = [
            p
            for p in payloads
            if p.get("type") == "assistant_audio_update"
            and (p.get("tts_streaming") is True or p.get("tts_streaming") is False)
        ]
        if not audio_frames:
            return {}
        streaming = [p for p in audio_frames if p.get("tts_streaming") is True]
        carrier = streaming[0] if streaming else audio_frames[-1]
        plan = carrier.get("narration_plan")
        return plan if isinstance(plan, dict) else {}

    def _expected_units(self, raw: str, lang: str) -> list[str]:
        req = parse_semantic_request(raw_text=raw, language_code_key=lang)
        self.assertIsNotNone(req)
        assert req is not None
        plan = select_content_units(req)
        self.assertIsNotNone(plan)
        assert plan is not None
        return list(plan.units)

    async def test_cse_data_science_hod_ws_matches_ir(self) -> None:
        raw = "Who is the HOD of CSE Data Science?"
        expected = self._expected_units(raw, "en")
        self.assertEqual(expected, ["cse_ds.hod"])
        ws_ids = await self._run_card_turn(raw, lang_key="en")
        self.assertEqual(ws_ids, expected)

    async def test_multi_hod_ws_order(self) -> None:
        raw = "Who is the HOD of AIML and Data Science?"
        expected = self._expected_units(raw, "en")
        self.assertEqual(expected, ["cse_aiml.hod", "cse_ds.hod"])
        ws_ids = await self._run_card_turn(raw, lang_key="en")
        self.assertEqual(ws_ids, expected)

    async def test_kannada_native_fees_ws(self) -> None:
        raw = "CSE ಶುಲ್ಕ"
        expected = self._expected_units(raw, "kn")
        self.assertEqual(expected, ["cse.fees"])
        ws_ids = await self._run_card_turn(raw, lang_key="kn")
        self.assertEqual(ws_ids, expected)

    async def test_three_hod_ws_order(self) -> None:
        raw = "Who are the HODs of AIML, Data Science and CSE?"
        expected = self._expected_units(raw, "en")
        self.assertEqual(expected, ["cse_aiml.hod", "cse_ds.hod", "cse.hod"])
        ws_ids = await self._run_card_turn(raw, lang_key="en")
        self.assertEqual(ws_ids, expected)

    async def test_kannada_ds_hod_ws(self) -> None:
        raw = "CSE Data Science HOD yaaru?"
        expected = self._expected_units(raw, "kn")
        self.assertEqual(expected, ["cse_ds.hod"])
        ws_ids = await self._run_card_turn(raw, lang_key="kn")
        self.assertEqual(ws_ids, expected)

    async def test_kannada_two_hod_ws_order(self) -> None:
        raw = "AIML mattu Data Science HOD yaaru?"
        expected = self._expected_units(raw, "kn")
        self.assertEqual(expected, ["cse_aiml.hod", "cse_ds.hod"])
        ws_ids = await self._run_card_turn(raw, lang_key="kn")
        self.assertEqual(ws_ids, expected)

    async def test_kannada_three_hod_ws_order(self) -> None:
        raw = "AIML, Data Science mattu CSE HOD yaaru?"
        expected = self._expected_units(raw, "kn")
        self.assertEqual(expected, ["cse_aiml.hod", "cse_ds.hod", "cse.hod"])
        ws_ids = await self._run_card_turn(raw, lang_key="kn")
        self.assertEqual(ws_ids, expected)

    async def test_first_clip_matches_first_hod_unit(self) -> None:
        raw = "Who are the HODs of AIML, Data Science and CSE?"
        plan = await self._run_card_turn_plan(raw, lang_key="en")
        segs = [s for s in (plan.get("segments") or []) if isinstance(s, dict)]
        self.assertGreaterEqual(len(segs), 3)
        self.assertEqual(segs[0].get("unitId"), "cse_aiml.hod")
        self.assertTrue(str(segs[0].get("ttsText") or "").strip())
        self.assertEqual(segs[1].get("unitId"), "cse_ds.hod")
        self.assertEqual(segs[2].get("unitId"), "cse.hod")
        self.assertEqual({s.get("sectionId") for s in segs[:3]}, {"hod_voice"})
        self.assertEqual(
            [s.get("canonicalCardId") for s in segs[:3]],
            ["hod_profile", "hod_profile", "hod_profile"],
        )
        self.assertEqual(plan.get("language"), "en")
        self.assertEqual(plan.get("activeIndex"), 0)
        self.assertEqual(
            plan.get("cards"),
            [
                {"cardId": "hod_profile", "departmentId": "cse_aiml", "unitId": "cse_aiml.hod"},
                {"cardId": "hod_profile", "departmentId": "cse_ds", "unitId": "cse_ds.hod"},
                {"cardId": "hod_profile", "departmentId": "cse", "unitId": "cse.hod"},
            ],
        )
        self.assertNotEqual(segs[0].get("ttsText"), segs[1].get("ttsText"))
        self.assertNotEqual(segs[1].get("ttsText"), segs[2].get("ttsText"))

    async def test_mixed_kannada_card_contract_is_canonical_and_localized(self) -> None:
        plan = await self._run_card_turn_plan("data science hod ಯಾರು?", lang_key="kn")
        self.assertEqual(plan.get("language"), "kn")
        self.assertEqual(plan.get("activeIndex"), 0)
        self.assertEqual(
            plan.get("cards"),
            [{"cardId": "hod_profile", "departmentId": "cse_ds", "unitId": "cse_ds.hod"}],
        )
        segments = [s for s in plan.get("segments") or [] if isinstance(s, dict)]
        self.assertTrue(segments)
        self.assertEqual(segments[0].get("canonicalCardId"), "hod_profile")
        self.assertRegex(str(segments[0].get("displayText") or ""), r"[\u0C80-\u0CFF]")
        self.assertRegex(str(segments[0].get("ttsText") or ""), r"[\u0C80-\u0CFF]")

    async def test_explicit_mixed_composition_ws_order(self) -> None:
        raw = "Data Science overview, AIML HOD and CSE fees"
        expected = self._expected_units(raw, "en")
        self.assertEqual(expected, ["cse_ds.overview", "cse_aiml.hod", "cse.fees"])
        ws_ids = await self._run_card_turn(raw, lang_key="en")
        self.assertEqual(ws_ids, expected)

    async def test_fail_closed_ws_has_no_unit_ids(self) -> None:
        # Unbindable: two departments with no topic could mean two decks or a
        # comparison. Nothing may be guessed onto the wire.
        ws_ids = await self._run_card_turn("tell me about CSE and AIML", lang_key="en")
        self.assertEqual(ws_ids, [])
