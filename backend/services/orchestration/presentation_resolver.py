"""Map M1 PolicyAction → exactly one presentation mode + response flags.

Surface selection is owned solely by SurfaceSelector (Milestone 4.2).
This module consumes SurfaceSelection — it never re-derives or replaces a surface.
"""

from __future__ import annotations

from typing import Any

from backend.services.answer_generation import INTENT_OFF_TOPIC
from backend.services.content.surface_selector import select_surface
from backend.services.conversation.intent_confidence import is_card_intent
from backend.services.conversation.semantic_normalize import UNSUPPORTED_TOPICS
from backend.services.conversation.types import PolicyAction, PolicyDecision
from backend.services.orchestration.types import ConversationResolution, PresentationMode

from backend.services.content.types import (
    SURFACE_DEPARTMENT_FEES,
    SURFACE_DEPARTMENT_OVERVIEW,
    SURFACE_FACULTY,
    SURFACE_HOD,
)
from backend.services.content.semantic_request import SemanticRequest
from backend.services.content.unit_selector import select_content_units

# Template-only topics: seal as DIRECT → DETERMINISTIC (never emit under GROQ).
_DETERMINISTIC_TOPICS: frozenset[str] = frozenset({"LOCATION"})


def _apply_surface_selection(
    resolution: ConversationResolution,
    selection: Any,
) -> None:
    """Apply SurfaceSelection to resolution show_card fields (consume only)."""
    if selection.department:
        resolution.department_label = str(selection.department)
        resolution.canonical_entities.setdefault("department", selection.department)
    if selection.supports_card and selection.card_surface:
        resolution.card_surface = selection.card_surface
        resolution.show_card = selection.card_surface
        resolution.presentation_type = selection.card_surface
    else:
        # FAQ / unknown / supports_card=False — no WS card
        resolution.card_surface = None
        resolution.show_card = None
        resolution.presentation_type = selection.surface


def _plan_is_m52_representable(plan: Any, semantic_request: Any) -> bool:
    """
    A selected plan is representable by definition.

    UnitSelector is the sole composition authority and already fails closed, so any
    plan it returns carries valid, independently addressable units. Re-judging the
    plan here would be a second card authority.
    """
    if plan is None or semantic_request is None:
        return False
    return bool(tuple(getattr(plan, "units", ()) or ()))


# Surfaces whose content is produced by UnitSelector. On a spoken turn they may only
# be shown when a unit plan exists; otherwise the turn fails closed to no card.
_UNIT_BACKED_SURFACES: frozenset[str] = frozenset(
    {SURFACE_DEPARTMENT_OVERVIEW, SURFACE_HOD, SURFACE_FACULTY, SURFACE_DEPARTMENT_FEES}
)


def _apply_unit_plan_authority(
    *,
    resolution: ConversationResolution,
    user_text: str,
    entities: dict[str, Any],
    local_intent: dict[str, Any] | None,
    semantic_request: SemanticRequest | None,
) -> None:
    """
    UnitSelector decides whether this turn has a department card, and which one.

    Contract:
    - never mutate CI intent (`resolution.intent`)
    - a representable plan promotes the surface to the unit-backed deck
    - a unit-backed surface with no plan is dropped (fail closed), unless the turn
      came from an explicit UI click, which owns its own deck
    """
    # SurfaceSelector has already chosen the canonical surface.  UnitSelector
    # validates/selects content for that surface; it must not reinterpret a
    # specific selection (HOD, fees, etc.) as a department overview.
    requested_surface = resolution.card_surface or SURFACE_DEPARTMENT_OVERVIEW
    plan = (
        select_content_units(semantic_request, surface=requested_surface)
        if semantic_request is not None
        else None
    )

    if _plan_is_m52_representable(plan, semantic_request):
        # The unit plan is the card authority for this turn. CI intent families
        # (comparison, course menu, fee-vs-hod ladders) must not veto an explicitly
        # requested composition.
        resolution.card_surface = requested_surface
        resolution.show_card = requested_surface
        resolution.presentation_type = requested_surface
        return

    from_click = bool(local_intent) or bool((entities or {}).get("from_menu"))
    if resolution.card_surface in _UNIT_BACKED_SURFACES and not from_click:
        resolution.card_surface = None
        resolution.show_card = None
        resolution.presentation_type = None
        resolution.should_generate_presentation = False


def resolve_presentation(
    *,
    decision: PolicyDecision,
    resolution: ConversationResolution,
    intent: str | None,
    semantic_topic: str | None,
    entities: dict[str, Any],
    local_intent: dict[str, Any] | None = None,
    faq_matched: bool = False,
    user_text: str = "",
    semantic_request: SemanticRequest | None = None,
) -> ConversationResolution:
    """
    Single presentationMode for the turn. Unsupported topics never become cards.
    Surface is selected only via SurfaceSelector.
    """
    action = decision.action
    resolution.policy = action.value if isinstance(action, PolicyAction) else str(action)
    resolution.answer_source = decision.answer_source or "none"
    resolution.length_kind = decision.length_kind or "normal"
    resolution.intent = intent
    resolution.semantic_topic = semantic_topic
    resolution.canonical_entities = dict(entities or {})
    resolution.short_circuit_reply = decision.reply_text
    resolution.semantic_request = semantic_request

    from backend.services.content.campus_units import campus_items_from_text

    # FOOD / ENVIRONMENT must not become nearest-department cards. Independently
    # registered hostel / canteen / event units are real cards and skip this veto.
    if (
        semantic_topic in UNSUPPORTED_TOPICS
        and action == PolicyAction.CARD_PRESENTATION
        and not campus_items_from_text(user_text)
    ):
        action = PolicyAction.ANSWER
        resolution.policy = PolicyAction.ANSWER.value

    if action == PolicyAction.NO_SPEECH_RETRY:
        resolution.presentation_mode = PresentationMode.RETRY.value
        resolution.response_type = "retry"
        resolution.should_call_groq = False
        resolution.should_call_rag = False
        resolution.should_generate_presentation = False
        return resolution

    if action == PolicyAction.UNKNOWN or action == PolicyAction.ASK_CLARIFICATION:
        resolution.presentation_mode = PresentationMode.UNKNOWN.value
        resolution.response_type = "unknown" if action == PolicyAction.UNKNOWN else "clarification"
        resolution.should_call_groq = False
        resolution.should_call_rag = False
        resolution.should_generate_presentation = False
        return resolution

    if action in (PolicyAction.ENTITY_UPDATE, PolicyAction.GREETING, PolicyAction.SMALL_TALK):
        resolution.presentation_mode = PresentationMode.DIRECT.value
        resolution.response_type = "direct"
        resolution.should_call_groq = False
        resolution.should_call_rag = False
        resolution.should_generate_presentation = False
        return resolution

    if action == PolicyAction.DIRECT_RESPONSE:
        # FAQ path — select surface for diagnostics/ownership; never emit WS card
        selection = select_surface(
            resolution=resolution,
            entities=entities,
            local_intent=local_intent,
            semantic_topic=semantic_topic,
            user_text=user_text,
            intent=intent,
            faq_matched=True,
        )
        _apply_surface_selection(resolution, selection)
        resolution.presentation_mode = PresentationMode.DIRECT_FAQ.value
        resolution.response_type = "faq"
        resolution.should_call_groq = False
        resolution.should_call_rag = False
        resolution.should_generate_presentation = False
        return resolution

    # Off-topic / location → DETERMINISTIC templates (never GROQ authority).
    if intent == INTENT_OFF_TOPIC or (
        semantic_topic in _DETERMINISTIC_TOPICS and semantic_request is None
    ):
        resolution.presentation_mode = PresentationMode.DIRECT.value
        resolution.response_type = "direct"
        resolution.should_call_groq = False
        resolution.should_call_rag = False
        resolution.should_generate_presentation = False
        resolution.length_kind = "clarification"
        if not resolution.short_circuit_reply and intent == INTENT_OFF_TOPIC:
            from backend.services.answer_generation import get_off_topic_reply

            resolution.short_circuit_reply = get_off_topic_reply(resolution.language)
            resolution.answer_source = "policy_off_topic"
        return resolution

    # Card presentation — SurfaceSelector is the only surface owner.
    # A card intent alone cannot open a card; ResponseDecision already projected the mode.
    if action == PolicyAction.CARD_PRESENTATION:
        selection = select_surface(
            resolution=resolution,
            entities=entities,
            local_intent=local_intent,
            semantic_topic=(semantic_request.topic if semantic_request is not None else semantic_topic),
            user_text=user_text,
            intent=intent,
            faq_matched=faq_matched,
        )
        resolution.presentation_mode = PresentationMode.CARD_PRESENTATION.value
        resolution.response_type = "presentation"
        resolution.should_generate_presentation = True
        resolution.should_call_rag = False
        resolution.should_call_groq = False
        resolution.length_kind = "presentation"
        _apply_surface_selection(resolution, selection)
        _apply_unit_plan_authority(
            resolution=resolution,
            user_text=user_text,
            entities=entities,
            local_intent=local_intent,
            semantic_request=semantic_request,
        )
        return resolution

    # ANSWER / passthrough — frontend localIntent presentation stays card-capable
    if (
        decision.answer_source == "localIntent"
        and (decision.length_kind or "") == "presentation"
        and entities.get("department")
    ):
        from backend.services.answer_generation import INTENT_DEPARTMENT_OVERVIEW

        card_intent = intent if intent and is_card_intent(intent) else INTENT_DEPARTMENT_OVERVIEW
        selection = select_surface(
            resolution=resolution,
            entities=entities,
            local_intent=local_intent or {"type": "department_click", "departmentLabel": entities.get("department")},
            semantic_topic=semantic_topic,
            user_text=user_text,
            intent=card_intent,
            faq_matched=False,
        )
        resolution.presentation_mode = PresentationMode.CARD_PRESENTATION.value
        resolution.response_type = "presentation"
        resolution.intent = card_intent
        resolution.should_generate_presentation = True
        resolution.should_call_rag = False
        resolution.should_call_groq = False
        resolution.length_kind = "presentation"
        _apply_surface_selection(resolution, selection)
        _apply_unit_plan_authority(
            resolution=resolution,
            user_text=user_text,
            entities=entities,
            local_intent=local_intent or {"type": "department_click"},
            semantic_request=semantic_request,
        )
        return resolution

    # ANSWER / passthrough normal reply
    resolution.presentation_mode = PresentationMode.NORMAL_REPLY.value
    resolution.response_type = "answer"
    resolution.should_call_groq = True
    resolution.should_call_rag = True
    resolution.should_generate_presentation = False
    return resolution


def degrade_to_full_text(resolution: ConversationResolution, reason: str) -> ConversationResolution:
    resolution.presentation_mode = PresentationMode.FULL_TEXT.value
    resolution.should_generate_presentation = False
    resolution.show_card = None
    resolution.card_surface = None
    resolution.degraded = True
    resolution.degrade_reason = reason
    resolution.length_kind = "normal"
    return resolution
