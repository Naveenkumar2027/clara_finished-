"""Orchestration types — single ConversationResolution for the turn."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.services.orchestration.presentation_bundle import PresentationBundle


class PresentationMode(str, Enum):
    NORMAL_REPLY = "NORMAL_REPLY"
    CARD_PRESENTATION = "CARD_PRESENTATION"
    FULL_TEXT = "FULL_TEXT"
    DIRECT_FAQ = "DIRECT_FAQ"
    UNKNOWN = "UNKNOWN"
    RETRY = "RETRY"
    DIRECT = "DIRECT"  # greeting / entity / small-talk short-circuit


@dataclass
class ConversationResolution:
    """Single source of truth for downstream main.py branching."""

    language: str = "English"
    language_code_key: str = "en"
    tts_code: str = "en-IN"
    intent: str | None = None
    semantic_topic: str | None = None
    policy: str = "ANSWER"
    presentation_mode: str = PresentationMode.NORMAL_REPLY.value
    presentation_type: str | None = None
    response_type: str = "answer"
    answer_source: str = "none"
    card_surface: str | None = None
    show_card: str | None = None
    should_call_groq: bool = True
    should_call_rag: bool = True
    should_generate_presentation: bool = False
    should_translate: bool = False
    canonical_entities: dict[str, Any] = field(default_factory=dict)
    short_circuit_reply: str | None = None
    length_kind: str = "normal"
    department_label: str | None = None
    degraded: bool = False
    degrade_reason: str | None = None
    # Milestone 3.5
    response_authority: str | None = None
    authority_sealed: bool = False
    presentation_bundle: Any | None = None  # PresentationBundle | None
    # M5.4 — authoritative response mode for the turn: CARD | ANSWER | CLARIFY | FALLBACK.
    # Downstream stages consume it; none of them may contradict it.
    response_mode: str | None = None
    clarification_target: str | None = None
    # Milestone 4.1 — backend-only canonical identity (never emitted on WS)
    canonical_surface: str | None = None
    canonical_content_id: str | None = None
    content_hash: str | None = None
    # Backend-only immutable understanding contract. It is created once by
    # Conversation Intelligence and consumed by presentation/narration.
    semantic_request: Any | None = None
