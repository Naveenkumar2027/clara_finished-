"""
ResponseDecision — the single authority for what kind of turn this is (M5.4).

Exactly one of four modes is chosen per turn:

    CARD      the user asked for content units or a supported card surface
    ANSWER    an institutional question that RAG / answer generation should answer
    CLARIFY   a recognised request that is missing or ambiguous in a known slot
    FALLBACK  out of domain, unsafe, or explicitly unsupported

Hard constraints:
- An LLM may propose a SemanticProposal. This function remains the only writer of
  ResponseDecision.mode. The LLM never writes unitIds.
- Token count is not evidence. A short institutional question is still a question.
- Absence of a card is not FALLBACK. FALLBACK is only off-domain, unsafe, or
  external-college comparison.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import TYPE_CHECKING, Any

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
    has_explicit_admissions_cue,
    maybe_override_intent_with_executive_profile,
)
from backend.services.content.campus_units import is_bare_hostel_request, is_campus_entity
from backend.services.content.global_units import is_global_entity
from backend.services.content.semantic_composition import detect_topic_spans
from backend.services.content.semantic_request import SemanticRequest
from backend.services.content.semantic_topics import cue_in_hay, detect_atomic_topics, is_full_department_scope
from backend.services.content.semantic_vocab.catalog import (
    TOPIC_ACHIEVEMENTS,
    TOPIC_CONTACT,
    TOPIC_FACULTY,
    TOPIC_FEES,
    TOPIC_HOD,
    TOPIC_PLACEMENTS,
)
from backend.services.content.semantic_vocab.institution import institution_cues
from backend.services.content.unicode_text import casefold_keep_scripts

if TYPE_CHECKING:
    from backend.services.conversation.semantic_proposal import SemanticProposal


class ResponseMode(str, Enum):
    CARD = "CARD"
    ANSWER = "ANSWER"
    CLARIFY = "CLARIFY"
    FALLBACK = "FALLBACK"


class DomainRelevance(str, Enum):
    INSTITUTION = "institution"
    UNKNOWN = "unknown"
    OFF_DOMAIN = "off_domain"


# Card surfaces that are not content units. They keep their existing owners but are
# still declared here so "is this a card turn" has one answer.
NON_UNIT_CARD_INTENTS: frozenset[str] = frozenset(
    {
        INTENT_ADMISSIONS,
        INTENT_BUS_ROUTES,
        INTENT_COLLEGE_OVERVIEW,
        INTENT_COURSE_MENU,
        INTENT_DEPARTMENT_COMPARISON,
        INTENT_DOCUMENTS,
        INTENT_HOD_TRUSTEES_PROFILE,
        INTENT_PLACEMENTS,
        INTENT_PRINCIPAL_PROFILE,
        INTENT_TRUSTEES_PROFILE,
        INTENT_VICE_PRINCIPAL_PROFILE,
    }
)

# Department-scoped card intents. Without a validated department these must clarify,
# never silently degrade and never pick a first department.
DEPARTMENT_CARD_INTENTS: frozenset[str] = frozenset(
    {
        INTENT_DEPARTMENT_FEES,
        INTENT_DEPARTMENT_OVERVIEW,
        INTENT_HOD_PROFILE,
    }
)


@dataclass(frozen=True)
class ResponseDecision:
    mode: ResponseMode
    topic: str | None = None
    items: tuple[tuple[str, str], ...] = ()  # (entity, topic) — never unitIds
    entities: tuple[str, ...] = ()
    scope: str = "single"
    confidence: float = 0.0
    clarification_target: str | None = None
    clarification_reason: str | None = None
    domain_relevance: DomainRelevance = DomainRelevance.UNKNOWN
    evidence: str = "none"
    diagnostics: dict[str, Any] = field(default_factory=dict)

    @property
    def is_card(self) -> bool:
        return self.mode is ResponseMode.CARD


# --- Deterministic evidence -------------------------------------------------------

# Institutional vocabulary. Presence means the utterance is about this college, so it
# deserves a real answer even when it is three words long.
_INSTITUTION_LEXICON: tuple[str, ...] = (
    "college", "campus", "institute", "institution", "university", "svit", "sai vidya",
    "teacher", "teachers", "faculty", "professor", "professors", "lecturer", "lecturers",
    "staff", "teaching", "hod", "principal", "dean", "trustee", "trustees",
    "student", "students", "class", "classes", "classroom", "classrooms",
    "lab", "labs", "laboratory", "laboratories", "library", "hostel", "canteen",
    "cafeteria", "mess", "food", "sports", "gym", "auditorium", "wifi", "internet",
    "infrastructure", "facility", "facilities", "amenities", "transport", "bus",
    "admission", "admissions", "apply", "application", "eligibility", "cutoff",
    "seat", "seats", "quota", "scholarship", "scholarships", "fee", "fees", "tuition",
    "placement", "placements", "package", "salary", "recruiter", "recruiters",
    "internship", "internships", "company", "companies",
    "course", "courses", "branch", "branches", "department", "departments",
    "syllabus", "curriculum", "semester", "exam", "exams", "result", "results",
    "degree", "engineering", "mba", "btech", "b tech", "vtu", "accreditation",
    "naac", "nba", "aicte", "ranking", "rankings", "achievement", "achievements",
    "research", "project", "projects", "workshop", "workshops", "event", "events",
    "culture", "campus life", "student life", "environment", "atmosphere",
    "hackathon", "hackathons", "club", "clubs", "fest", "fests",
    "experienced", "supportive", "makerspace", "studies", "study", "academic",
    "practical", "intern", "industry", "opportunity", "opportunities", "vibe",
)

# College-wide placement/achievement talk is ANSWER, not "which department?".
_COLLEGE_WIDE_ANSWER_TOPICS = frozenset(
    {TOPIC_PLACEMENTS, TOPIC_ACHIEVEMENTS, TOPIC_FACULTY, TOPIC_CONTACT}
)
_COLLEGE_WIDE_CARD_INTENTS = frozenset({INTENT_PLACEMENTS, INTENT_COLLEGE_OVERVIEW})

# Off-domain topics CLARA must refuse rather than guess at.
_OFF_DOMAIN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bcapital\s+of\b", re.I),
    re.compile(r"\b(weather|temperature|forecast)\b", re.I),
    re.compile(r"\b(joke|jokes|song|sing|poem|story)\b", re.I),
    re.compile(r"\b(cricket|football|movie|movies|film|actor|actress)\b", re.I),
    re.compile(r"\b(stock|bitcoin|crypto|share\s+price)\b", re.I),
    re.compile(r"\b(who\s+is\s+the\s+)?(president|prime\s+minister)\s+of\b", re.I),
    re.compile(r"\b(recipe|cook|restaurant)\b", re.I),
    re.compile(r"\bwrite\s+(me\s+)?(a|an)\s+(code|program|essay|poem)\b", re.I),
)

_UNSAFE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(fuck|shit|bitch|bastard|asshole)\b", re.I),
    re.compile(r"\b(kill|suicide|bomb|weapon|drugs)\b", re.I),
)

# Comparison against institutions that are not SVIT.
_EXTERNAL_COMPARISON_CUES: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(compare|comparison|versus|vs\.?|better\s+than)\b", re.I),
)
_EXTERNAL_INSTITUTION_CUES: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(another|other|different)\s+(college|university|institute|institution)\b", re.I),
    re.compile(r"\b(harvard|mit|stanford|oxford|cambridge|iit|nit|bms|rvce|pes|christ|manipal)\b", re.I),
    re.compile(r"\bwith\s+(any\s+)?other\s+(college|university)\b", re.I),
)

# Qualitative questions ask for an explanation, not a directory/list card.  These
# are concept cues shared across languages (not complete-sentence rules).
_QUALITATIVE_CUES: tuple[str, ...] = (
    "how", "good", "supportive", "quality", "environment", "scene",
    "hegide", "hegiddare", "chennag", "ಹೇಗ", "ಚೆನ್ನ",
    "kaisa", "kaise", "kaisi", "theek", "padhate", "कैस", "ठीक", "पढ़ा",
    "eppadi", "nalla", "எப்படி", "நல்ல",
    "ela", "bagunda", "bagunnara", "ఎలా", "బాగు",
    "engane", "nallatha", "nallathano", "എങ്ങനെ", "നല്ല",
)

_EXPLICIT_CARD_ACTION_CUES: tuple[str, ...] = (
    "show", "display", "details", "information", "profile", "list", "tell me about",
    "torisi", "heli", "ತೋರ", "ಹೇಳ", "ಬಗ್ಗೆ",
    "dikha", "batao", "bataiye", "jankari", "vivaran", "दिख", "बता", "जानकारी", "विवरण",
    "kattu", "soll", "காட்டு", "சொல்ல", "பற்றி",
    "chup", "chepp", "చూప", "చెప్ప", "గురించి",
    "kani", "parayu", "കാണ", "പറയ", "കുറിച്ച്",
    "दाखव", "सांगा", "माहिती",
)


def _hay(text: str) -> str:
    return casefold_keep_scripts(text or "")


def detect_domain_relevance(text: str) -> DomainRelevance:
    """Institution / off-domain / unknown, from vocabulary alone."""
    raw = text or ""
    for pattern in _UNSAFE_PATTERNS:
        if pattern.search(raw):
            return DomainRelevance.OFF_DOMAIN
    for pattern in _OFF_DOMAIN_PATTERNS:
        if pattern.search(raw):
            return DomainRelevance.OFF_DOMAIN

    hay = _hay(raw)
    if not hay:
        return DomainRelevance.UNKNOWN
    for term in _INSTITUTION_LEXICON:
        if cue_in_hay(hay, term):
            return DomainRelevance.INSTITUTION
    for cue in institution_cues():
        if cue_in_hay(hay, cue):
            return DomainRelevance.INSTITUTION
    # Unknown is not off-domain. Native-script questions without a cue stay unknown
    # so the LLM proposal can still mark institution; they are never auto-FALLBACK.
    return DomainRelevance.UNKNOWN


def is_external_comparison(text: str) -> bool:
    """True for 'compare us with <not SVIT>' — a product-policy FALLBACK."""
    raw = text or ""
    if not any(p.search(raw) for p in _EXTERNAL_COMPARISON_CUES):
        return False
    return any(p.search(raw) for p in _EXTERNAL_INSTITUTION_CUES)


def has_card_topic_cue(text: str) -> bool:
    """A department-scoped topic word (hod / fees / placements / achievements / overview)."""
    return bool(detect_topic_spans(text or ""))


def _has_any_concept_cue(text: str, cues: tuple[str, ...]) -> bool:
    hay = _hay(text)
    return any(cue_in_hay(hay, cue) for cue in cues)


def _has_atomic_card_topic(
    semantic_request: SemanticRequest | None,
    proposal: SemanticProposal | None,
) -> bool:
    from backend.services.conversation.semantic_proposal import ATOMIC_CARD_TOPICS

    items: tuple[tuple[str, str], ...] = ()
    if semantic_request is not None:
        items = semantic_request.unit_items
    if proposal is not None and proposal.items:
        items = items + proposal.items
    return any(topic in ATOMIC_CARD_TOPICS for _, topic in items)


def _proposal_diag(
    validated_proposal: SemanticProposal | None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if extra:
        out.update(extra)
    if validated_proposal is not None:
        out["proposal_status"] = "accepted"
        out["proposal_mode_hint"] = validated_proposal.mode_hint.value
        out["proposal_domain"] = validated_proposal.domain.value
        if validated_proposal.answer_topic:
            out["answer_topic"] = validated_proposal.answer_topic
    return out


def resolve_response_decision(
    *,
    text: str,
    semantic_request: SemanticRequest | None,
    ci_intent: str | None,
    has_department_entity: bool,
    faq_matched: bool = False,
    local_intent: dict[str, Any] | None = None,
    validated_proposal: SemanticProposal | None = None,
    proposal_diagnostics: dict[str, Any] | None = None,
) -> ResponseDecision:
    """
    Decide the response mode for one turn.

    Order of evidence is deliberate: explicit UI actions, then deterministic content
    resolution, then supported non-unit card surfaces, then domain relevance.
    A validated LLM proposal may fill the institution-without-card gap. It cannot
    override UI, off-domain, or external-comparison policy, and it cannot force
    FALLBACK merely because a request is not a card.
    """
    from backend.services.conversation.semantic_proposal import SemanticProposal as _Proposal

    raw = text or ""
    relevance = detect_domain_relevance(raw)
    proposal = validated_proposal
    base_diag = dict(proposal_diagnostics or {})
    if proposal is not None and not isinstance(proposal, _Proposal):
        proposal = None
        base_diag["proposal_status"] = "rejected"
        base_diag["proposal_reject_reason"] = "invalid_type"

    def _done(
        decision: ResponseDecision,
        **more: Any,
    ) -> ResponseDecision:
        diag = _proposal_diag(proposal, {**base_diag, **more})
        if not diag:
            return decision
        merged = dict(decision.diagnostics)
        merged.update(diag)
        return replace(decision, diagnostics=merged)

    # 1. Explicit UI action. The user physically chose a card.
    if local_intent and isinstance(local_intent, dict) and local_intent:
        return _done(
            ResponseDecision(
                mode=ResponseMode.CARD,
                domain_relevance=DomainRelevance.INSTITUTION,
                confidence=0.99,
                evidence="local_intent",
            )
        )

    # 2. Unsafe / off-domain wins over everything typed. Never card, never answer.
    if relevance is DomainRelevance.OFF_DOMAIN:
        return _done(
            ResponseDecision(
                mode=ResponseMode.FALLBACK,
                domain_relevance=relevance,
                confidence=0.95,
                evidence="off_domain_lexicon",
            )
        )

    # 3. Product policy: comparison against a non-SVIT institution is out of scope.
    if is_external_comparison(raw):
        return _done(
            ResponseDecision(
                mode=ResponseMode.FALLBACK,
                domain_relevance=DomainRelevance.OFF_DOMAIN,
                confidence=0.9,
                evidence="external_college_comparison",
            )
        )

    # LLM FALLBACK is ignored here: only steps 2–3 may emit FALLBACK.
    atomic = _has_atomic_card_topic(semantic_request, proposal)
    institution_proposal = (
        proposal is not None and proposal.domain is DomainRelevance.INSTITUTION
    )
    independently_selectable_items = bool(
        semantic_request is not None
        and any(
            is_campus_entity(entity) or is_global_entity(entity)
            for entity, _ in semantic_request.unit_items
        )
    )
    request_topics = (
        {topic for _, topic in semantic_request.unit_items}
        if semantic_request is not None
        else set()
    )
    qualitative_request = _has_any_concept_cue(raw, _QUALITATIVE_CUES)
    explicit_card_action = _has_any_concept_cue(raw, _EXPLICIT_CARD_ACTION_CUES)

    # A named faculty entity plus an evaluative modifier asks about teaching
    # quality. A bare/qualitative college-wide placement question likewise asks
    # for an answer; explicit show/details actions still open canonical cards.
    if semantic_request is not None and (
        (request_topics == {TOPIC_FACULTY} and qualitative_request)
        or (
            semantic_request.unit_items == (("college", TOPIC_PLACEMENTS),)
            and not explicit_card_action
        )
    ):
        return _done(
            ResponseDecision(
                mode=ResponseMode.ANSWER,
                domain_relevance=DomainRelevance.INSTITUTION,
                confidence=0.82,
                evidence="qualitative_institution_question",
            )
        )
    fee_requires_department = (
        semantic_request is None
        and not has_department_entity
        and TOPIC_FEES in detect_atomic_topics(raw)
        and not has_explicit_admissions_cue(raw)
    )
    hod_requires_department = (
        semantic_request is None
        and not has_department_entity
        and TOPIC_HOD in detect_atomic_topics(raw)
    )

    # 3b. Evaluative institutional question: entity mention is not automatically CARD.
    # Documents / admissions / course-menu / bus keep their card owners.
    if (
        institution_proposal
        and proposal is not None
        and proposal.mode_hint is ResponseMode.ANSWER
        and not atomic
        and not fee_requires_department
        and not hod_requires_department
        and not independently_selectable_items
        and (ci_intent or "") not in NON_UNIT_CARD_INTENTS
    ):
        return _done(
            ResponseDecision(
                mode=ResponseMode.ANSWER,
                domain_relevance=DomainRelevance.INSTITUTION,
                confidence=0.8,
                evidence="validated_proposal_answer",
            )
        )

    # 3c. LLM CARD with validated pairs, when parse did not already bind a request.
    if (
        proposal is not None
        and proposal.mode_hint is ResponseMode.CARD
        and proposal.items
        and semantic_request is None
        and not fee_requires_department
        and not hod_requires_department
    ):
        return _done(
            ResponseDecision(
                mode=ResponseMode.CARD,
                topic=proposal.items[0][1],
                items=proposal.items,
                entities=tuple(dict.fromkeys(e for e, _ in proposal.items)),
                scope=proposal.scope,
                confidence=0.9,
                domain_relevance=DomainRelevance.INSTITUTION,
                evidence="validated_proposal_card",
            )
        )

    # 3d. Naming a department inside a faculty/campus question is not an overview card.
    # "Datascience teachers hegiddare?" must ANSWER. "Tell me about Data Science" stays CARD.
    # Hostel / canteen / event units are independently selectable cards.
    if (
        semantic_request is not None
        and not independently_selectable_items
        and not _has_atomic_card_topic(semantic_request, None)
        and semantic_request.requested_scope != "full_department"
        and relevance is DomainRelevance.INSTITUTION
        and not is_full_department_scope(raw)
        and not (proposal is not None and proposal.mode_hint is ResponseMode.CARD)
    ):
        return _done(
            ResponseDecision(
                mode=ResponseMode.ANSWER,
                domain_relevance=DomainRelevance.INSTITUTION,
                confidence=0.78,
                evidence="entity_mention_in_answer",
            )
        )

    # 4. A resolved semantic request is the strongest card evidence there is.
    if semantic_request is not None:
        items = semantic_request.unit_items
        return _done(
            ResponseDecision(
                mode=ResponseMode.CARD,
                topic=semantic_request.topic,
                items=items,
                entities=semantic_request.entities,
                scope=semantic_request.requested_scope,
                confidence=0.95 if semantic_request.confidence == "HIGH" else 0.85,
                domain_relevance=DomainRelevance.INSTITUTION,
                evidence="semantic_request",
                diagnostics={"mixed": semantic_request.is_mixed_composition},
            )
        )

    # 5. FAQ is a curated institutional answer.
    if faq_matched:
        return _done(
            ResponseDecision(
                mode=ResponseMode.ANSWER,
                domain_relevance=DomainRelevance.INSTITUTION,
                confidence=0.92,
                evidence="faq",
            )
        )

    # Executive profiles (principal / vice-principal / trustees) are resolved here so the
    # frontend never has to infer them from user text.
    intent = maybe_override_intent_with_executive_profile((ci_intent or "").strip(), raw)

    # 6. Department-scoped card intent that never resolved an entity: ask, don't guess.
    if hod_requires_department:
        return _done(
            ResponseDecision(
                mode=ResponseMode.CLARIFY,
                clarification_target="department",
                clarification_reason="missing_department",
                domain_relevance=DomainRelevance.INSTITUTION,
                confidence=0.9,
                evidence="hod_topic_without_department",
                diagnostics={"fallbackReason": "MISSING_DEPARTMENT"},
            )
        )

    if intent in DEPARTMENT_CARD_INTENTS and not has_department_entity:
        return _done(
            ResponseDecision(
                mode=ResponseMode.CLARIFY,
                clarification_target="department",
                clarification_reason="missing_department",
                domain_relevance=DomainRelevance.INSTITUTION,
                confidence=0.8,
                evidence="department_card_without_entity",
            )
        )

    # 6b. Fee-only requests without a validated department are not general
    # admissions requests. Reuse the existing department clarification instead of
    # allowing either the legacy ADMISSIONS demotion or an earlier LLM proposal to
    # manufacture a card. Genuine admissions language keeps the admissions owner.
    if fee_requires_department:
        return _done(
            ResponseDecision(
                mode=ResponseMode.CLARIFY,
                clarification_target="department",
                clarification_reason="topic_without_department",
                domain_relevance=DomainRelevance.INSTITUTION,
                confidence=0.75,
                evidence="topic_cue_without_entity",
            )
        )

    # Preserve the narrow case where both explicit admissions language and the
    # existing legacy Admissions owner agree. Do not promote NORMAL_QUERY text.
    if has_explicit_admissions_cue(raw) and intent == INTENT_ADMISSIONS:
        return _done(
            ResponseDecision(
                mode=ResponseMode.CARD,
                domain_relevance=DomainRelevance.INSTITUTION,
                confidence=0.88,
                evidence="explicit_admissions_cue",
            )
        )

    # 7. Supported non-unit card surfaces keep their existing owners.
    # College-wide placements / college overview without a department are spoken
    # ANSWER turns, not a card. A UI click still CARD'd at step 1.
    if intent in NON_UNIT_CARD_INTENTS:
        if intent in _COLLEGE_WIDE_CARD_INTENTS and not has_department_entity:
            return _done(
                ResponseDecision(
                    mode=ResponseMode.ANSWER,
                    domain_relevance=DomainRelevance.INSTITUTION,
                    confidence=0.82,
                    evidence="college_wide_non_card",
                )
            )
        return _done(
            ResponseDecision(
                mode=ResponseMode.CARD,
                domain_relevance=DomainRelevance.INSTITUTION,
                confidence=0.88,
                evidence="non_unit_card_intent",
            )
        )

    # 8. A department card intent with an entity that the unit parser could not use
    #    (unlisted department, unsupported topic pairing) must clarify.
    if intent in DEPARTMENT_CARD_INTENTS:
        return _done(
            ResponseDecision(
                mode=ResponseMode.CLARIFY,
                clarification_target="department",
                clarification_reason="unresolved_department_request",
                domain_relevance=DomainRelevance.INSTITUTION,
                confidence=0.7,
                evidence="department_card_unresolved",
            )
        )

    # 9. A card topic word with no department at all (e.g. bare "Who is the HOD?").
    # College-wide placements/achievements are ANSWER, not "which department?".
    if has_card_topic_cue(raw) and not has_department_entity:
        topics = detect_atomic_topics(raw)
        if (
            relevance is DomainRelevance.INSTITUTION
            and topics
            and topics <= _COLLEGE_WIDE_ANSWER_TOPICS
        ):
            return _done(
                ResponseDecision(
                    mode=ResponseMode.ANSWER,
                    domain_relevance=DomainRelevance.INSTITUTION,
                    confidence=0.72,
                    evidence="college_wide_topic_answer",
                )
            )
        return _done(
            ResponseDecision(
                mode=ResponseMode.CLARIFY,
                clarification_target="department",
                clarification_reason="topic_without_department",
                domain_relevance=DomainRelevance.INSTITUTION,
                confidence=0.75,
                evidence="topic_cue_without_entity",
            )
        )

    # 9b. Bare "hostel" without girls/boys must clarify, not guess or dump RAG.
    if is_bare_hostel_request(raw):
        return _done(
            ResponseDecision(
                mode=ResponseMode.CLARIFY,
                clarification_target="hostel",
                clarification_reason="unrecognised_request",
                domain_relevance=DomainRelevance.INSTITUTION,
                confidence=0.8,
                evidence="bare_hostel_without_gender",
            )
        )

    # 10. Institutional question with no card family: answer it. Length is irrelevant.
    if relevance is DomainRelevance.INSTITUTION:
        return _done(
            ResponseDecision(
                mode=ResponseMode.ANSWER,
                domain_relevance=relevance,
                confidence=0.7,
                evidence="institution_lexicon",
            )
        )

    # 10b. Lexicon miss, but a validated proposal says this is still about the college.
    if institution_proposal:
        if proposal is not None and proposal.mode_hint is ResponseMode.CLARIFY:
            return _done(
                ResponseDecision(
                    mode=ResponseMode.CLARIFY,
                    clarification_target=proposal.clarification_target,
                    clarification_reason=proposal.clarification_reason or "unrecognised_request",
                    domain_relevance=DomainRelevance.INSTITUTION,
                    confidence=0.65,
                    evidence="validated_proposal_clarify",
                )
            )
        return _done(
            ResponseDecision(
                mode=ResponseMode.ANSWER,
                domain_relevance=DomainRelevance.INSTITUTION,
                confidence=0.7,
                evidence="validated_proposal_institution",
            )
        )

    # 11. Nothing recognised. Ask rather than invent or refuse.
    return _done(
        ResponseDecision(
            mode=ResponseMode.CLARIFY,
            clarification_reason="unrecognised_request",
            domain_relevance=relevance,
            confidence=0.4,
            evidence="no_evidence",
        )
    )
