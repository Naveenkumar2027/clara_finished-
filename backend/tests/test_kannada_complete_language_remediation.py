from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from backend.services import greetings
from backend.services.answer_generation import (
    BUS_ROUTES_SPOKEN_PROMPT_BY_LANGUAGE,
    COURSE_MENU_SPOKEN_PROMPT_BY_LANGUAGE,
    OFF_TOPIC_REPLY_BY_LANGUAGE,
    PROFILE_REPLY_TEMPLATES,
    generated_reply_is_safe_for_language,
)
from backend.services.content.content_unit_resolver import resolve_unit
from backend.services.content.unit_narration import narrate_unit
from backend.services.greetings import get_name_prompt, get_ready_prompt, normalize_guest_name
from backend.services.ui_localization import ui_text
from backend.services.answer_generation import load_locale_data_for_lang_key
from backend.services.narration_plan import DOCUMENT_ITEMS, DOCUMENT_TITLES, _admissions_slides


ROOT = Path(__file__).resolve().parents[2]
SAMPLE_STATUS = "SAMPLE_REPLACE_WITH_OFFICIAL"
BLOCKED_KN = (
    "ಈ ಮಾಹಿತಿಯನ್ನು ಇನ್ನೂ ಅಧಿಕೃತವಾಗಿ ದೃಢೀಕರಿಸಲಾಗಿಲ್ಲ.\n"
    "ಹೆಚ್ಚಿನ ಮಾಹಿತಿಗಾಗಿ ಸಂಬಂಧಿತ ವಿಭಾಗವನ್ನು ಸಂಪರ್ಕಿಸಿ."
)


def test_exact_kannada_fixed_ui_goldens() -> None:
    expected = {
        "welcome.general_display": "ಸ್ವಾಗತ.\nಇಂದು ನಿಮಗೆ ಯಾವ ಮಾಹಿತಿ ಬೇಕು?",
        "welcome.general_narration": "ಸ್ವಾಗತ. ಇಂದು ನಿಮಗೆ ಯಾವ ಮಾಹಿತಿ ಬೇಕು?",
        "welcome.name_prompt": "ದಯವಿಟ್ಟು ನಿಮ್ಮನ್ನು ಯಾವ ಹೆಸರಿನಿಂದ ಕರೆಯಬೇಕೆಂದು ತಿಳಿಸಿ.",
        "language.select": "ಭಾಷೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ.",
        "status.listening": "ನಿಮ್ಮ ಮಾತನ್ನು ಆಲಿಸುತ್ತಿದ್ದೇನೆ…",
        "status.processing": "ನಿಮ್ಮ ವಿನಂತಿಯನ್ನು ಪ್ರಕ್ರಿಯೆಗೊಳಿಸಲಾಗುತ್ತಿದೆ…",
        "clarification.department": "ನೀವು ಯಾವ ವಿಭಾಗದ ಬಗ್ಗೆ ತಿಳಿದುಕೊಳ್ಳಲು ಬಯಸುತ್ತೀರಿ?",
        "error.retry": "ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
        "session.timeout": "ಈ ಸಂವಾದದ ಅವಧಿ ಮುಗಿದಿದೆ.",
        "session.thank_you": "ಧನ್ಯವಾದಗಳು.",
        "session.ending": "ಈ ಸಂವಾದವು ಈಗ ಮುಕ್ತಾಯಗೊಳ್ಳುತ್ತಿದೆ.",
        "availability.official_fact_blocked": BLOCKED_KN,
    }
    assert {key: ui_text("kn", key) for key in expected} == expected


def test_corrected_critical_kannada_semantic_goldens() -> None:
    expected = {
        "clarification.hod_card": "ವಿಭಾಗದ ಮುಖ್ಯಸ್ಥರು ಮತ್ತು ಧ್ಯೇಯದೃಷ್ಟಿಯ ಬಗ್ಗೆ ತಿಳಿದುಕೊಳ್ಳಲು, ದಯವಿಟ್ಟು ವಿಭಾಗದ ಹೆಸರನ್ನು ಹೇಳಿ ಅಥವಾ ಆಯ್ಕೆಮಾಡಿ.",
        "error.voice_unrecognized": "ನೀವು ಹೇಳಿದ್ದು ಅರ್ಥವಾಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ ಅಥವಾ ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಟೈಪ್ ಮಾಡಿ.",
        "availability.off_topic": "ಆ ವಿಷಯದಲ್ಲಿ ನಾನು ಸಹಾಯ ಮಾಡಲು ಸಾಧ್ಯವಿಲ್ಲ. ಆದರೆ SVIT ಪ್ರವೇಶಾತಿ, ವಿಭಾಗಗಳು, ಶುಲ್ಕ, ಪ್ಲೇಸ್‌ಮೆಂಟ್‌ಗಳು, ಅಧ್ಯಾಪಕರು ಮತ್ತು ಕ್ಯಾಂಪಸ್ ಸೌಲಭ್ಯಗಳ ಕುರಿತ ಪ್ರಶ್ನೆಗಳಿಗೆ ಉತ್ತರಿಸಬಲ್ಲೆ.",
        "cards.hod_and_vision": "ವಿಭಾಗ ಮುಖ್ಯಸ್ಥರು (HOD) ಮತ್ತು ಧ್ಯೇಯದೃಷ್ಟಿ",
        "action.location": "SVIT ಕರ್ನಾಟಕದ ಬೆಂಗಳೂರಿನ ರಾಜಾನುಕುಂಟೆಯಲ್ಲಿ, ಯಲಹಂಕ ಮಾರ್ಗದಲ್ಲಿ, 560 064 ಅಂಚೆ ಸಂಖ್ಯೆಯ ಪ್ರದೇಶದಲ್ಲಿದೆ.",
        "action.principal": "ಪ್ರಾಂಶುಪಾಲರ ಪರಿಚಯವನ್ನು ಪರದೆಯ ಮೇಲೆ ತೋರಿಸಲಾಗುತ್ತಿದೆ.",
        "action.vice_principal": "ಉಪ ಪ್ರಾಂಶುಪಾಲರ ಪರಿಚಯವನ್ನು ಪರದೆಯ ಮೇಲೆ ತೋರಿಸಲಾಗುತ್ತಿದೆ.",
        "action.course_menu": "ನಮ್ಮ ಕಾಲೇಜಿನಲ್ಲಿ ಲಭ್ಯವಿರುವ ವಿಭಾಗಗಳು ಇಲ್ಲಿವೆ. ದಯವಿಟ್ಟು ಒಂದು ವಿಭಾಗವನ್ನು ಆಯ್ಕೆಮಾಡಿ.",
        "action.bus_routes": "ನಮ್ಮ ಕಾಲೇಜಿನ ಬಸ್ ಮಾರ್ಗಗಳು ಇಲ್ಲಿವೆ. ಬಸ್ ಏರುವ ನಿಲ್ದಾಣಗಳು ಮತ್ತು ಸಮಯಗಳನ್ನು ನೋಡಲು ಒಂದು ಮಾರ್ಗವನ್ನು ಆಯ್ಕೆಮಾಡಿ.",
    }
    assert {key: ui_text("kn", key) for key in expected} == expected


def test_corrected_institutional_kannada_preserves_verified_facts() -> None:
    data = load_locale_data_for_lang_key("kn")
    civil_hod = data["departments"]["civil"]["hod_voice"]
    mba_hod = data["departments"]["mba"]["hod_voice"]
    objectives = data["placements_and_training"]["objectives"]
    programs = data["placements_and_training"]["training_programs"]

    assert civil_hod == "ಡಾ. ಅನಂತಯ್ಯ ಎಂ ಬಿ ಅವರು ವಿದ್ಯಾರ್ಥಿಗಳನ್ನು ಮುಂಚೂಣಿ ಸಾಧಕರಾಗಿಯೂ ನೈಸರ್ಗಿಕ ಸಂಪನ್ಮೂಲಗಳ ರಕ್ಷಕರಾಗಿಯೂ ರೂಪಿಸುವ ನಮ್ಮ ಧ್ಯೇಯಕ್ಕೆ ಮಾರ್ಗದರ್ಶನ ನೀಡುತ್ತಾರೆ."
    assert mba_hod == "25+ ವರ್ಷಗಳ ಅನುಭವ ಹೊಂದಿರುವ ಡಾ. ಜೋಗೀಶ್ ಡಿ ಅವರ ನೇತೃತ್ವದಲ್ಲಿ, ಹಣಕಾಸು, HR, IT ಮತ್ತು ಮಾರ್ಕೆಟಿಂಗ್ ವಿಶೇಷೀಕರಣಗಳಲ್ಲಿ ಪರಿಣತಿ ನೀಡಲಾಗುತ್ತದೆ."
    assert "100%" in objectives and "ವೃತ್ತಿಪರ ವೃತ್ತಿ ಮಾರ್ಗದರ್ಶನ" in objectives
    assert "ವಾರಕ್ಕೊಮ್ಮೆ" in programs and "IT" in programs


@pytest.mark.parametrize("name", ["ಆಶಾ", "Asha", "Dr. ಆಶಾ Rao", "CSE ವಿದ್ಯಾರ್ಥಿ"])
def test_named_welcome_preserves_name_and_kannada_grammar(name: str) -> None:
    assert get_ready_prompt("Kannada", name) == (
        f"{name} ಅವರೇ, ಸ್ವಾಗತ. ಇಂದು ನಿಮಗೆ ಯಾವ ಮಾಹಿತಿ ಬೇಕು?"
    )


def test_missing_and_long_names_do_not_break_a_grapheme() -> None:
    assert get_ready_prompt("Kannada") == "ಸ್ವಾಗತ. ಇಂದು ನಿಮಗೆ ಯಾವ ಮಾಹಿತಿ ಬೇಕು?"
    assert get_name_prompt("Kannada") == "ದಯವಿಟ್ಟು ನಿಮ್ಮನ್ನು ಯಾವ ಹೆಸರಿನಿಂದ ಕರೆಯಬೇಕೆಂದು ತಿಳಿಸಿ."
    assert normalize_guest_name("ಆ" * 80) is None
    long_words = "ಆಶಾ " * 20
    normalized = normalize_guest_name(long_words)
    assert normalized
    assert len(normalized) <= 48
    assert not normalized.endswith("್")


def test_kannada_name_prompt_is_resolved_at_call_time(monkeypatch: pytest.MonkeyPatch) -> None:
    values = iter(("ಮೊದಲ ಪಠ್ಯ", "ನವೀಕರಿಸಿದ ಪಠ್ಯ"))
    monkeypatch.setattr(greetings, "ui_text", lambda *_args, **_kwargs: next(values))

    assert greetings.get_name_prompt("Kannada") == "ಮೊದಲ ಪಠ್ಯ"
    assert greetings.get_name_prompt("kn-IN") == "ನವೀಕರಿಸಿದ ಪಠ್ಯ"


def test_kannada_placeholder_is_internal_only_and_never_narrated() -> None:
    unit = resolve_unit(
        unit_id="hostel.girls.rooms",
        language="Kannada",
        language_code="kn",
    )
    assert unit is not None
    assert unit.metadata["content_status"] == SAMPLE_STATUS
    spoken = narrate_unit(unit, "kn")
    assert spoken == BLOCKED_KN.replace("\n", " ")
    assert SAMPLE_STATUS not in spoken
    assert "ಮಾದರಿ" not in unit.title


@pytest.mark.parametrize(
    "unsafe",
    [
        "Here is the answer.",
        '{"answer": "ಪಠ್ಯ"}',
        "SAMPLE_REPLACE_WITH_OFFICIAL",
        "ಮಾಹಿತಿ [source: 12]",
        "```json\n[]\n```",
    ],
)
def test_generated_kannada_rejects_language_and_metadata_leaks(unsafe: str) -> None:
    assert not generated_reply_is_safe_for_language(unsafe, "kn")


def test_generated_kannada_accepts_concise_kannada_with_protected_acronyms() -> None:
    assert generated_reply_is_safe_for_language(
        "SVIT ನಲ್ಲಿ CSE ವಿಭಾಗದ ಮಾಹಿತಿ ಲಭ್ಯವಿದೆ.", "kn"
    )


def test_conflicting_fee_structures_are_blocked_from_kannada_narration() -> None:
    slides = _admissions_slides(load_locale_data_for_lang_key("kn"), "kn")
    fee_slides = [(title, body) for title, body in slides if "ಶುಲ್ಕ" in title]
    assert len(fee_slides) >= 2
    for _, body in fee_slides:
        assert "ಅಧಿಕೃತವಾಗಿ ದೃಢೀಕರಿಸಲಾಗಿಲ್ಲ" in body
        assert "{'" not in body
        assert "₹" not in body


def test_authoritative_ui_contract_is_parseable_and_complete() -> None:
    data = json.loads((ROOT / "backend/data/locales/ui.json").read_text(encoding="utf-8"))
    assert set(data) == {"en", "hi", "kn", "te", "ml"}
    assert set(data["en"]) == set(data["kn"]) == set(data["hi"])
    assert data["kn"]["welcome"]["general_narration"] == get_ready_prompt("Kannada")
    assert ui_text("kn", "documents.items.aadhaar") == "ಆಧಾರ್ ಕಾರ್ಡ್‌ನ ಪ್ರತಿ"
    assert ui_text("kn", "comparison.heading") == "ಕಾರ್ಯಕ್ರಮಗಳ ಹೋಲಿಕೆ"
    assert "backend/data/locales/ui.json" in (
        ROOT / "frontend/src/localization/uiCopy.ts"
    ).read_text(encoding="utf-8").replace("@college-locales", "backend/data/locales")


def test_kannada_ui_contract_has_recursive_key_and_placeholder_parity() -> None:
    data = json.loads((ROOT / "backend/data/locales/ui.json").read_text(encoding="utf-8"))

    def flatten(value: object, prefix: str = "") -> dict[str, str]:
        if not isinstance(value, dict):
            return {prefix: str(value)}
        result: dict[str, str] = {}
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            result.update(flatten(child, path))
        return result

    english = flatten(data["en"])
    kannada = flatten(data["kn"])
    assert set(kannada) == set(english)
    assert all(value.strip() for value in kannada.values())
    placeholder = re.compile(r"\{[^{}]+\}")
    assert {
        path: placeholder.findall(value) for path, value in kannada.items()
    } == {
        path: placeholder.findall(value) for path, value in english.items()
    }


def test_fixed_kannada_dynamic_surfaces_use_complete_ui_templates() -> None:
    assert COURSE_MENU_SPOKEN_PROMPT_BY_LANGUAGE["Kannada"] == ui_text(
        "kn", "action.course_menu"
    )
    assert BUS_ROUTES_SPOKEN_PROMPT_BY_LANGUAGE["Kannada"] == ui_text(
        "kn", "action.bus_routes"
    )
    assert OFF_TOPIC_REPLY_BY_LANGUAGE["Kannada"] == ui_text("kn", "availability.off_topic")
    assert PROFILE_REPLY_TEMPLATES["Kannada"] == {
        "hod": ui_text("kn", "profile.hod"),
        "trustees": ui_text("kn", "profile.trustees"),
        "both": ui_text("kn", "profile.hod_and_trustees"),
    }
    document_paths = (
        "marks_10",
        "marks_12",
        "rank_allotment",
        "transfer",
        "conduct",
        "caste_income",
        "aadhaar",
        "photos",
        "migration",
        "vtu_eligibility",
    )
    assert DOCUMENT_ITEMS["kn"] == [
        ui_text("kn", f"documents.items.{key}") for key in document_paths
    ]
    assert DOCUMENT_TITLES["kn"] == ui_text("kn", "documents.title")


def test_orphan_frontend_locale_is_not_imported_by_production_code() -> None:
    source_root = ROOT / "frontend/src"
    for path in source_root.rglob("*.ts*"):
        if "__tests__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        assert "src/data/locales/kn.json" not in text
        assert "./data/locales/kn.json" not in text
        assert "../data/locales/kn.json" not in text
