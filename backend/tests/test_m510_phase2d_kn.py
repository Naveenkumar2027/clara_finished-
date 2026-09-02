"""M5.10 Phase 2D-KN — Kannada first-class language pipeline."""

from __future__ import annotations

import unittest

from backend.services.answer_generation import (
    CONTROLLED_FALLBACK_KN,
    build_receptionist_answer_system_prompt,
    get_off_topic_reply,
    get_profile_direct_reply,
    get_unavailable_reply,
    process_fallback_reply,
    INTENT_HOD_PROFILE,
)
from backend.services.content.content_unit_resolver import resolve_unit
from backend.services.content.semantic_request_parser import parse_semantic_request
from backend.services.content.semantic_vocab.kannada_terms import CANONICAL_KN, FORBIDDEN_KN_ALIASES
from backend.services.content.surface_narration_mapper import map_content_units_to_segments
from backend.services.content.unit_narration import narrate_unit
from backend.services.content.unit_selector import resolve_units_for_plan, select_content_units
from backend.services.conversation.answer_language import resolve_answer_language
from backend.services.conversation.policy_router import route_policy
from backend.services.conversation.response_decision import ResponseMode, resolve_response_decision
from backend.services.conversation.templates import (
    clarification_reply,
    greeting_reply,
    name_ack_reply,
    unknown_reply,
)
from backend.services.conversation.transcript_validator import assess_transcript
from backend.services.conversation.types import ExtractedEntities, IntentResult, PolicyAction
from backend.services.ui_localization import ui_text
from backend.tests.test_m59_universal_units import decide, plan_units


def kn_decision(raw: str):
    request = parse_semantic_request(raw_text=raw, language_code_key="kn")
    return resolve_response_decision(
        text=raw,
        semantic_request=request,
        ci_intent=None,
        has_department_entity=bool(request and request.entities),
        faq_matched=False,
        local_intent=None,
        validated_proposal=None,
    )


def _latin_sentences(text: str) -> list[str]:
    out = []
    for part in (text or "").replace("!", ".").replace("?", ".").split("."):
        s = part.strip()
        if s and all(ord(ch) < 128 for ch in s if not ch.isspace()):
            if any(ch.isalpha() for ch in s):
                out.append(s)
    return out


class TestKannadaCardTriggers(unittest.TestCase):
    def test_native_cse_hod(self) -> None:
        self.assertEqual(
            plan_units("ಸಿಎಸ್ಇ ವಿಭಾಗದ ಮುಖ್ಯಸ್ಥರು ಯಾರು?", "kn"),
            ("cse.hod",),
        )
        self.assertIs(decide("ಸಿಎಸ್ಇ ವಿಭಾಗದ ಮುಖ್ಯಸ್ಥರು ಯಾರು?", "kn"), ResponseMode.CARD)

    def test_browser_stt_spaced_acronym_and_phonetic_hod(self) -> None:
        self.assertEqual(
            plan_units("ಸಿ ಎಸ್ ಇ ಡಿಪಾರ್ಟ್ಮೆಂಟ್ ಹೋಡ್ ಯಾರು ಅಂಡ್ ಫೀಸ್", "kn"),
            ("cse.hod", "cse.fees"),
        )

    def test_hod_variant_does_not_turn_overview_into_hod(self) -> None:
        self.assertEqual(plan_units("CSE department overview", "en"), ("cse.overview",))

    def test_mixed_cse_ds_hod(self) -> None:
        self.assertEqual(
            plan_units("CSE Data Science HOD ಯಾರು?", "kn"),
            ("cse_ds.hod",),
        )

    def test_kannada_stt_data_science_hod_minister_confusions(self) -> None:
        self.assertEqual(plan_units("ಡೇಟಾ ಸೈನ್ಸ್ ಸಚಿವರು ಯಾರು", "kn"), ("cse_ds.hod",))
        self.assertEqual(plan_units("ಡೇಟಾ ಸಂಖ್ಯೆ ಸಚಿವರು ಯಾರು", "kn"), ("cse_ds.hod",))

    def test_principal_not_vp(self) -> None:
        self.assertEqual(plan_units("ಪ್ರಾಂಶುಪಾಲರು ಯಾರು", "kn"), ("leadership.principal",))

    def test_vp_does_not_collapse_to_principal(self) -> None:
        self.assertEqual(plan_units("ಉಪ ಪ್ರಾಂಶುಪಾಲರು ಯಾರು", "kn"), ("leadership.vice_principal",))

    def test_trustees(self) -> None:
        self.assertEqual(plan_units("ಟ್ರಸ್ಟಿಗಳು", "kn"), ("leadership.trustees",))

    def test_fees_data_science(self) -> None:
        self.assertEqual(plan_units("ಡೇಟಾ ಸೈನ್ಸ್ ಶುಲ್ಕ", "kn"), ("cse_ds.fees",))

    def test_girls_hostel_rooms(self) -> None:
        self.assertEqual(plan_units("ಹುಡುಗಿಯರ ಹಾಸ್ಟೆಲ್ ಕೊಠಡಿಗಳು", "kn"), ("hostel.girls.rooms",))

    def test_canteen(self) -> None:
        self.assertEqual(plan_units("ಕ್ಯಾಂಟೀನ್", "kn"), ("canteen.overview",))

    def test_event(self) -> None:
        self.assertEqual(plan_units("ಸಂಚಲನ", "kn"), ("events.sanchalana",))

    def test_multi_unit_independent(self) -> None:
        self.assertEqual(
            plan_units(
                "ಹುಡುಗಿಯರ ಹಾಸ್ಟೆಲ್ ಕೊಠಡಿಗಳು ಮತ್ತು ಕ್ಯಾಂಟೀನ್ ಸ್ವಚ್ಛತೆ ಹಾಗೂ ಟೆಕ್‌ವಿದ್ಯಾ ಬಗ್ಗೆ ತೋರಿಸಿ",
                "kn",
            ),
            ("hostel.girls.rooms", "canteen.hygiene", "events.techvidya"),
        )


class TestKannadaAnswerAndConversation(unittest.TestCase):
    def test_department_list_is_answer(self) -> None:
        self.assertIs(decide("ಕಾಲೇಜಿನಲ್ಲಿ ಯಾವ ವಿಭಾಗಗಳಿವೆ?", "kn"), ResponseMode.ANSWER)

    def test_answer_language_is_kannada(self) -> None:
        key, name, _tts = resolve_answer_language(
            "ಕಾಲೇಜಿನಲ್ಲಿ ಯಾವ ವಿಭಾಗಗಳಿವೆ?",
            {"language_code_key": "kn", "language_name": "Kannada"},
        )
        self.assertEqual(key, "kn")
        self.assertEqual(name, "Kannada")

    def test_receptionist_prompt_requires_kannada(self) -> None:
        prompt = build_receptionist_answer_system_prompt(
            "Kannada",
            get_unavailable_reply("Kannada"),
            get_off_topic_reply("Kannada"),
        )
        self.assertIn("Reply in Kannada", prompt)
        self.assertIn("ಅವರು", prompt)
        self.assertNotIn("Reply in English only", prompt)

    def test_greeting_namaskara(self) -> None:
        assessment = assess_transcript("ನಮಸ್ಕಾರ")
        decision = route_policy(
            assessment=assessment,
            entities=ExtractedEntities(),
            semantic_topic=None,
            intent_result=IntentResult(intent="NORMAL_QUERY", confidence=0.4, matched_source="none"),
            language="Kannada",
        )
        self.assertEqual(decision.action, PolicyAction.GREETING)
        self.assertEqual("ಸ್ವಾಗತ. ಇಂದು ನಿಮಗೆ ಯಾವ ಮಾಹಿತಿ ಬೇಕು?", greeting_reply("Kannada"))

    def test_hostel_clarification(self) -> None:
        d = kn_decision("ಹಾಸ್ಟೆಲ್")
        self.assertIs(d.mode, ResponseMode.CLARIFY)
        self.assertEqual(d.clarification_target, "hostel")
        text = clarification_reply("Kannada", "hostel")
        self.assertIn("ಹುಡುಗಿಯರ ಹಾಸ್ಟೆಲ್", text)
        self.assertIn("ಹುಡುಗರ ಹಾಸ್ಟೆಲ್", text)
        self.assertFalse(_latin_sentences(text))

    def test_fallback_and_error_are_kannada(self) -> None:
        # Exact wording is governed by the separately approved ui.error.backend
        # golden; an older draft required an added apology that contradicts it.
        self.assertEqual(process_fallback_reply("Kannada"), ui_text("kn", "error.backend"))
        self.assertEqual(get_unavailable_reply("Kannada"), CONTROLLED_FALLBACK_KN)
        self.assertFalse(_latin_sentences(get_unavailable_reply("Kannada").replace("SVIT", "")))
        self.assertIn("ವಿಭಾಗ", get_off_topic_reply("Kannada"))
        self.assertIn("ವಿಶ್ವಾಸಾರ್ಹ", unknown_reply("Kannada"))

    def test_name_ack_inserts_guest(self) -> None:
        text = name_ack_reply("Kannada", "Naveen")
        self.assertIn("Naveen", text)
        self.assertTrue(any(ord(ch) > 127 for ch in text))


class TestKannadaPersonFollowup(unittest.TestCase):
    def test_avaru_experience_keeps_hod(self) -> None:
        self.assertEqual(
            plan_units(
                "ಅವರ ಅನುಭವ ಎಷ್ಟು?",
                "kn",
                ci_entities={"last_person_unit_id": "cse.hod"},
            ),
            ("cse.hod",),
        )

    def test_experience_without_person_does_not_invent(self) -> None:
        self.assertIsNone(plan_units("ಅವರ ಅನುಭವ ಎಷ್ಟು?", "kn"))


class TestKannadaNarrationAndLocale(unittest.TestCase):
    def test_hod_honorific_and_guest_not_forced(self) -> None:
        unit = resolve_unit(unit_id="cse_ds.hod", language="kn", language_code="kn")
        assert unit is not None
        spoken = narrate_unit(unit, "kn", guest_name="Naveen")
        self.assertIn("ಮುಖ್ಯಸ್ಥರು", spoken)
        self.assertIn("ಅವರು", spoken)
        self.assertNotIn("Naveen", spoken)
        self.assertNotIn("The Head of", spoken)

    def test_principal_honorific(self) -> None:
        unit = resolve_unit(unit_id="leadership.principal", language="kn", language_code="kn")
        assert unit is not None
        spoken = narrate_unit(unit, "kn")
        self.assertIn("ಪ್ರಾಂಶುಪಾಲರು", spoken)
        self.assertIn("ಅವರು", spoken)

    def test_campus_guest_name_does_not_lowercase_kannada(self) -> None:
        unit = resolve_unit(unit_id="hostel.girls.rooms", language="kn", language_code="kn")
        assert unit is not None
        spoken = narrate_unit(unit, "kn", guest_name="Naveen")
        self.assertIn("Naveen", spoken)
        self.assertFalse(spoken.startswith("Naveen"))
        self.assertNotIn("this sample card", spoken.lower())

    def test_multi_card_sequence_stays_kannada(self) -> None:
        req = parse_semantic_request(
            raw_text="ಹುಡುಗಿಯರ ಹಾಸ್ಟೆಲ್ ಕೊಠಡಿಗಳು ಮತ್ತು ಕ್ಯಾಂಟೀನ್ ಸ್ವಚ್ಛತೆ ಹಾಗೂ ಟೆಕ್‌ವಿದ್ಯಾ ಬಗ್ಗೆ ತೋರಿಸಿ",
            language_code_key="kn",
        )
        plan = select_content_units(req)
        assert plan is not None
        units = resolve_units_for_plan(plan)
        self.assertEqual([u.language_code for u in units], ["kn", "kn", "kn"])
        segs = map_content_units_to_segments(units, lang_key="kn", guest_name="Naveen")
        self.assertEqual([s.unit_id for s in segs], list(plan.units))
        self.assertEqual(len(segs), 3)
        named = [s.tts_text or "" for s in segs if "Naveen" in (s.tts_text or "")]
        self.assertLessEqual(len(named), 1)
        for seg in segs:
            text = seg.tts_text or ""
            self.assertTrue(any(ord(ch) > 127 for ch in text))
            self.assertNotIn("Name:", text)
            self.assertNotIn("This sample card", text)

    def test_profile_direct_reply_is_sentence_not_label_dump(self) -> None:
        text = get_profile_direct_reply(INTENT_HOD_PROFILE, "Kannada") or ""
        self.assertIn("ಮುಖ್ಯಸ್ಥರು", text)
        self.assertNotIn("HOD ಹೆಸರು:", text)

    def test_canonical_terms_present(self) -> None:
        spoken = " ".join(
            [
                greeting_reply("Kannada"),
                clarification_reply("Kannada", "hostel"),
                get_off_topic_reply("Kannada"),
            ]
        )
        self.assertIn(CANONICAL_KN["hostel"], spoken)
        self.assertIn(CANONICAL_KN["department"], get_off_topic_reply("Kannada"))
        for alias in FORBIDDEN_KN_ALIASES["hod"]:
            self.assertNotIn(alias, spoken)


class TestKannadaEnglishUntouched(unittest.TestCase):
    def test_english_hod_still_cards(self) -> None:
        self.assertEqual(
            plan_units("Who is the HOD of CSE Data Science?"),
            ("cse_ds.hod",),
        )

    def test_english_greeting_unchanged(self) -> None:
        self.assertEqual(greeting_reply("English"), "Hello. How may I help you today?")

    def test_english_fallback_unchanged(self) -> None:
        self.assertEqual(
            process_fallback_reply("English"),
            "I'm sorry, I couldn't process your request right now.",
        )


if __name__ == "__main__":
    unittest.main()
