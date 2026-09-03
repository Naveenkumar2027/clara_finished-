from __future__ import annotations

import unittest

from backend.services.conversation.thinking_bridge import compose_thinking_bridge, infer_thinking_topic


class TestThinkingBridge(unittest.TestCase):
    def test_kannada_script_not_english(self) -> None:
        text = compose_thinking_bridge("ಶುಲ್ಕ ಎಷ್ಟು", "kn")
        self.assertRegex(text, r"[\u0C80-\u0CFF]")
        self.assertNotIn("Let me", text)

    def test_name_on_college_not_fees(self) -> None:
        named = compose_thinking_bridge("How good is the college?", "en", "Rahul")
        self.assertIn("Rahul", named)
        fees = compose_thinking_bridge("What is the fee?", "en", "Rahul")
        self.assertNotIn("Rahul", fees)

    def test_topics(self) -> None:
        self.assertEqual(infer_thinking_topic("Who is the HOD?"), "hod")
        self.assertEqual(infer_thinking_topic("What about the buses?"), "transport")

    def test_fallback_language(self) -> None:
        self.assertRegex(compose_thinking_bridge("", "hi"), r"[\u0900-\u097F]")
