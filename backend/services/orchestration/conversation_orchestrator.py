"""ConversationOrchestrator — fixed pipeline producing ConversationResolution."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from backend.services.conversation import is_short_circuit, run_conversation_intelligence
from backend.services.conversation.templates import unknown_reply
from backend.services.conversation.types import PolicyAction
from backend.services.orchestration.card_localization import localize_card_segments
from backend.services.orchestration.diagnostics import orch_event
from backend.services.orchestration.final_validation import validate_turn_integrity
from backend.services.orchestration.localization_resolver import resolve_localization
from backend.services.orchestration.narration_resolver import resolve_narration
from backend.services.orchestration.presentation_bundle import build_presentation_bundle
from backend.services.orchestration.presentation_resolver import (
    degrade_to_full_text,
    resolve_presentation,
)
from backend.services.presentation.diagnostics import presentation_event
from backend.services.presentation.presentation_timeline import build_presentation_timeline
from backend.services.presentation.timeline_contract import validate_presentation_timeline
from backend.services.orchestration.response_authority import (
    ResponseAuthority,
    seal_authority,
)
from backend.services.orchestration.result import OrchestratorResult
from backend.services.orchestration.types import ConversationResolution, PresentationMode
from backend.services.orchestration.validators import validate_conversation_resolution
from backend.services.narration_plan import finalize_segment_list
from backend.services.runtime import freeze_localization, release_localization, sync_runtime_from_session
from backend.services.runtime.presentation_integrity import validate_before_narration_plan
from backend.services.session_language import resolve_session_language


def _session_last_semantic_entities(session: dict[str, Any]) -> tuple[str, ...] | None:
    raw = session.get("last_semantic_entities")
    if not isinstance(raw, (list, tuple)):
        return None
    keys = tuple(str(k).strip() for k in raw if str(k).strip())
    return keys or None


class ConversationOrchestrator:
    """
    Integration layer: calls M1 CI + localization/presentation/narration resolvers + M2 contract.
    Does not reimplement transcript/entity/policy logic.
    """

    async def run(
        self,
        text: str,
        session: dict[str, Any],
        *,
        local_intent: dict[str, Any] | None = None,
        turn_id: str | None = None,
        groq_client: Any | None = None,
        model: str | None = None,
        defer_narration: bool = False,
    ) -> OrchestratorResult:
        orch_event("TURN_STARTED", turn_id=turn_id)
        resolution = ConversationResolution()
        session_updates: dict[str, Any] = {}

        lang_key, lang_name, _ = resolve_session_language(session)
        language_for_ci = session.get("language_name") or lang_name

        intel = await run_conversation_intelligence(
            text,
            language_name=language_for_ci,
            language_code_key=lang_key,
            local_intent=local_intent if isinstance(local_intent, dict) else None,
            department_hint=None,
            groq_client=groq_client,
            groq_model=model,
            turn_id=turn_id,
            last_semantic_entities=_session_last_semantic_entities(session),
            last_person_unit_id=str(session.get("last_person_unit_id") or "").strip() or None,
        )

        orch_event(
            "TRANSCRIPT_OK" if not intel.assessment.likely_noise else "TRANSCRIPT_DEGRADED",
            turn_id=turn_id,
            confidence=intel.assessment.confidence,
        )
        orch_event("ENTITY_OK", turn_id=turn_id, entities=intel.entities.as_session_dict())
        orch_event(
            "INTENT_OK",
            turn_id=turn_id,
            intent=intel.intent_result.intent if intel.intent_result else None,
            confidence=intel.intent_result.confidence if intel.intent_result else None,
            policy=intel.decision.action.value,
        )

        ent_dict = intel.entities.as_session_dict()
        if ent_dict:
            prev = session.get("conversation_entities")
            merged = dict(prev) if isinstance(prev, dict) else {}
            merged.update(ent_dict)
            session["conversation_entities"] = merged
            session_updates["conversation_entities"] = merged
        for key, val in (intel.decision.session_updates or {}).items():
            if key == "guest_name" and intel.entities.person_name:
                session[key] = intel.entities.person_name
                session_updates[key] = intel.entities.person_name
            else:
                session[key] = val
                session_updates[key] = val

        resolve_localization(session, resolution)
        orch_event(
            "LOCALIZATION_OK",
            turn_id=turn_id,
            language=resolution.language,
            code_key=resolution.language_code_key,
            tts_code=resolution.tts_code,
        )
        orch_event(
            "LOCALIZATION_LOCKED",
            turn_id=turn_id,
            language=resolution.language,
            code_key=resolution.language_code_key,
        )

        intent = (
            intel.decision.intent_hint
            or (intel.intent_result.intent if intel.intent_result else None)
        )
        entities_for_pres = dict(ent_dict)
        if intel.entities.person_name:
            entities_for_pres["person_name"] = intel.entities.person_name
        guest = str(session.get("guest_name") or "").strip()
        if guest:
            entities_for_pres["guest_name"] = guest
        if isinstance(local_intent, dict):
            dept_label = str(local_intent.get("departmentLabel") or "").strip()
            if dept_label and not entities_for_pres.get("department"):
                entities_for_pres["department"] = dept_label
                entities_for_pres["from_menu"] = True

        response_decision = getattr(intel, "response_decision", None)
        if response_decision is not None:
            mode = getattr(response_decision, "mode", None)
            resolution.response_mode = str(getattr(mode, "value", mode) or "")
            resolution.clarification_target = getattr(
                response_decision, "clarification_target", None
            )
            card_entities = tuple(getattr(response_decision, "entities", ()) or ())
            if card_entities:
                # CI has already resolved these through the semantic request policy.
                # Pass canonical keys to presentation so anaphoric unit planning can
                # apply the same exact-key validation instead of reusing raw session text.
                entities_for_pres["department_keys"] = list(card_entities)
                session["last_semantic_entities"] = list(card_entities)
                session_updates["last_semantic_entities"] = list(card_entities)
            from backend.services.content.person_context import last_person_unit_from_ids
            from backend.services.content.unit_selector import unit_id_for_item

            person_ids = []
            for entity, topic in tuple(getattr(response_decision, "items", ()) or ()):
                uid = unit_id_for_item(entity=entity, topic=topic)
                if uid:
                    person_ids.append(uid)
            person_uid = last_person_unit_from_ids(person_ids)
            if person_uid:
                session["last_person_unit_id"] = person_uid
                session_updates["last_person_unit_id"] = person_uid
            elif getattr(response_decision, "items", ()):
                session["last_person_unit_id"] = None
                session_updates["last_person_unit_id"] = None

        # M5.4: FOOD / ENVIRONMENT are no longer forced to UNKNOWN here. "How is the
        # canteen food?" and "How is the campus atmosphere?" are institutional questions;
        # the response decision routes genuine off-domain food requests to FALLBACK.
        decision = intel.decision

        resolve_presentation(
            decision=decision,
            resolution=resolution,
            intent=intent,
            semantic_topic=intel.semantic_topic,
            entities=entities_for_pres,
            local_intent=local_intent if isinstance(local_intent, dict) else None,
            faq_matched=bool(
                getattr(intel.decision, "answer_source", None) == "faq"
                or intel.decision.action == PolicyAction.DIRECT_RESPONSE
            ),
            user_text=text or "",
            semantic_request=getattr(intel, "semantic_request", None),
        )
        orch_event(
            "PRESENTATION_OK",
            turn_id=turn_id,
            mode=resolution.presentation_mode,
            show_card=resolution.show_card,
        )

        # Short-circuit: seal template authorities immediately.
        if resolution.short_circuit_reply and resolution.presentation_mode in (
            PresentationMode.RETRY.value,
            PresentationMode.UNKNOWN.value,
            PresentationMode.DIRECT.value,
        ):
            auth = seal_authority(resolution)
            orch_event(
                "AUTHORITY_SELECTED",
                turn_id=turn_id,
                authority=auth.value,
                sealed=True,
            )
            contract = validate_conversation_resolution(resolution)
            if not contract.ok:
                orch_event("CONVERSATION_CONTRACT_FAIL", turn_id=turn_id, failures=contract.failures)
            orch_event("TURN_COMPLETED", turn_id=turn_id, short_circuit=True, authority=auth.value)
            return OrchestratorResult(
                resolution=resolution,
                narration_segments=None,
                session_updates=session_updates,
                intel=intel,
            )

        narration_segments = None
        card_candidate = (
            resolution.presentation_mode == PresentationMode.CARD_PRESENTATION.value
            and resolution.should_generate_presentation
            and not resolution.degraded
        )

        if card_candidate and not defer_narration:
            narration_segments = self.attach_narration(
                resolution,
                session,
                text,
                turn_id=turn_id,
                entities=entities_for_pres,
            )
        elif not card_candidate:
            # Non-card continuing paths (FAQ / GROQ): seal now.
            auth = seal_authority(resolution)
            orch_event(
                "AUTHORITY_SELECTED",
                turn_id=turn_id,
                authority=auth.value,
                sealed=True,
            )
        else:
            # Card deferred — provisional authority not sealed until attach_narration.
            orch_event(
                "AUTHORITY_SELECTED",
                turn_id=turn_id,
                authority=ResponseAuthority.CARD_PRESENTATION.value,
                sealed=False,
                deferred=True,
            )

        conv_contract = validate_conversation_resolution(resolution)
        if not conv_contract.ok:
            orch_event("CONVERSATION_CONTRACT_FAIL", turn_id=turn_id, failures=conv_contract.failures)
            if resolution.presentation_mode == PresentationMode.RETRY.value:
                resolution.should_call_rag = False
                resolution.should_call_groq = False
                resolution.should_generate_presentation = False

        sync_runtime_from_session(
            session,
            turn_id=turn_id,
            current_intent=resolution.intent,
            current_language=resolution.language,
            active_surface=resolution.show_card,
        )
        orch_event(
            "TURN_COMPLETED",
            turn_id=turn_id,
            mode=resolution.presentation_mode,
            authority=resolution.response_authority,
            sealed=resolution.authority_sealed,
            should_call_rag=resolution.should_call_rag,
            should_call_groq=resolution.should_call_groq,
            should_generate_presentation=resolution.should_generate_presentation,
            narration_deferred=defer_narration,
        )
        return OrchestratorResult(
            resolution=resolution,
            narration_segments=narration_segments,
            session_updates=session_updates,
            intel=intel,
        )

    def attach_narration(
        self,
        resolution: ConversationResolution,
        session: dict[str, Any],
        text: str,
        *,
        turn_id: str | None = None,
        entities: dict[str, Any] | None = None,
    ) -> list[Any] | None:
        """
        Build + localize + M2-contract narration once; create immutable PresentationBundle.
        Seals CARD_PRESENTATION on success or GROQ on degrade.
        """
        if resolution.authority_sealed and resolution.response_authority != ResponseAuthority.CARD_PRESENTATION.value:
            orch_event("NARRATION_REJECT", turn_id=turn_id, reason="authority_not_card")
            return None

        if resolution.presentation_bundle is not None:
            orch_event("NARRATION_REJECT", turn_id=turn_id, reason="duplicate_narration")
            return list(resolution.presentation_bundle.segments)  # already built; no rebuild

        if not resolution.should_generate_presentation and not (
            resolution.presentation_mode == PresentationMode.CARD_PRESENTATION.value
        ):
            return None

        # Ensure card flags for deferred attach.
        if not resolution.should_generate_presentation:
            resolution.should_generate_presentation = True

        resolve_localization(session, resolution)
        orch_event(
            "LOCALIZATION_LOCKED",
            turn_id=turn_id,
            language=resolution.language,
            code_key=resolution.language_code_key,
        )

        narration_segments = resolve_narration(
            resolution=resolution,
            entities=entities or resolution.canonical_entities,
            user_text=text,
        )
        if not narration_segments:
            orch_event("NARRATION_DEGRADED", turn_id=turn_id, reason="empty_or_failed_plan")
            degrade_to_full_text(resolution, "narration_plan_fail")
            seal_authority(resolution, authority=ResponseAuthority.GROQ, force=True)
            orch_event("AUTHORITY_SELECTED", turn_id=turn_id, authority=ResponseAuthority.GROQ.value, sealed=True)
            return None

        fid = turn_id or "pending"
        finalize_segment_list(fid, narration_segments)
        orch_event(
            "SEGMENTS_FINALIZED",
            turn_id=turn_id,
            segment_count=len(narration_segments),
            surface=resolution.show_card,
        )

        before_localize = [
            (getattr(s, "display_text", None), getattr(s, "tts_text", None)) for s in narration_segments
        ]
        localized = localize_card_segments(narration_segments, resolution)
        if localized is None:
            orch_event("NARRATION_DEGRADED", turn_id=turn_id, reason="card_localization_fail")
            degrade_to_full_text(resolution, "card_localization_fail")
            seal_authority(resolution, authority=ResponseAuthority.GROQ, force=True)
            orch_event("AUTHORITY_SELECTED", turn_id=turn_id, authority=ResponseAuthority.GROQ.value, sealed=True)
            return None

        narration_segments = localized
        after_localize = [
            (getattr(s, "display_text", None), getattr(s, "tts_text", None)) for s in narration_segments
        ]
        if after_localize != before_localize:
            finalize_segment_list(fid, narration_segments)
            orch_event(
                "SEGMENTS_FINALIZED",
                turn_id=turn_id,
                segment_count=len(narration_segments),
                surface=resolution.show_card,
                reason="post_localize",
            )

        freeze_localization(session)
        sync_runtime_from_session(
            session,
            turn_id=turn_id,
            current_intent=resolution.intent,
            active_surface=resolution.show_card,
            runtime_state="presenting",
        )
        contract = validate_before_narration_plan(
            session,
            narration_segments,
            plan_lang_key=resolution.language_code_key,
            tts_lang_code=resolution.tts_code,
            expected_card_count=len(narration_segments),
            turn_id=turn_id,
        )
        if not contract.ok:
            orch_event(
                "NARRATION_DEGRADED",
                turn_id=turn_id,
                reason=getattr(contract, "primary_reason", None) or "contract_fail",
            )
            release_localization(session)
            sync_runtime_from_session(session, runtime_state="conversation")
            degrade_to_full_text(resolution, "presentation_contract_fail")
            seal_authority(resolution, authority=ResponseAuthority.GROQ, force=True)
            orch_event("AUTHORITY_SELECTED", turn_id=turn_id, authority=ResponseAuthority.GROQ.value, sealed=True)
            return None

        # Build immutable bundle once — no translation/mutation after this.
        bundle = build_presentation_bundle(
            resolution=resolution,
            segments=narration_segments,
            turn_id=turn_id,
        )

        # M4.3 — PresentationTimeline is the playback authority (section_id keyed).
        timeline = build_presentation_timeline(bundle, turn_id=turn_id)
        timeline_contract = validate_presentation_timeline(timeline, bundle=bundle)
        if not timeline_contract.ok:
            orch_event(
                "NARRATION_DEGRADED",
                turn_id=turn_id,
                reason=timeline_contract.primary_reason or "timeline_contract_fail",
                failures=timeline_contract.failures,
            )
            presentation_event(
                "TIMELINE_CONTRACT_FAIL",
                turn_id=turn_id,
                presentationId=bundle.presentation_id,
                failures=timeline_contract.failures,
            )
            presentation_event(
                "PLAYBACK_CONTEXT_REJECTED",
                turn_id=turn_id,
                presentation_id=bundle.presentation_id,
                reason=timeline_contract.primary_reason or "timeline_contract_fail",
            )
            release_localization(session)
            sync_runtime_from_session(session, runtime_state="conversation")
            degrade_to_full_text(resolution, "timeline_contract_fail")
            seal_authority(resolution, authority=ResponseAuthority.GROQ, force=True)
            orch_event(
                "AUTHORITY_SELECTED",
                turn_id=turn_id,
                authority=ResponseAuthority.GROQ.value,
                sealed=True,
            )
            return None

        resolution.presentation_bundle = bundle
        resolution.presentation_mode = PresentationMode.CARD_PRESENTATION.value
        seal_authority(resolution, authority=ResponseAuthority.CARD_PRESENTATION, force=True)
        session["_presentation_timeline"] = timeline
        presentation_event(
            "PRESENTATION_STARTED",
            turn_id=turn_id,
            presentationId=timeline.presentation_id,
            timelineHash=timeline.contract_hash,
            section_ids=[e.section_id for e in timeline.entries],
            segment_count=len(timeline.entries),
            surface=timeline.card_surface,
        )
        presentation_event(
            "PLAYBACK_CONTEXT_SEALED",
            turn_id=turn_id,
            presentation_id=timeline.presentation_id,
            section_ids=[e.section_id for e in timeline.entries],
            surface=timeline.card_surface,
        )

        integrity = validate_turn_integrity(resolution, bundle)
        if not integrity.ok:
            orch_event("TURN_INTEGRITY_FAIL", turn_id=turn_id, failures=integrity.failures)
            resolution.presentation_bundle = None
            session.pop("_presentation_timeline", None)
            release_localization(session)
            degrade_to_full_text(resolution, "turn_integrity_fail")
            seal_authority(resolution, authority=ResponseAuthority.GROQ, force=True)
            return None

        sync_runtime_from_session(
            session,
            turn_id=turn_id,
            active_presentation_id=bundle.presentation_id,
            active_surface=bundle.card_surface,
            runtime_state="presenting",
        )
        orch_event(
            "PRESENTATION_READY",
            turn_id=turn_id,
            presentationId=bundle.presentation_id,
            bundleHash=bundle.contract_hash,
            language=bundle.language,
            segments=len(bundle.segments),
            surface=bundle.card_surface,
            segment_count=len(bundle.segments),
            canonical_surface=bundle.canonical_surface,
            canonical_content_id=bundle.canonical_content_id,
            content_hash=bundle.content_hash,
            timelineHash=timeline.contract_hash,
        )
        orch_event(
            "BUNDLE_READY",
            turn_id=turn_id,
            presentationId=bundle.presentation_id,
            bundleHash=bundle.contract_hash,
            surface=bundle.card_surface,
            segment_count=len(bundle.segments),
        )
        orch_event(
            "AUTHORITY_SELECTED",
            turn_id=turn_id,
            authority=ResponseAuthority.CARD_PRESENTATION.value,
            sealed=True,
        )
        orch_event("NARRATION_OK", turn_id=turn_id, segments=len(narration_segments))
        return narration_segments


def should_short_circuit(result: OrchestratorResult) -> bool:
    """True when main should emit direct reply and return."""
    res = result.resolution
    if res.response_authority in (
        ResponseAuthority.RETRY_TEMPLATE.value,
        ResponseAuthority.UNKNOWN_TEMPLATE.value,
        ResponseAuthority.DETERMINISTIC.value,
    ) and res.short_circuit_reply:
        return True
    if res.short_circuit_reply and res.presentation_mode in (
        PresentationMode.RETRY.value,
        PresentationMode.UNKNOWN.value,
        PresentationMode.DIRECT.value,
    ):
        return True
    if result.intel is not None and is_short_circuit(result.intel) and res.short_circuit_reply:
        return True
    return False
