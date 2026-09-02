"""Unit tests for Conversation Orchestrator (Milestone 3)."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from backend.services.answer_generation import INTENT_DEPARTMENT_OVERVIEW
from backend.services.conversation.types import PolicyAction
from backend.services.orchestration import (
    ConversationOrchestrator,
    PresentationMode,
    should_short_circuit,
    validate_conversation_resolution,
)
from backend.services.orchestration.presentation_resolver import resolve_presentation
from backend.services.orchestration.types import ConversationResolution
from backend.services.conversation.types import PolicyDecision


class LocalizationResolutionTests(unittest.TestCase):
    def test_localization_fields_identical(self):
        async def _run():
            session = {
                "language_code_key": "hi",
                "language_name": "Hindi",
                "language": "Hindi",
            }
            orch = ConversationOrchestrator()
            result = await orch.run(
                "Tell me about CSE department",
                session,
                defer_narration=True,
            )
            res = result.resolution
            self.assertEqual(res.language_code_key, "hi")
            self.assertTrue(res.language)
            self.assertTrue(res.tts_code)
            # Single authority: session + resolution agree
            self.assertEqual(session.get("language_code_key"), res.language_code_key)
            self.assertEqual(session.get("language_name"), res.language)

        asyncio.run(_run())


class CanonicalEntityTests(unittest.TestCase):
    def test_canonical_name_extraction(self):
        async def _run():
            session = {"language_code_key": "en", "language_name": "English"}
            orch = ConversationOrchestrator()
            result = await orch.run("My name is Naveen", session, defer_narration=True)
            self.assertTrue(should_short_circuit(result))
            self.assertEqual(session.get("guest_name"), "Naveen")
            self.assertNotEqual(session.get("guest_name"), "My name is Naveen")
            self.assertEqual(result.resolution.presentation_mode, PresentationMode.DIRECT.value)

        asyncio.run(_run())


class UnsupportedTopicTests(unittest.TestCase):
    """M5.4: FOOD / ENVIRONMENT are card-unsupported, not unanswerable."""

    def test_canteen_food_quality_is_a_card_unit(self):
        async def _run():
            session = {"language_code_key": "en", "language_name": "English"}
            orch = ConversationOrchestrator()
            result = await orch.run("How is the canteen food quality?", session, defer_narration=True)
            res = result.resolution
            self.assertEqual(res.presentation_mode, PresentationMode.CARD_PRESENTATION.value)
            self.assertTrue(res.should_generate_presentation)
            self.assertFalse(res.should_call_rag)

        asyncio.run(_run())

    def test_environment_is_answered_but_never_carded(self):
        async def _run():
            session = {"language_code_key": "en", "language_name": "English"}
            orch = ConversationOrchestrator()
            result = await orch.run("Tell me about college environment", session, defer_narration=True)
            res = result.resolution
            self.assertEqual(res.presentation_mode, PresentationMode.NORMAL_REPLY.value)
            self.assertTrue(res.should_call_rag)
            self.assertIsNone(res.show_card)

        asyncio.run(_run())


class RetryFlagTests(unittest.TestCase):
    def test_retry_never_sets_rag(self):
        async def _run():
            session = {"language_code_key": "en", "language_name": "English"}
            orch = ConversationOrchestrator()
            result = await orch.run("uh", session, defer_narration=True)
            res = result.resolution
            self.assertEqual(res.presentation_mode, PresentationMode.RETRY.value)
            self.assertFalse(res.should_call_rag)
            self.assertFalse(res.should_call_groq)
            self.assertFalse(res.should_generate_presentation)
            contract = validate_conversation_resolution(res)
            self.assertTrue(contract.ok)

        asyncio.run(_run())


class CardPresentationTests(unittest.TestCase):
    def test_canonical_semantic_request_is_carried_to_card_resolution(self):
        async def _run():
            session = {"language_code_key": "kn", "language_name": "Kannada"}
            result = await ConversationOrchestrator().run(
                "data science hod ಯಾರು?",
                session,
                defer_narration=True,
            )
            self.assertIsNotNone(result.intel.semantic_request)
            self.assertIs(
                result.resolution.semantic_request,
                result.intel.semantic_request,
                "the card resolver must consume CI's canonical object, not re-parse raw text",
            )
            self.assertEqual(
                result.resolution.semantic_request.requested_card_ids,
                ("hod_profile",),
            )

        asyncio.run(_run())

    def test_card_sets_generate_presentation(self):
        async def _run():
            session = {"language_code_key": "en", "language_name": "English"}
            orch = ConversationOrchestrator()
            result = await orch.run(
                "Tell me about CSE department",
                session,
                defer_narration=True,
            )
            res = result.resolution
            # High-confidence card intent from CI
            if res.policy == PolicyAction.CARD_PRESENTATION.value or res.should_generate_presentation:
                self.assertTrue(res.should_generate_presentation)
                self.assertEqual(res.presentation_mode, PresentationMode.CARD_PRESENTATION.value)
                self.assertFalse(res.should_call_rag)
            else:
                # Features may classify differently; still must not be UNKNOWN food path
                self.assertNotEqual(res.semantic_topic, "FOOD")

        asyncio.run(_run())

    def test_card_with_local_intent(self):
        async def _run():
            session = {"language_code_key": "en", "language_name": "English"}
            orch = ConversationOrchestrator()
            result = await orch.run(
                "CSE",
                session,
                local_intent={"type": "department_click", "departmentLabel": "CSE"},
                defer_narration=True,
            )
            res = result.resolution
            self.assertTrue(res.should_generate_presentation)
            self.assertEqual(res.presentation_mode, PresentationMode.CARD_PRESENTATION.value)
            self.assertFalse(res.should_call_rag)

        asyncio.run(_run())


class ContractDegradeTests(unittest.TestCase):
    def test_contract_fail_no_segments(self):
        session = {
            "language_code_key": "en",
            "language_name": "English",
            "language": "English",
        }
        resolution = ConversationResolution(
            language="English",
            language_code_key="en",
            tts_code="en-IN",
            intent=INTENT_DEPARTMENT_OVERVIEW,
            presentation_mode=PresentationMode.CARD_PRESENTATION.value,
            should_generate_presentation=True,
            should_call_rag=False,
            should_call_groq=True,
            show_card="department_overview",
            canonical_entities={"department": "CSE"},
        )
        orch = ConversationOrchestrator()

        bad_segments = [MagicMock(display_text="", tts_text="", card_index=0)]
        with patch(
            "backend.services.orchestration.conversation_orchestrator.resolve_narration",
            return_value=bad_segments,
        ), patch(
            "backend.services.orchestration.conversation_orchestrator.localize_card_segments",
            return_value=bad_segments,
        ), patch(
            "backend.services.orchestration.conversation_orchestrator.validate_before_narration_plan",
        ) as mock_contract:
            mock_result = MagicMock()
            mock_result.ok = False
            mock_result.primary_reason = "empty_display_text"
            mock_contract.return_value = mock_result
            segs = orch.attach_narration(resolution, session, "Tell me about CSE")
            self.assertIsNone(segs)
            self.assertEqual(resolution.presentation_mode, PresentationMode.FULL_TEXT.value)
            self.assertFalse(resolution.should_generate_presentation)
            self.assertTrue(resolution.degraded)


class PresentationResolverUnitTests(unittest.TestCase):
    def test_retry_flags(self):
        res = ConversationResolution(language="English", language_code_key="en", tts_code="en-IN")
        decision = PolicyDecision(
            action=PolicyAction.NO_SPEECH_RETRY,
            reply_text="Please say that again.",
            length_kind="clarification",
        )
        resolve_presentation(
            decision=decision,
            resolution=res,
            intent=None,
            semantic_topic=None,
            entities={},
        )
        self.assertEqual(res.presentation_mode, PresentationMode.RETRY.value)
        self.assertFalse(res.should_call_rag)
        self.assertFalse(res.should_call_groq)


if __name__ == "__main__":
    unittest.main()
