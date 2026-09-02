"""Focused regressions for unit-plan preservation of SurfaceSelector authority."""

from backend.services.answer_generation import (
    INTENT_DEPARTMENT_FEES,
    INTENT_DEPARTMENT_OVERVIEW,
    INTENT_HOD_PROFILE,
    INTENT_PRINCIPAL_PROFILE,
)
from backend.services.content.semantic_request import SemanticRequest
from backend.services.content.types import (
    SURFACE_DEPARTMENT_FEES,
    SURFACE_DEPARTMENT_OVERVIEW,
    SURFACE_HOD,
    SURFACE_PRINCIPAL,
)
from backend.services.conversation.types import PolicyAction, PolicyDecision
from backend.services.orchestration.presentation_resolver import resolve_presentation
from backend.services.orchestration.types import ConversationResolution


def _request(*items: tuple[str, str], language: str = "en", raw_text: str = "") -> SemanticRequest:
    return SemanticRequest(
        language_code=language,
        topic=items[0][1],
        entities=tuple(dict.fromkeys(entity for entity, _ in items if entity != "leadership")),
        context="leadership" if items[0][0] == "leadership" else "department",
        requested_scope="single",
        confidence="HIGH",
        source="surface-authority-regression",
        raw_text=raw_text,
        items=items,
    )


def _resolve(intent: str, request: SemanticRequest, text: str = "") -> ConversationResolution:
    return resolve_presentation(
        decision=PolicyDecision(
            action=PolicyAction.CARD_PRESENTATION,
            answer_source="intent",
            length_kind="presentation",
        ),
        resolution=ConversationResolution(language_code_key=request.language_code),
        intent=intent,
        semantic_topic=request.topic.upper(),
        entities={"department": request.entities[0]} if request.entities else {},
        user_text=text or request.raw_text,
        semantic_request=request,
    )


def test_hod_surface_is_not_downgraded_to_department_overview() -> None:
    result = _resolve(INTENT_HOD_PROFILE, _request(("mechanical", "hod")))
    assert (result.card_surface, result.show_card, result.presentation_type) == (
        SURFACE_HOD,
        SURFACE_HOD,
        SURFACE_HOD,
    )


def test_department_overview_surface_remains_overview() -> None:
    result = _resolve(INTENT_DEPARTMENT_OVERVIEW, _request(("mechanical", "overview")))
    assert result.show_card == SURFACE_DEPARTMENT_OVERVIEW


def test_fees_surface_is_not_downgraded() -> None:
    result = _resolve(INTENT_DEPARTMENT_FEES, _request(("ece", "fees")))
    assert result.show_card == SURFACE_DEPARTMENT_FEES


def test_principal_surface_remains_unchanged() -> None:
    result = _resolve(INTENT_PRINCIPAL_PROFILE, _request(("leadership", "principal")))
    assert result.show_card == SURFACE_PRINCIPAL


def test_multi_hod_request_preserves_hod_surface_and_order() -> None:
    request = _request(("cse", "hod"), ("cse_ds", "hod"))
    result = _resolve(INTENT_HOD_PROFILE, request)
    assert result.show_card == SURFACE_HOD
    assert result.semantic_request.unit_items == (("cse", "hod"), ("cse_ds", "hod"))


def test_mixed_hod_and_fees_preserves_primary_surface_and_order() -> None:
    request = _request(("cse", "hod"), ("cse_ds", "fees"))
    result = _resolve(INTENT_HOD_PROFILE, request)
    assert result.show_card == SURFACE_HOD
    assert result.semantic_request.unit_items == (("cse", "hod"), ("cse_ds", "fees"))


def test_hindi_mechanical_hod_live_regression() -> None:
    text = "मेकेनिकल का hod कौन है"
    result = _resolve(INTENT_HOD_PROFILE, _request(("mechanical", "hod"), language="hi", raw_text=text))
    assert result.show_card == SURFACE_HOD


def test_kannada_mechanical_hod_regression() -> None:
    text = "mechanical hod ಯಾರು?"
    result = _resolve(INTENT_HOD_PROFILE, _request(("mechanical", "hod"), language="kn", raw_text=text))
    assert result.show_card == SURFACE_HOD


def test_english_mechanical_hod_regression() -> None:
    text = "Who is the Mechanical HOD?"
    result = _resolve(INTENT_HOD_PROFILE, _request(("mechanical", "hod"), raw_text=text))
    assert result.show_card == SURFACE_HOD
