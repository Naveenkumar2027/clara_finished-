"""UnitSelector — deterministic selection of ContentUnit IDs from SemanticRequest (M5.1)."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Sequence

from backend.services.content.content_unit_registry import (
    get_unit_descriptor,
    list_department_unit_descriptors,
)
from backend.services.content.content_unit_resolver import resolve_unit
from backend.services.content.content_unit import ContentUnit
from backend.services.content.campus_units import (
    is_campus_entity,
    unit_id_for_campus_item,
)
from backend.services.content.leadership_units import (
    LEADERSHIP_ENTITY,
    is_leadership_topic,
    unit_id_for_leadership_topic,
)
from backend.services.content.global_units import is_global_entity, unit_id_for_global_item
from backend.services.content.multilingual_terms import (
    TOPIC_ACHIEVEMENTS,
    TOPIC_FEES,
    TOPIC_HOD,
    TOPIC_OVERVIEW,
    TOPIC_PLACEMENTS,
)
from backend.services.content.semantic_request import SemanticRequest
from backend.services.presentation.presentation_plan import PresentationPlan
from backend.services.presentation.presentation_policy import PresentationPolicy


_PLANNER_VERSION = "m5.10-partial-unit-preserving-selector"


def _compute_plan_hash(*, units: Sequence[str], surface: str) -> str:
    payload = {"units": list(units), "surface": surface, "planner_version": _PLANNER_VERSION}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _unit_id_for_topic(*, dept_key: str, topic: str) -> str | None:
    suffix_map = {
        TOPIC_OVERVIEW: "overview",
        TOPIC_HOD: "hod",
        TOPIC_FEES: "fees",
        TOPIC_ACHIEVEMENTS: "achievements",
        TOPIC_PLACEMENTS: "placements",
        "faculty": "faculty",
    }
    suffix = suffix_map.get(topic)
    if not suffix:
        return None
    return f"{dept_key}.{suffix}"


def _unit_id_for_item(*, entity: str, topic: str) -> str | None:
    """Map one (entity, topic) pair to a registered unit id. No pairwise special cases."""
    if is_global_entity(entity):
        uid = unit_id_for_global_item(entity, topic)
        return uid if uid and get_unit_descriptor(uid) is not None else None
    if is_campus_entity(entity) or (entity or "").startswith("events.") or (entity or "").startswith("hostel."):
        uid = unit_id_for_campus_item(entity, topic)
        if uid and get_unit_descriptor(uid) is not None:
            return uid
        return None
    if is_leadership_topic(topic) or (entity or "").strip().lower() == LEADERSHIP_ENTITY:
        uid = unit_id_for_leadership_topic(topic)
        if uid and get_unit_descriptor(uid) is not None:
            return uid
        return None
    uid = _unit_id_for_topic(dept_key=entity, topic=topic)
    if uid and get_unit_descriptor(uid) is not None:
        return uid
    return None


def unit_id_for_item(*, entity: str, topic: str) -> str | None:
    """Public map of one (entity, topic) pair to a registered unit id."""
    return _unit_id_for_item(entity=entity, topic=topic)


def semantic_fallback_reason(semantic_request: SemanticRequest | None) -> str | None:
    """Explain why deterministic card selection cannot complete.

    Parsing and registration are deliberately separate: a known concept such as
    ``faculty`` must not become ``overview`` merely because this deployment has no
    faculty ContentUnit/data.
    """
    if semantic_request is None:
        return "UNKNOWN_INTENT"
    if semantic_request.confidence not in {"HIGH", "MEDIUM"}:
        return "LOW_CONFIDENCE"
    if not semantic_request.unit_items:
        return "MISSING_CARD_TYPE"
    if not semantic_request.entities and semantic_request.context == "department":
        return "MISSING_DEPARTMENT"
    if any(
        _unit_id_for_item(entity=entity, topic=topic) is None
        for entity, topic in semantic_request.unit_items
    ):
        return "CARD_NOT_REGISTERED"
    return None


def select_content_units(
    semantic_request: SemanticRequest,
    *,
    surface: str = "department_overview",
) -> PresentationPlan | None:
    """
    Deterministically select content unit IDs required by semantic_request.

    - Never mutates CI intent values.
    - No RAG/LLM.
    - N items → N units. No hidden card cap, no hardcoded pair families.
    """
    if not semantic_request:
        return None
    if semantic_request.confidence not in {"HIGH", "MEDIUM"}:
        return None

    items = semantic_request.unit_items
    if not items:
        return None

    unit_ids: list[str] = []

    if semantic_request.requested_scope == "full_department":
        # Full-department deck stays atomic: one entity, overview only, never mixed.
        if len(items) != 1:
            return None
        dept_key, topic = items[0]
        if topic != TOPIC_OVERVIEW or is_leadership_topic(topic):
            return None
        descriptors = list_department_unit_descriptors(dept_key)
        unit_ids = [d.unit_id for d in descriptors]
    else:
        # N compatible (entity, topic) pairs → N independently addressable units,
        # in user order. No first-only, no family lock, no arbitrary cap.
        seen: set[str] = set()
        unresolved_items: list[tuple[str, str]] = []
        for entity, topic in items:
            uid = _unit_id_for_item(entity=entity, topic=topic)
            if not uid:
                # Preserve every valid requested unit.  A malformed or
                # unsupported pair must not discard valid cards from the same
                # turn, and no replacement entity is invented here.
                unresolved_items.append((entity, topic))
                continue
            if uid in seen:
                continue
            seen.add(uid)
            unit_ids.append(uid)

    if not unit_ids:
        return None

    order = tuple(range(len(unit_ids)))
    planner_policy = PresentationPolicy.SINGLE_UNIT if len(unit_ids) == 1 else PresentationPolicy.MULTI_UNIT
    plan_hash = _compute_plan_hash(units=unit_ids, surface=surface)
    return PresentationPlan(
        presentation_id=str(uuid.uuid4()),
        turn_id="m5.1-unit-selection",
        surface=surface,
        units=tuple(unit_ids),
        order=order,
        language=semantic_request.language_code,
        language_code=semantic_request.language_code,
        presentation_policy=planner_policy,
        planner_version=_PLANNER_VERSION,
        plan_hash=plan_hash,
        unresolved_items=tuple(unresolved_items) if semantic_request.requested_scope != "full_department" else (),
    )


def resolve_units_for_plan(plan: PresentationPlan) -> tuple[ContentUnit, ...]:
    resolved: list[ContentUnit] = []
    for unit_id in plan.units:
        u = resolve_unit(
            unit_id=unit_id,
            language=plan.language,
            language_code=plan.language_code,
        )
        if u is not None:
            resolved.append(u)
    return tuple(resolved)
