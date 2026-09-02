"""NarrationResolver — department_overview via CanonicalContent; other intents legacy."""

from __future__ import annotations

from typing import Any

from backend.services.answer_generation import (
    INTENT_DEPARTMENT_OVERVIEW,
    _wants_all_departments_narration,
)
from backend.services.content.department_resolver import resolve_department_key
from backend.services.content.diagnostics import content_event
from backend.services.content.resolver import ContentResolver
from backend.services.content.surface_narration_mapper import (
    department_unlisted_segments,
    extract_department_units,
    map_canonical_content_to_segments,
    map_content_units_to_segments,
)
from backend.services.content.unit_selector import resolve_units_for_plan, select_content_units
from backend.services.content.semantic_request_parser import parse_semantic_request
from backend.services.content.types import SURFACE_DEPARTMENT_OVERVIEW, ResolveRequest
from backend.services.presentation.presentation_plan_builder import build_full_department_plan
from backend.services.narration_plan import build_pre_llm_narration_plan
from backend.services.orchestration.diagnostics import orch_event
from backend.services.orchestration.types import ConversationResolution


def resolve_narration(
    *,
    resolution: ConversationResolution,
    entities: dict[str, Any] | None = None,
    user_text: str = "",
) -> list[Any] | None:
    """
    Build narration segments only when should_generate_presentation.
    Uses resolution.language_code_key (never invents a second language).
    """
    if not resolution.should_generate_presentation:
        return None
    intent = resolution.intent
    if not intent:
        orch_event("NARRATION_FAIL", reason="missing_intent")
        return None

    ents = dict(entities or resolution.canonical_entities or {})
    dept = resolution.department_label or ents.get("department")
    lang_key = resolution.language_code_key or "en"

    # M5.2 UNIT-BACKED: when department_overview card is active, narration is owned by
    # UnitSelector → PresentationPlan (never RAG/LLM). Do not hybridize with fixed decks.
    if resolution.semantic_request is not None or resolution.card_surface == SURFACE_DEPARTMENT_OVERVIEW:
        if _wants_all_departments_narration(user_text or ""):
            return _legacy_plan(
                intent=intent,
                resolution=resolution,
                user_text=user_text,
                dept=dept,
                menu_key=None,
            )

        semantic_request = resolution.semantic_request
        if semantic_request is None:
            # Compatibility for direct resolver callers predating the canonical
            # orchestration contract. Production turns always carry the request
            # created by Conversation Intelligence and never enter this branch.
            semantic_request = parse_semantic_request(
                raw_text=user_text or "",
                language_code_key=resolution.language_code_key or "en",
                ci_entities=ents,
            )
        if semantic_request is None and not ents.get("from_menu"):
            # Fail closed. An unresolved semantic request must never be answered with a
            # guessed department deck; the response decision clarifies instead.
            orch_event("NARRATION_FAIL", reason="semantic_request_unresolved")
            return None

        if semantic_request:
            plan = select_content_units(
                semantic_request,
                surface=resolution.card_surface or SURFACE_DEPARTMENT_OVERVIEW,
            )
            # UnitSelector already fails closed, so any plan it returns is authoritative,
            # including mixed-topic and mixed-department compositions.
            if plan and plan.units:
                units = resolve_units_for_plan(plan)
                if len(units) == len(plan.units):
                    segs = map_content_units_to_segments(
                        units,
                        lang_key=lang_key,
                        guest_name=str(ents.get("guest_name") or "").strip() or None,
                    )
                    if segs and len(segs) == len(plan.units):
                        # Populate canonical metadata for M4.x migration parity checks.
                        # Multi-HOD: use first entity for canonical dept metadata only.
                        from_menu = bool(ents.get("from_menu"))
                        hint = ents.get("department_hint")
                        meta_dept = dept
                        if len(semantic_request.entities) >= 1:
                            meta_dept = semantic_request.entities[0]
                        dept_res = resolve_department_key(
                            department=None if from_menu else meta_dept,
                            menu_department=dept if from_menu else None,
                            department_hint=str(hint).strip() if hint else None,
                            language=lang_key,
                            user_text=user_text,
                        )
                        if (
                            resolution.card_surface == SURFACE_DEPARTMENT_OVERVIEW
                            and dept_res.json_key
                            and len(semantic_request.entities) == 1
                        ):
                            content = ContentResolver().resolve(
                                ResolveRequest(
                                    surface=SURFACE_DEPARTMENT_OVERVIEW,
                                    department=dept_res.json_key,
                                    language=resolution.language,
                                    language_code=lang_key,
                                )
                            )
                            if content is not None and content.metadata.get("mode") != "all":
                                resolution.canonical_surface = content.surface
                                resolution.canonical_content_id = content.content_id
                                resolution.content_hash = content.hash

                        content_event(
                            "CONTENT_READY",
                            surface=SURFACE_DEPARTMENT_OVERVIEW,
                            content_id="m5.2-unit-selector",
                            content_hash=plan.plan_hash,
                        )
                        return segs

        # Keep the overview compatibility fallback, but never replace an
        # unavailable specific unit with a broader department overview.
        if resolution.card_surface == SURFACE_DEPARTMENT_OVERVIEW:
            return _resolve_department_overview(
                resolution=resolution,
                entities=ents,
                department_label=str(dept).strip() if dept else None,
                user_text=user_text or "",
            )
        return None

    if intent == INTENT_DEPARTMENT_OVERVIEW:
        return _resolve_department_overview(
            resolution=resolution,
            entities=ents,
            department_label=str(dept).strip() if dept else None,
            user_text=user_text or "",
        )

    # Non-department intents: legacy builder (menu_department_json_key unused for non-dept)
    return _legacy_plan(
        intent=intent,
        resolution=resolution,
        user_text=user_text,
        dept=dept,
        menu_key=None,
    )


def _legacy_plan(
    *,
    intent: str,
    resolution: ConversationResolution,
    user_text: str,
    dept: Any,
    menu_key: str | None,
) -> list[Any] | None:
    try:
        plan = build_pre_llm_narration_plan(
            intent,
            resolution.language_code_key,
            user_text=user_text or "",
            detected_department_label=dept,
            menu_department_json_key=menu_key,
        )
    except Exception as exc:  # noqa: BLE001
        orch_event("NARRATION_FAIL", reason="plan_exception", detail=str(exc)[:200])
        return None
    if not plan:
        orch_event("NARRATION_FAIL", reason="empty_plan")
        return None
    content_event("NARRATION_READY", intent=intent, segment_count=len(plan), via="legacy")
    orch_event("NARRATION_OK", segments=len(plan), intent=intent)
    return plan


def _resolve_department_overview(
    *,
    resolution: ConversationResolution,
    entities: dict[str, Any],
    department_label: str | None,
    user_text: str,
) -> list[Any] | None:
    lang_key = resolution.language_code_key or "en"
    from_menu = bool(entities.get("from_menu"))
    hint = entities.get("department_hint")

    dept_res = resolve_department_key(
        department=None if from_menu else department_label,
        menu_department=department_label if from_menu else None,
        department_hint=str(hint).strip() if hint else None,
        language=lang_key,
        user_text=user_text,
    )
    # If menu/voice both passed same label into department when from_menu was set above;
    # also try department when menu path had empty menu_department edge case.
    if not dept_res.json_key and department_label and from_menu:
        dept_res = resolve_department_key(
            department=department_label,
            menu_department=department_label,
            language=lang_key,
            user_text=user_text,
        )

    if not dept_res.json_key:
        segs = department_unlisted_segments(lang_key)
        orch_event("NARRATION_OK", segments=len(segs), intent=INTENT_DEPARTMENT_OVERVIEW, fallback="unlisted")
        return segs

    content = ContentResolver().resolve(
        ResolveRequest(
            surface=SURFACE_DEPARTMENT_OVERVIEW,
            department=dept_res.json_key,
            language=resolution.language,
            language_code=lang_key,
        )
    )
    if content is None:
        segs = department_unlisted_segments(lang_key)
        orch_event("NARRATION_OK", segments=len(segs), intent=INTENT_DEPARTMENT_OVERVIEW, fallback="unlisted")
        return segs

    # Guard: single-dept request must not silently expand to all-departments mode
    if content.metadata.get("mode") == "all":
        segs = department_unlisted_segments(lang_key)
        orch_event("NARRATION_OK", segments=len(segs), intent=INTENT_DEPARTMENT_OVERVIEW, fallback="unlisted")
        return segs

    resolution.canonical_surface = content.surface
    resolution.canonical_content_id = content.content_id
    resolution.content_hash = content.hash
    content_event(
        "CANONICAL_CONTENT_USED",
        surface=content.surface,
        content_id=content.content_id,
        content_hash=content.hash,
        json_key=dept_res.json_key,
        language=lang_key,
    )

    # M5.0 — unit composition path (full 5-unit dept plan; byte-identical to M4.1)
    plan = build_full_department_plan(
        dept_key=dept_res.json_key,
        turn_id="dept-overview",
        language=resolution.language or "English",
        language_code=lang_key,
        surface=SURFACE_DEPARTMENT_OVERVIEW,
    )
    units = extract_department_units(content, lang_key=lang_key)
    if units and len(units) == len(plan.units):
        segs = map_content_units_to_segments(units, lang_key=lang_key)
    else:
        segs = map_canonical_content_to_segments(content, lang_key=lang_key)
    if not segs:
        segs = department_unlisted_segments(lang_key)
    content_event(
        "CONTENT_READY",
        surface=content.surface,
        content_id=content.content_id,
        content_hash=content.hash,
    )
    content_event(
        "NARRATION_READY",
        surface=SURFACE_DEPARTMENT_OVERVIEW,
        segment_count=len(segs),
        via="canonical",
    )
    orch_event(
        "NARRATION_OK",
        segments=len(segs),
        intent=INTENT_DEPARTMENT_OVERVIEW,
        via="canonical",
        json_key=dept_res.json_key,
    )
    return segs
