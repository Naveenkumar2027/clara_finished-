"""Ordered multi-entity/card composition through the canonical parser."""

from __future__ import annotations

import pytest

from backend.services.content.semantic_request_parser import parse_semantic_request
from backend.services.content.unit_selector import select_content_units


def _request(text: str, language: str = "en"):
    request = parse_semantic_request(
        raw_text=text,
        language_code_key=language,
    )
    assert request is not None
    return request


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        (
            "Who is the CSE HOD and Data Science HOD?",
            [
                {"cardId": "hod_profile", "departmentId": "cse"},
                {"cardId": "hod_profile", "departmentId": "cse_ds"},
            ],
        ),
        (
            "Who is the Data Science HOD and CSE HOD?",
            [
                {"cardId": "hod_profile", "departmentId": "cse_ds"},
                {"cardId": "hod_profile", "departmentId": "cse"},
            ],
        ),
        (
            "CSE HOD and Data Science fees",
            [
                {"cardId": "hod_profile", "departmentId": "cse"},
                {"cardId": "fees", "departmentId": "cse_ds"},
            ],
        ),
        (
            "CSE HOD and faculty",
            [
                {"cardId": "hod_profile", "departmentId": "cse"},
                {"cardId": "faculty_list", "departmentId": "cse"},
            ],
        ),
        (
            "CSE, ECE and Data Science HODs",
            [
                {"cardId": "hod_profile", "departmentId": "cse"},
                {"cardId": "hod_profile", "departmentId": "ece"},
                {"cardId": "hod_profile", "departmentId": "cse_ds"},
            ],
        ),
        (
            "Principal and CSE HOD",
            [
                {"cardId": "principal_profile"},
                {"cardId": "hod_profile", "departmentId": "cse"},
            ],
        ),
        (
            "CSE HOD, Data Science faculty, ECE fees",
            [
                {"cardId": "hod_profile", "departmentId": "cse"},
                {"cardId": "faculty_list", "departmentId": "cse_ds"},
                {"cardId": "fees", "departmentId": "ece"},
            ],
        ),
        (
            "CSE HOD and CSE HOD",
            [{"cardId": "hod_profile", "departmentId": "cse"}],
        ),
        (
            "CSE department, Data Science HOD and ECE placements",
            [
                {"cardId": "department_overview", "departmentId": "cse"},
                {"cardId": "hod_profile", "departmentId": "cse_ds"},
                {"cardId": "placements", "departmentId": "ece"},
            ],
        ),
    ),
)
def test_ordered_requested_card_instances(text: str, expected: list[dict[str, str]]) -> None:
    result = _request(text).canonical_result()
    assert result["requestedCards"] == expected
    assert result["activeIndex"] == 0


def test_repeated_topic_occurrences_do_not_break_clause_pairing() -> None:
    request = _request("CSE HOD, Data Science HOD, ECE fees")
    assert request.unit_items == (
        ("cse", "hod"),
        ("cse_ds", "hod"),
        ("ece", "fees"),
    )
    plan = select_content_units(request)
    assert plan is not None
    assert plan.units == ("cse.hod", "cse_ds.hod", "ece.fees")


_LANGUAGE_FORMS = (
    ("en", "and", "who?"),
    ("kn", "ಮತ್ತು", "ಯಾರು?"),
    ("hi", "और", "कौन है?"),
    ("te", "మరియు", "ఎవరు?"),
    ("ta", "மற்றும்", "யார்?"),
    ("ml", "കൂടാതെ", "ആരാണ്?"),
)


@pytest.mark.parametrize(("language", "joiner", "question"), _LANGUAGE_FORMS)
def test_language_matrix_two_departments_same_card(language: str, joiner: str, question: str) -> None:
    request = _request(f"CSE HOD {joiner} Data Science HOD {question}", language)
    assert request.unit_items == (("cse", "hod"), ("cse_ds", "hod"))


@pytest.mark.parametrize(("language", "joiner", "question"), _LANGUAGE_FORMS)
def test_language_matrix_two_departments_different_cards(language: str, joiner: str, question: str) -> None:
    request = _request(f"CSE HOD {joiner} Data Science fees {question}", language)
    assert request.unit_items == (("cse", "hod"), ("cse_ds", "fees"))


@pytest.mark.parametrize(("language", "joiner", "question"), _LANGUAGE_FORMS)
def test_language_matrix_same_department_two_cards(language: str, joiner: str, question: str) -> None:
    request = _request(f"CSE HOD {joiner} fees {question}", language)
    assert request.unit_items == (("cse", "hod"), ("cse", "fees"))


@pytest.mark.parametrize(("language", "joiner", "question"), _LANGUAGE_FORMS)
def test_language_matrix_three_cards(language: str, joiner: str, question: str) -> None:
    request = _request(
        f"CSE HOD, Data Science HOD {joiner} ECE fees {question}",
        language,
    )
    assert request.unit_items == (("cse", "hod"), ("cse_ds", "hod"), ("ece", "fees"))


@pytest.mark.parametrize(("language", "joiner", "question"), _LANGUAGE_FORMS)
def test_language_matrix_representative_stt_code_switch(language: str, joiner: str, question: str) -> None:
    request = _request(f"C S E HOD {joiner} data science HOD {question}", language)
    assert request.unit_items == (("cse", "hod"), ("cse_ds", "hod"))
