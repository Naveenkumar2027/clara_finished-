"""Exact-string goldens for the 2 Batch 6 SAFE_CORRECTION_CANDIDATE applied corrections.

Scope: kn.departments.cse_aiml.fees and kn.departments.cse_ds.fees.
No other row is asserted here.

These two corrections replace the incorrect management-quota terminology
(ನಿರ್ವಹಣೆ = "maintenance") with the glossary term (ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್ ಕೋಟಾ =
"management quota"). Protected tokens (KCET, KEA, ₹, /ವರ್ಷ, fee amounts)
and the literal `|` separator are preserved exactly.

The `|` pipe separator reaching TTS is a pre-existing global sanitizer
defect and is tracked in a separate deferred workstream; it does not
invalidate the terminology correction.
"""
from __future__ import annotations

from backend.services.answer_generation import load_locale_data_for_lang_key
from backend.services.content.content_unit_registry import (
    get_unit_descriptor,
)


APPROVED = {
    "kn.departments.cse_aiml.fees": (
        "KCET: KEA ಮಾನದಂಡಗಳ ಪ್ರಕಾರ | ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್ ಕೋಟಾ: ₹3,50,000/ವರ್ಷ"
    ),
    "kn.departments.cse_ds.fees": (
        "KCET: KEA ಮಾನದಂಡಗಳ ಪ್ರಕಾರ | ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್ ಕೋಟಾ: ₹3,00,000/ವರ್ಷ"
    ),
}


# --- Exact-string approval (read through the authoritative locale loader) ---


def test_kn_departments_cse_aiml_fees_approved_value() -> None:
    data = load_locale_data_for_lang_key("kn")
    assert data["departments"]["cse_aiml"]["fees"] == APPROVED["kn.departments.cse_aiml.fees"]


def test_kn_departments_cse_ds_fees_approved_value() -> None:
    data = load_locale_data_for_lang_key("kn")
    assert data["departments"]["cse_ds"]["fees"] == APPROVED["kn.departments.cse_ds.fees"]


# --- Protected-token assertions (cheap, high-signal) ---


def test_cse_aiml_fees_contains_required_tokens() -> None:
    fees = APPROVED["kn.departments.cse_aiml.fees"]
    assert "KCET" in fees
    assert "KEA" in fees
    assert "ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್ ಕೋಟಾ" in fees
    assert "₹3,50,000" in fees
    assert "ವರ್ಷ" in fees


def test_cse_ds_fees_contains_required_tokens() -> None:
    fees = APPROVED["kn.departments.cse_ds.fees"]
    assert "KCET" in fees
    assert "KEA" in fees
    assert "ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್ ಕೋಟಾ" in fees
    assert "₹3,00,000" in fees
    assert "ವರ್ಷ" in fees


# --- Defect absence: the standalone ನಿರ್ವಹಣೆ: terminology must not appear ---


def test_cse_aiml_fees_omits_incorrect_terminology() -> None:
    fees = APPROVED["kn.departments.cse_aiml.fees"]
    # The pre-pilot defect was "ನಿರ್ವಹಣೆ:" (maintenance, with colon separator).
    assert "ನಿರ್ವಹಣೆ:" not in fees


def test_cse_ds_fees_omits_incorrect_terminology() -> None:
    fees = APPROVED["kn.departments.cse_ds.fees"]
    # The pre-pilot defect was "ನಿರ್ವಹಣೆ:" (maintenance, with colon separator).
    assert "ನಿರ್ವಹಣೆ:" not in fees


# --- Amount preservation: the two department fees remain different ---


def test_two_department_fee_amounts_remain_different_and_unchanged() -> None:
    aiml = APPROVED["kn.departments.cse_aiml.fees"]
    ds = APPROVED["kn.departments.cse_ds.fees"]
    # Department-specific amounts must be preserved exactly.
    assert "₹3,50,000" in aiml
    assert "₹3,00,000" in ds
    # They are intentionally different per-department amounts; not a conflict.
    assert aiml != ds
    assert "₹3,50,000" not in ds
    assert "₹3,00,000" not in aiml


# --- Runtime path: the three CSE-family fee units are registered and loadable ---


def test_cse_aiml_fees_unit_descriptor_is_registered() -> None:
    desc = get_unit_descriptor("cse_aiml.fees")
    assert desc is not None
    assert desc.context == "department"
    assert desc.context_id == "cse_aiml"
    assert desc.section_id == "fees"


def test_cse_ds_fees_unit_descriptor_is_registered() -> None:
    desc = get_unit_descriptor("cse_ds.fees")
    assert desc is not None
    assert desc.context == "department"
    assert desc.context_id == "cse_ds"
    assert desc.section_id == "fees"


def test_cse_fees_unit_descriptor_still_registered() -> None:
    """Pilot-applied cse.fees must still resolve through the registry."""
    desc = get_unit_descriptor("cse.fees")
    assert desc is not None
    assert desc.context == "department"
    assert desc.context_id == "cse"
    assert desc.section_id == "fees"


def test_cse_family_fee_values_load_via_authoritative_loader() -> None:
    """End-to-end: the locale loader returns the approved exact strings for all
    three CSE-family fee units. This is the same path the content resolver uses
    (load_locale_data_for_lang_key('kn') → data['departments'][dept_key]['fees'])."""
    data = load_locale_data_for_lang_key("kn")
    # Pilot-applied cse.fees uses 'ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್' (no 'ಕೋಟಾ') — different but equivalent
    # glossary form. It must still be present and must not contain ನಿರ್ವಹಣೆ.
    cse = data["departments"]["cse"]["fees"]
    assert "KCET" in cse
    assert "KEA" in cse
    assert "₹3,50,000" in cse
    assert "ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್" in cse
    assert "ನಿರ್ವಹಣೆ:" not in cse
    # New Batch 6 corrections.
    assert data["departments"]["cse_aiml"]["fees"] == APPROVED["kn.departments.cse_aiml.fees"]
    assert data["departments"]["cse_ds"]["fees"] == APPROVED["kn.departments.cse_ds.fees"]
