"""
Span-based topic detection and entity/topic pairing (M5.4 composition contract).

One authority for binding *which topic belongs to which department* inside a single
utterance. Positions come from the same haystack used by department identity matching,
so pairing is positional, never first-match-wins.

This module never produces unitIds. It only produces ordered (entity, topic) items,
which `unit_selector` turns into unitIds.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from backend.services.content.department_identity import (
    DepartmentSpan,
    normalize_for_department_match,
)
from backend.services.content.semantic_topics import ATOMIC_TOPICS
from backend.services.content.semantic_vocab.catalog import TOPIC_OVERVIEW, all_entries
from backend.services.content.unicode_text import casefold_keep_scripts

# Topics that can be positionally bound to a department inside one utterance.
PAIRABLE_TOPICS = frozenset(ATOMIC_TOPICS | {TOPIC_OVERVIEW})

_LISTED_DEPARTMENT_OVERVIEW_RE = re.compile(
    r"(?:\bdepartment|ವಿಭಾಗ|विभाग|విభాగం|துறை|വകുപ്പ്)\s*"
    r"(?:[,;]|\band\b|ಮತ್ತು|और|आणि|మరియు|மற்றும்|കൂടാതെ)",
    re.IGNORECASE,
)

_TOPIC_CATEGORIES = frozenset({"TOPIC", "QUESTION", "ROMANIZED", "CODE-SWITCH"})


@dataclass(frozen=True)
class TopicSpan:
    topic: str
    start: int
    end: int


@dataclass(frozen=True)
class SemanticItem:
    """One addressable (department, topic) pair in user order."""

    entity: str
    topic: str


def composition_haystack(text: str) -> str:
    """Shared haystack for entity and topic spans."""
    return normalize_for_department_match(text or "")


def detect_topic_spans(text: str) -> tuple[TopicSpan, ...]:
    """
    Ordered topic spans over the shared haystack.

    Longer cues are consumed first so `head of department` does not also register
    `head of`, and `fees` does not also register `fee`.
    """
    hay = composition_haystack(text)
    if not hay:
        return ()

    variants: list[tuple[str, str]] = []
    for entry in all_entries():
        if entry.canonical not in PAIRABLE_TOPICS:
            continue
        if entry.category not in _TOPIC_CATEGORIES:
            continue
        variant = casefold_keep_scripts(entry.variant)
        if variant:
            variants.append((variant, entry.canonical))
    variants.sort(key=lambda v: len(v[0]), reverse=True)

    occupied = [False] * len(hay)
    spans: list[TopicSpan] = []
    for variant, canonical in variants:
        for start, end in _find_all_free(hay, variant, occupied):
            for i in range(start, end):
                occupied[i] = True
            spans.append(TopicSpan(topic=canonical, start=start, end=end))

    # In a list, "CSE department, HOD and fees" explicitly requests the
    # overview as its first item. Delimiter/conjunction gating avoids treating
    # ordinary grammar such as "HOD of the department" as another card.
    listed_overview = _LISTED_DEPARTMENT_OVERVIEW_RE.search(text or "")
    if listed_overview and not any(span.topic == TOPIC_OVERVIEW for span in spans):
        prefix = casefold_keep_scripts((text or "")[: listed_overview.start()])
        start = len(prefix) + (1 if prefix else 0)
        spans.append(TopicSpan(topic=TOPIC_OVERVIEW, start=start, end=start + 1))
    spans.sort(key=lambda s: s.start)
    return tuple(spans)


def _find_all_free(hay: str, variant: str, occupied: list[bool]) -> list[tuple[int, int]]:
    """All unoccupied, word-boundary-safe occurrences of `variant` in `hay`."""
    if not variant:
        return []
    found: list[tuple[int, int]] = []
    probe = 0
    while True:
        idx = hay.find(variant, probe)
        if idx < 0:
            break
        end = idx + len(variant)
        if not any(occupied[idx:end]) and _boundaries_ok(hay, idx, end):
            found.append((idx, end))
            probe = end
        else:
            probe = idx + 1
    return found


def _latinish(s: str) -> bool:
    return all(ord(ch) < 128 for ch in s)


def _boundaries_ok(hay: str, start: int, end: int) -> bool:
    """Latin cues need word boundaries; Indic scripts match as substrings."""
    if not _latinish(hay[start:end]):
        return True
    left_ok = start == 0 or not (hay[start - 1].isalnum() or hay[start - 1] == "_")
    right_ok = end >= len(hay) or not (hay[end].isalnum() or hay[end] == "_")
    return left_ok and right_ok


def _distance(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    if a_end <= b_start:
        return b_start - a_end
    if b_end <= a_start:
        return a_start - b_end
    return 0


def pair_entities_and_topics(
    *,
    entity_spans: tuple[DepartmentSpan, ...],
    topic_spans: tuple[TopicSpan, ...],
    fallback_topic: str,
) -> tuple[SemanticItem, ...] | None:
    """
    Bind topics to departments positionally.

    Returns ordered items, or None when the request cannot bind uniquely
    (the caller must then CLARIFY — never guess).
    """
    if not entity_spans:
        return None

    distinct_topics: list[str] = []
    for span in topic_spans:
        if span.topic not in distinct_topics:
            distinct_topics.append(span.topic)

    # No explicit topic: every entity takes the caller's default topic.
    if not distinct_topics:
        if len(entity_spans) != 1:
            # "tell me about CSE and AIML" — two decks, a comparison, or two
            # overviews are all plausible. Never guess.
            return None
        return (SemanticItem(entity=entity_spans[0].json_key, topic=fallback_topic),)

    # One topic broadcasts across every named department, in user order.
    if len(distinct_topics) == 1:
        topic = distinct_topics[0]
        return tuple(SemanticItem(entity=e.json_key, topic=topic) for e in entity_spans)

    # One department takes every named topic, in user order.
    if len(entity_spans) == 1:
        entity = entity_spans[0].json_key
        return tuple(SemanticItem(entity=entity, topic=t) for t in distinct_topics)

    # Multiple departments and multiple topic types: bind each explicit topic
    # occurrence to its nearest department.  Occurrences matter here, not merely
    # distinct topic names: "CSE HOD, DS HOD, ECE fees" has three clauses but
    # only two topic types.  Every named department must receive at least one
    # topic or the composition remains ambiguous and fails closed.
    return _bind_occurrences_by_proximity(
        entity_spans=entity_spans,
        topic_spans=topic_spans,
    )


def _bind_occurrences_by_proximity(
    *,
    entity_spans: tuple[DepartmentSpan, ...],
    topic_spans: tuple[TopicSpan, ...],
) -> tuple[SemanticItem, ...] | None:
    bound: list[tuple[int, TopicSpan]] = []
    assigned_entities: set[int] = set()

    for topic_span in topic_spans:
        choice: tuple[int, int, int] | None = None
        for entity_index, entity_span in enumerate(entity_spans):
            distance = _distance(
                topic_span.start,
                topic_span.end,
                entity_span.start,
                entity_span.end,
            )
            # On an exact tie, prefer the preceding entity.  This matches normal
            # "CSE HOD" clause order while remaining deterministic for every script.
            follows_entity = 0 if entity_span.end <= topic_span.start else 1
            candidate = (distance, follows_entity, entity_index)
            if choice is None or candidate < choice:
                choice = candidate
        if choice is None:
            return None
        entity_index = choice[2]
        assigned_entities.add(entity_index)
        bound.append((entity_index, topic_span))

    if len(assigned_entities) != len(entity_spans):
        return None

    out: list[SemanticItem] = []
    seen: set[tuple[str, str]] = set()
    for entity_index, topic_span in bound:
        item = SemanticItem(
            entity=entity_spans[entity_index].json_key,
            topic=topic_span.topic,
        )
        identity = (item.entity, item.topic)
        if identity in seen:
            continue
        seen.add(identity)
        out.append(item)
    return tuple(out) or None


def _bind_by_proximity(
    *,
    entity_spans: tuple[DepartmentSpan, ...],
    topic_spans: tuple[TopicSpan, ...],
    topics: list[str],
) -> tuple[SemanticItem, ...] | None:
    """Greedy globally-minimum-distance assignment; deterministic tie-breaks."""
    best_span: dict[tuple[str, int], int] = {}
    for t_index, topic in enumerate(topics):
        for e_index, ent in enumerate(entity_spans):
            distances = [
                _distance(ts.start, ts.end, ent.start, ent.end)
                for ts in topic_spans
                if ts.topic == topic
            ]
            if distances:
                best_span[(topic, e_index)] = min(distances)

    unbound_topics = list(enumerate(topics))
    unbound_entities = list(range(len(entity_spans)))
    bound: list[tuple[int, int]] = []  # (entity_index, topic_index)

    while unbound_topics and unbound_entities:
        choice: tuple[int, int, int, int] | None = None  # (dist, t_index, e_index, t_pos)
        for t_pos, (t_index, topic) in enumerate(unbound_topics):
            for e_index in unbound_entities:
                dist = best_span.get((topic, e_index))
                if dist is None:
                    continue
                candidate = (dist, t_index, e_index, t_pos)
                if choice is None or candidate < choice:
                    choice = candidate
        if choice is None:
            return None
        _, t_index, e_index, t_pos = choice
        bound.append((e_index, t_index))
        unbound_topics.pop(t_pos)
        unbound_entities.remove(e_index)

    if unbound_topics or unbound_entities:
        return None

    def _order_key(pair: tuple[int, int]) -> int:
        e_index, t_index = pair
        topic = topics[t_index]
        starts = [ts.start for ts in topic_spans if ts.topic == topic]
        return min([entity_spans[e_index].start] + starts)

    bound.sort(key=_order_key)
    return tuple(
        SemanticItem(entity=entity_spans[e_index].json_key, topic=topics[t_index])
        for e_index, t_index in bound
    )
