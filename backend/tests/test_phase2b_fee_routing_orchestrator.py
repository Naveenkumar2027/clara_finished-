"""Phase 2B fee routing through the production conversation pipeline."""

from __future__ import annotations

import asyncio

import pytest

from backend.services.conversation.templates import clarification_reply
from backend.services.conversation.types import PolicyAction
from backend.services.orchestration import ConversationOrchestrator, PresentationMode


def _run_turn(text: str, *, language: str = "English", code_key: str = "en"):
    session = {"language_code_key": code_key, "language_name": language}
    return asyncio.run(
        ConversationOrchestrator().run(text, session, defer_narration=True)
    )


@pytest.mark.parametrize(
    ("text", "language", "code_key"),
    (
        ("fees", "English", "en"),
        ("ಶುಲ್ಕ ಎಷ್ಟು", "Kannada", "kn"),
    ),
)
def test_fee_without_department_reaches_existing_clarification(
    text: str,
    language: str,
    code_key: str,
) -> None:
    result = _run_turn(text, language=language, code_key=code_key)
    resolution = result.resolution

    assert resolution.response_mode == "CLARIFY"
    assert resolution.policy == PolicyAction.ASK_CLARIFICATION.value
    assert resolution.clarification_target == "department"
    assert resolution.short_circuit_reply == clarification_reply(language, "department")
    assert resolution.presentation_mode == PresentationMode.UNKNOWN.value
    assert resolution.show_card is None
    assert result.intel.response_decision.clarification_reason == "topic_without_department"
    assert result.intel.decision.answer_source == "policy_clarification"


def test_explicit_admissions_fee_request_keeps_admissions_card() -> None:
    result = _run_turn("admission fees enquiry")
    resolution = result.resolution

    assert resolution.response_mode == "CARD"
    assert resolution.policy == PolicyAction.CARD_PRESENTATION.value
    assert resolution.presentation_mode == PresentationMode.CARD_PRESENTATION.value
    assert resolution.show_card == "admissions"
    assert result.intel.response_decision.items == (("college", "admissions"),)
    assert resolution.should_generate_presentation


def test_known_department_fees_keeps_department_fee_card() -> None:
    result = _run_turn("CSE fees")
    resolution = result.resolution

    assert resolution.response_mode == "CARD"
    assert resolution.policy == PolicyAction.CARD_PRESENTATION.value
    assert resolution.presentation_mode == PresentationMode.CARD_PRESENTATION.value
    assert resolution.show_card == "department_fees"
    assert resolution.should_generate_presentation
    assert result.intel.response_decision.items == (("cse", "fees"),)
