"""SurfaceSelector — sole production owner of surface selection (Milestone 4.2).

Invariant: Consumers may never derive or replace a surface. They only consume
SurfaceSelection (same spirit as ResponseAuthority).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.services.answer_generation import (
    INTENT_ADMISSIONS,
    INTENT_BUS_ROUTES,
    INTENT_COLLEGE_OVERVIEW,
    INTENT_COURSE_MENU,
    INTENT_DEPARTMENT_COMPARISON,
    INTENT_DEPARTMENT_FEES,
    INTENT_DEPARTMENT_OVERVIEW,
    INTENT_DOCUMENTS,
    INTENT_HOD_PROFILE,
    INTENT_HOD_TRUSTEES_PROFILE,
    INTENT_PLACEMENTS,
    INTENT_PRINCIPAL_PROFILE,
    INTENT_TRUSTEES_PROFILE,
    INTENT_VICE_PRINCIPAL_PROFILE,
)
from backend.services.content.diagnostics import content_event
from backend.services.content.surface_registry import SurfaceDescriptor, get_surface
from backend.services.content.types import (
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
    SURFACE_PLACEMENTS,
    SURFACE_PRINCIPAL,
    SURFACE_TRUSTEES,
    SURFACE_VICE_PRINCIPAL,
)
from backend.services.conversation.semantic_normalize import UNSUPPORTED_TOPICS

# FE / localIntent trigger aliases → canonical surface
_TRIGGER_ALIASES: dict[str, str] = {
    "department_overview": SURFACE_DEPARTMENT_OVERVIEW,
    "department": SURFACE_DEPARTMENT_OVERVIEW,
    "dept": SURFACE_DEPARTMENT_OVERVIEW,
    "department_fees": SURFACE_DEPARTMENT_FEES,
    "fees": SURFACE_DEPARTMENT_FEES,
    "documents": SURFACE_DOCUMENTS,
    "principal_profile": SURFACE_PRINCIPAL,
    "principal": SURFACE_PRINCIPAL,
    "vice_principal_profile": SURFACE_VICE_PRINCIPAL,
    "vice_principal": SURFACE_VICE_PRINCIPAL,
    "hod": SURFACE_HOD,
    "hod_info": SURFACE_HOD,
    "faculty": SURFACE_FACULTY,
    "faculty_list": SURFACE_FACULTY,
    "placements": SURFACE_PLACEMENTS,
    "admissions": SURFACE_ADMISSIONS,
    "trustees": SURFACE_TRUSTEES,
    "college": SURFACE_COLLEGE,
    "department_comparison": SURFACE_COMPARISON,
    "comparison": SURFACE_COMPARISON,
    "bus_routes": SURFACE_BUS,
    "bus_route": SURFACE_BUS,
    "bus": SURFACE_BUS,
    "course_menu": SURFACE_COURSE_MENU,
    "faq": SURFACE_FAQ,
}

_INTENT_TO_SURFACE: dict[str, str] = {
    INTENT_DEPARTMENT_OVERVIEW: SURFACE_DEPARTMENT_OVERVIEW,
    INTENT_HOD_PROFILE: SURFACE_HOD,
    INTENT_PRINCIPAL_PROFILE: SURFACE_PRINCIPAL,
    INTENT_VICE_PRINCIPAL_PROFILE: SURFACE_VICE_PRINCIPAL,
    INTENT_DEPARTMENT_FEES: SURFACE_DEPARTMENT_FEES,
    INTENT_DOCUMENTS: SURFACE_DOCUMENTS,
    INTENT_ADMISSIONS: SURFACE_ADMISSIONS,
    INTENT_PLACEMENTS: SURFACE_PLACEMENTS,
    INTENT_DEPARTMENT_COMPARISON: SURFACE_COMPARISON,
    INTENT_COLLEGE_OVERVIEW: SURFACE_COLLEGE,
    INTENT_TRUSTEES_PROFILE: SURFACE_TRUSTEES,
    INTENT_BUS_ROUTES: SURFACE_BUS,
    INTENT_COURSE_MENU: SURFACE_COURSE_MENU,
    # Composite: prefer HOD card surface (matches successful CARD emit primary)
    INTENT_HOD_TRUSTEES_PROFILE: SURFACE_HOD,
}

_SEMANTIC_TOPIC_TO_SURFACE: dict[str, str] = {
    "overview": SURFACE_DEPARTMENT_OVERVIEW,
    "hod": SURFACE_HOD,
    "faculty": SURFACE_FACULTY,
    "fees": SURFACE_DEPARTMENT_FEES,
    "placements": SURFACE_PLACEMENTS,
    "admissions": SURFACE_ADMISSIONS,
}


@dataclass(frozen=True)
class SurfaceSelection:
    """Exactly one surface decision for the turn (+ content owner + capability snapshot)."""

    surface: str | None
    owner: str | None
    confidence: float
    reason: str
    department: str | None
    requested_card: str | None
    semantic_topic: str | None
    source: str
    card_surface: str | None = None
    supports_card: bool = False
    narration_owner: str | None = None
    presentation_mode: str | None = None


def normalize_requested_card(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    key = str(raw).strip().lower().replace(" ", "_")
    return _TRIGGER_ALIASES.get(key) or _TRIGGER_ALIASES.get(str(raw).strip()) or (
        key if key in _TRIGGER_ALIASES.values() else None
    )


def intent_to_surface(intent: str | None) -> str | None:
    if not intent:
        return None
    return _INTENT_TO_SURFACE.get(str(intent).strip())


def select_surface(
    *,
    resolution: Any = None,
    entities: dict[str, Any] | None = None,
    local_intent: dict[str, Any] | None = None,
    semantic_topic: str | None = None,
    user_text: str = "",
    intent: str | None = None,
    faq_matched: bool = False,
) -> SurfaceSelection:
    """
    Sole production owner of surface selection.
    Returns exactly one SurfaceSelection (surface may be None = unknown / no card).
    """
    ents = dict(entities or {})
    li = local_intent if isinstance(local_intent, dict) else None
    topic = semantic_topic
    if resolution is not None and topic is None:
        topic = getattr(resolution, "semantic_topic", None)
    if resolution is not None and intent is None:
        intent = getattr(resolution, "intent", None)

    requested = None
    if li:
        requested = li.get("trigger") or li.get("requested_card") or li.get("showCard")
    requested = requested or ents.get("requested_card")
    requested_norm = normalize_requested_card(str(requested) if requested else None)
    dept = ents.get("department") or (li.get("departmentLabel") if li else None)
    if dept is not None:
        dept = str(dept).strip() or None

    content_event(
        "SURFACE_REQUESTED",
        intent=intent,
        local_intent_type=(li or {}).get("type") if li else None,
        requested_card=requested_norm,
        faq_matched=faq_matched,
        semantic_topic=topic,
        department=dept,
    )

    from backend.services.content.campus_units import campus_items_from_text

    if topic in UNSUPPORTED_TOPICS and not campus_items_from_text(user_text or ""):
        return _finish(
            surface=None,
            confidence=1.0,
            reason="unsupported_semantic_topic",
            department=dept,
            requested_card=requested_norm,
            semantic_topic=topic,
            source="unknown",
        )

    # 1) localIntent department_click
    if li and str(li.get("type") or "").strip() == "department_click" and dept:
        return _finish(
            surface=SURFACE_DEPARTMENT_OVERVIEW,
            confidence=0.99,
            reason="localIntent.department_click",
            department=dept,
            requested_card=requested_norm,
            semantic_topic=topic,
            source="localIntent",
        )

    # 2) Explicit requested card / trigger
    if requested_norm:
        return _finish(
            surface=requested_norm,
            confidence=0.95,
            reason="requested_card",
            department=dept,
            requested_card=requested_norm,
            semantic_topic=topic,
            source="requested_card",
        )

    # 3) FAQ
    if faq_matched or (li and normalize_requested_card(str(li.get("trigger") or "")) == SURFACE_FAQ):
        return _finish(
            surface=SURFACE_FAQ,
            confidence=0.98,
            reason="faq_matched",
            department=dept,
            requested_card=requested_norm,
            semantic_topic=topic,
            source="faq",
        )

    # Canonical semantic requests are more specific than the legacy CI intent.  For
    # example, an inherited "ECE fees" follow-up can carry the legacy ADMISSIONS
    # intent while its canonical topic is unambiguously `fees`.
    semantic_surface = _SEMANTIC_TOPIC_TO_SURFACE.get(str(topic or "").strip().casefold())
    if semantic_surface:
        return _finish(
            surface=semantic_surface,
            confidence=0.94,
            reason=f"semantic_topic:{topic}",
            department=dept,
            requested_card=requested_norm,
            semantic_topic=topic,
            source="semantic_request",
        )

    # Intent map (priority order among intents is encoded in _INTENT_TO_SURFACE lookup
    # after callers resolve a single intent). When multiple cues exist, intent is already
    # the winner from CI/main; we map that intent to one surface.
    mapped = intent_to_surface(intent)
    if mapped:
        return _finish(
            surface=mapped,
            confidence=0.9,
            reason=f"intent:{intent}",
            department=dept,
            requested_card=requested_norm,
            semantic_topic=topic,
            source="intent",
        )

    # localIntent presentation with department but no card intent yet
    if li and dept and (li.get("type") or ents.get("from_menu")):
        return _finish(
            surface=SURFACE_DEPARTMENT_OVERVIEW,
            confidence=0.85,
            reason="localIntent.department_fallback",
            department=dept,
            requested_card=requested_norm,
            semantic_topic=topic,
            source="localIntent",
        )

    return _finish(
        surface=None,
        confidence=0.0,
        reason="unknown",
        department=dept,
        requested_card=requested_norm,
        semantic_topic=topic,
        source="unknown",
    )


def _finish(
    *,
    surface: str | None,
    confidence: float,
    reason: str,
    department: str | None,
    requested_card: str | None,
    semantic_topic: str | None,
    source: str,
) -> SurfaceSelection:
    content_event(
        "SURFACE_RESOLVED",
        surface=surface,
        reason=reason,
        source=source,
        confidence=confidence,
    )
    desc: SurfaceDescriptor | None = get_surface(surface) if surface else None
    owner = desc.content_owner if desc else None
    if desc:
        content_event(
            "CONTENT_OWNER_SELECTED",
            surface=surface,
            owner=owner,
            narration_owner=desc.narration_owner,
        )
    content_event(
        "SURFACE_SELECTED",
        surface=surface,
        owner=owner,
        confidence=confidence,
        reason=reason,
        source=source,
    )
    return SurfaceSelection(
        surface=surface,
        owner=owner,
        confidence=confidence,
        reason=reason,
        department=department,
        requested_card=requested_card,
        semantic_topic=semantic_topic,
        source=source,
        card_surface=desc.card_surface if desc else None,
        supports_card=bool(desc.supports_card) if desc else False,
        narration_owner=desc.narration_owner if desc else None,
        presentation_mode=desc.presentation_mode if desc else None,
    )


def surface_selection_to_hints(selection: SurfaceSelection) -> dict[str, Any]:
    """Compatibility shape formerly produced by card_trigger_hints."""
    show = selection.card_surface if selection.supports_card else None
    return {"showCard": show, "departmentId": selection.department}
