"""Regression coverage for the confirmed Hindi STT rendering of HOD as `होद`."""

import pytest

from backend.services.content.semantic_composition import detect_topic_spans
from backend.services.content.semantic_request_parser import parse_semantic_request
from backend.services.content.semantic_topics import detect_atomic_topics
from backend.services.content.unit_selector import semantic_fallback_reason, select_content_units


@pytest.mark.parametrize(
    ("text", "department"),
    [
        ("डेटा साइंस का HOD कौन है", "cse_ds"),
        ("डेटा साइंस का hod कौन है", "cse_ds"),
        ("डेटा साइंस का एचओडी कौन है", "cse_ds"),
        ("डेटा साइंस का एच ओ डी कौन है", "cse_ds"),
        ("डेटा साइंस का होद कौन है", "cse_ds"),
        ("डाटा साइंस डिपार्टमेंट का होद कौन है", "cse_ds"),
        ("मेकेनिकल का होद कौन है", "mechanical"),
        ("CSE का होद कौन है", "cse"),
        ("ECE का होद कौन है", "ece"),
    ],
)
def test_hindi_hod_stt_forms_resolve_to_the_same_canonical_card(
    text: str,
    department: str,
) -> None:
    assert detect_atomic_topics(text) == frozenset({"hod"})
    assert [span.topic for span in detect_topic_spans(text)] == ["hod"]

    request = parse_semantic_request(raw_text=text, language_code_key="hi")
    assert request is not None
    assert request.topic == "hod"
    assert request.intent_id == "show_hod"
    assert request.requested_cards == ({"cardId": "hod_profile", "departmentId": department},)
    assert semantic_fallback_reason(request) is None

    plan = select_content_units(request, surface="hod")
    assert plan is not None
    assert plan.units == (f"{department}.hod",)


def test_hindi_generic_data_science_request_remains_overview() -> None:
    text = "डेटा साइंस डिपार्टमेंट के बारे में बताओ"
    request = parse_semantic_request(raw_text=text, language_code_key="hi")
    assert request is not None
    assert request.unit_items == (("cse_ds", "overview"),)
    assert request.requested_cards == ({"cardId": "department_overview", "departmentId": "cse_ds"},)


def test_hindi_phonetic_hod_preserves_multi_entity_pairing() -> None:
    text = "CSE का होद और Data Science का होद कौन है"
    request = parse_semantic_request(raw_text=text, language_code_key="hi")
    assert request is not None
    assert request.unit_items == (("cse", "hod"), ("cse_ds", "hod"))
    assert request.requested_cards == (
        {"cardId": "hod_profile", "departmentId": "cse"},
        {"cardId": "hod_profile", "departmentId": "cse_ds"},
    )
    plan = select_content_units(request, surface="hod")
    assert plan is not None
    assert plan.units == ("cse.hod", "cse_ds.hod")
