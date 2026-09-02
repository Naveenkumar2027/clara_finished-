"""Orchestrate Conversation Intelligence before answer generation."""

from __future__ import annotations

from typing import Any

from backend.config.settings import SEMANTIC_ROUTER_ENABLED
from backend.services.conversation.entity_extractor import (
    entities_need_llm,
    extract_entities_llm_optional,
    extract_entities_rules,
    merge_entities,
)
from backend.services.conversation.intent_confidence import score_intent_from_features
from backend.services.conversation.logging_util import log_conversation_intelligence
from backend.services.conversation.policy_router import route_policy
from backend.services.conversation.response_decision import resolve_response_decision
from backend.services.conversation.semantic_normalize import normalize_semantic_topic
from backend.services.conversation.semantic_router import maybe_propose_semantics
from backend.services.content.semantic_request_parser import parse_semantic_request
from backend.services.conversation.transcript_validator import assess_transcript, needs_speech_retry
from backend.services.conversation.types import (
    ConversationIntelligenceResult,
    IntentResult,
    SHORT_CIRCUIT_ACTIONS,
)
from backend.services.faq_answers import get_faq_answer_for_question


async def run_conversation_intelligence(
    text: str,
    *,
    language_name: str | None,
    language_code_key: str | None = None,
    local_intent: dict[str, Any] | None = None,
    department_hint: str | None = None,
    groq_client: Any | None = None,
    groq_model: str | None = None,
    turn_id: str | None = None,
    skip_faq_probe: bool = False,
    last_semantic_entities: tuple[str, ...] | None = None,
    last_person_unit_id: str | None = None,
) -> ConversationIntelligenceResult:
    """
    Evaluate transcript → entities → intent confidence → policy.

    Does not call RAG. May optionally call Groq only for ambiguous entity extraction.
    FAQ is probed lightly to set DIRECT_RESPONSE passthrough (same matcher as main).
    """
    assessment = assess_transcript(text)

    # Fast path: do not score intent / entities when speech retry is required,
    # unless frontend forced a localIntent (card click).
    force_local = bool(local_intent and isinstance(local_intent, dict) and local_intent)
    if needs_speech_retry(assessment) and not force_local:
        entities = extract_entities_rules("")
        decision = route_policy(
            assessment=assessment,
            entities=entities,
            semantic_topic=None,
            intent_result=None,
            language=language_name,
            local_intent=None,
            faq_matched=False,
        )
        result = ConversationIntelligenceResult(
            assessment=assessment,
            entities=entities,
            semantic_topic=None,
            intent_result=None,
            decision=decision,
        )
        log_conversation_intelligence(result, turn_id=turn_id, language=language_name)
        return result

    entities = extract_entities_rules(text)
    if (
        not force_local
        and not SEMANTIC_ROUTER_ENABLED
        and assessment.confidence >= 0.5
        and entities_need_llm(entities, text)
    ):
        llm_ents = await extract_entities_llm_optional(
            text, groq_client=groq_client, model=groq_model
        )
        entities = merge_entities(entities, llm_ents)

    semantic_topic = normalize_semantic_topic(assessment.normalized_text or text)

    faq_matched = False
    if not skip_faq_probe and not force_local:
        try:
            faq_matched = bool(get_faq_answer_for_question(text, language_name or "English"))
        except Exception:
            faq_matched = False

    intent_result: IntentResult | None = score_intent_from_features(
        assessment.normalized_text or text,
        department_hint=department_hint or entities.department,
        faq_matched=faq_matched,
        local_intent=local_intent if force_local else None,
    )

    # AUTHORITATIVE response mode. Computed before policy/presentation so that every
    # downstream stage consumes one decision instead of re-deriving its own.
    ci_entities: dict[str, Any] = {}
    if entities.department:
        ci_entities["department"] = entities.department
    if last_semantic_entities:
        ci_entities["department_keys"] = list(last_semantic_entities)
    if last_person_unit_id:
        ci_entities["last_person_unit_id"] = last_person_unit_id
    semantic_request = parse_semantic_request(
        raw_text=text or "",
        language_code_key=language_code_key or "en",
        ci_entities=ci_entities or None,
    )
    proposal_result = await maybe_propose_semantics(
        text or "",
        semantic_request=semantic_request,
        local_intent=local_intent if force_local else None,
        faq_matched=faq_matched,
        groq_client=groq_client,
        last_semantic_entities=last_semantic_entities,
    )
    proposal_diagnostics = {
        "proposal_status": proposal_result.status,
        "proposal_reject_reason": proposal_result.reject_reason,
    }
    response_decision = resolve_response_decision(
        text=text or "",
        semantic_request=semantic_request,
        ci_intent=intent_result.intent if intent_result else None,
        has_department_entity=bool(entities.department or (semantic_request and semantic_request.entities)),
        faq_matched=faq_matched,
        local_intent=local_intent if force_local else None,
        validated_proposal=proposal_result.proposal,
        proposal_diagnostics=proposal_diagnostics,
    )

    decision = route_policy(
        assessment=assessment,
        entities=entities,
        semantic_topic=semantic_topic,
        intent_result=intent_result,
        language=language_name,
        local_intent=local_intent if force_local else None,
        faq_matched=faq_matched,
        response_decision=response_decision,
    )

    result = ConversationIntelligenceResult(
        assessment=assessment,
        entities=entities,
        semantic_topic=semantic_topic,
        intent_result=intent_result,
        decision=decision,
        response_decision=response_decision,
        semantic_request=semantic_request,
    )
    log_conversation_intelligence(result, turn_id=turn_id, language=language_name)
    return result


def is_short_circuit(result: ConversationIntelligenceResult) -> bool:
    return result.decision.action in SHORT_CIRCUIT_ACTIONS and not result.decision.passthrough
