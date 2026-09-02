"""M5.2 clean cutover — unit-backed path gates, TTS contract, no hidden expansion."""

from __future__ import annotations

import unittest

from backend.services.answer_generation import (
    INTENT_DEPARTMENT_COMPARISON,
    INTENT_DEPARTMENT_FEES,
    INTENT_DEPARTMENT_OVERVIEW,
    INTENT_HOD_PROFILE,
    INTENT_PLACEMENTS,
)
from backend.services.content.surface_narration_mapper import map_content_units_to_segments
from backend.services.content.types import SURFACE_DEPARTMENT_OVERVIEW
from backend.services.content.unit_selector import resolve_units_for_plan, select_content_units
from backend.services.content.semantic_request_parser import parse_semantic_request
from backend.services.conversation.types import PolicyAction, PolicyDecision
from backend.services.narration_plan import NarrationSegment, finalize_segment_list
from backend.services.orchestration.narration_resolver import resolve_narration
from backend.services.orchestration.presentation_resolver import resolve_presentation
from backend.services.orchestration.types import ConversationResolution, PresentationMode


_SIBLINGS = (
    "cse.overview",
    "cse.hod",
    "cse.achievements",
    "cse.placements",
    "cse.fees",
)


def _card_resolution(*, intent: str, dept: str = "CSE") -> ConversationResolution:
    return ConversationResolution(
        language="English",
        language_code_key="en",
        tts_code="en-IN",
        intent=intent,
        show_card=SURFACE_DEPARTMENT_OVERVIEW,
        card_surface=SURFACE_DEPARTMENT_OVERVIEW,
        should_generate_presentation=True,
        presentation_mode=PresentationMode.CARD_PRESENTATION.value,
        department_label=dept,
    )


def _assert_no_hidden_expansion(unit_ids: list[str], expected: list[str]) -> None:
    assert unit_ids == expected
    unexpected = [u for u in _SIBLINGS if u not in expected]
    for u in unexpected:
        assert u not in unit_ids, f"hidden expansion leaked {u} into {unit_ids}"


class TestM52NoHiddenFiveCardExpansion(unittest.TestCase):
    def _unit_ids_via_resolver(self, *, user_text: str, intent: str) -> list[str]:
        res = _card_resolution(intent=intent)
        segs = resolve_narration(
            resolution=res,
            entities={"department": "CSE"},
            user_text=user_text,
        )
        self.assertIsNotNone(segs)
        assert segs is not None
        finalize_segment_list("cutover", segs)
        return [s.unit_id for s in segs if getattr(s, "unit_id", None)]

    def test_cse_fees_singleton(self) -> None:
        ids = self._unit_ids_via_resolver(user_text="CSE fees", intent=INTENT_DEPARTMENT_FEES)
        _assert_no_hidden_expansion(ids, ["cse.fees"])
        self.assertEqual(len(ids), 1)

    def test_cse_hod_singleton(self) -> None:
        ids = self._unit_ids_via_resolver(user_text="CSE HOD", intent=INTENT_HOD_PROFILE)
        _assert_no_hidden_expansion(ids, ["cse.hod"])
        self.assertEqual(len(ids), 1)

    def test_cse_placements_singleton(self) -> None:
        ids = self._unit_ids_via_resolver(user_text="CSE placements", intent=INTENT_PLACEMENTS)
        _assert_no_hidden_expansion(ids, ["cse.placements"])
        self.assertEqual(len(ids), 1)

    def test_cse_overview_singleton(self) -> None:
        ids = self._unit_ids_via_resolver(
            user_text="CSE overview",
            intent=INTENT_DEPARTMENT_OVERVIEW,
        )
        _assert_no_hidden_expansion(ids, ["cse.overview"])
        self.assertEqual(len(ids), 1)

    def test_tell_me_about_cse_five_units(self) -> None:
        ids = self._unit_ids_via_resolver(
            user_text="Tell me about CSE",
            intent=INTENT_DEPARTMENT_OVERVIEW,
        )
        self.assertEqual(ids, list(_SIBLINGS))
        self.assertEqual(len(ids), 5)


class TestM52MultiHodPath(unittest.TestCase):
    def test_aiml_ds_hod_two_units_shared_section(self) -> None:
        res = _card_resolution(intent=INTENT_HOD_PROFILE, dept="CSE (AI & ML)")
        segs = resolve_narration(
            resolution=res,
            entities={},
            user_text="AIML and Data Science HOD",
        )
        self.assertIsNotNone(segs)
        assert segs is not None
        finalize_segment_list("multi-hod", segs)
        unit_ids = [s.unit_id for s in segs]
        self.assertEqual(unit_ids, ["cse_aiml.hod", "cse_ds.hod"])
        self.assertEqual([s.section_id for s in segs], ["hod_voice", "hod_voice"])
        self.assertEqual(len(segs), 2)


class TestM52TtsContract(unittest.TestCase):
    def test_unit_backed_tts_is_body_only(self) -> None:
        req = parse_semantic_request(raw_text="CSE fees", language_code_key="en")
        self.assertIsNotNone(req)
        assert req is not None
        plan = select_content_units(req, surface=SURFACE_DEPARTMENT_OVERVIEW)
        self.assertIsNotNone(plan)
        assert plan is not None
        units = resolve_units_for_plan(plan)
        segs = map_content_units_to_segments(units, lang_key="en")
        self.assertEqual(len(segs), 1)
        seg = segs[0]
        title = (units[0].title or "").strip()
        body = (units[0].body or "").strip()
        spoken = (seg.tts_text or "").strip()
        self.assertTrue(title)
        self.assertIn(title, seg.display_text)
        self.assertTrue(spoken)
        self.assertNotIn(title, spoken)
        self.assertNotIn("View details", spoken)
        self.assertNotEqual(spoken, (seg.display_text or "").strip())
        # M5.9: narration planner speaks a sentence that still carries body facts.
        # It is no longer a raw body clone (a short lead is allowed).
        body_lead = body[:80].strip()
        self.assertTrue(
            body_lead in spoken or spoken in body,
            msg=f"spoken narration lost unit facts: {spoken!r}",
        )

    def test_finalize_preserves_explicit_tts(self) -> None:
        seg = NarrationSegment(
            display_text="Title\nBody spoken",
            tts_text="Body spoken",
        )
        finalize_segment_list("fin", [seg])
        self.assertEqual(seg.tts_text, "Body spoken")

    def test_finalize_legacy_derives_tts_from_display(self) -> None:
        seg = NarrationSegment(display_text="Legacy caption only")
        finalize_segment_list("fin-legacy", [seg])
        self.assertEqual(seg.tts_text, "Legacy caption only")


class TestM52PresentationOverride(unittest.TestCase):
    def _override(self, *, intent: str, user_text: str, entities: dict | None = None) -> ConversationResolution:
        res = ConversationResolution(
            language="English",
            language_code_key="en",
            tts_code="en-IN",
            department_label="CSE",
        )
        decision = PolicyDecision(
            action=PolicyAction.CARD_PRESENTATION,
            answer_source="policy",
            length_kind="normal",
        )
        semantic_request = parse_semantic_request(
            raw_text=user_text,
            language_code_key="en",
            ci_entities=entities or {"department": "CSE"},
        )
        return resolve_presentation(
            decision=decision,
            resolution=res,
            intent=intent,
            semantic_topic=None,
            entities=entities or {"department": "CSE"},
            user_text=user_text,
            semantic_request=semantic_request,
        )

    def test_fees_intent_preserves_department_fees_surface(self) -> None:
        res = self._override(intent=INTENT_DEPARTMENT_FEES, user_text="CSE fees")
        self.assertEqual(res.card_surface, "department_fees")
        self.assertEqual(res.show_card, "department_fees")

    def test_multi_hod_preserves_hod_surface(self) -> None:
        res = self._override(
            intent=INTENT_HOD_PROFILE,
            user_text="AIML and Data Science HOD",
            entities={},
        )
        self.assertEqual(res.card_surface, "hod")
        self.assertEqual(res.show_card, "hod")

    def test_representable_hod_plan_wins_over_comparison_intent(self) -> None:
        res = self._override(
            intent=INTENT_DEPARTMENT_COMPARISON,
            user_text="Who are the HODs of AIML, Data Science and CSE?",
            entities={},
        )
        self.assertEqual(res.card_surface, "hod")
        self.assertEqual(res.show_card, "hod")
        self.assertEqual(res.intent, INTENT_DEPARTMENT_COMPARISON)


if __name__ == "__main__":
    unittest.main()
