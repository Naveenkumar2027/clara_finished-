"""Code-switched input stays inside the one canonical semantic pipeline."""

from __future__ import annotations

import asyncio
import pytest

from backend.services.content.semantic_request_parser import parse_semantic_request
from backend.services.content.unit_selector import (
    select_content_units,
    semantic_fallback_reason,
)
from backend.services.orchestration import ConversationOrchestrator


def _request(text: str, language: str = "kn", context: dict | None = None):
    request = parse_semantic_request(
        raw_text=text,
        language_code_key=language,
        ci_entities=context,
    )
    assert request is not None
    return request


@pytest.mark.parametrize(
    ("text", "department", "cards", "units"),
    (
        ("data science hod ಯಾರು?", "cse_ds", ("hod_profile",), ("cse_ds.hod",)),
        ("CSE HOD ಯಾರು?", "cse", ("hod_profile",), ("cse.hod",)),
        ("ಡೇಟಾ ಸೈನ್ಸ್ HOD ಯಾರು?", "cse_ds", ("hod_profile",), ("cse_ds.hod",)),
        ("computer science ಮುಖ್ಯಸ್ಥರು ಯಾರು?", "cse", ("hod_profile",), ("cse.hod",)),
        ("data science fees ಎಷ್ಟು?", "cse_ds", ("fees",), ("cse_ds.fees",)),
        ("AI ML department ಬಗ್ಗೆ ಹೇಳಿ", "cse_aiml", ("department_overview",), ("cse_aiml.overview",)),
        ("ECE placements ತೋರಿಸಿ", "ece", ("placements",), ("ece.placements",)),
        (
            "mechanical HOD ಮತ್ತು fees ತೋರಿಸಿ",
            "mechanical",
            ("hod_profile", "fees"),
            ("mechanical.hod", "mechanical.fees"),
        ),
    ),
)
def test_kannada_english_matrix(text, department, cards, units) -> None:
    request = _request(text)
    assert request.department_ids == (department,)
    assert request.requested_card_ids == cards
    plan = select_content_units(request)
    assert plan is not None
    assert plan.units == units
    assert semantic_fallback_reason(request) is None


def test_expected_canonical_projection() -> None:
    assert _request("data science hod ಯಾರು?").canonical_result() == {
        "language": "kn",
        "intentId": "show_hod",
        "intentIds": ["show_hod"],
        "departmentIds": ["cse_ds"],
        "requestedCardIds": ["hod_profile"],
        "requestedCards": [{"cardId": "hod_profile", "departmentId": "cse_ds"}],
        "activeIndex": 0,
    }


@pytest.mark.parametrize(
    "text",
    (
        "C S E H O D ಯಾರು",
        "ಸಿ ಎಸ್ ಇ HOD ಯಾರು",
        "data science ಹೆಚ್ ಓ ಡಿ ಯಾರು",
        "data science ಎಚ್ ಓ ಡಿ ಯಾರು",
    ),
)
def test_realistic_stt_acronym_variants(text: str) -> None:
    request = _request(text)
    assert request.intent_id == "show_hod"
    assert request.requested_card_ids == ("hod_profile",)


@pytest.mark.parametrize(
    ("language", "text"),
    (
        ("hi", "डेटा साइंस HOD कौन है?"),
        ("te", "డేటా సైన్స్ HOD ఎవరు?"),
        ("ta", "டேட்டா சயின்ஸ் HOD யார்?"),
        ("ml", "ഡാറ്റാ സയൻസ് HOD ആര്?"),
        ("en", "Who is the HOD of Data Science?"),
    ),
)
def test_regional_english_and_english_regression(language: str, text: str) -> None:
    request = _request(text, language)
    assert request.department_ids == ("cse_ds",)
    assert request.intent_id == "show_hod"
    assert select_content_units(request).units == ("cse_ds.hod",)


@pytest.mark.parametrize("text", ("HOD also", "hod ಕೂಡ", "fees?"))
def test_concise_mixed_followup_reuses_active_department(text: str) -> None:
    request = _request(text, context={"department_keys": ["cse_ds"]})
    assert request.department_ids == ("cse_ds",)


def test_new_explicit_department_overrides_active_context() -> None:
    request = _request(
        "mechanical HOD",
        context={"department_keys": ["cse_ds"]},
    )
    assert request.department_ids == ("mechanical",)


def test_missing_and_unknown_department_still_fail_closed() -> None:
    assert parse_semantic_request(raw_text="HOD ಯಾರು?", language_code_key="kn") is None
    assert parse_semantic_request(raw_text="unknownbranch HOD ಯಾರು?", language_code_key="kn") is None


@pytest.mark.parametrize(
    ("text", "intent", "card"),
    (
        ("CSE ಸಂಪರ್ಕ", "show_contact", "contact_details"),
    ),
)
def test_known_but_unregistered_concept_never_misroutes_to_overview(
    text: str,
    intent: str,
    card: str,
) -> None:
    request = _request(text)
    assert request.intent_id == intent
    assert request.requested_card_ids == (card,)
    assert select_content_units(request) is None
    assert semantic_fallback_reason(request) == "CARD_NOT_REGISTERED"


def test_faculty_concept_uses_registered_fact_safe_card() -> None:
    request = _request("CSE faculty ತೋರಿಸಿ")
    assert request.intent_id == "show_faculty"
    assert request.requested_card_ids == ("faculty_list",)
    plan = select_content_units(request)
    assert plan is not None
    assert plan.units == ("cse.faculty",)
    assert semantic_fallback_reason(request) is None


def test_valid_cards_are_preserved_when_an_unregistered_card_is_also_requested() -> None:
    request = _request("CSE department, HOD ಮತ್ತು contact details")
    assert request.requested_card_ids == (
        "department_overview",
        "hod_profile",
        "contact_details",
    )
    plan = select_content_units(request)
    assert plan is not None
    assert plan.units == ("cse.overview", "cse.hod")
    assert plan.unresolved_items == (("cse", "contact"),)
    assert semantic_fallback_reason(request) == "CARD_NOT_REGISTERED"


def test_live_orchestrator_preserves_kannada_response_and_hod_unit() -> None:
    result = asyncio.run(
        ConversationOrchestrator().run(
            "data science hod ಯಾರು?",
            {"language_code_key": "kn", "language_name": "Kannada"},
            defer_narration=False,
        )
    )
    assert result.resolution.language_code_key == "kn"
    assert result.resolution.show_card == "hod"
    assert result.resolution.canonical_entities["department_keys"] == ["cse_ds"]
    assert result.narration_segments is not None
    assert [segment.unit_id for segment in result.narration_segments] == ["cse_ds.hod"]
