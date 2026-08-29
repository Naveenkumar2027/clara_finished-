"""Exact-string goldens for the 5 SAFE_TO_APPLY pilot corrections applied in this batch.

Scope: ui.error.backend and kn.departments.cse.{intro,hod_voice,fees,placement}.
No other row is asserted here. Each test asserts the exact approved Kannada value
and verifies protected tokens (names, acronyms, currency, numbers) are present.
"""
from __future__ import annotations

import pytest

from backend.services.answer_generation import load_locale_data_for_lang_key
from backend.services.ui_localization import ui_text


APPROVED = {
    "ui.error.backend": "ಸೇವೆಯು ತಾತ್ಕಾಲಿಕವಾಗಿ ಲಭ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
    "kn.departments.cse.intro": (
        "ಕಂಪ್ಯೂಟರ್ ಸೈನ್ಸ್ ಮತ್ತು ಎಂಜಿನಿಯರಿಂಗ್ ವಿಭಾಗವು ಅತ್ಯಾಧುನಿಕ ಪಠ್ಯಕ್ರಮದೊಂದಿಗೆ ಡಿಜಿಟಲ್ ಕ್ರಾಂತಿಯನ್ನು ಮುನ್ನಡೆಸುತ್ತದೆ. "
        "ನಾವು ವಿದ್ಯಾರ್ಥಿಗಳನ್ನು ಉನ್ನತ ದರ್ಜೆಯ ಸಾಫ್ಟ್‌ವೇರ್ ಡೆವಲಪರ್‌ಗಳಾಗಿ ಮತ್ತು ಸಿಸ್ಟಮ್ ಆರ್ಕಿಟೆಕ್ಟ್‌ಗಳಾಗಿ ರೂಪಿಸುತ್ತೇವೆ."
    ),
    "kn.departments.cse.hod_voice": (
        "ಡಾ. ಶಶಿಕುಮಾರ್ ಡಿ ಆರ್ ಅವರ ನೇತೃತ್ವದಲ್ಲಿ, ನಮ್ಮ ದೃಷ್ಟಿಕೋನವು ಜಾಗತಿಕ ಬೇಡಿಕೆಗಳಿಗೆ ಅನುಗುಣವಾಗಿ ಉದ್ಯಮಾಧಾರಿತ ಕಲಿಕೆಯ ಮೇಲೆ ಕೇಂದ್ರೀಕರಿಸುತ್ತದೆ. "
        "ನಾವು ಪ್ರಾಯೋಗಿಕ ಸಮಸ್ಯೆ ಪರಿಹಾರ ಮತ್ತು ನೈತಿಕ ಕೋಡಿಂಗ್ ಅಭ್ಯಾಸಗಳಿಗೆ ಆದ್ಯತೆ ನೀಡುತ್ತೇವೆ."
    ),
    "kn.departments.cse.fees": "KCET: KEA ಮಾನದಂಡಗಳ ಪ್ರಕಾರ | ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್: ₹3,50,000/ವರ್ಷ",
    "kn.departments.cse.placement": (
        "ಉನ್ನತ ನೇಮಕಾತಿದಾರರಲ್ಲಿ TCS, Infosys ಮತ್ತು Amazon ಸೇರಿವೆ. "
        "ವಿದ್ಯಾರ್ಥಿಗಳು ಕಠಿಣ ತಾಂತ್ರಿಕ ಮತ್ತು ಆಪ್ಟಿಟ್ಯೂಡ್ ತರಬೇತಿಯನ್ನು ಪಡೆಯುತ್ತಾರೆ."
    ),
}


def test_ui_error_backend_approved_value() -> None:
    assert ui_text("kn", "error.backend") == APPROVED["ui.error.backend"]


def test_kn_departments_cse_intro_approved_value() -> None:
    data = load_locale_data_for_lang_key("kn")
    assert data["departments"]["cse"]["intro"] == APPROVED["kn.departments.cse.intro"]


def test_kn_departments_cse_hod_voice_approved_value() -> None:
    data = load_locale_data_for_lang_key("kn")
    assert data["departments"]["cse"]["hod_voice"] == APPROVED["kn.departments.cse.hod_voice"]


def test_kn_departments_cse_fees_approved_value() -> None:
    data = load_locale_data_for_lang_key("kn")
    assert data["departments"]["cse"]["fees"] == APPROVED["kn.departments.cse.fees"]


def test_kn_departments_cse_placement_approved_value() -> None:
    data = load_locale_data_for_lang_key("kn")
    assert data["departments"]["cse"]["placement"] == APPROVED["kn.departments.cse.placement"]


# --- Protected-token assertions (cheap, high-signal) -------------------------


def test_cse_fees_preserves_kcet_kea_currency_and_number() -> None:
    fees = APPROVED["kn.departments.cse.fees"]
    assert "KCET" in fees
    assert "KEA" in fees
    assert "₹3,50,000" in fees
    assert "ವರ್ಷ" in fees


def test_cse_placement_preserves_latin_company_names() -> None:
    placement = APPROVED["kn.departments.cse.placement"]
    assert "TCS" in placement
    assert "Infosys" in placement
    assert "Amazon" in placement
    # Sarvam had narrowed "students" to "female students"; assert the safe term is kept.
    assert "ವಿದ್ಯಾರ್ಥಿಗಳು" in placement
    assert "ವಿದ್ಯಾರ್ಥಿನಿಯರು" not in placement


def test_cse_hod_voice_preserves_hod_name_token() -> None:
    hod = APPROVED["kn.departments.cse.hod_voice"]
    assert "ಡಾ. ಶಶಿಕುಮಾರ್ ಡಿ ಆರ್" in hod
    # Honorific added; HOD name itself is unchanged.
    assert "ಅವರ" in hod
