"""Phase 2B canonical department context at the presentation boundary."""

from __future__ import annotations

import asyncio

import pytest

from backend.services.conversation.types import PolicyAction
from backend.services.orchestration import ConversationOrchestrator, PresentationMode


def _session(*, carried: list[str] | None = None) -> dict:
    session = {"language_code_key": "en", "language_name": "English"}
    if carried is not None:
        session["last_semantic_entities"] = carried
    return session


def _run_turn(text: str, session: dict | None = None):
    active_session = session if session is not None else _session()
    result = asyncio.run(
        ConversationOrchestrator().run(
            text,
            active_session,
            defer_narration=True,
        )
    )
    return result, active_session


def _assert_department_fees_card(result, department: str) -> None:
    resolution = result.resolution
    assert resolution.response_mode == "CARD"
    assert resolution.policy == PolicyAction.CARD_PRESENTATION.value
    assert resolution.presentation_mode == PresentationMode.CARD_PRESENTATION.value
    assert resolution.show_card == "department_fees"
    assert resolution.should_generate_presentation
    assert result.intel.response_decision.items == ((department, "fees"),)


def test_direct_and_inherited_cse_fees_have_surface_parity() -> None:
    direct, _ = _run_turn("CSE fees")

    session = _session()
    overview, session = _run_turn("tell me about CSE", session)
    assert overview.resolution.show_card == "department_overview"
    inherited, _ = _run_turn("what is its fees?", session)

    _assert_department_fees_card(direct, "cse")
    _assert_department_fees_card(inherited, "cse")
    assert inherited.resolution.show_card == direct.resolution.show_card


def test_another_canonical_department_inherits_into_fees_presentation() -> None:
    session = _session()
    overview, session = _run_turn("tell me about ECE", session)
    assert overview.intel.response_decision.entities == ("ece",)

    inherited, _ = _run_turn("what are its fees?", session)
    _assert_department_fees_card(inherited, "ece")


@pytest.mark.parametrize("carried", (["unknown"], ["cse_quantum"]))
def test_invalid_or_stale_department_context_clarifies(carried: list[str]) -> None:
    result, _ = _run_turn("what are its fees?", _session(carried=carried))

    assert result.resolution.response_mode == "CLARIFY"
    assert result.resolution.policy == PolicyAction.ASK_CLARIFICATION.value
    assert result.resolution.clarification_target == "department"
    assert result.resolution.show_card is None
    assert result.intel.response_decision.items == ()


def test_forged_alias_in_canonical_key_slot_does_not_create_department_card() -> None:
    result, _ = _run_turn(
        "what are its fees?",
        _session(carried=["Computer Science and Engineering"]),
    )

    assert result.resolution.response_mode == "CLARIFY"
    assert result.resolution.show_card is None
    assert result.intel.response_decision.items == ()


def test_multi_card_with_fees_keeps_surface_and_ordered_units() -> None:
    result, _ = _run_turn("CSE achievements and fees and HOD")

    assert result.resolution.show_card == "hod"
    assert result.intel.response_decision.items == (
        ("cse", "achievements"),
        ("cse", "fees"),
        ("cse", "hod"),
    )


def test_explicit_admissions_fees_still_uses_admissions_surface() -> None:
    result, _ = _run_turn("admission fees enquiry")

    assert result.resolution.show_card == "admissions"
    assert result.intel.response_decision.items == (("college", "admissions"),)


def test_fees_without_department_still_clarifies_without_card() -> None:
    result, _ = _run_turn("fees")

    assert result.resolution.response_mode == "CLARIFY"
    assert result.resolution.policy == PolicyAction.ASK_CLARIFICATION.value
    assert result.resolution.show_card is None
    assert result.intel.response_decision.items == ()
