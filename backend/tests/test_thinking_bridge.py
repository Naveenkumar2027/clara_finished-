from __future__ import annotations

import unittest

from backend.services.content.semantic_request_parser import parse_semantic_request
from backend.services.conversation.thinking_bridge import (
    compose_thinking_bridge,
    compose_thinking_bridge_from_semantic,
    infer_thinking_topic,
)


class TestThinkingBridge(unittest.TestCase):
    def test_principal_is_not_department_head(self) -> None:
        text = compose_thinking_bridge("Who is the principal?", "en")
        self.assertIn("principal", text.lower())
        self.assertNotIn("department head", text.lower())

    def test_hod_includes_department_entity(self) -> None:
        text = compose_thinking_bridge("Who is the HOD of CSE Data Science?", "en")
        self.assertRegex(text.lower(), r"hod|department")
        self.assertRegex(text, r"Data Science|CSE")

    def test_fees_includes_data_science(self) -> None:
        text = compose_thinking_bridge("What is the fee for Data Science?", "en")
        self.assertRegex(text.lower(), r"fee")
        self.assertRegex(text, r"Data Science|CSE")

    def test_kannada_script_not_english(self) -> None:
        text = compose_thinking_bridge("ಶುಲ್ಕ ಎಷ್ಟು", "kn")
        self.assertRegex(text, r"[\u0C80-\u0CFF]")
        self.assertNotIn("Let me", text)

    def test_name_optional_on_warm_topics_not_forced_on_fees(self) -> None:
        fees = compose_thinking_bridge("What is the fee for Data Science?", "en", "Rahul")
        self.assertNotIn("Rahul", fees)
        # College-quality may fall back to generic when semantic is None; name optional.
        generic = compose_thinking_bridge("zzzz unrelated", "en", "Rahul")
        self.assertNotIn("department head", generic.lower())

    def test_semantic_object_path(self) -> None:
        req = parse_semantic_request(raw_text="Who is the principal?", language_code_key="en")
        self.assertIsNotNone(req)
        text = compose_thinking_bridge_from_semantic(req, "en")
        self.assertIn("principal", text.lower())

    def test_infer_topic_uses_semantic_principal(self) -> None:
        self.assertEqual(infer_thinking_topic("Who is the principal?"), "principal")
        self.assertEqual(infer_thinking_topic("What about the buses?"), "general")

    def test_fallback_language(self) -> None:
        self.assertRegex(compose_thinking_bridge("", "hi"), r"[\u0900-\u097F]")

    def test_session_carry_over_for_short_placements_followup(self) -> None:
        session = {"last_semantic_entities": ["cse_ds"]}
        text = compose_thinking_bridge("placements?", "en", session=session)
        self.assertRegex(text.lower(), r"placement")
        self.assertRegex(text, r"Data Science|CSE")
