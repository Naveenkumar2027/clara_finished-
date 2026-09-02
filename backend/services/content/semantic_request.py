"""SemanticRequest — language-independent semantic intent for ContentUnit selection (M5.1/M5.3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from backend.services.content.card_registry import card_id_for_topic, intent_id_for_topic

SemanticConfidence = Literal["HIGH", "MEDIUM", "LOW", "NONE"]

@dataclass(frozen=True)
class SemanticRequest:
    """
    Immutable semantic request used only for deterministic unit selection.

    Must not:
    - mutate CI intent values
    - choose presentation surface
    - call RAG / LLM
    """

    language_code: str
    topic: str
    entities: tuple[str, ...]  # department json keys, e.g. ("cse", "cse_aiml")
    context: str  # e.g. "department"
    requested_scope: str  # "single" | "full_department"
    confidence: SemanticConfidence
    source: str
    raw_text: str

    # Ordered (entity, topic) pairs in user order. This is the composition contract:
    # N pairs → N independently addressable units. Empty means "derive from
    # topic × entities", which keeps pre-M5.4 constructions valid.
    items: tuple[tuple[str, str], ...] = ()

    diagnostics: dict[str, Any] | None = None

    @property
    def unit_items(self) -> tuple[tuple[str, str], ...]:
        """Canonical ordered (entity, topic) pairs for unit selection."""
        if self.items:
            return self.items
        return tuple((entity, self.topic) for entity in self.entities)

    @property
    def is_mixed_composition(self) -> bool:
        """True when the request addresses more than one topic."""
        return len({topic for _, topic in self.unit_items}) > 1

    @property
    def intent_ids(self) -> tuple[str, ...]:
        """Language-independent intent IDs, ordered as expressed by the user."""
        out: list[str] = []
        for _, topic in self.unit_items:
            intent_id = intent_id_for_topic(topic)
            if intent_id not in out:
                out.append(intent_id)
        return tuple(out)

    @property
    def intent_id(self) -> str:
        """Primary canonical intent ID (multi-card requests also expose intent_ids)."""
        return self.intent_ids[0] if self.intent_ids else "unknown"

    @property
    def department_ids(self) -> tuple[str, ...]:
        """Canonical department IDs, never localized display labels."""
        return self.entities

    @property
    def requested_card_ids(self) -> tuple[str, ...]:
        """Legacy ordered card *types* independent of presentation language.

        This projection deliberately remains de-duplicated for compatibility.  Code
        that needs card instances must use :attr:`requested_cards`; a card ID alone
        cannot distinguish the same card for two departments.
        """
        out: list[str] = []
        for _, topic in self.unit_items:
            card_id = card_id_for_topic(topic)
            if card_id not in out:
                out.append(card_id)
        return tuple(out)

    @property
    def requested_cards(self) -> tuple[dict[str, str], ...]:
        """Ordered canonical card instances with their entity association intact."""
        out: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        department_ids = set(self.department_ids)
        for entity, topic in self.unit_items:
            card_id = card_id_for_topic(topic)
            department_id = entity if entity in department_ids else ""
            entity_id = entity if entity and not department_id and entity not in {"leadership", "college"} else ""
            identity = (card_id, department_id, entity_id or "global")
            if identity in seen:
                continue
            seen.add(identity)
            card = {"cardId": card_id}
            if department_id:
                card["departmentId"] = department_id
            elif entity_id:
                card["entityId"] = entity_id
            out.append(card)
        return tuple(out)

    def canonical_result(self) -> dict[str, object]:
        """Stable debug/test projection of the understanding layer."""
        return {
            "language": self.language_code,
            "intentId": self.intent_id,
            "intentIds": list(self.intent_ids),
            "departmentIds": list(self.department_ids),
            "requestedCardIds": list(self.requested_card_ids),
            "requestedCards": list(self.requested_cards),
            "activeIndex": 0,
        }
