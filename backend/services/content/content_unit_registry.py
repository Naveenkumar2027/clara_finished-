"""ContentUnitRegistry — authoritative map of independently addressable units (M5.0)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from backend.services.answer_generation import DEPARTMENT_JSON_KEY_ORDER
from backend.services.content.leadership_units import (
    LEADERSHIP_ENTITY,
    TOPIC_PRINCIPAL,
    TOPIC_TRUSTEES,
    TOPIC_VICE_PRINCIPAL,
    UNIT_PRINCIPAL,
    UNIT_TRUSTEES,
    UNIT_VICE_PRINCIPAL,
)
from backend.services.content.campus_units import CAMPUS_UNIT_IDS
from backend.services.content.global_units import (
    GLOBAL_ENTITY,
    TOPIC_ADMISSIONS,
    TOPIC_LOCATION,
    TOPIC_PLACEMENTS,
    UNIT_ADMISSIONS,
    UNIT_LOCATION,
    UNIT_PLACEMENTS,
)
from backend.services.content.types import (
    SURFACE_ADMISSIONS,
    SURFACE_CANTEEN,
    SURFACE_COLLEGE,
    SURFACE_DEPARTMENT_FEES,
    SURFACE_DEPARTMENT_OVERVIEW,
    SURFACE_DOCUMENTS,
    SURFACE_EVENT,
    SURFACE_FACULTY,
    SURFACE_HOSTEL,
    SURFACE_PRINCIPAL,
    SURFACE_PLACEMENTS,
    SURFACE_TRUSTEES,
    SURFACE_VICE_PRINCIPAL,
    ContentType,
)
from backend.services.narration_plan import _DEPT_SLIDE_SECTION_IDS

# section_id → unit_id suffix (topic within entity)
_SECTION_TO_UNIT_SUFFIX: dict[str, str] = {
    "intro": "overview",
    "hod_voice": "hod",
    "achievements": "achievements",
    "placement": "placements",
    "fees": "fees",
}

_DEPT_CANONICAL_SOURCE = "backend/data/locales/*.json#departments"
_FEES_CANONICAL_SOURCE = "backend/services/narration_plan.py#_FEES_AMOUNT_BY_KEY"
_DOCUMENTS_CANONICAL_SOURCE = "backend/services/narration_plan.py#DOCUMENT_ITEMS"
_CAMPUS_CANONICAL_SOURCE = "backend/data/locales/*.json#campus_units"
_LEADERSHIP_CANONICAL_SOURCE = "backend/services/narration_plan.py#EXEC_PRINCIPAL|EXEC_VICE + locales role_holders"
_UI_CANONICAL_SOURCE = "backend/data/locales/ui.json"


@dataclass(frozen=True)
class ContentUnitDescriptor:
    unit_id: str
    surface: str
    content_type: str
    entity_type: str
    entity_id: str
    context: str
    context_id: str
    section_id: str
    unit_suffix: str
    canonical_source: str
    adapter_key: str
    supported_languages: tuple[str, ...] = ("en", "hi", "kn", "ta", "te", "ml")
    presentation_role: str = ""


def _department_descriptor(dept_key: str, section_id: str) -> ContentUnitDescriptor:
    suffix = _SECTION_TO_UNIT_SUFFIX[section_id]
    return ContentUnitDescriptor(
        unit_id=f"{dept_key}.{suffix}",
        surface=SURFACE_DEPARTMENT_OVERVIEW,
        content_type=ContentType.DEPARTMENT.value,
        entity_type="department",
        entity_id=dept_key,
        context="department",
        context_id=dept_key,
        section_id=section_id,
        unit_suffix=suffix,
        canonical_source=_DEPT_CANONICAL_SOURCE,
        adapter_key="department",
        presentation_role=suffix,
    )


def _faculty_descriptor(dept_key: str) -> ContentUnitDescriptor:
    return ContentUnitDescriptor(
        unit_id=f"{dept_key}.faculty",
        surface=SURFACE_FACULTY,
        content_type=ContentType.DEPARTMENT.value,
        entity_type="department",
        entity_id=dept_key,
        context="department",
        context_id=dept_key,
        section_id="faculty",
        unit_suffix="faculty",
        canonical_source=_UI_CANONICAL_SOURCE,
        adapter_key="faculty",
        presentation_role="faculty",
    )


_CONTEXT_SCOPED_DESCRIPTORS: tuple[ContentUnitDescriptor, ...] = (
    ContentUnitDescriptor(
        unit_id=UNIT_PLACEMENTS,
        surface=SURFACE_PLACEMENTS,
        content_type=ContentType.PLACEMENTS.value,
        entity_type="global",
        entity_id=GLOBAL_ENTITY,
        context="global",
        context_id=TOPIC_PLACEMENTS,
        section_id=TOPIC_PLACEMENTS,
        unit_suffix=TOPIC_PLACEMENTS,
        canonical_source="backend/data/locales/*.json#placements_and_training",
        adapter_key="aggregate_surface",
        presentation_role=TOPIC_PLACEMENTS,
    ),
    ContentUnitDescriptor(
        unit_id=UNIT_ADMISSIONS,
        surface=SURFACE_ADMISSIONS,
        content_type=ContentType.ADMISSIONS.value,
        entity_type="global",
        entity_id=GLOBAL_ENTITY,
        context="global",
        context_id=TOPIC_ADMISSIONS,
        section_id=TOPIC_ADMISSIONS,
        unit_suffix=TOPIC_ADMISSIONS,
        canonical_source="backend/data/locales/*.json#admissions_and_fees",
        adapter_key="aggregate_surface",
        presentation_role=TOPIC_ADMISSIONS,
    ),
    ContentUnitDescriptor(
        unit_id=UNIT_LOCATION,
        surface=SURFACE_COLLEGE,
        content_type=ContentType.COLLEGE.value,
        entity_type="global",
        entity_id=GLOBAL_ENTITY,
        context="global",
        context_id=TOPIC_LOCATION,
        section_id=TOPIC_LOCATION,
        unit_suffix=TOPIC_LOCATION,
        canonical_source=_UI_CANONICAL_SOURCE,
        adapter_key="location",
        presentation_role=TOPIC_LOCATION,
    ),
    ContentUnitDescriptor(
        unit_id="fees.overview",
        surface=SURFACE_DEPARTMENT_FEES,
        content_type=ContentType.FEES.value,
        entity_type="",
        entity_id="",
        context="global",
        context_id="fees",
        section_id="overview",
        unit_suffix="overview",
        canonical_source=_FEES_CANONICAL_SOURCE,
        adapter_key="fees",
        presentation_role="overview",
    ),
    ContentUnitDescriptor(
        unit_id="documents.overview",
        surface=SURFACE_DOCUMENTS,
        content_type=ContentType.DOCUMENTS.value,
        entity_type="",
        entity_id="",
        context="global",
        context_id="documents",
        section_id="overview",
        unit_suffix="overview",
        canonical_source=_DOCUMENTS_CANONICAL_SOURCE,
        adapter_key="documents",
        presentation_role="overview",
    ),
    ContentUnitDescriptor(
        unit_id="admission.documents_required",
        surface=SURFACE_DOCUMENTS,
        content_type=ContentType.DOCUMENTS.value,
        entity_type="",
        entity_id="",
        context="admission",
        context_id="admission",
        section_id="documents_required",
        unit_suffix="documents_required",
        canonical_source=_DOCUMENTS_CANONICAL_SOURCE,
        adapter_key="documents",
        presentation_role="checklist",
    ),
)

_LEADERSHIP_DESCRIPTORS: tuple[ContentUnitDescriptor, ...] = (
    ContentUnitDescriptor(
        unit_id=UNIT_PRINCIPAL,
        surface=SURFACE_PRINCIPAL,
        content_type=ContentType.PRINCIPAL.value,
        entity_type=LEADERSHIP_ENTITY,
        entity_id=LEADERSHIP_ENTITY,
        context=LEADERSHIP_ENTITY,
        context_id=TOPIC_PRINCIPAL,
        section_id=TOPIC_PRINCIPAL,
        unit_suffix=TOPIC_PRINCIPAL,
        canonical_source=_LEADERSHIP_CANONICAL_SOURCE,
        adapter_key="principal",
        presentation_role=TOPIC_PRINCIPAL,
    ),
    ContentUnitDescriptor(
        unit_id=UNIT_VICE_PRINCIPAL,
        surface=SURFACE_VICE_PRINCIPAL,
        content_type=ContentType.VICE_PRINCIPAL.value,
        entity_type=LEADERSHIP_ENTITY,
        entity_id=LEADERSHIP_ENTITY,
        context=LEADERSHIP_ENTITY,
        context_id=TOPIC_VICE_PRINCIPAL,
        section_id=TOPIC_VICE_PRINCIPAL,
        unit_suffix=TOPIC_VICE_PRINCIPAL,
        canonical_source=_LEADERSHIP_CANONICAL_SOURCE,
        adapter_key="vice_principal",
        presentation_role=TOPIC_VICE_PRINCIPAL,
    ),
    ContentUnitDescriptor(
        unit_id=UNIT_TRUSTEES,
        surface=SURFACE_TRUSTEES,
        content_type=ContentType.TRUSTEES.value,
        entity_type=LEADERSHIP_ENTITY,
        entity_id=LEADERSHIP_ENTITY,
        context=LEADERSHIP_ENTITY,
        context_id=TOPIC_TRUSTEES,
        section_id=TOPIC_TRUSTEES,
        unit_suffix=TOPIC_TRUSTEES,
        canonical_source="backend/data/locales/*.json#role_holders.trustees",
        adapter_key="trustees",
        presentation_role=TOPIC_TRUSTEES,
    ),
)


def _campus_descriptor(unit_id: str) -> ContentUnitDescriptor:
    uid = unit_id.strip().lower()
    if uid.startswith("hostel."):
        parts = uid.split(".")
        entity_id = ".".join(parts[:2])
        suffix = parts[-1]
        return ContentUnitDescriptor(
            unit_id=uid,
            surface=SURFACE_HOSTEL,
            content_type=ContentType.HOSTEL.value,
            entity_type="hostel",
            entity_id=entity_id,
            context="hostel",
            context_id=entity_id,
            section_id=suffix,
            unit_suffix=suffix,
            canonical_source=_CAMPUS_CANONICAL_SOURCE,
            adapter_key="campus_unit",
            presentation_role=suffix,
        )
    if uid.startswith("canteen."):
        suffix = uid.split(".", 1)[1]
        return ContentUnitDescriptor(
            unit_id=uid,
            surface=SURFACE_CANTEEN,
            content_type=ContentType.CANTEEN.value,
            entity_type="canteen",
            entity_id="canteen",
            context="canteen",
            context_id="canteen",
            section_id=suffix,
            unit_suffix=suffix,
            canonical_source=_CAMPUS_CANONICAL_SOURCE,
            adapter_key="campus_unit",
            presentation_role=suffix,
        )
    suffix = uid.split(".", 1)[1] if "." in uid else uid
    return ContentUnitDescriptor(
        unit_id=uid,
        surface=SURFACE_EVENT,
        content_type=ContentType.EVENT.value,
        entity_type="event",
        entity_id=uid,
        context="event",
        context_id=uid,
        section_id="overview",
        unit_suffix=suffix,
        canonical_source=_CAMPUS_CANONICAL_SOURCE,
        adapter_key="campus_unit",
        presentation_role="overview",
    )


_CAMPUS_DESCRIPTORS: tuple[ContentUnitDescriptor, ...] = tuple(
    _campus_descriptor(uid) for uid in CAMPUS_UNIT_IDS
)


@lru_cache(maxsize=1)
def _all_descriptors_by_id() -> dict[str, ContentUnitDescriptor]:
    out: dict[str, ContentUnitDescriptor] = {}
    for dept_key in DEPARTMENT_JSON_KEY_ORDER:
        for section_id in _DEPT_SLIDE_SECTION_IDS:
            desc = _department_descriptor(dept_key, section_id)
            out[desc.unit_id] = desc
        faculty = _faculty_descriptor(dept_key)
        out[faculty.unit_id] = faculty
    for desc in _CONTEXT_SCOPED_DESCRIPTORS:
        out[desc.unit_id] = desc
    for desc in _LEADERSHIP_DESCRIPTORS:
        out[desc.unit_id] = desc
    for desc in _CAMPUS_DESCRIPTORS:
        out[desc.unit_id] = desc
    return out


def list_department_unit_descriptors(dept_key: str) -> tuple[ContentUnitDescriptor, ...]:
    key = (dept_key or "").strip().lower()
    if key not in DEPARTMENT_JSON_KEY_ORDER:
        return ()
    return tuple(_department_descriptor(key, sid) for sid in _DEPT_SLIDE_SECTION_IDS)


def list_context_scoped_descriptors(context: str) -> tuple[ContentUnitDescriptor, ...]:
    ctx = (context or "").strip().lower()
    return tuple(d for d in _CONTEXT_SCOPED_DESCRIPTORS if d.context == ctx)


def get_unit_descriptor(unit_id: str) -> ContentUnitDescriptor | None:
    uid = (unit_id or "").strip()
    if not uid:
        return None
    return _all_descriptors_by_id().get(uid)


def unit_id_for(dept_key: str, section_id: str) -> str | None:
    key = (dept_key or "").strip().lower()
    sid = (section_id or "").strip()
    suffix = _SECTION_TO_UNIT_SUFFIX.get(sid)
    if not suffix or key not in DEPARTMENT_JSON_KEY_ORDER:
        return None
    return f"{key}.{suffix}"


def all_unit_descriptors() -> tuple[ContentUnitDescriptor, ...]:
    return tuple(_all_descriptors_by_id().values())


def section_ids_for_department() -> tuple[str, ...]:
    return _DEPT_SLIDE_SECTION_IDS


def unit_suffix_for_section(section_id: str) -> str | None:
    return _SECTION_TO_UNIT_SUFFIX.get((section_id or "").strip())
