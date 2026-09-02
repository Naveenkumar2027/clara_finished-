"""M5.10 Phase 2D — universal unit selection, six-language triggers, person follow-up."""

from __future__ import annotations

import unittest

from backend.services.content.campus_units import CAMPUS_UNIT_IDS, SAMPLE_STATUS
from backend.services.content.content_unit_registry import all_unit_descriptors, get_unit_descriptor
from backend.services.content.content_unit_resolver import resolve_unit
from backend.services.content.surface_narration_mapper import map_content_units_to_segments
from backend.services.content.unit_narration import narrate_unit
from backend.services.content.unit_selector import resolve_units_for_plan, select_content_units
from backend.services.content.semantic_request_parser import parse_semantic_request
from backend.services.conversation.response_decision import ResponseMode
from backend.tests.test_m59_universal_units import decide, plan_units

LANGS = ("en", "kn", "hi", "ta", "te", "ml")
FORBIDDEN_TTS = (
    "showing the",
    "here is the card",
    "this card contains",
    "this sample card",
    "here is the cse department",
)


class TestPhase2DRegistryForensics(unittest.TestCase):
    def test_every_registered_unit_resolves_and_narrates_in_six_languages(self) -> None:
        ids = [d.unit_id for d in all_unit_descriptors()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 89)
        for desc in all_unit_descriptors():
            self.assertIsNotNone(get_unit_descriptor(desc.unit_id))
            for lang in LANGS:
                with self.subTest(uid=desc.unit_id, lang=lang):
                    unit = resolve_unit(unit_id=desc.unit_id, language=lang, language_code=lang)
                    self.assertIsNotNone(unit)
                    assert unit is not None
                    self.assertEqual(unit.language_code, lang)
                    segs = map_content_units_to_segments((unit,), lang_key=lang)
                    self.assertEqual(len(segs), 1)
                    spoken = (segs[0].tts_text or "").strip()
                    self.assertTrue(spoken)
                    lowered = spoken.lower()
                    for banned in FORBIDDEN_TTS:
                        self.assertNotIn(banned, lowered)
                    self.assertEqual(segs[0].unit_id, desc.unit_id)

    def test_campus_sample_metadata_is_never_exposed(self) -> None:
        for uid in CAMPUS_UNIT_IDS:
            unit = resolve_unit(unit_id=uid, language="en", language_code="en")
            assert unit is not None
            self.assertNotIn(SAMPLE_STATUS, unit.body)
            self.assertIn("officially confirmed", unit.body)


class TestPhase2DCombinations(unittest.TestCase):
    CASES = (
        ("Show me CSE Data Science and CSE AIML.", ("cse_ds.overview", "cse_aiml.overview")),
        (
            "Who is the HOD of CSE Data Science and who is the principal?",
            ("cse_ds.hod", "leadership.principal"),
        ),
        ("Tell me about the principal and trustees.", ("leadership.principal", "leadership.trustees")),
        ("Tell me about girls hostel rooms and fees", ("hostel.girls.rooms", "hostel.girls.fees")),
        ("Tell me about boys hostel safety and canteen hygiene", ("hostel.boys.safety", "canteen.hygiene")),
        ("Tell me about the canteen and TechVidya", ("canteen.overview", "events.techvidya")),
        (
            "CSE overview and girls hostel rooms and Sanchalana",
            ("cse.overview", "hostel.girls.rooms", "events.sanchalana"),
        ),
        (
            "Show me CSE Data Science HOD, overview and placements",
            ("cse_ds.hod", "cse_ds.overview", "cse_ds.placements"),
        ),
        (
            "Tell me about the principal, trustees and Sanchalana",
            ("leadership.principal", "leadership.trustees", "events.sanchalana"),
        ),
        (
            "Tell me about girls hostel rooms, boys hostel fees, canteen timings, Sanchalana and TechVidya",
            (
                "hostel.girls.rooms",
                "hostel.boys.fees",
                "canteen.timings",
                "events.sanchalana",
                "events.techvidya",
            ),
        ),
    )

    def test_n_independent_units(self) -> None:
        for raw, expected in self.CASES:
            with self.subTest(raw=raw):
                self.assertEqual(plan_units(raw), expected)
                self.assertIs(decide(raw), ResponseMode.CARD)

    def test_hod_is_not_duplicated_into_overview(self) -> None:
        self.assertEqual(plan_units("Who is the HOD of CSE Data Science?"), ("cse_ds.hod",))
        self.assertEqual(plan_units("CSE overview"), ("cse.overview",))

    def test_overview_word_does_not_broadcast_onto_hostel(self) -> None:
        self.assertEqual(
            plan_units("CSE overview and girls hostel rooms"),
            ("cse.overview", "hostel.girls.rooms"),
        )


class TestPhase2DSixLanguageTriggers(unittest.TestCase):
    CASES = (
        ("en", "Tell me about the girls hostel rooms", ("hostel.girls.rooms",)),
        ("kn", "ಹುಡುಗಿಯರ ಹಾಸ್ಟೆಲ್ ಕೊಠಡಿ", ("hostel.girls.rooms",)),
        ("hi", "लड़कियों के हॉस्टल के कमरे", ("hostel.girls.rooms",)),
        ("ta", "கேண்டீன் சுகாதாரம்", ("canteen.hygiene",)),
        ("te", "కాంటీన్ పరిశుభ్రత", ("canteen.hygiene",)),
        ("ml", "കാന്റീൻ ശുചിത്വം", ("canteen.hygiene",)),
        ("en", "Girls hostel rooms hegive?", ("hostel.girls.rooms",)),
        ("kn", "CSE Data Science fees eshtu", ("cse_ds.fees",)),
        ("hi", "AIML का HOD कौन है", ("cse_aiml.hod",)),
        ("hi", "सीएसई फीस", ("cse.fees",)),
        ("kn", "ಡೇಟಾ ಸೈನ್ಸ್ ಪ್ಲೇಸ್‌ಮೆಂಟ್", ("cse_ds.placements",)),
        ("kn", "canteen hygiene hegive", ("canteen.hygiene",)),
        ("ta", "Sanchalana patri sollu", ("events.sanchalana",)),
        ("te", "TechVidya gurinchi cheppu", ("events.techvidya",)),
        ("ml", "principal aaranu", ("leadership.principal",)),
        ("en", "CSE Data Science ke HOD kaun hain?", ("cse_ds.hod",)),
    )

    def test_realistic_and_mixed_language_queries(self) -> None:
        for lang, raw, expected in self.CASES:
            with self.subTest(lang=lang, raw=raw):
                self.assertEqual(plan_units(raw, lang), expected)

    def test_tamil_canteen_does_not_steal_dean(self) -> None:
        self.assertEqual(plan_units("கேண்டீன் சுகாதாரம்", "ta"), ("canteen.hygiene",))


class TestPhase2DLanguagePersistence(unittest.TestCase):
    def test_switching_units_keeps_session_language(self) -> None:
        req = parse_semantic_request(
            raw_text="Tell me about girls hostel rooms, canteen hygiene and TechVidya",
            language_code_key="kn",
        )
        plan = select_content_units(req)
        assert plan is not None
        units = resolve_units_for_plan(plan)
        self.assertEqual([u.unit_id for u in units], list(plan.units))
        self.assertTrue(all(u.language_code == "kn" for u in units))
        segs = map_content_units_to_segments(units, lang_key="kn")
        self.assertEqual([s.unit_id for s in segs], list(plan.units))
        spoken = [(s.tts_text or "") for s in segs]
        self.assertTrue(all(SAMPLE_STATUS not in text for text in spoken))
        self.assertTrue(all("ಅಧಿಕೃತವಾಗಿ ದೃಢೀಕರಿಸಲಾಗಿಲ್ಲ" in text for text in spoken))
        for text in spoken:
            self.assertTrue(any(ord(ch) > 127 for ch in text))
            self.assertNotIn("This sample card", text)


class TestPhase2DPersonFollowup(unittest.TestCase):
    def test_his_experience_stays_on_hod_unit(self) -> None:
        self.assertEqual(
            plan_units(
                "What about his experience?",
                ci_entities={"last_person_unit_id": "cse_ds.hod"},
            ),
            ("cse_ds.hod",),
        )

    def test_hod_without_anaphora_still_fail_closed(self) -> None:
        self.assertIsNone(
            plan_units("Who is the HOD?", ci_entities={"last_person_unit_id": "cse_ds.hod"})
        )

    def test_person_followup_does_not_become_overview(self) -> None:
        units = plan_units(
            "What about her experience?",
            ci_entities={"last_person_unit_id": "cse_ds.hod"},
        )
        self.assertEqual(units, ("cse_ds.hod",))
        self.assertNotIn("cse_ds.overview", units or ())


class TestPhase2DGuestNameNarration(unittest.TestCase):
    def test_name_is_sparse_and_not_a_greeting(self) -> None:
        unit = resolve_unit(unit_id="hostel.girls.rooms", language="en", language_code="en")
        assert unit is not None
        spoken = narrate_unit(unit, "en", guest_name="Naveen")
        self.assertIn("Naveen", spoken)
        self.assertFalse(spoken.startswith("Naveen"))
        self.assertFalse(spoken.lower().startswith("hello"))
        self.assertNotIn("Showing", spoken)
        self.assertNotIn("Naveen", unit.title)
        self.assertNotIn("Naveen", unit.body)

    def test_short_hod_fact_does_not_force_the_name(self) -> None:
        unit = resolve_unit(unit_id="cse_ds.hod", language="en", language_code="en")
        assert unit is not None
        spoken = narrate_unit(unit, "en", guest_name="Naveen")
        self.assertNotIn("Naveen", spoken)
        self.assertIn("Nagashree", spoken)

    def test_name_used_once_across_n_units(self) -> None:
        rooms = resolve_unit(unit_id="hostel.girls.rooms", language="en", language_code="en")
        hygiene = resolve_unit(unit_id="canteen.hygiene", language="en", language_code="en")
        event = resolve_unit(unit_id="events.techvidya", language="en", language_code="en")
        segs = map_content_units_to_segments(
            (rooms, hygiene, event),
            lang_key="en",
            guest_name="Naveen",
        )
        named = [s.tts_text for s in segs if s.tts_text and "Naveen" in s.tts_text]
        self.assertEqual(len(named), 1)
        self.assertEqual([s.unit_id for s in segs], [
            "hostel.girls.rooms",
            "canteen.hygiene",
            "events.techvidya",
        ])


if __name__ == "__main__":
    unittest.main()
