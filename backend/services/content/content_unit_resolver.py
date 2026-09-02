"""ContentUnitResolver — deterministic contextual unit resolution (M5.0)."""

from __future__ import annotations

from backend.core.language_detection import LANGUAGE_KEY_TO_NAME
from backend.services.content.content_unit import ContentUnit
from backend.services.content.content_unit_registry import (
    ContentUnitDescriptor,
    get_unit_descriptor,
)
from backend.services.content.diagnostics import content_event
from backend.services.content.resolver import ContentResolver
from backend.services.content.types import (
    SURFACE_DEPARTMENT_OVERVIEW,
    SURFACE_PRINCIPAL,
    SURFACE_TRUSTEES,
    SURFACE_VICE_PRINCIPAL,
    CanonicalContent,
    ContentSection,
    ResolveRequest,
)
from backend.services.content.validators import compute_unit_hash, validate_content_unit
from backend.services.narration_plan import dept_labels, _effective_lang
from backend.services.ui_localization import ui_text
from backend.services.answer_generation import (
    load_locale_data_for_lang_key,
    locale_file_id_for_lang_key,
)

_SOURCE_VERSION = "m5.0"
_SAMPLE_CONTENT_STATUS = "SAMPLE_REPLACE_WITH_OFFICIAL"


def _public_campus_title(title: str) -> str:
    """Remove editorial sample markers that must never reach kiosk UI or speech."""
    return (
        title.replace("(ಮಾದರಿ)", "")
        .replace("（ಮಾದರಿ）", "")
        .replace("(sample)", "")
        .replace("(Sample)", "")
        .strip()
    )


def resolve_unit(
    *,
    unit_id: str,
    language: str,
    language_code: str,
    entity: str | None = None,
) -> ContentUnit | None:
    """Resolve one ContentUnit by globally unique unit_id."""
    descriptor = get_unit_descriptor(unit_id)
    if descriptor is None:
        content_event("CONTENT_UNIT_FAILED", unit_id=unit_id, reason="unknown_unit_id")
        return None

    content_event(
        "CONTENT_UNIT_REQUESTED",
        unit_id=unit_id,
        context=descriptor.context,
        context_id=descriptor.context_id,
        language_code=language_code,
    )

    unit: ContentUnit | None
    if descriptor.adapter_key == "department":
        unit = _resolve_department_unit(descriptor, language=language, language_code=language_code)
    elif descriptor.adapter_key == "fees":
        unit = _resolve_fees_overview(descriptor, language=language, language_code=language_code)
    elif descriptor.adapter_key == "documents":
        unit = _resolve_documents_unit(descriptor, language=language, language_code=language_code)
    elif descriptor.adapter_key in {"principal", "vice_principal", "trustees"}:
        unit = _resolve_leadership_unit(descriptor, language=language, language_code=language_code)
    elif descriptor.adapter_key == "campus_unit":
        unit = _resolve_campus_unit(descriptor, language=language, language_code=language_code)
    elif descriptor.adapter_key in {"faculty", "location"}:
        unit = _resolve_shared_ui_unit(descriptor, language=language, language_code=language_code)
    elif descriptor.adapter_key == "aggregate_surface":
        unit = _resolve_aggregate_surface_unit(descriptor, language=language, language_code=language_code)
    else:
        content_event("CONTENT_UNIT_FAILED", unit_id=unit_id, reason="unsupported_adapter")
        return None

    if unit is None:
        content_event("CONTENT_UNIT_FAILED", unit_id=unit_id, reason="resolution_failed")
        return None

    validation = validate_content_unit(unit)
    if not validation.ok:
        content_event(
            "CONTENT_UNIT_FAILED",
            unit_id=unit_id,
            reason="validation_failed",
            failures=validation.failures,
        )
        return None

    content_event(
        "CONTENT_UNIT_RESOLVED",
        unit_id=unit_id,
        section_id=unit.section_id,
        context=unit.context,
        context_id=unit.context_id,
        content_hash=unit.content_hash,
        language_code=language_code,
    )
    return unit


def _resolve_department_unit(
    descriptor: ContentUnitDescriptor,
    *,
    language: str,
    language_code: str,
) -> ContentUnit | None:
    dept_key = descriptor.entity_id
    content = ContentResolver().resolve(
        ResolveRequest(
            surface=SURFACE_DEPARTMENT_OVERVIEW,
            department=dept_key,
            language=language,
            language_code=language_code,
        )
    )
    if content is None or content.metadata.get("mode") == "all":
        return None
    return _unit_from_department_content(descriptor, content)


def _resolve_shared_ui_unit(
    descriptor: ContentUnitDescriptor,
    *,
    language: str,
    language_code: str,
) -> ContentUnit:
    """Resolve fact-safe shared cards without inventing institutional content."""
    if descriptor.adapter_key == "faculty":
        title = ui_text(language_code, "cards.faculty")
        body = ui_text(language_code, "availability.missing_source").replace("\n", " ")
    else:
        title = ui_text(language_code, "cards.location")
        body = ui_text(language_code, "action.location")
    unit_hash = compute_unit_hash(
        unit_id=descriptor.unit_id,
        context=descriptor.context,
        context_id=descriptor.context_id,
        section_id=descriptor.section_id,
        body=body,
        language_code=language_code,
        canonical_source=descriptor.canonical_source,
    )
    display = (language or "").strip() or LANGUAGE_KEY_TO_NAME.get(language_code, "English")
    return ContentUnit(
        unit_id=descriptor.unit_id,
        surface=descriptor.surface,
        content_type=descriptor.content_type,
        entity_type=descriptor.entity_type,
        entity_id=descriptor.entity_id,
        context=descriptor.context,
        context_id=descriptor.context_id,
        section_id=descriptor.section_id,
        title=title,
        summary=body,
        body=body,
        language=display,
        language_code=language_code,
        canonical_source=descriptor.canonical_source,
        source_version=_SOURCE_VERSION,
        content_hash=unit_hash,
        metadata={"department": descriptor.entity_id} if descriptor.adapter_key == "faculty" else {},
        keywords=(descriptor.entity_id, descriptor.unit_suffix),
        presentation_capabilities=("generic_unit",),
    )


def _resolve_aggregate_surface_unit(
    descriptor: ContentUnitDescriptor,
    *,
    language: str,
    language_code: str,
) -> ContentUnit | None:
    content = ContentResolver().resolve(
        ResolveRequest(
            surface=descriptor.surface,
            language=language,
            language_code=language_code,
        )
    )
    if content is None:
        return None
    label_paths = {
        "objectives": "cards.training_objectives",
        "training": "cards.training_programs",
        "eligibility": "cards.eligibility",
        "entrance_exams": "cards.entrance_exams",
    }
    body = "\n".join(
        f"{ui_text(language_code, label_paths[section.id])}: {section.body}"
        if section.id in label_paths
        else (f"{section.title}: {section.body}" if section.title else section.body)
        for section in content.sections
        if section.body
    ).strip()
    if not body:
        body = (content.summary or content.title).strip()
    title_path = (
        "cards.placements_training"
        if descriptor.context_id == "placements"
        else "cards.admissions"
    )
    return _unit_from_aggregate_content(
        descriptor,
        content,
        body=body,
        title=ui_text(language_code, title_path),
    )
def _unit_from_department_content(
    descriptor: ContentUnitDescriptor,
    content: CanonicalContent,
) -> ContentUnit | None:
    by_id = {s.id: s for s in content.sections}
    sec = by_id.get(descriptor.section_id)
    if sec is None:
        return None

    locale_id = locale_file_id_for_lang_key(content.language_code)
    lk = _effective_lang(locale_id)
    labels = dept_labels(lk)

    if descriptor.section_id == "intro":
        title = (content.title or sec.title or "").strip() or labels["department"]
    else:
        label_key = {
            "hod_voice": "hodAndVision",
            "achievements": "achievements",
            "placement": "placements",
            "fees": "fees",
        }.get(descriptor.section_id)
        title = labels[label_key] if label_key else sec.title

    body = (sec.body or "").strip() or labels["notAvail"]
    summary = body[:200] if body else title
    hod_name = ""
    if descriptor.section_id == "hod_voice":
        hod_name = _hod_name_for_department(descriptor.entity_id, content.language_code)

    unit_hash = compute_unit_hash(
        unit_id=descriptor.unit_id,
        context=descriptor.context,
        context_id=descriptor.context_id,
        section_id=descriptor.section_id,
        body=body,
        language_code=content.language_code,
        canonical_source=descriptor.canonical_source,
    )

    return ContentUnit(
        unit_id=descriptor.unit_id,
        surface=descriptor.surface,
        content_type=descriptor.content_type,
        entity_type=descriptor.entity_type,
        entity_id=descriptor.entity_id,
        context=descriptor.context,
        context_id=descriptor.context_id,
        section_id=descriptor.section_id,
        title=title,
        summary=summary,
        body=body,
        language=content.language,
        language_code=content.language_code,
        canonical_source=descriptor.canonical_source,
        source_version=_SOURCE_VERSION,
        content_hash=unit_hash,
        metadata={"department": descriptor.entity_id, "hod_name": hod_name} if hod_name else {"department": descriptor.entity_id},
        keywords=(descriptor.entity_id, descriptor.unit_suffix),
        presentation_capabilities=("dept_slide",),
    )


def _hod_name_for_department(dept_key: str, language_code: str) -> str:
    """Official HOD name from locale role_holders; English fallback. Proper noun, not translated."""
    key = (dept_key or "").strip().lower()
    for code in (language_code, "en"):
        data = load_locale_data_for_lang_key(code)
        holders = data.get("role_holders") if isinstance(data, dict) else None
        by_dept = holders.get("hod_by_department") if isinstance(holders, dict) else None
        row = by_dept.get(key) if isinstance(by_dept, dict) else None
        if isinstance(row, dict):
            name = str(row.get("hod_name") or "").strip()
            if name:
                return name
    return ""


def _resolve_leadership_unit(
    descriptor: ContentUnitDescriptor,
    *,
    language: str,
    language_code: str,
) -> ContentUnit | None:
    surface = {
        "principal": SURFACE_PRINCIPAL,
        "vice_principal": SURFACE_VICE_PRINCIPAL,
        "trustees": SURFACE_TRUSTEES,
    }.get(descriptor.adapter_key)
    if not surface:
        return None
    display = (language or "").strip() or LANGUAGE_KEY_TO_NAME.get(language_code, "English")
    content = ContentResolver().resolve(
        ResolveRequest(
            surface=surface,
            language=display,
            language_code=language_code,
        )
    )
    if content is None:
        return None
    bio = ""
    title = (content.title or "").strip()
    by_id = {s.id: s for s in content.sections}
    if "bio" in by_id:
        bio = (by_id["bio"].body or "").strip()
        title = (by_id.get("title").body if by_id.get("title") else title) or title
    elif content.sections:
        bio = "\n".join(s.body for s in content.sections if s.body).strip()
    body = bio or (content.summary or title)
    return _unit_from_aggregate_content(descriptor, content, body=body, title=title or content.title)


def _resolve_fees_overview(
    descriptor: ContentUnitDescriptor,
    *,
    language: str,
    language_code: str,
) -> ContentUnit | None:
    from backend.services.content.types import SURFACE_DEPARTMENT_FEES

    content = ContentResolver().resolve(
        ResolveRequest(
            surface=SURFACE_DEPARTMENT_FEES,
            language=language,
            language_code=language_code,
        )
    )
    if content is None:
        return None
    body = "\n".join(f"{s.title}: {s.body}" for s in content.sections).strip()
    return _unit_from_aggregate_content(descriptor, content, body=body, title=content.title)


def _resolve_documents_unit(
    descriptor: ContentUnitDescriptor,
    *,
    language: str,
    language_code: str,
) -> ContentUnit | None:
    from backend.services.content.types import SURFACE_DOCUMENTS

    content = ContentResolver().resolve(
        ResolveRequest(
            surface=SURFACE_DOCUMENTS,
            language=language,
            language_code=language_code,
        )
    )
    if content is None:
        return None
    body = "\n".join(f"{i + 1}. {s.body}" for i, s in enumerate(content.sections)).strip()
    title = content.title
    return _unit_from_aggregate_content(descriptor, content, body=body, title=title)


def _resolve_campus_unit(
    descriptor: ContentUnitDescriptor,
    *,
    language: str,
    language_code: str,
) -> ContentUnit | None:
    data = load_locale_data_for_lang_key(language_code)
    block = data.get("campus_units") if isinstance(data, dict) else None
    row = block.get(descriptor.unit_id) if isinstance(block, dict) else None
    if not isinstance(row, dict):
        return None
    content_status = str(row.get("content_status") or "").strip()
    raw_title = str(row.get("title") or descriptor.unit_id).strip()
    title = _public_campus_title(raw_title) if language_code == "kn" else raw_title
    body = str(row.get("body") or "").strip()
    summary = str(row.get("tts_summary") or body or title).strip()
    points = row.get("points") if isinstance(row.get("points"), list) else []
    if content_status == _SAMPLE_CONTENT_STATUS:
        blocked = ui_text(language_code, "availability.official_fact_blocked").replace("\n", " ")
        body = blocked
        summary = blocked
        points = []
    elif points:
        extra = "\n".join(str(p).strip() for p in points if str(p).strip())
        if extra and extra not in body:
            body = f"{body}\n{extra}".strip()
    display = (language or "").strip() or LANGUAGE_KEY_TO_NAME.get(language_code, "English")
    unit_hash = compute_unit_hash(
        unit_id=descriptor.unit_id,
        context=descriptor.context,
        context_id=descriptor.context_id,
        section_id=descriptor.section_id,
        body=body,
        language_code=language_code,
        canonical_source=descriptor.canonical_source,
    )
    return ContentUnit(
        unit_id=descriptor.unit_id,
        surface=descriptor.surface,
        content_type=descriptor.content_type,
        entity_type=descriptor.entity_type,
        entity_id=descriptor.entity_id,
        context=descriptor.context,
        context_id=descriptor.context_id,
        section_id=descriptor.section_id,
        title=title,
        summary=summary if language_code == "kn" else summary[:200],
        body=body,
        language=display,
        language_code=language_code,
        canonical_source=descriptor.canonical_source,
        source_version=_SOURCE_VERSION,
        content_hash=unit_hash,
        metadata={
            "content_status": content_status,
            "tts_summary": summary,
        },
        keywords=(descriptor.entity_id, descriptor.unit_suffix),
        presentation_capabilities=("campus_unit",),
    )


def _unit_from_aggregate_content(
    descriptor: ContentUnitDescriptor,
    content: CanonicalContent,
    *,
    body: str,
    title: str,
) -> ContentUnit:
    unit_hash = compute_unit_hash(
        unit_id=descriptor.unit_id,
        context=descriptor.context,
        context_id=descriptor.context_id,
        section_id=descriptor.section_id,
        body=body,
        language_code=content.language_code,
        canonical_source=descriptor.canonical_source,
    )
    return ContentUnit(
        unit_id=descriptor.unit_id,
        surface=descriptor.surface,
        content_type=descriptor.content_type,
        entity_type=descriptor.entity_type,
        entity_id=descriptor.entity_id,
        context=descriptor.context,
        context_id=descriptor.context_id,
        section_id=descriptor.section_id,
        title=title,
        summary=(content.summary or title)[:200],
        body=body,
        language=content.language,
        language_code=content.language_code,
        canonical_source=descriptor.canonical_source,
        source_version=_SOURCE_VERSION,
        content_hash=unit_hash,
        metadata=dict(content.metadata or {}),
        keywords=tuple(content.keywords or ()),
        presentation_capabilities=(),
    )


def build_unit_from_section(
    *,
    descriptor: ContentUnitDescriptor,
    content: CanonicalContent,
    section: ContentSection,
    lang_key: str,
) -> ContentUnit:
    """Build a ContentUnit from an already-resolved department CanonicalContent section."""
    locale_id = locale_file_id_for_lang_key(lang_key)
    lk = _effective_lang(locale_id)
    labels = dept_labels(lk)

    if descriptor.section_id == "intro":
        title = (content.title or section.title or "").strip() or labels["department"]
    else:
        label_key = {
            "hod_voice": "hodAndVision",
            "achievements": "achievements",
            "placement": "placements",
            "fees": "fees",
        }.get(descriptor.section_id)
        title = labels[label_key] if label_key else section.title

    body = (section.body or "").strip() or labels["notAvail"]
    summary = body[:200] if body else title
    hod_name = ""
    if descriptor.section_id == "hod_voice":
        hod_name = _hod_name_for_department(descriptor.entity_id, content.language_code)
    unit_hash = compute_unit_hash(
        unit_id=descriptor.unit_id,
        context=descriptor.context,
        context_id=descriptor.context_id,
        section_id=descriptor.section_id,
        body=body,
        language_code=content.language_code,
        canonical_source=descriptor.canonical_source,
    )
    return ContentUnit(
        unit_id=descriptor.unit_id,
        surface=descriptor.surface,
        content_type=descriptor.content_type,
        entity_type=descriptor.entity_type,
        entity_id=descriptor.entity_id,
        context=descriptor.context,
        context_id=descriptor.context_id,
        section_id=descriptor.section_id,
        title=title,
        summary=summary,
        body=body,
        language=content.language,
        language_code=content.language_code,
        canonical_source=descriptor.canonical_source,
        source_version=_SOURCE_VERSION,
        content_hash=unit_hash,
        metadata={"department": descriptor.entity_id, "hod_name": hod_name} if hod_name else {"department": descriptor.entity_id},
        keywords=(descriptor.entity_id, descriptor.unit_suffix),
        presentation_capabilities=("dept_slide",),
    )
