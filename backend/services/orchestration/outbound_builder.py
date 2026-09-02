"""Single outbound response builder — main.py emits only (M3.6)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.services.orchestration.presentation_bundle import PresentationBundle
from backend.services.orchestration.response_authority import ResponseAuthority
from backend.services.orchestration.types import ConversationResolution


@dataclass(frozen=True)
class OutboundResponse:
    """Immutable assistant answer payload (existing WS field names via to_ws_payload)."""

    assistant_text: str
    spoken_text: str
    show_card: str | None = None
    narration_plan: dict[str, Any] | None = None
    intent: str | None = None
    department_id: str | None = None
    audio_pending: bool = False
    audio_unavailable: bool = False
    is_speaking: bool = False
    is_processing: bool = False
    direct_reply: bool = False
    utterance_kind: str = "assistant_full_reply"
    segment_index: int = 0
    is_final_segment: bool = True
    rag_used: bool = False
    llm_used: bool = False
    tts_cache_hit: bool = False
    llm_cache_hit: bool = False
    options: list[Any] | None = None
    comparison_departments: list[str] | None = None
    comparison_recommend_focus: str | None = None
    comparison_highlight_id: str | None = None
    payload_type: str | None = None  # e.g. assistant_audio_update
    # Language metadata for multilingual support
    language_code_key: str | None = None
    language_name: str | None = None
    tts_code: str | None = None

    def to_ws_payload(
        self,
        *,
        messages: list[Any],
        turn_id: str,
        debug: dict[str, Any] | None = None,
        audio_b64: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "messages": messages,
            "isProcessing": self.is_processing,
            "isSpeaking": self.is_speaking if audio_b64 is None else bool(audio_b64) or self.is_speaking,
            "audioPending": self.audio_pending,
            "audioUnavailable": self.audio_unavailable if audio_b64 is None else not bool(audio_b64),
            "turn_id": turn_id,
            "assistantText": self.assistant_text,
            "spokenText": self.spoken_text,
            "utterance_kind": self.utterance_kind,
            "segment_index": self.segment_index,
            "is_final_segment": self.is_final_segment,
            "showCard": self.show_card,
            "intent": self.intent,
            "direct_reply": self.direct_reply,
            "rag_used": self.rag_used,
            "llm_used": self.llm_used,
            "tts_cache_hit": self.tts_cache_hit,
            "llm_cache_hit": self.llm_cache_hit,
            # Language fields
            "languageCodeKey": self.language_code_key,
            "languageName": self.language_name,
            "ttsCode": self.tts_code,
        }
        if self.payload_type:
            payload["type"] = self.payload_type
        if self.narration_plan is not None:
            payload["narration_plan"] = self.narration_plan
        if self.department_id:
            payload["departmentId"] = self.department_id
        if self.options:
            payload["options"] = self.options
        if self.comparison_departments:
            payload["comparisonDepartments"] = list(self.comparison_departments)
        if self.comparison_recommend_focus is not None:
            payload["comparisonRecommendFocus"] = self.comparison_recommend_focus
        if self.comparison_highlight_id:
            payload["comparisonHighlightId"] = self.comparison_highlight_id
        if audio_b64:
            payload["audioBase64"] = audio_b64
            payload["audioUnavailable"] = False
            payload["isSpeaking"] = True
        if debug:
            payload.update(debug)
        if extra:
            payload.update(extra)
        return payload


def build_template_outbound(
    *,
    text: str,
    resolution: ConversationResolution,
    utterance_kind: str = "conversation_policy_direct",
    show_card: str | None = None,
) -> OutboundResponse:
    spoken = (text or resolution.short_circuit_reply or "").strip()
    return OutboundResponse(
        assistant_text=spoken,
        spoken_text=spoken,
        show_card=show_card,
        intent=resolution.intent,
        department_id=resolution.department_label,
        direct_reply=True,
        utterance_kind=utterance_kind,
        is_final_segment=True,
        rag_used=False,
        llm_used=False,
        language_code_key=resolution.language_code_key,
        language_name=resolution.language,
        tts_code=resolution.tts_code,
    )


def build_faq_outbound(
    *,
    text: str,
    resolution: ConversationResolution,
) -> OutboundResponse:
    spoken = (text or "").strip()
    return OutboundResponse(
        assistant_text=spoken,
        spoken_text=spoken,
        intent=resolution.intent,
        direct_reply=True,
        utterance_kind="assistant_full_reply",
        rag_used=False,
        llm_used=False,
        language_code_key=resolution.language_code_key,
        language_name=resolution.language,
        tts_code=resolution.tts_code,
    )


def build_card_outbound(
    *,
    resolution: ConversationResolution,
    assistant_text: str,
    turn_id: str,
    department_id: str | None = None,
    options: list[Any] | None = None,
    audio_pending: bool = False,
    is_speaking: bool = False,
    defer_show_card: bool = False,
    llm_cache_hit: bool = False,
    comparison_departments: list[str] | None = None,
    comparison_recommend_focus: str | None = None,
    comparison_highlight_id: str | None = None,
) -> OutboundResponse:
    bundle: PresentationBundle | None = resolution.presentation_bundle
    narration = None
    spoken = (assistant_text or "").strip()
    show = resolution.show_card
    if (
        resolution.response_authority == ResponseAuthority.CARD_PRESENTATION.value
        and bundle is not None
    ):
        narration = bundle.narration_plan_payload(turn_id)
        spoken = bundle.joined_spoken_text() or spoken
        show = bundle.card_surface or show
    return OutboundResponse(
        assistant_text=(assistant_text or spoken).strip(),
        spoken_text=spoken,
        show_card=None if defer_show_card else show,
        narration_plan=narration,
        intent=resolution.intent,
        department_id=department_id or resolution.department_label,
        audio_pending=audio_pending,
        is_speaking=is_speaking,
        direct_reply=False,
        utterance_kind="assistant_visible_answer" if audio_pending else "assistant_full_reply",
        is_final_segment=not audio_pending,
        rag_used=False,
        llm_used=False,
        llm_cache_hit=llm_cache_hit,
        options=options,
        comparison_departments=comparison_departments,
        comparison_recommend_focus=comparison_recommend_focus,
        comparison_highlight_id=comparison_highlight_id,
    )


def build_answer_outbound(
    *,
    resolution: ConversationResolution,
    assistant_text: str,
    spoken_text: str | None = None,
    show_card: str | None = None,
    turn_id: str | None = None,
    department_id: str | None = None,
    direct_reply: bool = False,
    rag_used: bool = False,
    llm_used: bool = False,
    llm_cache_hit: bool = False,
    audio_pending: bool = False,
    is_speaking: bool = False,
    utterance_kind: str = "assistant_full_reply",
    segment_index: int = 0,
    is_final_segment: bool = True,
    options: list[Any] | None = None,
    comparison_departments: list[str] | None = None,
    comparison_recommend_focus: str | None = None,
    comparison_highlight_id: str | None = None,
    payload_type: str | None = None,
    defer_show_card: bool = False,
) -> OutboundResponse:
    """Generic builder for GROQ / DETERMINISTIC / FAQ continuing paths."""
    auth = resolution.response_authority
    bundle: PresentationBundle | None = resolution.presentation_bundle
    narration = None
    spoken = (spoken_text if spoken_text is not None else assistant_text or "").strip()
    card = show_card if show_card is not None else resolution.show_card

    if auth == ResponseAuthority.CARD_PRESENTATION.value and bundle is not None and turn_id:
        narration = bundle.narration_plan_payload(turn_id)
        spoken = bundle.joined_spoken_text() or spoken
        card = bundle.card_surface or card

    return OutboundResponse(
        assistant_text=(assistant_text or spoken).strip(),
        spoken_text=spoken,
        show_card=None if defer_show_card else card,
        narration_plan=narration,
        intent=resolution.intent,
        department_id=department_id or resolution.department_label,
        audio_pending=audio_pending,
        is_speaking=is_speaking,
        direct_reply=direct_reply,
        utterance_kind=utterance_kind,
        segment_index=segment_index,
        is_final_segment=is_final_segment,
        rag_used=rag_used,
        llm_used=llm_used,
        llm_cache_hit=llm_cache_hit,
        options=options,
        comparison_departments=comparison_departments,
        comparison_recommend_focus=comparison_recommend_focus,
        comparison_highlight_id=comparison_highlight_id,
        payload_type=payload_type,
        language_code_key=resolution.language_code_key,
        language_name=resolution.language,
        tts_code=resolution.tts_code,
    )
