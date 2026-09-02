"""Hindi input and UI copy use the shared canonical architecture."""

from __future__ import annotations

import asyncio
import pytest

from backend.services.content.semantic_request_parser import parse_semantic_request
from backend.services.content.unit_selector import (
    resolve_units_for_plan,
    select_content_units,
    semantic_fallback_reason,
)
from backend.services.content.surface_narration_mapper import map_content_units_to_segments
from backend.services.ui_localization import load_ui_locales, ui_text
from backend.services.conversation.response_decision import (
    DomainRelevance,
    ResponseMode,
    resolve_response_decision,
)
from backend.services.conversation.semantic_proposal import SemanticProposal
from backend.services.orchestration.conversation_orchestrator import ConversationOrchestrator
from backend.services.answer_generation import (
    OFF_TOPIC_REPLY_BY_LANGUAGE,
    UNAVAILABLE_REPLY_BY_LANGUAGE,
)


def _request(text: str, context: dict | None = None):
    request = parse_semantic_request(
        raw_text=text,
        language_code_key="hi",
        ci_entities=context,
    )
    assert request is not None
    return request


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("डेटा साइंस के HOD कौन हैं?", (("cse_ds", "hod"),)),
        ("CSE के HOD कौन हैं?", (("cse", "hod"),)),
        ("data science के एच ओ डी कौन है", (("cse_ds", "hod"),)),
        ("सी एस ई के एचओडी कौन हैं", (("cse", "hod"),)),
        ("ईसीई fees बताओ", (("ece", "fees"),)),
        ("आई एस ई HOD कौन हैं", (("ise", "hod"),)),
        ("एम बी ए fees बताओ", (("mba", "fees"),)),
        ("ए आई और एम एल HOD कौन हैं", (("cse_aiml", "hod"),)),
        ("प्रिंसिपल कौन हैं?", (("leadership", "principal"),)),
    ),
)
def test_hindi_and_code_switched_transcripts_resolve_canonically(text, expected) -> None:
    request = _request(text)
    assert request.unit_items == expected


@pytest.mark.parametrize(
    ("text", "expected_cards", "expected_units"),
    (
        (
            "CSE और डेटा साइंस के एच ओ डी कौन हैं?",
            [
                {"cardId": "hod_profile", "departmentId": "cse"},
                {"cardId": "hod_profile", "departmentId": "cse_ds"},
            ],
            ("cse.hod", "cse_ds.hod"),
        ),
        (
            "CSE HOD और data science fees बताओ",
            [
                {"cardId": "hod_profile", "departmentId": "cse"},
                {"cardId": "fees", "departmentId": "cse_ds"},
            ],
            ("cse.hod", "cse_ds.fees"),
        ),
        (
            "CSE, ECE और Data Science के HOD दिखाओ",
            [
                {"cardId": "hod_profile", "departmentId": "cse"},
                {"cardId": "hod_profile", "departmentId": "ece"},
                {"cardId": "hod_profile", "departmentId": "cse_ds"},
            ],
            ("cse.hod", "ece.hod", "cse_ds.hod"),
        ),
    ),
)
def test_hindi_multi_card_order_and_units(text, expected_cards, expected_units) -> None:
    request = _request(text)
    assert request.canonical_result()["requestedCards"] == expected_cards
    plan = select_content_units(request)
    assert plan is not None
    assert plan.units == expected_units


@pytest.mark.parametrize(
    ("text", "expected_cards"),
    (
        ("डेटा साइंस विभाग दिखाओ", [{"cardId": "department_overview", "departmentId": "cse_ds"}]),
        ("CSE faculty दिखाओ", [{"cardId": "faculty_list", "departmentId": "cse"}]),
        ("डेटा साइंस faculty", [{"cardId": "faculty_list", "departmentId": "cse_ds"}]),
        ("mechanical fees बताओ", [{"cardId": "fees", "departmentId": "mechanical"}]),
        (
            "CSE HOD और faculty दिखाओ",
            [
                {"cardId": "hod_profile", "departmentId": "cse"},
                {"cardId": "faculty_list", "departmentId": "cse"},
            ],
        ),
        (
            "CSE HOD, Data Science faculty और ECE fees",
            [
                {"cardId": "hod_profile", "departmentId": "cse"},
                {"cardId": "faculty_list", "departmentId": "cse_ds"},
                {"cardId": "fees", "departmentId": "ece"},
            ],
        ),
        (
            "data science HOD और CSE HOD",
            [
                {"cardId": "hod_profile", "departmentId": "cse_ds"},
                {"cardId": "hod_profile", "departmentId": "cse"},
            ],
        ),
        (
            "सी एस ई और data science के एच ओ डी",
            [
                {"cardId": "hod_profile", "departmentId": "cse"},
                {"cardId": "hod_profile", "departmentId": "cse_ds"},
            ],
        ),
    ),
)
def test_required_hindi_card_matrix_reaches_canonical_queue(text, expected_cards) -> None:
    assert _request(text).canonical_result()["requestedCards"] == expected_cards


@pytest.mark.parametrize("text", ("HOD भी दिखाओ", "faculty भी", "fees भी बताओ"))
def test_hindi_followup_reuses_active_department(text: str) -> None:
    request = _request(text, {"department_keys": ["cse_ds"]})
    assert request.department_ids == ("cse_ds",)


def test_explicit_hindi_followup_department_overrides_context() -> None:
    request = _request("ECE के HOD भी दिखाओ", {"department_keys": ["cse_ds"]})
    assert request.department_ids == ("ece",)


def test_hindi_followup_context_flows_through_real_orchestrator() -> None:
    async def _run() -> None:
        session = {"language_code_key": "hi", "language_name": "Hindi"}
        orchestrator = ConversationOrchestrator()
        first = await orchestrator.run("डेटा साइंस विभाग दिखाओ", session, defer_narration=True)
        assert first.resolution.language_code_key == "hi"
        assert first.resolution.tts_code == "hi-IN"
        assert first.resolution.semantic_request.unit_items == (("cse_ds", "overview"),)
        assert session["last_semantic_entities"] == ["cse_ds"]

        for followup, topic in (("HOD भी", "hod"), ("faculty भी", "faculty"), ("fees?", "fees")):
            result = await orchestrator.run(followup, session, defer_narration=True)
            assert result.resolution.semantic_request.unit_items == (("cse_ds", topic),)

        explicit = await orchestrator.run("ECE HOD दिखाओ", session, defer_narration=True)
        assert explicit.resolution.semantic_request.unit_items == (("ece", "hod"),)
        assert session["last_semantic_entities"] == ["ece"]

    asyncio.run(_run())


def test_hindi_faculty_is_canonical_and_resolves_fact_safely() -> None:
    request = _request("CSE faculty दिखाओ")
    assert request.requested_card_ids == ("faculty_list",)
    plan = select_content_units(request)
    assert plan is not None
    assert plan.units == ("cse.faculty",)
    assert semantic_fallback_reason(request) is None


def test_hindi_global_location_card_has_no_department_identity() -> None:
    request = _request("कॉलेज कहाँ है?")
    assert request.canonical_result()["requestedCards"] == [{"cardId": "location"}]
    plan = select_content_units(request)
    assert plan is not None
    assert plan.units == ("college.location",)


def test_global_and_department_cards_preserve_order_without_cross_product() -> None:
    request = _request("CSE fees और college location दिखाओ")
    assert request.canonical_result()["requestedCards"] == [
        {"cardId": "fees", "departmentId": "cse"},
        {"cardId": "location"},
    ]
    plan = select_content_units(request)
    assert plan is not None
    assert plan.units == ("cse.fees", "college.location")


@pytest.mark.parametrize(
    ("text", "unit_id"),
    (
        ("डेटा साइंस विभाग के प्रमुख कौन हैं?", "cse_ds.hod"),
        ("कंप्यूटर साइंस के विभागाध्यक्ष कौन हैं?", "cse.hod"),
        ("प्लेसमेंट की जानकारी दिखाइए", "college.placements"),
        ("प्रवेश की जानकारी बताइए", "college.admissions"),
        ("placements के बारे में बताओ", "college.placements"),
        ("admission details बताओ", "college.admissions"),
    ),
)
def test_natural_hindi_and_global_cards_use_canonical_units(text: str, unit_id: str) -> None:
    request = _request(text)
    plan = select_content_units(request)
    assert plan is not None
    assert plan.units == (unit_id,)


def _leaf_paths(node: object, prefix: str = "") -> set[str]:
    if not isinstance(node, dict):
        return {prefix}
    return {
        path
        for key, value in node.items()
        for path in _leaf_paths(value, f"{prefix}.{key}" if prefix else key)
    }


def test_hindi_shared_ui_contract_is_complete_and_not_english() -> None:
    locales = load_ui_locales()
    assert _leaf_paths(locales["hi"]) == _leaf_paths(locales["en"])
    for path in (
        "status.listening",
        "status.processing",
        "error.microphone_denied",
        "error.network",
        "clarification.department",
        "availability.unknown",
        "session.goodbye",
    ):
        hindi = ui_text("hi-IN", path)
        assert hindi != ui_text("en", path)
        assert any("\u0900" <= char <= "\u097f" for char in hindi)

    assert OFF_TOPIC_REPLY_BY_LANGUAGE["Hindi"] == ui_text("hi", "availability.off_topic")
    assert UNAVAILABLE_REPLY_BY_LANGUAGE["Hindi"] == ui_text(
        "hi", "availability.missing_source"
    ).replace("\n", " ")


def test_hindi_ui_placeholders_are_preserved_then_substituted() -> None:
    assert "{department}" in ui_text("Hindi", "action.hod")
    assert "डेटा साइंस" in ui_text(
        "Hindi", "action.hod", department="डेटा साइंस"
    )


def test_departmentless_hod_reports_missing_department_and_hindi_clarification() -> None:
    request = parse_semantic_request(raw_text="HOD कौन हैं?", language_code_key="hi")
    assert request is None
    decision = resolve_response_decision(
        text="HOD कौन हैं?",
        semantic_request=None,
        ci_intent="HOD_PROFILE",
        has_department_entity=False,
    )
    assert decision.mode.value == "CLARIFY"
    assert decision.clarification_target == "department"
    assert decision.clarification_reason == "missing_department"
    assert decision.diagnostics["fallbackReason"] == "MISSING_DEPARTMENT"
    assert "विभाग" in ui_text("hi", "clarification.department")


@pytest.mark.parametrize(
    ("text", "unit_id", "card_id"),
    (
        ("डेटा साइंस के HOD कौन हैं?", "cse_ds.hod", "hod_profile"),
        ("CSE faculty दिखाओ", "cse.faculty", "faculty_list"),
        ("ECE fees बताओ", "ece.fees", "fees"),
        ("प्रिंसिपल कौन हैं?", "leadership.principal", "principal_profile"),
        ("कॉलेज कहाँ है?", "college.location", "location"),
        ("प्रवेश की जानकारी बताइए", "college.admissions", "admissions"),
        ("प्लेसमेंट की जानकारी दिखाइए", "college.placements", "placements"),
        ("लड़कियों के हॉस्टल की फीस बताओ", "hostel.girls.fees", "hostel"),
        ("कैंटीन का समय बताओ", "canteen.timings", "canteen"),
    ),
)
def test_resolved_hindi_cards_and_narration_are_localized(
    text: str,
    unit_id: str,
    card_id: str,
) -> None:
    plan = select_content_units(_request(text))
    assert plan is not None
    units = resolve_units_for_plan(plan)
    assert [unit.unit_id for unit in units] == [unit_id]
    assert units[0].language_code == "hi"
    assert any("\u0900" <= char <= "\u097f" for char in units[0].title)
    assert any("\u0900" <= char <= "\u097f" for char in units[0].body)
    assert "SAMPLE_REPLACE_WITH_OFFICIAL" not in units[0].title
    assert "SAMPLE_REPLACE_WITH_OFFICIAL" not in units[0].body
    segments = map_content_units_to_segments(units, lang_key="hi")
    assert len(segments) == 1
    assert segments[0].canonical_card_id == card_id
    assert any("\u0900" <= char <= "\u097f" for char in segments[0].display_text)
    assert any("\u0900" <= char <= "\u097f" for char in segments[0].tts_text)


@pytest.mark.parametrize(
    "text",
    (
        "admission details बताओ",
        "प्रवेश की जानकारी बताइए",
        "admission details",
    ),
)
def test_registered_global_admissions_request_keeps_card_authority(text: str) -> None:
    request = parse_semantic_request(raw_text=text, language_code_key="hi")
    assert request is not None
    assert request.unit_items == (("college", "admissions"),)
    decision = resolve_response_decision(
        text=text,
        semantic_request=request,
        ci_intent="ADMISSIONS",
        has_department_entity=False,
        faq_matched=True,
        validated_proposal=SemanticProposal(
            domain=DomainRelevance.INSTITUTION,
            mode_hint=ResponseMode.ANSWER,
        ),
    )
    assert decision.mode is ResponseMode.CARD
    assert decision.evidence == "semantic_request"


def test_mixed_hindi_admissions_reaches_card_through_real_orchestrator() -> None:
    async def _run() -> None:
        session = {"language_code_key": "hi", "language_name": "Hindi"}
        orchestrator = ConversationOrchestrator()
        result = await orchestrator.run(
            "admission details बताओ", session, defer_narration=True
        )
        assert result.intel.response_decision.mode is ResponseMode.CARD
        assert result.resolution.presentation_mode == "CARD_PRESENTATION"
        assert result.resolution.semantic_request is not None
        assert result.resolution.semantic_request.unit_items == (("college", "admissions"),)
        assert result.resolution.card_surface == "admissions"
        segments = orchestrator.attach_narration(result.resolution, session, "admission details बताओ")
        assert segments is not None
        assert [segment.unit_id for segment in segments] == ["college.admissions"]
        assert result.resolution.response_authority == "CARD_PRESENTATION"

    asyncio.run(_run())


def test_global_hindi_request_replaces_leadership_context_in_real_orchestrator() -> None:
    async def _run() -> None:
        session = {"language_code_key": "hi", "language_name": "Hindi"}
        orchestrator = ConversationOrchestrator()
        principal = await orchestrator.run(
            "प्रिंसिपल कौन हैं?", session, defer_narration=True
        )
        assert principal.resolution.semantic_request is not None
        assert principal.resolution.semantic_request.unit_items == (("leadership", "principal"),)

        admissions = await orchestrator.run(
            "admission details बताओ", session, defer_narration=True
        )
        assert admissions.resolution.semantic_request is not None
        assert admissions.resolution.semantic_request.unit_items == (("college", "admissions"),)
        assert admissions.intel.response_decision.mode is ResponseMode.CARD
        assert admissions.resolution.presentation_mode == "CARD_PRESENTATION"

    asyncio.run(_run())
