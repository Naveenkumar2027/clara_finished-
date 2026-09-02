"""Canonical content types — pure data, no presentation/narration/translation logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ContentType(str, Enum):
    DEPARTMENT = "department"
    FEES = "fees"
    DOCUMENTS = "documents"
    PRINCIPAL = "principal"
    VICE_PRINCIPAL = "vice_principal"
    HOD = "hod"
    FACULTY = "faculty"
    PLACEMENTS = "placements"
    ADMISSIONS = "admissions"
    TRUSTEES = "trustees"
    COLLEGE = "college"
    COMPARISON = "comparison"
    BUS = "bus"
    COURSE_MENU = "course_menu"
    FAQ = "faq"
    HOSTEL = "hostel"
    CANTEEN = "canteen"
    EVENT = "event"


# Surfaces mirror backend showCard / card_trigger_hints values.
SURFACE_DEPARTMENT_OVERVIEW = "department_overview"
SURFACE_DEPARTMENT_FEES = "department_fees"
SURFACE_DOCUMENTS = "documents"
SURFACE_PRINCIPAL = "principal_profile"
SURFACE_VICE_PRINCIPAL = "vice_principal_profile"
SURFACE_HOD = "hod"
SURFACE_FACULTY = "faculty"
SURFACE_PLACEMENTS = "placements"
SURFACE_ADMISSIONS = "admissions"
SURFACE_TRUSTEES = "trustees"
SURFACE_COLLEGE = "college"
SURFACE_COMPARISON = "department_comparison"
SURFACE_BUS = "bus_routes"
SURFACE_COURSE_MENU = "course_menu"
SURFACE_FAQ = "faq"
SURFACE_HOSTEL = "hostel"
SURFACE_CANTEEN = "canteen"
SURFACE_EVENT = "event"

ALL_SURFACES: frozenset[str] = frozenset(
    {
        SURFACE_DEPARTMENT_OVERVIEW,
        SURFACE_DEPARTMENT_FEES,
        SURFACE_DOCUMENTS,
        SURFACE_PRINCIPAL,
        SURFACE_VICE_PRINCIPAL,
        SURFACE_HOD,
        SURFACE_FACULTY,
        SURFACE_PLACEMENTS,
        SURFACE_ADMISSIONS,
        SURFACE_TRUSTEES,
        SURFACE_COLLEGE,
        SURFACE_COMPARISON,
        SURFACE_BUS,
        SURFACE_COURSE_MENU,
        SURFACE_FAQ,
        SURFACE_HOSTEL,
        SURFACE_CANTEEN,
        SURFACE_EVENT,
    }
)


@dataclass(frozen=True)
class ContentSection:
    id: str
    title: str
    body: str


@dataclass(frozen=True)
class CanonicalContent:
    """Immutable content object. No presentation, narration, or translation logic."""

    content_id: str
    content_type: str
    surface: str
    language: str
    language_code: str
    title: str
    subtitle: str
    summary: str
    sections: tuple[ContentSection, ...]
    metadata: dict[str, Any]
    keywords: tuple[str, ...]
    presentation_mode: str
    canonical_source: str
    version: str
    hash: str
    created_at: str


@dataclass(frozen=True)
class ResolveRequest:
    intent: str | None = None
    department: str | None = None
    language: str = "English"
    language_code: str = "en"
    surface: str | None = None
    semantic_topic: str | None = None
    requested_card: str | None = None
    faq_question: str | None = None
    comparison_department_ids: tuple[str, ...] = ()


@dataclass
class ValidationResult:
    ok: bool
    failures: list[str] = field(default_factory=list)

    @property
    def primary_reason(self) -> str | None:
        return self.failures[0] if self.failures else None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
