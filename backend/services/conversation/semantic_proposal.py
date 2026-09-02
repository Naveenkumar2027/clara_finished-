"""SemanticProposal — LLM hint only. Never a ResponseDecision, never a unitId."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from backend.services.conversation.response_decision import DomainRelevance, ResponseMode

ProposalConfidence = Literal["HIGH", "MEDIUM", "LOW"]

ALLOWED_PROPOSAL_KEYS: frozenset[str] = frozenset(
    {
        "domain",
        "mode_hint",
        "items",
        "scope",
        "clarification_target",
        "clarification_reason",
        "answer_topic",
        "confidence",
    }
)

FORBIDDEN_PROPOSAL_KEYS: frozenset[str] = frozenset(
    {
        "unitId",
        "unitid",
        "unit_id",
        "showCard",
        "surface",
        "narration",
        "tts",
        "facts",
        "language",
    }
)

CANONICAL_TOPICS: frozenset[str] = frozenset(
    {"overview", "hod", "faculty", "fees", "achievements", "placements", "location"}
)
ATOMIC_CARD_TOPICS: frozenset[str] = frozenset(
    {"hod", "faculty", "fees", "achievements", "placements", "location", "principal", "vice_principal", "trustees"}
)
ALLOWED_SCOPES: frozenset[str] = frozenset({"single", "full_department"})
ALLOWED_CLARIFY_TARGETS: frozenset[str] = frozenset(
    {"department", "topic", "pairing", "none"}
)
ALLOWED_CLARIFY_REASONS: frozenset[str] = frozenset(
    {
        "missing_department",
        "unknown_department",
        "unbindable_composition",
        "unrecognised_request",
        "none",
    }
)


@dataclass(frozen=True)
class SemanticProposal:
    """Validated LLM proposal. resolve_response_decision remains the mode owner."""

    domain: DomainRelevance
    mode_hint: ResponseMode
    items: tuple[tuple[str, str], ...] = ()
    scope: str = "single"
    clarification_target: str | None = None
    clarification_reason: str | None = None
    answer_topic: str = ""
    confidence: ProposalConfidence = "MEDIUM"
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProposalValidationResult:
    proposal: SemanticProposal | None
    status: str  # accepted | rejected | skipped | error
    reject_reason: str | None = None
    raw: dict[str, Any] | None = None


def has_atomic_card_topics(items: tuple[tuple[str, str], ...] | None) -> bool:
    if not items:
        return False
    return any(topic in ATOMIC_CARD_TOPICS for _, topic in items)
