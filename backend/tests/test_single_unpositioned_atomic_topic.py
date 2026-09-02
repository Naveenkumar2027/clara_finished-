"""Focused regression for one entity plus one unpositioned canonical topic."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.services.content.semantic_request_parser import parse_semantic_request


def _canonical(text: str, language: str = "hi") -> dict[str, object]:
    request = parse_semantic_request(raw_text=text, language_code_key=language)
    assert request is not None
    return request.canonical_result()


@pytest.mark.parametrize(
    ("text", "language", "department", "card"),
    (
        ("मेकेनिकल का hod कौन है", "hi", "mechanical", "hod_profile"),
        ("मैकैनिकल का HOD कौन है?", "hi", "mechanical", "hod_profile"),
        ("mechanical HOD कौन है?", "hi", "mechanical", "hod_profile"),
        ("डेटा साइंस के HOD कौन हैं?", "hi", "cse_ds", "hod_profile"),
        ("Who is the Mechanical HOD?", "en", "mechanical", "hod_profile"),
        ("mechanical hod ಯಾರು?", "kn", "mechanical", "hod_profile"),
        ("मैकेनिकल fees बताओ", "hi", "mechanical", "fees"),
    ),
)
def test_single_entity_single_topic_resolves_canonical_card(
    text: str,
    language: str,
    department: str,
    card: str,
) -> None:
    result = _canonical(text, language)
    assert result["departmentIds"] == [department]
    assert result["requestedCards"] == [{"cardId": card, "departmentId": department}]


def test_unpositioned_atomic_topic_bypasses_overview_fallback() -> None:
    with patch(
        "backend.services.content.semantic_request_parser.detect_topic_spans",
        return_value=(),
    ):
        result = _canonical("mechanical HOD कौन है?", "hi")

    assert result["intentId"] == "show_hod"
    assert result["requestedCards"] == [
        {"cardId": "hod_profile", "departmentId": "mechanical"}
    ]


def test_generic_mechanical_request_remains_overview() -> None:
    result = _canonical("मैकेनिकल विभाग के बारे में बताओ", "hi")
    assert result["requestedCards"] == [
        {"cardId": "department_overview", "departmentId": "mechanical"}
    ]


def test_mixed_multi_topic_pairing_is_unchanged() -> None:
    result = _canonical("CSE HOD and Data Science fees", "en")
    assert result["requestedCards"] == [
        {"cardId": "hod_profile", "departmentId": "cse"},
        {"cardId": "fees", "departmentId": "cse_ds"},
    ]


def test_shared_intent_pairing_is_unchanged() -> None:
    result = _canonical("CSE and Data Science HOD", "en")
    assert result["requestedCards"] == [
        {"cardId": "hod_profile", "departmentId": "cse"},
        {"cardId": "hod_profile", "departmentId": "cse_ds"},
    ]


def test_unpositioned_topic_does_not_broadcast_across_multiple_entities() -> None:
    with patch(
        "backend.services.content.semantic_request_parser.detect_topic_spans",
        return_value=(),
    ):
        request = parse_semantic_request(
            raw_text="CSE and Data Science HOD",
            language_code_key="en",
        )

    assert request is None
