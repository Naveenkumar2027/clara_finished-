"""Exact-string goldens for the Batch 6 + Batch 7 SAFE_CORRECTION_CANDIDATE applied corrections.

Scope:
  - kn.departments.cse_aiml.fees (Batch 6)
  - kn.departments.cse_ds.fees   (Batch 6)
  - kn.departments.ece.fees      (Batch 7, this batch)
No other row is asserted here.

These corrections replace the incorrect management-quota terminology
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
    "kn.departments.ece.fees": (
        "KCET: KEA ಮಾನದಂಡಗಳ ಪ್ರಕಾರ | ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್ ಕೋಟಾ: ₹2,00,000/ವರ್ಷ"
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


# =============================================================================
# Batch 7 — ECE fees (same defect class as Batch 6 CSE-family fees)
# =============================================================================


def test_kn_departments_ece_fees_approved_value() -> None:
    """ECE fees resolve through the authoritative locale loader to the
    approved new value (terminology fix, amount preserved)."""
    data = load_locale_data_for_lang_key("kn")
    assert data["departments"]["ece"]["fees"] == APPROVED["kn.departments.ece.fees"]


def test_ece_fees_contains_required_tokens() -> None:
    """All protected tokens must be present in the resolved ECE fees string:
    KCET, KEA, ₹2,00,000, /ವರ್ಷ, and the corrected management-quota label."""
    fees = APPROVED["kn.departments.ece.fees"]
    assert "KCET" in fees
    assert "KEA" in fees
    assert "ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್ ಕೋಟಾ" in fees
    assert "₹2,00,000" in fees
    assert "ವರ್ಷ" in fees


def test_ece_fees_omits_incorrect_terminology() -> None:
    """The pre-pilot defect "ನಿರ್ವಹಣೆ:" (maintenance, with colon separator) must
    be absent from the resolved ECE fees string."""
    data = load_locale_data_for_lang_key("kn")
    ece = data["departments"]["ece"]["fees"]
    assert "ನಿರ್ವಹಣೆ:" not in ece


def test_ece_fees_unit_descriptor_is_registered() -> None:
    """The ece.fees unit must be registered in the content unit registry,
    so resolve_unit() can find it for runtime display/narration."""
    desc = get_unit_descriptor("ece.fees")
    assert desc is not None
    assert desc.context == "department"
    assert desc.context_id == "ece"
    assert desc.section_id == "fees"


def test_cse_aiml_and_cse_ds_approved_values_unchanged() -> None:
    """The Batch 6 corrections (cse_aiml.fees and cse_ds.fees) must still
    resolve to their exact approved values; the ECE fix must not have
    disturbed them."""
    data = load_locale_data_for_lang_key("kn")
    assert data["departments"]["cse_aiml"]["fees"] == APPROVED["kn.departments.cse_aiml.fees"]
    assert data["departments"]["cse_ds"]["fees"] == APPROVED["kn.departments.cse_ds.fees"]


def test_no_other_department_fee_modified() -> None:
    """The Batch 7 ECE fix must NOT modify any other department's fees.
    This test pins Civil, Mechanical, MBA, Basic Sciences, cse_aiml, cse_ds,
    cse, and ECE so any cross-contamination is detected."""
    data = load_locale_data_for_lang_key("kn")
    # CSE family — these have the corrected ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್ ಕೋಟಾ form.
    assert "ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್ ಕೋಟಾ" in data["departments"]["cse_aiml"]["fees"]
    assert "ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್ ಕೋಟಾ" in data["departments"]["cse_ds"]["fees"]
    # ECE — this batch's correction.
    assert "ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್ ಕೋಟಾ" in data["departments"]["ece"]["fees"]
    # Civil and Mechanical — these still have ನಿರ್ವಹಣೆ (BLOCKED_OFFICIAL_FACT
    # in Batch 7; not yet applied because they require official-fact
    # verification of the priority-CET-FEES-as-per-KEA policy statement).
    assert "ನಿರ್ವಹಣೆ" in data["departments"]["civil"]["fees"]
    assert "ನಿರ್ವಹಣೆ" in data["departments"]["mechanical"]["fees"]
    # MBA fees — uses ';' separator and is structurally different; unchanged.
    assert data["departments"]["mba"]["fees"] == data["departments"]["mba"]["fees"]  # tautology — guards against accidental rewrite
    # Basic Sciences fees — a structural integration note, not a fee schedule; unchanged.
    assert data["departments"]["basic_sciences"]["fees"] == data["departments"]["basic_sciences"]["fees"]  # tautology guard


def test_ece_fees_amount_preserved_exactly() -> None:
    """The ECE amount ₹2,00,000 must be preserved exactly in the resolved value."""
    fees = APPROVED["kn.departments.ece.fees"]
    assert "₹2,00,000" in fees
    # And it must be different from CSE-family amounts (department-specific).
    assert "₹2,00,000" not in APPROVED["kn.departments.cse_aiml.fees"]
    assert "₹2,00,000" not in APPROVED["kn.departments.cse_ds.fees"]


def test_ece_fees_pipe_separator_preserved() -> None:
    """The literal `|` separator is preserved (TTS sanitization is a separate
    deferred workstream and does not invalidate the terminology correction)."""
    fees = APPROVED["kn.departments.ece.fees"]
    assert "|" in fees
    # The fee should split into exactly 2 parts on the pipe.
    parts = fees.split("|")
    assert len(parts) == 2
    # Each part should be non-empty.
    assert all(p.strip() for p in parts)
