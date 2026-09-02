"""Phase 2B policy regression tests for fee/admissions routing."""

from __future__ import annotations

import pytest

from backend.services.answer_generation import (
    INTENT_ADMISSIONS,
    extract_features,
    has_explicit_admissions_cue,
    load_locale_data_for_lang_key,
    normalize_user_input,
    resolve_intent_from_features,
)
from backend.services.content.semantic_request_parser import parse_semantic_request
from backend.services.content.unit_selector import select_content_units
from backend.services.conversation.entity_extractor import extract_entities_rules
from backend.services.conversation.response_decision import (
    DomainRelevance,
    ResponseDecision,
    ResponseMode,
    resolve_response_decision,
)
from backend.services.conversation.semantic_proposal import SemanticProposal
from backend.services.conversation.semantic_proposal_validator import validate_semantic_proposal


LANGUAGES = ("en", "kn", "hi", "ta", "te", "ml")
FEE_TERMS = {
    "en": "fees",
    "kn": "ಶುಲ್ಕ",
    "hi": "फीस",
    "ta": "கட்டணம்",
    "te": "ఫీజు",
    "ml": "ഫീസ്",
}
UNKNOWN_DEPARTMENT = {
    "kn": "ಕ್ವಾಂಟಮ್ ವಿಭಾಗ",
    "hi": "क्वांटम विभाग",
    "ta": "குவாண்டம் துறை",
    "te": "క్వాంటం విభాగం",
    "ml": "ക്വാണ്ടം വിഭാഗം",
}


def _native_cse(language: str) -> str:
    locale = load_locale_data_for_lang_key(language)
    return str(locale["departments"]["cse"]["name"])


def _request(text: str, language: str = "en", *, previous: list[str] | None = None):
    ci_entities = {"department_keys": previous} if previous else None
    return parse_semantic_request(
        raw_text=text,
        language_code_key=language,
        ci_entities=ci_entities,
    )


def _units(text: str, language: str = "en", *, previous: list[str] | None = None):
    request = _request(text, language, previous=previous)
    if request is None:
        return None
    plan = select_content_units(request)
    return None if plan is None else tuple(plan.units)


def _decision(
    text: str,
    language: str = "en",
    *,
    previous: list[str] | None = None,
    proposal: SemanticProposal | None = None,
) -> ResponseDecision:
    request = _request(text, language, previous=previous)
    normalized = normalize_user_input(text)
    intent = resolve_intent_from_features(extract_features(normalized))
    entities = extract_entities_rules(text)
    return resolve_response_decision(
        text=text,
        semantic_request=request,
        ci_intent=intent,
        has_department_entity=bool(entities.department or (request and request.entities)),
        validated_proposal=proposal,
    )


@pytest.mark.parametrize("language", LANGUAGES)
def test_bare_fees_clarify_in_every_language(language: str) -> None:
    decision = _decision(FEE_TERMS[language], language)
    assert decision.mode is ResponseMode.CLARIFY
    assert decision.clarification_target == "department"
    assert decision.clarification_reason == "topic_without_department"


@pytest.mark.parametrize("language", ("kn", "hi", "ta", "te", "ml"))
def test_unknown_native_department_fees_clarify(language: str) -> None:
    text = f"{UNKNOWN_DEPARTMENT[language]} {FEE_TERMS[language]}"
    assert _units(text, language) is None
    decision = _decision(text, language)
    assert decision.mode is ResponseMode.CLARIFY
    assert decision.clarification_target == "department"
    assert decision.clarification_reason == "topic_without_department"


def test_unknown_english_department_fees_clarify() -> None:
    decision = _decision("quantum department fees")
    assert decision.mode is ResponseMode.CLARIFY
    assert decision.clarification_target == "department"


@pytest.mark.parametrize("language", LANGUAGES)
def test_known_department_fees_remain_department_card(language: str) -> None:
    text = f"CSE {FEE_TERMS[language]}"
    assert _units(text, language) == ("cse.fees",)
    decision = _decision(text, language)
    assert decision.mode is ResponseMode.CARD
    assert decision.items == (("cse", "fees"),)


@pytest.mark.parametrize("language", ("kn", "hi", "ta", "te", "ml"))
def test_native_department_with_english_fees(language: str) -> None:
    text = f"{_native_cse(language)} fees"
    assert _units(text, language) == ("cse.fees",)
    assert _decision(text, language).mode is ResponseMode.CARD


@pytest.mark.parametrize("language", ("kn", "hi", "ta", "te", "ml"))
def test_english_acronym_with_regional_fee_word(language: str) -> None:
    text = f"CSE {FEE_TERMS[language]}"
    assert _units(text, language) == ("cse.fees",)


def test_mixed_language_fee_request() -> None:
    assert _units("ದಯವಿಟ್ಟು CSE ಶುಲ್ಕ", "kn") == ("cse.fees",)
    assert _decision("ದಯವಿಟ್ಟು CSE ಶುಲ್ಕ", "kn").mode is ResponseMode.CARD


def test_explicit_admissions_with_fee_wording_remains_admissions_card() -> None:
    decision = _decision("admission fees enquiry")
    assert decision.mode is ResponseMode.CARD
    assert decision.items == (("college", "admissions"),)
    assert decision.evidence == "semantic_request"


def test_bare_eligibility_does_not_gain_an_admissions_card() -> None:
    decision = _decision("eligibility")
    assert decision.mode is ResponseMode.ANSWER
    assert decision.evidence == "institution_lexicon"


def test_known_department_plus_admissions_preserves_existing_answer_policy() -> None:
    decision = _decision("CSE admission")
    assert decision.mode is ResponseMode.ANSWER
    assert decision.evidence == "entity_mention_in_answer"


def test_known_department_plus_admissions_fees_keeps_department_fee_card() -> None:
    assert _units("CSE admission fees") == ("cse.fees",)
    decision = _decision("CSE admission fees")
    assert decision.mode is ResponseMode.CARD
    assert decision.items == (("cse", "fees"),)


def test_multi_card_request_with_fees_stays_ordered() -> None:
    text = "CSE achievements and fees and HOD"
    assert _units(text) == ("cse.achievements", "cse.fees", "cse.hod")
    decision = _decision(text)
    assert decision.mode is ResponseMode.CARD
    assert decision.items == (
        ("cse", "achievements"),
        ("cse", "fees"),
        ("cse", "hod"),
    )


def test_valid_previous_department_context_is_inherited() -> None:
    assert _units("What about its fees?", previous=["cse"]) == ("cse.fees",)
    decision = _decision("What about its fees?", previous=["cse"])
    assert decision.mode is ResponseMode.CARD
    assert decision.items == (("cse", "fees"),)


@pytest.mark.parametrize("previous", (None, ["unknown"], ["cse_quantum"]))
def test_stale_or_invalid_previous_department_does_not_create_card(previous) -> None:
    decision = _decision("What about its fees?", previous=previous)
    assert decision.mode is ResponseMode.CLARIFY
    assert decision.clarification_target == "department"


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("admission", True),
        ("ADMISSIONS?", True),
        ("how to apply", True),
        ("KCET counselling", True),
        ("application", True),
        ("readmission", False),
        ("inadmissions", False),
        ("applicable", False),
        ("applicationware", False),
        ("quotable", False),
        ("fees", False),
        ("fee structure", False),
    ),
)
def test_explicit_admissions_vocabulary_is_boundary_aware(text: str, expected: bool) -> None:
    assert has_explicit_admissions_cue(text) is expected


def test_validated_card_proposal_cannot_manufacture_fee_department() -> None:
    raw = {
        "domain": "institution",
        "mode_hint": "CARD",
        "items": [{"entity": "cse", "topic": "fees"}],
        "scope": "single",
        "clarification_target": "none",
        "clarification_reason": "none",
        "answer_topic": "",
        "confidence": "HIGH",
    }
    validated = validate_semantic_proposal(raw, utterance="quantum department fees")
    assert validated.status == "accepted"
    assert validated.proposal is not None
    decision = _decision("quantum department fees", proposal=validated.proposal)
    assert decision.mode is ResponseMode.CLARIFY
    assert decision.evidence == "topic_cue_without_entity"


def test_validated_answer_proposal_cannot_bypass_missing_fee_clarification() -> None:
    proposal = SemanticProposal(
        domain=DomainRelevance.INSTITUTION,
        mode_hint=ResponseMode.ANSWER,
        confidence="HIGH",
    )
    decision = resolve_response_decision(
        text="fees",
        semantic_request=None,
        ci_intent=None,
        has_department_entity=False,
        validated_proposal=proposal,
    )
    assert decision.mode is ResponseMode.CLARIFY
    assert decision.evidence == "topic_cue_without_entity"


def test_legacy_fee_intent_contract_is_unchanged() -> None:
    intent = resolve_intent_from_features(extract_features("fee structure"))
    assert intent == INTENT_ADMISSIONS
