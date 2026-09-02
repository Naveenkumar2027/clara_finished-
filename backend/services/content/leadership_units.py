"""Leadership unit identity — existing executive cards, not new content.

Principal / vice-principal (dean) / trustees already have card surfaces and
canonical copy. They were excluded from UnitSelector because the semantic
parser required a department span. This module exposes those existing units
as ordered (entity, topic) items so they can compose with department units.

Does not invent campus, canteen, faculty, or clubs cards.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.services.answer_generation import (
    PRINCIPAL_PROFILE_KEYWORDS,
    VICE_PRINCIPAL_PROFILE_KEYWORDS,
    _contains_phrase,
    _matches_any_phrase,
    _principal_word_intent_positive,
    normalized_text_for_executive_keyword_scan,
)
from backend.services.content.semantic_composition import SemanticItem
from backend.services.content.unicode_text import casefold_keep_scripts

LEADERSHIP_ENTITY = "leadership"
TOPIC_PRINCIPAL = "principal"
TOPIC_VICE_PRINCIPAL = "vice_principal"
TOPIC_TRUSTEES = "trustees"

LEADERSHIP_TOPICS = frozenset({TOPIC_PRINCIPAL, TOPIC_VICE_PRINCIPAL, TOPIC_TRUSTEES})

UNIT_PRINCIPAL = "leadership.principal"
UNIT_VICE_PRINCIPAL = "leadership.vice_principal"
UNIT_TRUSTEES = "leadership.trustees"

# Existing executive cards only. Dean is the vice-principal / dean-academics surface.
LEADERSHIP_UNIT_IDS = (UNIT_PRINCIPAL, UNIT_VICE_PRINCIPAL, UNIT_TRUSTEES)

# Tight trustee cues. Do not reuse TRUSTEES_PROFILE_KEYWORDS ("management", "board",
# "president", "founder") — those fire on unrelated institutional talk.
_TRUSTEE_CUES: tuple[str, ...] = (
    "trustees",
    "trustee",
    "trusties",
    "trusty",
    "ಟ್ರಸ್ಟಿ",
    "ट्रस्टी",
    "ट्रस्टीज",
    "அறங்காவலர்",
    "அறங்காவலர்கள்",
    "ట్రస్టీ",
    "ట్రస్టీలు",
    "ട്രസ്റ്റി",
    "ട്രസ്റ്റിമാർ",
)

# Native principal role words already used in locale / regression copy.
# Do not add generic question words (ಯಾರು / कौन / who).
_PRINCIPAL_NATIVE_CUES: tuple[str, ...] = (
    "ಪ್ರಾಂಶುಪಾಲ",
    "ಪ್ರಿನ್ಸಿಪಾಲ್",
    "प्राचार्य",
    "मुख्यध्यापक",
    "प्रिंसिपल",
    "முதல்வர்",
    "ప్రిన్సిపాల్",
    "ప్రాంశుపాల",
    "പ്രിൻസിപ്പൽ",
)

_DEAN_CUES: tuple[str, ...] = (
    "dean academics",
    "dean of academics",
    "academic dean",
    "dean",
    "ಡೀನ್",
    "डीन",
    "டீன்",
    "డీన్",
    "ഡീൻ",
)

# Multi-department listing without a topic: "Show me CSE Data Science and CSE AIML."
# Distinct from "tell me about CSE and AIML" (full-scope, still fail-closed).
_SHOW_MULTI_OVERVIEW_CUES: tuple[str, ...] = (
    "show me",
    "show",
    "display",
    "ತೋರಿಸು",
    "ತೋರಿಸಿ",
    "दिखाओ",
    "दिखाइए",
    "दिखाएँ",
    "காட்டு",
    "காட்டி",
    "చూపించు",
    "చూపు",
    "കാണിക്ക്",
    "കാണിച്ചു",
    "torisi",
    "dikhao",
    "kaattu",
    "chupinchu",
    "kaanikku",
)


@dataclass(frozen=True)
class LeadershipSpan:
    topic: str
    start: int
    end: int


def is_leadership_topic(topic: str) -> bool:
    return (topic or "").strip().lower() in LEADERSHIP_TOPICS


def unit_id_for_leadership_topic(topic: str) -> str | None:
    t = (topic or "").strip().lower()
    if t == TOPIC_PRINCIPAL:
        return UNIT_PRINCIPAL
    if t == TOPIC_VICE_PRINCIPAL:
        return UNIT_VICE_PRINCIPAL
    if t == TOPIC_TRUSTEES:
        return UNIT_TRUSTEES
    return None


def detect_leadership_spans(raw_text: str) -> tuple[LeadershipSpan, ...]:
    """Ordered leadership topic spans. Vice-principal consumes 'principal' inside it."""
    if not raw_text or not isinstance(raw_text, str):
        return ()
    hay = casefold_keep_scripts(raw_text)
    if not hay:
        return ()
    occupied = [False] * len(hay)
    # Longer campus words (Tamil கேண்டீன்) contain short dean cues (டீன்).
    # Occupy campus entity spans first so leadership never steals a substring.
    from backend.services.content.campus_units import detect_campus_entity_spans

    for campus in detect_campus_entity_spans(raw_text):
        for i in range(campus.start, min(campus.end, len(occupied))):
            occupied[i] = True
    spans: list[LeadershipSpan] = []

    def _consume(topic: str, cues: tuple[str, ...]) -> None:
        variants = sorted((casefold_keep_scripts(c) for c in cues if c), key=len, reverse=True)
        for variant in variants:
            if not variant:
                continue
            probe = 0
            while True:
                idx = hay.find(variant, probe)
                if idx < 0:
                    break
                end = idx + len(variant)
                if end <= len(occupied) and not any(occupied[idx:end]) and _boundaries_ok(hay, idx, end):
                    for i in range(idx, end):
                        occupied[i] = True
                    spans.append(LeadershipSpan(topic=topic, start=idx, end=end))
                    probe = end
                else:
                    probe = idx + 1

    _consume(TOPIC_VICE_PRINCIPAL, tuple(VICE_PRINCIPAL_PROFILE_KEYWORDS) + _DEAN_CUES)
    _consume(TOPIC_PRINCIPAL, tuple(PRINCIPAL_PROFILE_KEYWORDS) + _PRINCIPAL_NATIVE_CUES)
    _consume(TOPIC_TRUSTEES, _TRUSTEE_CUES)

    normalized = normalized_text_for_executive_keyword_scan(raw_text)
    if _principal_word_intent_positive(normalized) and not any(s.topic == TOPIC_PRINCIPAL for s in spans):
        if not any(s.topic == TOPIC_VICE_PRINCIPAL for s in spans):
            match = re.search(r"\bprincipal\b|\bprinciple\b", hay)
            if match and not any(occupied[match.start():match.end()]):
                spans.append(LeadershipSpan(topic=TOPIC_PRINCIPAL, start=match.start(), end=match.end()))

    spans.sort(key=lambda s: s.start)
    # One unit per leadership topic; keep first mention order.
    seen: set[str] = set()
    out: list[LeadershipSpan] = []
    for span in spans:
        if span.topic in seen:
            continue
        seen.add(span.topic)
        out.append(span)
    return tuple(out)


def leadership_items_from_text(raw_text: str) -> tuple[SemanticItem, ...]:
    return tuple(
        SemanticItem(entity=LEADERSHIP_ENTITY, topic=span.topic)
        for span in detect_leadership_spans(raw_text)
    )


def is_show_multi_overview_request(raw_text: str, normalized: str) -> bool:
    """True when the user asked to display named departments, not a full-deck 'tell me about'."""
    hays = (
        casefold_keep_scripts(raw_text or ""),
        casefold_keep_scripts(normalized or ""),
    )
    for cue in _SHOW_MULTI_OVERVIEW_CUES:
        folded = casefold_keep_scripts(cue)
        if not folded:
            continue
        if any(folded in hay for hay in hays if hay):
            return True
    return False


def _boundaries_ok(hay: str, start: int, end: int) -> bool:
    chunk = hay[start:end]
    if any(ord(ch) > 127 for ch in chunk):
        return True
    left_ok = start == 0 or not (hay[start - 1].isalnum() or hay[start - 1] == "_")
    right_ok = end >= len(hay) or not (hay[end].isalnum() or hay[end] == "_")
    return left_ok and right_ok


def has_existing_executive_cue(raw_text: str) -> bool:
    """Whether existing executive-profile detection would fire (regression-safe)."""
    normalized = normalized_text_for_executive_keyword_scan(raw_text)
    if not normalized:
        return False
    if _matches_any_phrase(normalized, VICE_PRINCIPAL_PROFILE_KEYWORDS):
        return True
    if _matches_any_phrase(normalized, PRINCIPAL_PROFILE_KEYWORDS) or _principal_word_intent_positive(normalized):
        return True
    if any(_contains_phrase(normalized, cue) for cue in _TRUSTEE_CUES):
        return True
    if any(_contains_phrase(normalized, cue) for cue in _DEAN_CUES):
        return True
    if any(_contains_phrase(normalized, cue) for cue in _PRINCIPAL_NATIVE_CUES):
        return True
    return False
