"""Telugu/Malayalam canonical-engine parity matrix."""

import pytest
import json
from pathlib import Path

from backend.services.answer_generation import INTENT_DEPARTMENT_FEES, INTENT_HOD_PROFILE
from backend.services.content.semantic_request_parser import parse_semantic_request
from backend.services.content.types import SURFACE_DEPARTMENT_FEES, SURFACE_FACULTY, SURFACE_HOD
from backend.services.content.unit_selector import semantic_fallback_reason, select_content_units
from backend.services.conversation.types import PolicyAction, PolicyDecision
from backend.services.orchestration.presentation_resolver import resolve_presentation
from backend.services.orchestration.types import ConversationResolution


def _leaf_paths(value: object, prefix: str = "") -> set[str]:
    if not isinstance(value, dict):
        return {prefix}
    return {
        path
        for key, child in value.items()
        for path in _leaf_paths(child, f"{prefix}.{key}" if prefix else key)
    }


def test_telugu_and_malayalam_ui_packs_have_full_key_parity() -> None:
    path = Path(__file__).resolve().parents[1] / "data" / "locales" / "ui.json"
    locales = json.loads(path.read_text(encoding="utf-8"))
    english_paths = _leaf_paths(locales["en"])
    assert _leaf_paths(locales["te"]) == english_paths
    assert _leaf_paths(locales["ml"]) == english_paths


CORE_CASES = [
    ("te", "డేటా సైన్స్ HOD ఎవరు?", (("cse_ds", "hod"),)),
    ("te", "CSE HOD ఎవరు?", (("cse", "hod"),)),
    ("te", "data science HOD ఎవరు?", (("cse_ds", "hod"),)),
    ("te", "CSE faculty చూపించు", (("cse", "faculty"),)),
    ("te", "ECE fees ఎంత?", (("ece", "fees"),)),
    ("te", "CSE HOD మరియు Data Science HOD ఎవరు?", (("cse", "hod"), ("cse_ds", "hod"))),
    ("te", "CSE HOD మరియు Data Science fees చూపించు", (("cse", "hod"), ("cse_ds", "fees"))),
    ("ml", "ഡാറ്റ സയൻസ് HOD ആരാണ്?", (("cse_ds", "hod"),)),
    ("ml", "CSE HOD ആരാണ്?", (("cse", "hod"),)),
    ("ml", "data science HOD ആരാണ്?", (("cse_ds", "hod"),)),
    ("ml", "CSE faculty കാണിക്കൂ", (("cse", "faculty"),)),
    ("ml", "ECE fees എത്ര?", (("ece", "fees"),)),
    ("ml", "CSE HOD ഉം Data Science HOD ഉം ആരാണ്?", (("cse", "hod"), ("cse_ds", "hod"))),
    ("ml", "CSE HOD ഉം Data Science fees ഉം കാണിക്കൂ", (("cse", "hod"), ("cse_ds", "fees"))),
]


@pytest.mark.parametrize(("language", "text", "items"), CORE_CASES)
def test_core_canonical_matrix(language: str, text: str, items: tuple[tuple[str, str], ...]) -> None:
    request = parse_semantic_request(raw_text=text, language_code_key=language)
    assert request is not None, text
    assert request.unit_items == items
    assert semantic_fallback_reason(request) is None
    plan = select_content_units(request, surface=request.requested_card_ids[0])
    assert plan is not None
    assert plan.units == tuple(f"{entity}.{topic}" for entity, topic in items)


@pytest.mark.parametrize(
    ("language", "text"),
    [
        ("te", "డేటా సైన్స్ డిపార్ట్మెంట్ చూపించు"),
        ("ml", "ഡാറ്റ സയൻസ് ഡിപ്പാർട്ട്മെന്റ് കാണിക്കൂ"),
    ],
)
def test_native_department_overview(language: str, text: str) -> None:
    request = parse_semantic_request(raw_text=text, language_code_key=language)
    assert request is not None
    assert request.unit_items == (("cse_ds", "overview"),)


@pytest.mark.parametrize(
    ("language", "text", "items"),
    [
        ("te", "CSE HOD మరియు faculty చూపించు", (("cse", "hod"), ("cse", "faculty"))),
        ("ml", "CSE HOD ഉം faculty ഉം കാണിക്കൂ", (("cse", "hod"), ("cse", "faculty"))),
        ("te", "CSE HOD, Data Science faculty మరియు ECE fees చూపించు", (("cse", "hod"), ("cse_ds", "faculty"), ("ece", "fees"))),
        ("ml", "CSE HOD, Data Science faculty, ECE fees കാണിക്കൂ", (("cse", "hod"), ("cse_ds", "faculty"), ("ece", "fees"))),
    ],
)
def test_multi_card_order(language: str, text: str, items: tuple[tuple[str, str], ...]) -> None:
    request = parse_semantic_request(raw_text=text, language_code_key=language)
    assert request is not None
    assert request.unit_items == items


@pytest.mark.parametrize(
    ("language", "text", "items"),
    [
        ("te", "డేటా సైన్స్ విభాగం అధిపతి ఎవరు?", (("cse_ds", "hod"),)),
        ("ml", "ഡാറ്റ സയൻസ് വിഭാഗത്തിന്റെ മേധാവി ആരാണ്?", (("cse_ds", "hod"),)),
        ("te", "కంప్యూటర్ సైన్స్ & ఇంజనీరింగ్ HOD ఎవరు?", (("cse", "hod"),)),
        ("ml", "കമ്പ്യൂട്ടർ സയൻസ് & എഞ്ചിനീയറിംഗ് HOD ആരാണ്?", (("cse", "hod"),)),
        ("te", "మెకానికల్ ఇంజనీరింగ్ fees ఎంత?", (("mechanical", "fees"),)),
        ("ml", "മെക്കാനിക്കൽ എഞ്ചിനീയറിംഗ് fees എത്ര?", (("mechanical", "fees"),)),
        ("te", "CSE అధ్యాపకులు చూపించు", (("cse", "faculty"),)),
        ("ml", "CSE അധ്യാപകർ കാണിക്കൂ", (("cse", "faculty"),)),
        ("te", "ECE ఫీజు ఎంత?", (("ece", "fees"),)),
        ("ml", "ECE ഫീസ് എത്ര?", (("ece", "fees"),)),
        ("te", "ECE ప్లేస్‌మెంట్ చూపించు", (("ece", "placements"),)),
        ("ml", "ECE പ്ലേസ്‌മെന്റ് കാണിക്കൂ", (("ece", "placements"),)),
    ],
)
def test_native_entity_and_topic_combinations(
    language: str,
    text: str,
    items: tuple[tuple[str, str], ...],
) -> None:
    request = parse_semantic_request(raw_text=text, language_code_key=language)
    assert request is not None
    assert request.unit_items == items


@pytest.mark.parametrize(
    ("language", "overview", "followup", "topic"),
    [
        ("te", "డేటా సైన్స్ డిపార్ట్మెంట్ చూపించు", "HOD కూడా", "hod"),
        ("te", "డేటా సైన్స్ డిపార్ట్మెంట్ చూపించు", "faculty కూడా", "faculty"),
        ("ml", "ഡാറ്റ സയൻസ് ഡിപ്പാർട്ട്മെന്റ് കാണിക്കൂ", "HOD കൂടി", "hod"),
        ("ml", "ഡാറ്റ സയൻസ് ഡിപ്പാർട്ട്മെന്റ് കാണിക്കൂ", "faculty കൂടി", "faculty"),
    ],
)
def test_followup_reuses_active_department(
    language: str,
    overview: str,
    followup: str,
    topic: str,
) -> None:
    first = parse_semantic_request(raw_text=overview, language_code_key=language)
    assert first is not None and first.entities == ("cse_ds",)
    second = parse_semantic_request(
        raw_text=followup,
        language_code_key=language,
        ci_entities={"department": "cse_ds"},
    )
    assert second is not None
    assert second.unit_items == (("cse_ds", topic),)


@pytest.mark.parametrize(
    ("language", "text"),
    [
        ("te", "CSE మరియు Data Science HODs ఎవరు?"),
        ("ml", "CSE ഉം Data Science ഉം HOD ആരാണ്?"),
    ],
)
def test_shared_hod_intent_broadcasts_without_cross_product(language: str, text: str) -> None:
    request = parse_semantic_request(raw_text=text, language_code_key=language)
    assert request is not None
    assert request.unit_items == (("cse", "hod"), ("cse_ds", "hod"))


@pytest.mark.parametrize(
    ("language", "text", "items"),
    [
        ("te", "ప్రిన్సిపాల్ ఎవరు?", (("leadership", "principal"),)),
        ("ml", "പ്രിൻസിപ്പൽ ആരാണ്?", (("leadership", "principal"),)),
        ("te", "కాలేజీ ఎక్కడ ఉంది?", (("college", "location"),)),
        ("ml", "കോളേജ് എവിടെയാണ്?", (("college", "location"),)),
        ("te", "ప్రవేశాల వివరాలు చూపించు", (("college", "admissions"),)),
        ("ml", "പ്രവേശന വിവരങ്ങൾ കാണിക്കൂ", (("college", "admissions"),)),
        ("te", "బాలికల హాస్టల్ చూపించు", (("hostel.girls", "overview"),)),
        ("ml", "പെൺകുട്ടികളുടെ ഹോസ്റ്റൽ കാണിക്കൂ", (("hostel.girls", "overview"),)),
        ("te", "కాంటీన్ చూపించు", (("canteen", "overview"),)),
        ("ml", "കാന്റീൻ കാണിക്കൂ", (("canteen", "overview"),)),
    ],
)
def test_native_global_leadership_and_campus_cards(
    language: str,
    text: str,
    items: tuple[tuple[str, str], ...],
) -> None:
    request = parse_semantic_request(raw_text=text, language_code_key=language)
    assert request is not None
    assert request.unit_items == items
    assert semantic_fallback_reason(request) is None


@pytest.mark.parametrize(
    ("language", "text", "intent", "surface"),
    [
        ("te", "డేటా సైన్స్ HOD ఎవరు?", INTENT_HOD_PROFILE, SURFACE_HOD),
        ("ml", "ഡാറ്റ സയൻസ് HOD ആരാണ്?", INTENT_HOD_PROFILE, SURFACE_HOD),
        ("te", "ECE fees ఎంత?", INTENT_DEPARTMENT_FEES, SURFACE_DEPARTMENT_FEES),
        ("ml", "ECE fees എത്ര?", INTENT_DEPARTMENT_FEES, SURFACE_DEPARTMENT_FEES),
        ("te", "CSE faculty చూపించు", "NORMAL_QUERY", SURFACE_FACULTY),
        ("ml", "CSE faculty കാണിക്കൂ", "NORMAL_QUERY", SURFACE_FACULTY),
    ],
)
def test_specific_surface_is_preserved(
    language: str,
    text: str,
    intent: str,
    surface: str,
) -> None:
    request = parse_semantic_request(raw_text=text, language_code_key=language)
    assert request is not None
    resolution = resolve_presentation(
        decision=PolicyDecision(
            action=PolicyAction.CARD_PRESENTATION,
            answer_source="intent",
            length_kind="presentation",
        ),
        resolution=ConversationResolution(language_code_key=language),
        intent=intent,
        semantic_topic=request.topic.upper(),
        entities={"department": request.entities[0]},
        user_text=text,
        semantic_request=request,
    )
    assert resolution.card_surface == surface
    assert resolution.show_card == surface
    assert resolution.presentation_type == surface
