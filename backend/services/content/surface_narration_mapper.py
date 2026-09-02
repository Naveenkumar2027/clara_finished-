"""SurfaceNarrationMapper — CanonicalContent / ContentUnit → NarrationSegment[] (M5.0)."""

from __future__ import annotations

from backend.services.content.content_unit import ContentUnit
from backend.services.content.card_registry import card_id_for_unit_id
from backend.services.content.content_unit_registry import list_department_unit_descriptors
from backend.services.content.content_unit_resolver import build_unit_from_section
from backend.services.content.diagnostics import content_event
from backend.services.content.types import (
    SURFACE_DEPARTMENT_OVERVIEW,
    CanonicalContent,
    ContentType,
)
from backend.services.content.unit_narration import narrate_unit
from backend.services.narration_plan import (
    NarrationSegment,
    _clip_caption,
    _effective_lang,
    dept_labels,
)
from backend.services.answer_generation import locale_file_id_for_lang_key


_DEPT_SECTION_ORDER = (
    ("intro", None),
    ("hod_voice", "hodAndVision"),
    ("achievements", "achievements"),
    ("placement", "placements"),
    ("fees", "fees"),
)


def map_canonical_content_to_segments(
    content: CanonicalContent | None,
    *,
    lang_key: str,
) -> list[NarrationSegment]:
    """Map CanonicalContent to narration segments. Department only in M4.1/M5.0."""
    if content is None:
        return _department_unlisted_segments(lang_key)

    ctype = (content.content_type or "").lower()
    surface = (content.surface or "").strip()

    if ctype == ContentType.DEPARTMENT.value or surface == SURFACE_DEPARTMENT_OVERVIEW:
        segs = _map_department(content, lang_key)
        content_event(
            "NARRATION_FROM_CANONICAL",
            surface=content.surface,
            language=lang_key,
            segment_count=len(segs),
            content_id=content.content_id,
        )
        return segs

    content_event(
        "NARRATION_FROM_CANONICAL",
        surface=surface,
        language=lang_key,
        ok=False,
        reason="unsupported_content_type",
    )
    return []


def extract_department_units(
    content: CanonicalContent,
    *,
    lang_key: str,
) -> tuple[ContentUnit, ...]:
    """Extract entity-scoped department ContentUnits from resolved CanonicalContent."""
    dept_key = str(content.metadata.get("department") or "").strip().lower()
    if not dept_key or content.metadata.get("mode") == "all":
        return ()

    descriptors = list_department_unit_descriptors(dept_key)
    if not descriptors:
        return ()

    by_id = {s.id: s for s in content.sections}
    if "intro" not in by_id:
        return ()

    units: list[ContentUnit] = []
    for descriptor in descriptors:
        sec = by_id.get(descriptor.section_id)
        if sec is None:
            continue
        units.append(
            build_unit_from_section(
                descriptor=descriptor,
                content=content,
                section=sec,
                lang_key=lang_key,
            )
        )
    return tuple(units)


def map_content_units_to_segments(
    units: tuple[ContentUnit, ...] | list[ContentUnit],
    *,
    lang_key: str,
    guest_name: str | None = None,
) -> list[NarrationSegment]:
    """Map ordered ContentUnits to narration segments (M4.3 section_id contract)."""
    locale_id = locale_file_id_for_lang_key(lang_key)
    lk = _effective_lang(locale_id)
    labels = dept_labels(lk)

    segments: list[NarrationSegment] = []
    name_used = False
    for i, unit in enumerate(units):
        if unit.section_id == "intro":
            title = (unit.title or "").strip() or labels["department"]
        else:
            title = (unit.title or "").strip() or labels["department"]
        body = unit.body or labels["notAvail"]
        body_clipped = _clip_caption(body, 280)
        inject = None if name_used else guest_name
        spoken = narrate_unit(unit, lang_key, guest_name=inject) or body_clipped
        if inject and inject.strip() and inject.strip() in spoken:
            name_used = True
        raw_line = f"{title}\n{body_clipped}".strip()
        # Display keeps card facts. Spoken text is the intent-aware narration plan.
        # M5.8 TTS only speaks tts_text.
        segments.append(
            NarrationSegment(
                display_text=_clip_caption(raw_line, 320),
                tts_text=spoken,
                card_index=i,
                card_id="dept_slide",
                section_id=unit.section_id,
                unit_id=unit.unit_id,
                canonical_card_id=card_id_for_unit_id(unit.unit_id),
            )
        )
    return segments


def department_unlisted_segments(lang_key: str) -> list[NarrationSegment]:
    """Public helper for unknown-department graceful fallback."""
    return _department_unlisted_segments(lang_key)


def _department_unlisted_segments(lang_key: str) -> list[NarrationSegment]:
    locale_id = locale_file_id_for_lang_key(lang_key)
    lk = _effective_lang(locale_id)
    labels = dept_labels(lk)
    txt = f'{labels["department"]}\n{labels["unlisted"]}'
    return [
        NarrationSegment(
            display_text=txt,
            card_index=0,
            card_id="dept",
            section_id="unlisted",
        )
    ]


def _map_department(content: CanonicalContent, lang_key: str) -> list[NarrationSegment]:
    by_id = {s.id: s for s in content.sections}
    if content.metadata.get("mode") == "all" or "intro" not in by_id:
        if content.metadata.get("mode") == "all":
            segs: list[NarrationSegment] = []
            for i, sec in enumerate(content.sections):
                txt = _clip_caption(f"{sec.title}\n{sec.body}".strip(), 280)
                segs.append(
                    NarrationSegment(
                        display_text=txt,
                        card_index=i,
                        card_id="dept_summary",
                        section_id=(sec.id or f"dept_{i}").strip() or f"dept_{i}",
                    )
                )
            return segs if segs else _department_unlisted_segments(lang_key)
        return _department_unlisted_segments(lang_key)

    units = extract_department_units(content, lang_key=lang_key)
    if units:
        return map_content_units_to_segments(units, lang_key=lang_key)

    # Fallback to legacy inline mapping if unit extraction fails
    slides: list[tuple[str, str, str]] = []
    for sec_id, label_key in _DEPT_SECTION_ORDER:
        sec = by_id.get(sec_id)
        body = (sec.body if sec else "") or labels_fallback(lang_key)["notAvail"]
        if sec_id == "intro":
            title = (content.title or (sec.title if sec else "") or "").strip() or labels_fallback(lang_key)["department"]
        else:
            assert label_key is not None
            title = labels_fallback(lang_key)[label_key]
        slides.append((sec_id, title, body))

    segments: list[NarrationSegment] = []
    for i, (sec_id, title, body) in enumerate(slides):
        raw_line = f"{title}\n{_clip_caption(body, 280)}".strip()
        segments.append(
            NarrationSegment(
                display_text=_clip_caption(raw_line, 320),
                card_index=i,
                card_id="dept_slide",
                section_id=sec_id,
            )
        )
    return segments


def labels_fallback(lang_key: str) -> dict[str, str]:
    locale_id = locale_file_id_for_lang_key(lang_key)
    lk = _effective_lang(locale_id)
    return dept_labels(lk)
