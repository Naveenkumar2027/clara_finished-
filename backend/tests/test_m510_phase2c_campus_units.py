"""M5.10 Phase 2C — independently selectable hostel, canteen, and event units."""

from __future__ import annotations

import unittest

from backend.services.content.campus_units import CAMPUS_UNIT_IDS, SAMPLE_STATUS
from backend.services.content.content_unit_registry import all_unit_descriptors, get_unit_descriptor
from backend.services.content.content_unit_resolver import resolve_unit
from backend.services.content.surface_narration_mapper import map_content_units_to_segments
from backend.services.content.unit_selector import resolve_units_for_plan, select_content_units
from backend.services.content.semantic_request_parser import parse_semantic_request
from backend.services.conversation.response_decision import ResponseMode
from backend.tests.test_m59_universal_units import decide, plan_units

LANGS = ("en", "kn", "hi", "ta", "te", "ml")


class TestPhase2CRegistry(unittest.TestCase):
    def test_every_new_unit_is_registered(self) -> None:
        ids = {d.unit_id for d in all_unit_descriptors()}
        for uid in CAMPUS_UNIT_IDS:
            with self.subTest(uid=uid):
                self.assertIn(uid, ids)
                self.assertIsNotNone(get_unit_descriptor(uid))
        self.assertNotIn("hostel.girls", ids)
        self.assertNotIn("canteen", ids)
        self.assertNotIn("events", ids)

    def test_existing_department_and_leadership_untouched(self) -> None:
        ids = {d.unit_id for d in all_unit_descriptors()}
        self.assertIn("cse_ds.hod", ids)
        self.assertIn("leadership.principal", ids)
        self.assertIn("leadership.trustees", ids)


class TestPhase2CSelector(unittest.TestCase):
    def test_girls_rooms(self) -> None:
        self.assertEqual(plan_units("Tell me about the girls hostel rooms"), ("hostel.girls.rooms",))
        self.assertIs(decide("Tell me about the girls hostel rooms"), ResponseMode.CARD)

    def test_girls_rooms_and_fees(self) -> None:
        self.assertEqual(
            plan_units("Tell me about girls hostel rooms and fees"),
            ("hostel.girls.rooms", "hostel.girls.fees"),
        )

    def test_girls_food_and_timings(self) -> None:
        self.assertEqual(
            plan_units("How is the food in the girls hostel and what are the timings?"),
            ("hostel.girls.food", "hostel.girls.timings"),
        )

    def test_girls_food_and_canteen_hygiene(self) -> None:
        self.assertEqual(
            plan_units("How is the food in the girls hostel and canteen hygiene?"),
            ("hostel.girls.food", "canteen.hygiene"),
        )

    def test_canteen_and_event(self) -> None:
        self.assertEqual(
            plan_units("Tell me about the canteen and TechVidya"),
            ("canteen.overview", "events.techvidya"),
        )

    def test_three_unrelated_units(self) -> None:
        self.assertEqual(
            plan_units("Tell me about girls hostel safety, canteen hygiene and TechVidya"),
            ("hostel.girls.safety", "canteen.hygiene", "events.techvidya"),
        )

    def test_five_unrelated_units(self) -> None:
        self.assertEqual(
            plan_units(
                "Tell me about girls hostel rooms, boys hostel fees, canteen timings, Sanchalana and TechVidya"
            ),
            (
                "hostel.girls.rooms",
                "hostel.boys.fees",
                "canteen.timings",
                "events.sanchalana",
                "events.techvidya",
            ),
        )

    def test_events_independent(self) -> None:
        self.assertEqual(
            plan_units("Tell me about Sanchalana and TechVidya"),
            ("events.sanchalana", "events.techvidya"),
        )

    def test_no_hidden_cap(self) -> None:
        units = plan_units(
            "Tell me about girls hostel rooms, girls hostel food, girls hostel safety, "
            "canteen hygiene and TechVidya"
        )
        self.assertIsNotNone(units)
        assert units is not None
        self.assertEqual(len(units), 5)

    def test_bare_hostel_does_not_guess_gender(self) -> None:
        self.assertIsNone(plan_units("Tell me about the hostel rooms"))

    def test_department_hod_still_works(self) -> None:
        self.assertEqual(
            plan_units("Who is the HOD of CSE Data Science?"),
            ("cse_ds.hod",),
        )


class TestPhase2CLanguages(unittest.TestCase):
    CASES = (
        ("Tell me about the girls hostel rooms", "en", ("hostel.girls.rooms",)),
        ("ಹುಡುಗಿಯರ ಹಾಸ್ಟೆಲ್ ಕೊಠಡಿ", "kn", ("hostel.girls.rooms",)),
        ("लड़कियों के हॉस्टल के कमरे कैसे हैं?", "hi", ("hostel.girls.rooms",)),
        ("பெண்கள் விடுதி அறைகள் எப்படி இருக்கின்றன?", "ta", ("hostel.girls.rooms",)),
        ("బాలికల హాస్టల్ గదులు", "te", ("hostel.girls.rooms",)),
        ("പെൺകുട്ടികളുടെ ഹോസ്റ്റൽ മുറികൾ", "ml", ("hostel.girls.rooms",)),
        ("Girls hostel rooms hegive?", "en", ("hostel.girls.rooms",)),
    )

    def test_regional_queries_same_unit_ids(self) -> None:
        for raw, lang, expected in self.CASES:
            with self.subTest(lang=lang, raw=raw):
                self.assertEqual(plan_units(raw, lang), expected)


class TestPhase2CLocalizationAndNarration(unittest.TestCase):
    def test_every_sample_unit_is_blocked_from_production_copy(self) -> None:
        for lang in LANGS:
            for uid in CAMPUS_UNIT_IDS:
                with self.subTest(lang=lang, uid=uid):
                    unit = resolve_unit(unit_id=uid, language=lang, language_code=lang)
                    self.assertIsNotNone(unit)
                    assert unit is not None
                    self.assertEqual(unit.language_code, lang)
                    self.assertNotIn(SAMPLE_STATUS, unit.body)
                    if lang == "kn":
                        self.assertIn("ಅಧಿಕೃತವಾಗಿ ದೃಢೀಕರಿಸಲಾಗಿಲ್ಲ", unit.body)
                    elif lang == "hi":
                        self.assertIn("आधिकारिक पुष्टि", unit.body)
                    self.assertTrue((unit.metadata or {}).get("tts_summary"))
                    self.assertNotIn(
                        SAMPLE_STATUS,
                        str((unit.metadata or {}).get("tts_summary") or ""),
                    )

    def test_safe_narration_preserves_the_selected_unit_identity(self) -> None:
        rooms = resolve_unit(unit_id="hostel.girls.rooms", language="en", language_code="en")
        food = resolve_unit(unit_id="hostel.girls.food", language="en", language_code="en")
        assert rooms is not None and food is not None
        room_seg = map_content_units_to_segments((rooms,), lang_key="en")[0]
        food_seg = map_content_units_to_segments((food,), lang_key="en")[0]
        self.assertEqual(room_seg.unit_id, "hostel.girls.rooms")
        self.assertEqual(food_seg.unit_id, "hostel.girls.food")
        self.assertNotIn(SAMPLE_STATUS, room_seg.tts_text or "")
        self.assertNotIn(SAMPLE_STATUS, food_seg.tts_text or "")
        self.assertNotIn("Showing", room_seg.tts_text or "")

    def test_no_silent_fallback_to_another_unit(self) -> None:
        kn_rooms = resolve_unit(unit_id="hostel.girls.rooms", language="kn", language_code="kn")
        en_rooms = resolve_unit(unit_id="hostel.girls.rooms", language="en", language_code="en")
        assert kn_rooms is not None and en_rooms is not None
        self.assertNotEqual(kn_rooms.body, en_rooms.body)
        self.assertIn("ಕೊಠಡಿ", kn_rooms.title)
        boys = resolve_unit(unit_id="hostel.boys.rooms", language="en", language_code="en")
        girls = resolve_unit(unit_id="hostel.girls.rooms", language="en", language_code="en")
        assert boys is not None and girls is not None
        self.assertNotEqual(boys.title, girls.title)

    def test_switching_n_units_keeps_unit_identity(self) -> None:
        req = parse_semantic_request(
            raw_text="Tell me about girls hostel rooms, canteen hygiene and TechVidya",
            language_code_key="kn",
        )
        self.assertIsNotNone(req)
        plan = select_content_units(req)
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(
            tuple(plan.units),
            ("hostel.girls.rooms", "canteen.hygiene", "events.techvidya"),
        )
        self.assertEqual(plan.language_code, "kn")
        units = resolve_units_for_plan(plan)
        self.assertEqual(len(units), 3)
        self.assertEqual([u.unit_id for u in units], list(plan.units))
        self.assertTrue(all(u.language_code == "kn" for u in units))
        segs = map_content_units_to_segments(units, lang_key="kn")
        self.assertEqual([s.unit_id for s in segs], list(plan.units))
        # Unconfirmed Kannada sample facts retain their unit identities but
        # must all narrate the approved status message, never placeholder copy.
        self.assertTrue(all(SAMPLE_STATUS not in (s.tts_text or "") for s in segs))
        self.assertTrue(all("ಅಧಿಕೃತವಾಗಿ ದೃಢೀಕರಿಸಲಾಗಿಲ್ಲ" in (s.tts_text or "") for s in segs))


class TestPhase2CDecision(unittest.TestCase):
    def test_canteen_is_a_card(self) -> None:
        self.assertEqual(plan_units("How is the canteen?"), ("canteen.overview",))
        self.assertIs(decide("How is the canteen?"), ResponseMode.CARD)

    def test_campus_without_canteen_is_still_answer(self) -> None:
        self.assertIsNone(plan_units("Tell me about the campus."))
        self.assertIs(decide("Tell me about the campus."), ResponseMode.ANSWER)


if __name__ == "__main__":
    unittest.main()
