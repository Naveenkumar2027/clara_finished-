"""Topic / scope / unsupported cue detection from structured vocab (not first-keyword-wins)."""

from __future__ import annotations

import re

from backend.services.content.semantic_vocab.catalog import (
    SCOPE_FULL,
    TOPIC_ACHIEVEMENTS,
    TOPIC_CONTACT,
    TOPIC_FACULTY,
    TOPIC_FEES,
    TOPIC_HOD,
    TOPIC_PLACEMENTS,
    UNSUPPORTED_BUS,
    UNSUPPORTED_DOCUMENTS,
    all_entries,
)
from backend.services.content.unicode_text import casefold_keep_scripts

ATOMIC_TOPICS = frozenset(
    {
        TOPIC_HOD,
        TOPIC_FEES,
        TOPIC_PLACEMENTS,
        TOPIC_ACHIEVEMENTS,
        TOPIC_FACULTY,
        TOPIC_CONTACT,
    }
)


def _latinish(s: str) -> bool:
    return all(ord(ch) < 128 for ch in s)


def cue_in_hay(hay: str, cue: str) -> bool:
    if not hay or not cue:
        return False
    n = casefold_keep_scripts(cue) if any(ord(c) > 127 for c in cue) else cue.casefold()
    if not n:
        return False
    if not _latinish(n):
        return n in hay
    return re.search(rf"(?<![a-z0-9_]){re.escape(n)}(?![a-z0-9_])", hay) is not None


def _hays(*texts: str) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for t in texts:
        h = casefold_keep_scripts(t)
        if h and h not in seen:
            seen.add(h)
            out.append(h)
    return tuple(out)


def detect_atomic_topics(*texts: str) -> frozenset[str]:
    hays = _hays(*texts)
    found: set[str] = set()
    for e in all_entries():
        if e.canonical not in ATOMIC_TOPICS:
            continue
        if e.category not in {"TOPIC", "QUESTION", "ROMANIZED", "CODE-SWITCH"}:
            continue
        if any(cue_in_hay(h, e.variant) for h in hays):
            found.add(e.canonical)
    return frozenset(found)


def detect_unsupported(*texts: str) -> frozenset[str]:
    hays = _hays(*texts)
    found: set[str] = set()
    for e in all_entries():
        if e.category != "UNSUPPORTED":
            continue
        if any(cue_in_hay(h, e.variant) for h in hays):
            found.add(e.canonical)
    return frozenset(found)


def is_full_department_scope(*texts: str) -> bool:
    hays = _hays(*texts)
    for e in all_entries():
        if e.canonical != SCOPE_FULL:
            continue
        if e.category not in {"SCOPE", "CODE-SWITCH"}:
            continue
        if any(cue_in_hay(h, e.variant) for h in hays):
            return True
    return False
