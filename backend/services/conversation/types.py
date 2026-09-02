"""Shared types for the Conversation Intelligence Layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PolicyAction(str, Enum):
    ANSWER = "ANSWER"
    ASK_CLARIFICATION = "ASK_CLARIFICATION"
    UNKNOWN = "UNKNOWN"
    GREETING = "GREETING"
    SMALL_TALK = "SMALL_TALK"
    ENTITY_UPDATE = "ENTITY_UPDATE"
    CARD_PRESENTATION = "CARD_PRESENTATION"
    DIRECT_RESPONSE = "DIRECT_RESPONSE"
    NO_SPEECH_RETRY = "NO_SPEECH_RETRY"


# Actions that must not call Groq / RAG / narration plan.
SHORT_CIRCUIT_ACTIONS: frozenset[PolicyAction] = frozenset(
    {
        PolicyAction.NO_SPEECH_RETRY,
        PolicyAction.UNKNOWN,
        PolicyAction.ASK_CLARIFICATION,
        PolicyAction.ENTITY_UPDATE,
        PolicyAction.GREETING,
        PolicyAction.SMALL_TALK,
    }
)


@dataclass
class TranscriptAssessment:
    confidence: float
    too_short: bool
    likely_noise: bool
    likely_partial: bool
    contains_only_filler: bool
    normalized_text: str


@dataclass
class ExtractedEntities:
    person_name: str | None = None
    department: str | None = None
    course: str | None = None
    year: str | None = None
    bus_route: str | None = None
    location: str | None = None
    phone: str | None = None
    email: str | None = None
    name_introduction: bool = False  # True when utterance is primarily a name intro

    def as_session_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.department:
            out["department"] = self.department
        if self.course:
            out["course"] = self.course
        if self.year:
            out["year"] = self.year
        if self.bus_route:
            out["bus_route"] = self.bus_route
        if self.location:
            out["location"] = self.location
        if self.phone:
            out["phone"] = self.phone
        if self.email:
            out["email"] = self.email
        return out


@dataclass
class IntentResult:
    intent: str
    confidence: float
    matched_source: str  # features | faq | localIntent | semantic_topic | none


@dataclass
class PolicyDecision:
    action: PolicyAction
    reply_text: str | None = None
    answer_source: str = "none"
    unknown_fallback: bool = False
    passthrough: bool = False
    intent_hint: str | None = None
    length_kind: str = "normal"  # normal | unknown | clarification | presentation
    session_updates: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationIntelligenceResult:
    assessment: TranscriptAssessment
    entities: ExtractedEntities
    semantic_topic: str | None
    intent_result: IntentResult | None
    decision: PolicyDecision
    # Authoritative CARD / ANSWER / CLARIFY / FALLBACK decision for the turn.
    # Typed as Any to keep this module free of content-layer imports.
    response_decision: Any = None
    # The single canonical language-independent request built by CI. Card and
    # narration layers consume this object; they must not reparse raw text.
    semantic_request: Any = None
