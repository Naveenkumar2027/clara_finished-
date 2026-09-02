"""Content ownership registry — points at current owners; no migration."""

from __future__ import annotations

from dataclasses import dataclass

from backend.services.content.types import (
    ALL_SURFACES,
    SURFACE_ADMISSIONS,
    SURFACE_BUS,
    SURFACE_COLLEGE,
    SURFACE_COMPARISON,
    SURFACE_COURSE_MENU,
    SURFACE_DEPARTMENT_FEES,
    SURFACE_DEPARTMENT_OVERVIEW,
    SURFACE_DOCUMENTS,
    SURFACE_FAQ,
    SURFACE_FACULTY,
    SURFACE_HOD,
    SURFACE_HOSTEL,
    SURFACE_CANTEEN,
    SURFACE_EVENT,
    SURFACE_PLACEMENTS,
    SURFACE_PRINCIPAL,
    SURFACE_TRUSTEES,
    SURFACE_VICE_PRINCIPAL,
    ContentType,
)


@dataclass(frozen=True)
class ContentOwnerDescriptor:
    surface: str
    owner_id: str
    adapter_key: str
    content_type: str
    canonical_source: str
    notes: str = ""


# Pointer-only registry (Phase 3.7 current owners).
_REGISTRY: dict[str, ContentOwnerDescriptor] = {
    SURFACE_DEPARTMENT_OVERVIEW: ContentOwnerDescriptor(
        surface=SURFACE_DEPARTMENT_OVERVIEW,
        owner_id="locale.departments",
        adapter_key="department",
        content_type=ContentType.DEPARTMENT.value,
        canonical_source="backend/data/locales/*.json#departments",
        notes="Locale departments.*; narration and FE slides both read this store.",
    ),
    SURFACE_DEPARTMENT_FEES: ContentOwnerDescriptor(
        surface=SURFACE_DEPARTMENT_FEES,
        owner_id="narration_plan.fees_table",
        adapter_key="fees",
        content_type=ContentType.FEES.value,
        canonical_source="backend/services/narration_plan.py#_FEES_AMOUNT_BY_KEY",
        notes="Spoken path today. Diverges from locale departments.*.fees prose and FE MANAGEMENT_QUOTA_FEE_BY_KEY.",
    ),
    SURFACE_DOCUMENTS: ContentOwnerDescriptor(
        surface=SURFACE_DOCUMENTS,
        owner_id="narration_plan.documents",
        adapter_key="documents",
        content_type=ContentType.DOCUMENTS.value,
        canonical_source="backend/services/narration_plan.py#DOCUMENT_ITEMS",
        notes="Spoken path. FE DocumentsBlock has parallel list with KN wording drift.",
    ),
    SURFACE_PRINCIPAL: ContentOwnerDescriptor(
        surface=SURFACE_PRINCIPAL,
        owner_id="narration_plan.exec_principal",
        adapter_key="principal",
        content_type=ContentType.PRINCIPAL.value,
        canonical_source="backend/services/narration_plan.py#EXEC_PRINCIPAL",
        notes="Spoken EXEC_PRINCIPAL. UI PRINCIPAL_COPY and locale role_holders.principal also exist.",
    ),
    SURFACE_VICE_PRINCIPAL: ContentOwnerDescriptor(
        surface=SURFACE_VICE_PRINCIPAL,
        owner_id="narration_plan.exec_vice",
        adapter_key="vice_principal",
        content_type=ContentType.VICE_PRINCIPAL.value,
        canonical_source="backend/services/narration_plan.py#EXEC_VICE",
        notes="Spoken EXEC_VICE (often shorter than UI/locale).",
    ),
    SURFACE_HOD: ContentOwnerDescriptor(
        surface=SURFACE_HOD,
        owner_id="locale.departments.hod_voice",
        adapter_key="hod",
        content_type=ContentType.HOD.value,
        canonical_source="backend/data/locales/*.json#departments.*.hod_voice",
        notes="Matches segment_hod_single input. role_holders.hod_by_department is a parallel UI bio.",
    ),
    SURFACE_FACULTY: ContentOwnerDescriptor(
        surface=SURFACE_FACULTY,
        owner_id="ui.cards.faculty",
        adapter_key="faculty",
        content_type=ContentType.FACULTY.value,
        canonical_source="backend/data/locales/ui.json#cards.faculty|availability.missing_source",
        notes="Fact-safe localized faculty card produced by the shared ContentUnit resolver.",
    ),
    SURFACE_PLACEMENTS: ContentOwnerDescriptor(
        surface=SURFACE_PLACEMENTS,
        owner_id="locale.placements",
        adapter_key="placements",
        content_type=ContentType.PLACEMENTS.value,
        canonical_source="backend/data/locales/*.json#placements_and_training",
        notes="Shared locale block; dual BE/FE builders.",
    ),
    SURFACE_ADMISSIONS: ContentOwnerDescriptor(
        surface=SURFACE_ADMISSIONS,
        owner_id="locale.admissions",
        adapter_key="admissions",
        content_type=ContentType.ADMISSIONS.value,
        canonical_source="backend/data/locales/*.json#admissions_and_fees",
        notes="Locale SSOT; ChatScreen currently forces FULL_TEXT for admissions card.",
    ),
    SURFACE_TRUSTEES: ContentOwnerDescriptor(
        surface=SURFACE_TRUSTEES,
        owner_id="static_cards.trustees",
        adapter_key="trustees",
        content_type=ContentType.TRUSTEES.value,
        canonical_source="backend/data/locales/*.json#role_holders.trustees",
        notes="Localized source data; card UI and unit narration consume the same trustee records.",
    ),
    SURFACE_COLLEGE: ContentOwnerDescriptor(
        surface=SURFACE_COLLEGE,
        owner_id="static_cards.college",
        adapter_key="college",
        content_type=ContentType.COLLEGE.value,
        canonical_source="backend/data/narration/static_cards.json#college",
        notes="Marketing slides. institution_overview is a parallel structured store.",
    ),
    SURFACE_COMPARISON: ContentOwnerDescriptor(
        surface=SURFACE_COMPARISON,
        owner_id="department_comparison.json",
        adapter_key="comparison",
        content_type=ContentType.COMPARISON.value,
        canonical_source="backend/data/department_comparison.json",
        notes="BE file. FE has parallel departmentComparison.json.",
    ),
    SURFACE_BUS: ContentOwnerDescriptor(
        surface=SURFACE_BUS,
        owner_id="bus_spoken_prompt",
        adapter_key="bus",
        content_type=ContentType.BUS.value,
        canonical_source="backend/services/answer_generation.py#BUS_ROUTES_SPOKEN_PROMPT_BY_LANGUAGE",
        notes="Spoken prompt only. Route table is FE collegeBusRoutes.json.",
    ),
    SURFACE_COURSE_MENU: ContentOwnerDescriptor(
        surface=SURFACE_COURSE_MENU,
        owner_id="course_menu",
        adapter_key="course_menu",
        content_type=ContentType.COURSE_MENU.value,
        canonical_source="backend/services/answer_generation.py#COURSE_MENU_OPTIONS+PROMPT",
        notes="Options + spoken prompt. FE DEFAULT_COURSE_MENU_OPTIONS duplicates options.",
    ),
    SURFACE_FAQ: ContentOwnerDescriptor(
        surface=SURFACE_FAQ,
        owner_id="faq_answers.json",
        adapter_key="faq",
        content_type=ContentType.FAQ.value,
        canonical_source="backend/data/faq_answers.json",
        notes="Deterministic FAQ answers. Chip questions are separate (faqSuggestions.ts).",
    ),
    SURFACE_HOSTEL: ContentOwnerDescriptor(
        surface=SURFACE_HOSTEL,
        owner_id="locales.campus_units.hostel",
        adapter_key="campus_unit",
        content_type=ContentType.HOSTEL.value,
        canonical_source="backend/data/locales/*.json#campus_units",
        notes="SAMPLE_REPLACE_WITH_OFFICIAL hostel units. Independently selectable.",
    ),
    SURFACE_CANTEEN: ContentOwnerDescriptor(
        surface=SURFACE_CANTEEN,
        owner_id="locales.campus_units.canteen",
        adapter_key="campus_unit",
        content_type=ContentType.CANTEEN.value,
        canonical_source="backend/data/locales/*.json#campus_units",
        notes="SAMPLE_REPLACE_WITH_OFFICIAL canteen units. Independently selectable.",
    ),
    SURFACE_EVENT: ContentOwnerDescriptor(
        surface=SURFACE_EVENT,
        owner_id="locales.campus_units.events",
        adapter_key="campus_unit",
        content_type=ContentType.EVENT.value,
        canonical_source="backend/data/locales/*.json#campus_units",
        notes="SAMPLE_REPLACE_WITH_OFFICIAL event units. Independently selectable.",
    ),
}


def get_owner(surface: str) -> ContentOwnerDescriptor | None:
    return _REGISTRY.get(str(surface or "").strip())


def all_owners() -> list[ContentOwnerDescriptor]:
    return [_REGISTRY[s] for s in sorted(_REGISTRY.keys())]


def registered_surfaces() -> frozenset[str]:
    return frozenset(_REGISTRY.keys())


def assert_registry_complete() -> None:
    missing = ALL_SURFACES - registered_surfaces()
    if missing:
        raise AssertionError(f"Registry missing surfaces: {sorted(missing)}")
