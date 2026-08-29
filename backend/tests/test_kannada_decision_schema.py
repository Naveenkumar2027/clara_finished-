"""Tool-schema test for the structured decision-evidence builder.

These tests cover the executable review-tool contract introduced in
Batch 4. They do NOT touch production locale values and do NOT cover
the per-batch content review (that is the per-batch human report).

Scope:
  - build_structured_evidence emits every required field
  - the 14 check fields have one of the three valid statuses
  - the four input/output fields are always present
  - the classification is one of the 7 allowed values
  - backfill_legacy_entry preserves existing fields and only adds
    LEGACY_UNSTRUCTURED markers for absent fields (no fabrication)
"""
from __future__ import annotations

import json
from pathlib import Path

from backend.tools.kannada_sarvam_review import (
    ALLOWED_CLASSIFICATIONS,
    LEGACY_UNSTRUCTURED,
    backfill_legacy_entry,
    build_structured_evidence,
)


CHECK_FIELD_NAMES: tuple[str, ...] = (
    "placeholder_check",
    "name_check",
    "number_check",
    "currency_check",
    "acronym_check",
    "latin_name_check",
    "gender_narrowing",
    "subject_object_drift",
    "punctuation_assessment",
    "display_assessment",
    "narration_assessment",
)

LIST_FIELD_NAMES: tuple[str, ...] = (
    "missing_clauses",
    "added_clauses",
    "terminology_conflicts",
)

ALL_CHECK_FIELDS: tuple[str, ...] = CHECK_FIELD_NAMES + LIST_FIELD_NAMES

INPUT_OUTPUT_FIELDS: tuple[str, ...] = (
    "existing_back_translation",
    "candidate_back_translation",
    "classification",
    "reason",
)

VALID_STATUSES: frozenset[str] = frozenset({"PASS", "FAIL", "N/A"})


def _sample_row() -> dict:
    return {
        "id": "ui.test.smoke",
        "english": "Voice recognition timed out. Please try again or type your question.",
        "existing_kn": "ಧ್ವನಿ ಗುರುತಿಸುವಿಕೆ ಸಮಯ ಮೀರಿದೆ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ ಅಥವಾ ಪ್ರಶ್ನೆಯನ್ನು ಟೈಪ್ ಮಾಡಿ.",
        "sarvam_kn": "ಧ್ವನಿ ಗುರುತಿಸುವಿಕೆ ಸಮಯ ಮೀರಿತು. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ ಅಥವಾ ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಟೈಪ್ ಮಾಡಿ.",
    }


def test_build_structured_evidence_emits_every_required_field() -> None:
    ev = build_structured_evidence(
        _sample_row(),
        "KEEP_EXISTING_MECHANICALLY_SUPPORTED",
        "near-identical",
    )
    for f in INPUT_OUTPUT_FIELDS:
        assert f in ev, f"missing input/output field: {f}"
    for f in ALL_CHECK_FIELDS:
        assert f in ev, f"missing check field: {f}"


def test_build_structured_evidence_check_field_statuses_are_valid() -> None:
    ev = build_structured_evidence(
        _sample_row(),
        "KEEP_EXISTING_MECHANICALLY_SUPPORTED",
        "near-identical",
    )
    for f in CHECK_FIELD_NAMES:
        v = ev[f]
        assert isinstance(v, dict), f"{f} must be a dict, got {type(v)}"
        assert "status" in v, f"{f} missing 'status'"
        assert "detail" in v, f"{f} missing 'detail'"
        assert v["status"] in VALID_STATUSES, (
            f"{f} has invalid status {v['status']!r}"
        )


def test_build_structured_evidence_list_fields_are_lists_of_strings() -> None:
    ev = build_structured_evidence(
        _sample_row(),
        "KEEP_EXISTING_MECHANICALLY_SUPPORTED",
        "near-identical",
    )
    for f in LIST_FIELD_NAMES:
        v = ev[f]
        assert isinstance(v, list), f"{f} must be a list, got {type(v)}"
        for item in v:
            assert isinstance(item, str), f"{f} contains non-string item"


def test_build_structured_evidence_rejects_invalid_classification() -> None:
    try:
        build_structured_evidence(_sample_row(), "VERIFIED", "not allowed")
    except ValueError:
        return
    raise AssertionError("expected ValueError for invalid classification")


def test_build_structured_evidence_accepts_all_seven_classifications() -> None:
    for c in ALLOWED_CLASSIFICATIONS:
        ev = build_structured_evidence(_sample_row(), c, "test")
        assert ev["classification"] == c


def test_build_structured_evidence_records_back_translations() -> None:
    ev = build_structured_evidence(
        _sample_row(),
        "KEEP_EXISTING_MECHANICALLY_SUPPORTED",
        "near-identical",
        back_en_of_candidate="The voice recognition time has exceeded. Please try again or type your query.",
        back_en_of_existing="The voice recognition time has exceeded. Please try again or type a query.",
    )
    assert "voice recognition time" in ev["candidate_back_translation"]
    assert "voice recognition time" in ev["existing_back_translation"]


def test_build_structured_evidence_detects_pipe_in_candidate() -> None:
    row = {
        "english": "Fee details",
        "existing_kn": "ಶುಲ್ಕದ ವಿವರಗಳು",
        "sarvam_kn": "ಶುಲ್ಕದ ವಿವರಗಳು | ಆಫ್",
    }
    ev = build_structured_evidence(row, "BLOCKED_RUNTIME_STRUCTURE", "pipe char")
    assert ev["punctuation_assessment"]["status"] == "FAIL"
    assert "|" in ev["punctuation_assessment"]["detail"]


def test_build_structured_evidence_detects_glossary_violation() -> None:
    row = {
        "english": "Department",
        "existing_kn": "ವಿಭಾಗ",
        "sarvam_kn": "ಇಲಾಖೆ",
    }
    ev = build_structured_evidence(row, "BLOCKED_LINGUISTIC", "glossary violation")
    assert any("ಇಲಾಖೆ" in c for c in ev["terminology_conflicts"])


def test_backfill_legacy_entry_preserves_existing_fields() -> None:
    legacy = {
        "decision": "KEEP_EXISTING",
        "approved": "ವಿದಾಯ.",
        "reason": "old free-text reason",
        "batch": 1,
    }
    out = backfill_legacy_entry(legacy)
    # All original fields preserved
    for k, v in legacy.items():
        assert out[k] == v, f"field {k!r} mutated by backfill"
    # Absent schema fields marked
    for f in ALL_CHECK_FIELDS:
        assert out.get(f) == LEGACY_UNSTRUCTURED, f"{f} not marked legacy"
    for f in INPUT_OUTPUT_FIELDS:
        if f not in legacy:
            assert out.get(f) == LEGACY_UNSTRUCTURED, f"{f} not marked legacy"


def test_backfill_legacy_entry_does_not_invent_pass() -> None:
    """No field that is absent in the legacy entry may be set to PASS.
    This is the explicit anti-fabrication guarantee."""
    legacy = {"decision": "KEEP_EXISTING", "approved": "x", "reason": "y"}
    out = backfill_legacy_entry(legacy)
    for f in ALL_CHECK_FIELDS:
        if f not in legacy:
            v = out[f]
            if isinstance(v, dict):
                assert v.get("status") != "PASS", (
                    f"backfill fabricated PASS for {f}"
                )
            assert v == LEGACY_UNSTRUCTURED, (
                f"backfill used non-LEGACY marker for {f}: {v!r}"
            )


def test_backfill_legacy_entry_does_not_overwrite_existing_structured() -> None:
    legacy = {
        "decision": "KEEP_EXISTING_MECHANICALLY_SUPPORTED",
        "classification": "KEEP_EXISTING_MECHANICALLY_SUPPORTED",
        "placeholder_check": {"status": "PASS", "detail": "explicitly set"},
    }
    out = backfill_legacy_entry(legacy)
    # The explicitly-set field must not be overwritten by LEGACY_UNSTRUCTURED.
    assert out["placeholder_check"] == {"status": "PASS", "detail": "explicitly set"}
    # Absent fields are still marked.
    assert out.get("name_check") == LEGACY_UNSTRUCTURED
