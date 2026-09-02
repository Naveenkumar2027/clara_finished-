"""SemanticRequest parser — deterministic, multilingual, language-independent (M5.3 Option B)."""

from __future__ import annotations

from typing import Any

from backend.services.answer_generation import normalize_user_input
from backend.services.content.department_identity import (
    DepartmentSpan,
    match_department_spans_exclusive,
)
from backend.services.content.department_resolver import known_department_keys, resolve_department_key
from backend.services.content.multilingual_terms import (
    TOPIC_OVERVIEW,
)
from backend.services.content.semantic_anaphora import has_anaphora, has_person_anaphora
from backend.services.content.person_context import semantic_item_for_person_unit
from backend.services.content.campus_units import (
    campus_items_from_text,
    detect_campus_entity_spans,
)
from backend.services.content.leadership_units import (
    LEADERSHIP_ENTITY,
    detect_leadership_spans,
    is_show_multi_overview_request,
    leadership_items_from_text,
)
from backend.services.content.global_units import (
    GLOBAL_ENTITY,
    detect_global_spans,
    global_items_from_text,
)
from backend.services.content.semantic_composition import (
    SemanticItem,
    detect_topic_spans,
    pair_entities_and_topics,
)
from backend.services.content.semantic_request import SemanticRequest
from backend.services.content.semantic_topics import (
    detect_atomic_topics,
    detect_unsupported,
    is_full_department_scope,
)
from backend.services.content.unicode_text import casefold_keep_scripts
from backend.services.content.semantic_vocab.catalog import (
    UNSUPPORTED_BUS,
    UNSUPPORTED_DOCUMENTS,
)


def _dedupe_keep_order(xs: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for x in xs:
        if not x:
            continue
        nx = str(x).strip().lower()
        if not nx or nx in seen:
            continue
        seen.add(nx)
        out.append(nx)
    return tuple(out)


_FOLLOWUP_JOINERS = frozenset(
    {
        "also", "too", "and", "ಮತ್ತು", "ಕೂಡ", "भी", "और",
        "కూడా", "மற்றும்", "கூட", "കൂടി", "आणि", "सुद्धा",
    }
)


def _is_concise_topic_followup(raw_text: str, topics: frozenset[str]) -> bool:
    """Admit active context only for a short, unambiguous topic request."""
    if len(topics) != 1:
        return False
    tokens = casefold_keep_scripts(raw_text).split()
    if not tokens or len(tokens) > 4:
        return False
    return len(tokens) <= 2 or any(token in _FOLLOWUP_JOINERS for token in tokens)


def parse_semantic_request(
    *,
    raw_text: str,
    language_code_key: str,
    ci_entities: dict[str, Any] | None = None,
) -> SemanticRequest | None:
    """
    Parse a user request into a language-independent semantic request.

    Deterministic: no LLM, no RAG, no CI intent mutation.
    Fail-closed: multiple atomic topics or unresolved identity → None (no unitId).
    """
    if not raw_text or not isinstance(raw_text, str):
        return None

    normalized = normalize_user_input(raw_text)
    unsupported = detect_unsupported(raw_text, normalized)
    if UNSUPPORTED_BUS in unsupported or UNSUPPORTED_DOCUMENTS in unsupported:
        return None

    # Topic extraction is independent from entity extraction. Besides enabling
    # code-switching, doing this before context lookup lets concise follow-ups such
    # as "HOD also", "fees?", or "faculty ಕೂಡ" reuse an active department.
    atomic = detect_atomic_topics(raw_text, normalized)
    entity_spans = match_department_spans_exclusive(raw_text)
    if not entity_spans and isinstance(ci_entities, dict):
        # A department from an earlier turn is identity for this turn only when the
        # user actually pointed back at it ("its HOD"). Otherwise the request has no
        # entity and must clarify.
        entity_spans = _entity_spans_from_hint(
            ci_entities=ci_entities,
            language_code_key=language_code_key,
            allow_carry_over=has_anaphora(raw_text) or _is_concise_topic_followup(raw_text, atomic),
        )
    if entity_spans:
        entity_spans = _validate_entity_spans(
            entity_spans=entity_spans,
            language_code_key=language_code_key,
        )

    leadership_spans = detect_leadership_spans(raw_text)
    leadership_items = tuple(
        SemanticItem(entity=LEADERSHIP_ENTITY, topic=span.topic) for span in leadership_spans
    )
    if not leadership_items:
        leadership_items = leadership_items_from_text(raw_text)

    campus_spans = detect_campus_entity_spans(raw_text)
    campus_items = campus_items_from_text(raw_text) if campus_spans else ()
    global_spans = detect_global_spans(raw_text)
    if entity_spans:
        global_spans = tuple(span for span in global_spans if span.topic == "location")
    global_items = global_items_from_text(raw_text) if global_spans else ()
    if global_spans:
        allowed_global_topics = {span.topic for span in global_spans}
        global_items = tuple(item for item in global_items if item.topic in allowed_global_topics)

    if not entity_spans and not leadership_items and not campus_items and not global_items:
        person_item = _person_followup_item(
            raw_text=raw_text,
            normalized=normalized,
            ci_entities=ci_entities if isinstance(ci_entities, dict) else None,
        )
        if person_item is None:
            return None
        items = (person_item,)
        return SemanticRequest(
            language_code=language_code_key,
            topic=person_item.topic,
            entities=() if person_item.entity == LEADERSHIP_ENTITY else (person_item.entity,),
            context="leadership" if person_item.entity == LEADERSHIP_ENTITY else "department",
            confidence="HIGH",
            requested_scope="single",
            source="m5.4_semantic_request_parser",
            raw_text=raw_text,
            items=((person_item.entity, person_item.topic),),
            diagnostics={
                "normalized": normalized,
                "person_followup": True,
                "last_person_unit_id": str((ci_entities or {}).get("last_person_unit_id") or ""),
            },
        )

    topic_spans = detect_topic_spans(raw_text) if entity_spans else ()

    # The span detector runs on raw text only. `detect_atomic_topics` additionally sees
    # the normalized text, so a topic can be known without having a bindable position.
    # In that case the request is not composable and must clarify rather than guess.
    atomic = atomic if entity_spans else frozenset()
    span_topics = {s.topic for s in topic_spans}
    unpositioned = atomic - span_topics
    single_unpositioned_item: SemanticItem | None = None
    if unpositioned:
        if len(atomic | span_topics) > 1 or len(entity_spans) > 1:
            return None
        # One entity and one canonical topic is a complete, unambiguous request
        # even when raw-text span extraction could not position the normalized
        # topic cue. Preserve that topic directly; never route it through the
        # no-topic overview fallback.
        single_unpositioned_item = SemanticItem(
            entity=entity_spans[0].json_key,
            topic=next(iter(unpositioned)),
        )

    has_explicit_topic = bool(span_topics or atomic)
    is_full_scope = (
        bool(entity_spans)
        and not has_explicit_topic
        and not leadership_items
        and is_full_department_scope(raw_text, normalized)
    )

    dept_items: tuple[SemanticItem, ...] | None = None
    if entity_spans:
        if single_unpositioned_item is not None:
            dept_items = (single_unpositioned_item,)
        else:
            dept_items = pair_entities_and_topics(
                entity_spans=entity_spans,
                topic_spans=topic_spans,
                fallback_topic=TOPIC_OVERVIEW,
            )
        if (
            dept_items is None
            and not has_explicit_topic
            and not is_full_scope
            and len(entity_spans) > 1
            and is_show_multi_overview_request(raw_text, normalized)
        ):
            # "Show me CSE Data Science and CSE AIML." — N overview units, not a guess
            # at comparison vs two full decks ("tell me about CSE and AIML" stays closed).
            dept_items = tuple(
                SemanticItem(entity=span.json_key, topic=TOPIC_OVERVIEW) for span in entity_spans
            )
    items = _merge_department_leadership_and_campus_items(
        dept_items=dept_items or (),
        leadership_spans=leadership_spans,
        entity_spans=entity_spans,
        campus_items=campus_items,
        campus_spans=campus_spans,
        global_items=global_items,
        global_spans=global_spans,
    )
    if not items:
        return None

    requested_scope = (
        "full_department"
        if is_full_scope and len(items) == 1 and items[0].entity != LEADERSHIP_ENTITY
        else "single"
    )

    entities = _dedupe_keep_order(
        [item.entity for item in items if item.entity not in {LEADERSHIP_ENTITY, GLOBAL_ENTITY}]
    )
    topics = [item.topic for item in items]
    primary_topic = topics[0]
    mixed = len(set(topics)) > 1
    has_leadership = any(item.entity == LEADERSHIP_ENTITY for item in items)
    has_campus = any(
        item.entity == "canteen"
        or item.entity.startswith("hostel.")
        or item.entity.startswith("events.")
        for item in items
    )
    has_global = any(item.entity == GLOBAL_ENTITY for item in items)
    context = "global" if has_global and not entities and not has_leadership and not has_campus else (
        "leadership" if has_leadership and not entities and not has_campus and not has_global else (
        "campus" if has_campus and not entities and not has_leadership else (
            "mixed" if has_leadership or has_campus or has_global else "department"
        )
    ))

    confidence: str
    if requested_scope == "full_department":
        confidence = "HIGH"
    elif len(items) == 1:
        confidence = "HIGH"
    else:
        confidence = "MEDIUM"

    return SemanticRequest(
        language_code=language_code_key,
        topic=str(primary_topic),
        entities=entities,
        context=context,
        confidence=confidence,  # type: ignore[arg-type]
        requested_scope=requested_scope,
        source="m5.4_semantic_request_parser",
        raw_text=raw_text,
        items=tuple((item.entity, item.topic) for item in items),
        diagnostics={
            "normalized": normalized,
            "atomic_topics": sorted(atomic),
            "span_topics": sorted(span_topics),
            "mixed_composition": mixed,
            "confidence": confidence,
            "leadership_topics": [s.topic for s in leadership_spans],
        },
    )


def _merge_department_leadership_and_campus_items(
    *,
    dept_items: tuple[SemanticItem, ...],
    leadership_spans: tuple,
    entity_spans,
    campus_items: tuple[SemanticItem, ...],
    campus_spans: tuple,
    global_items: tuple[SemanticItem, ...] = (),
    global_spans: tuple = (),
) -> tuple[SemanticItem, ...]:
    """Preserve user order across department, leadership, and campus items."""
    tagged: list[tuple[int, int, SemanticItem]] = []
    entity_start = {span.json_key: span.start for span in entity_spans or ()}
    campus_start = {span.entity: span.start for span in campus_spans or ()}
    global_start = {span.topic: span.start for span in global_spans or ()}
    for i, item in enumerate(dept_items):
        tagged.append((entity_start.get(item.entity, 0), i, item))
    for i, span in enumerate(leadership_spans or ()):
        tagged.append((span.start, 1000 + i, SemanticItem(entity=LEADERSHIP_ENTITY, topic=span.topic)))
    for i, item in enumerate(campus_items or ()):
        tagged.append((campus_start.get(item.entity, 0), 2000 + i, item))
    for i, item in enumerate(global_items or ()):
        tagged.append((global_start.get(item.topic, 0), 3000 + i, item))
    if not tagged:
        return ()
    tagged.sort(key=lambda row: (row[0], row[1]))
    out: list[SemanticItem] = []
    seen: set[tuple[str, str]] = set()
    for _, _, item in tagged:
        key = (item.entity, item.topic)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return tuple(out)


def _person_followup_item(
    *,
    raw_text: str,
    normalized: str,
    ci_entities: dict[str, Any] | None,
) -> SemanticItem | None:
    """Repeat the last person unit. Never invent a biography or switch to overview."""
    if not ci_entities:
        return None
    if not has_person_anaphora(raw_text):
        return None
    if detect_atomic_topics(raw_text, normalized):
        return None
    uid = str(ci_entities.get("last_person_unit_id") or "").strip()
    return semantic_item_for_person_unit(uid)


def _merge_department_and_leadership_items(
    *,
    dept_items: tuple[SemanticItem, ...],
    leadership_spans: tuple,
    entity_spans,
) -> tuple[SemanticItem, ...]:
    return _merge_department_leadership_and_campus_items(
        dept_items=dept_items,
        leadership_spans=leadership_spans,
        entity_spans=entity_spans,
        campus_items=(),
        campus_spans=(),
        global_items=(),
        global_spans=(),
    )


def _entity_spans_from_hint(
    *,
    ci_entities: dict[str, Any],
    language_code_key: str,
    allow_carry_over: bool,
) -> tuple[DepartmentSpan, ...]:
    """Resolve a department carried by conversation entities, never a user-text blob."""
    if not allow_carry_over:
        return ()
    keys_raw = ci_entities.get("department_keys")
    if isinstance(keys_raw, (list, tuple)):
        spans: list[DepartmentSpan] = []
        seen: set[str] = set()
        known_keys = known_department_keys(language_code_key)
        for key in keys_raw:
            canonical = str(key).strip().lower()
            if canonical in known_keys and canonical not in seen:
                seen.add(canonical)
                spans.append(DepartmentSpan(json_key=canonical, start=0, end=0))
        if spans:
            return tuple(spans)
    hint = ci_entities.get("department") or ci_entities.get("departmentLabel")
    if not hint or ci_entities.get("from_menu"):
        return ()
    hint_spans = match_department_spans_exclusive(str(hint))
    if len(hint_spans) == 1:
        return (DepartmentSpan(json_key=hint_spans[0].json_key, start=0, end=0),)
    resolved = resolve_department_key(
        department=str(hint),
        language=language_code_key,
        user_text="",
    )
    if resolved.json_key:
        return (DepartmentSpan(json_key=resolved.json_key, start=0, end=0),)
    return ()


def _validate_entity_spans(
    *,
    entity_spans: tuple[DepartmentSpan, ...],
    language_code_key: str,
) -> tuple[DepartmentSpan, ...]:
    """Keep only spans whose key survives canonical department validation."""
    out: list[DepartmentSpan] = []
    seen: set[str] = set()
    for span in entity_spans:
        dep_res = resolve_department_key(
            department=str(span.json_key),
            language=language_code_key,
            user_text="",
        )
        key = dep_res.json_key
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(DepartmentSpan(json_key=key, start=span.start, end=span.end))
    return tuple(out)
