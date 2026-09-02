"""Canonical department identity — exclusive longest-span matching.

Never uses substring identity (cse must not match inside cse_ds / CSE Data Science).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from backend.services.answer_generation import (
    _CANONICAL_DEPARTMENT_TO_JSON_KEY,
    DEPARTMENT_JSON_KEY_ORDER,
    _inject_regional_department_tokens,
    department_label_to_json_key,
    load_locale_data_for_lang_key,
)
from backend.services.content.semantic_vocab.catalog import entries_for
from backend.services.content.unicode_text import casefold_keep_scripts, latin_token_boundaries_ok


def normalize_for_department_match(text: str) -> str:
    raw = _inject_regional_department_tokens(text or "")
    return casefold_keep_scripts(raw)


def _latinish(s: str) -> bool:
    return all(ord(ch) < 128 for ch in s)


def _find_unoccupied(hay: str, needle: str, occupied: list[bool], start: int = 0) -> int:
    if not needle:
        return -1
    from_idx = start
    while True:
        idx = hay.find(needle, from_idx)
        if idx < 0:
            return -1
        end = idx + len(needle)
        if end <= len(occupied) and not any(occupied[idx:end]):
            if _latinish(needle) and not latin_token_boundaries_ok(hay, idx, end):
                from_idx = idx + 1
                continue
            return idx
        from_idx = idx + 1


_LOCALE_ALIAS_LANGUAGES = ("en", "kn", "hi", "ta", "te", "ml")
_LOCALE_ALIAS_DIR = Path(__file__).resolve().parents[2] / "data" / "locales"


def _locale_alias_revision() -> tuple[int, ...]:
    """Cheap cache key that still honours the locale loader's hot-reload contract."""
    revisions: list[int] = []
    for language in _LOCALE_ALIAS_LANGUAGES:
        try:
            revisions.append((_LOCALE_ALIAS_DIR / f"{language}.json").stat().st_mtime_ns)
        except OSError:
            revisions.append(-1)
    return tuple(revisions)


def department_alias_table() -> tuple[tuple[str, str], ...]:
    return _department_alias_table_cached(_locale_alias_revision())


@lru_cache(maxsize=4)
def _department_alias_table_cached(_revision: tuple[int, ...]) -> tuple[tuple[str, str], ...]:
    """(variant, json_key) longest-first. Canonical labels included."""
    rows: list[tuple[str, str]] = []
    for e in entries_for(category="DEPARTMENT"):
        v = normalize_for_department_match(e.variant)
        if v:
            rows.append((v, e.canonical))
    for label, jkey in _CANONICAL_DEPARTMENT_TO_JSON_KEY.items():
        v = normalize_for_department_match(label)
        if v:
            rows.append((v, jkey))
    # Authoritative backend locale names are display labels at the boundary only.
    # Register their normalized forms against existing language-independent keys so
    # translated text never becomes an internal identity. Normalizing aliases with
    # the same regional-token injection as the user haystack is essential for
    # compound names such as ``CSE (ಡೇಟಾ ಸೈನ್ಸ್)``: the complete specialization
    # span must consume the parent CSE token instead of returning both identities.
    for language in _LOCALE_ALIAS_LANGUAGES:
        locale = load_locale_data_for_lang_key(language)
        departments = locale.get("departments") if isinstance(locale, dict) else None
        if not isinstance(departments, dict):
            continue
        for jkey in DEPARTMENT_JSON_KEY_ORDER:
            department = departments.get(jkey)
            label = department.get("name") if isinstance(department, dict) else None
            if not isinstance(label, str) or not label.strip():
                continue
            v = normalize_for_department_match(label)
            if v:
                rows.append((v, jkey))
    # Longest span first; compound keys before plain cse when length ties.
    rows.sort(key=lambda x: (len(x[0]), 0 if "_" in x[1] or x[1] != "cse" else 1), reverse=True)
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []
    for v, k in rows:
        if (v, k) in seen:
            continue
        seen.add((v, k))
        out.append((v, k))
    return tuple(out)


@dataclass(frozen=True)
class DepartmentSpan:
    """A department identity match with its position in the shared match haystack."""

    json_key: str
    start: int
    end: int


def match_department_spans_exclusive(text: str) -> tuple[DepartmentSpan, ...]:
    """
    Ordered unique department spans over ``normalize_for_department_match(text)``.

    Positions are offsets into that haystack so topic spans detected on the same
    haystack can be paired with entities by proximity.
    """
    hay = normalize_for_department_match(text)
    if not hay:
        return ()
    occupied = [False] * len(hay)
    hits: list[DepartmentSpan] = []
    for alias, jkey in department_alias_table():
        start = 0
        while True:
            idx = _find_unoccupied(hay, alias, occupied, start)
            if idx < 0:
                break
            end = idx + len(alias)
            for i in range(idx, end):
                occupied[i] = True
            hits.append(DepartmentSpan(json_key=jkey, start=idx, end=end))
            start = end
    hits.sort(key=lambda s: s.start)
    out: list[DepartmentSpan] = []
    seen: set[str] = set()
    for span in hits:
        if span.json_key in seen:
            continue
        seen.add(span.json_key)
        out.append(span)
    return tuple(out)


def match_department_keys_exclusive(text: str) -> tuple[str, ...]:
    """Ordered unique json keys. Consumes matched spans so cse cannot leak from cse_ds."""
    return tuple(s.json_key for s in match_department_spans_exclusive(text))


def resolve_label_to_json_key_exact(label: str | None) -> str | None:
    """Exact canonical label or json key. No blob/substring search."""
    if not label or not isinstance(label, str):
        return None
    direct = department_label_to_json_key(label)
    if direct:
        return direct
    candidate = label.strip().lower().replace(" ", "_")
    known = {e.canonical for e in entries_for(category="DEPARTMENT")}
    known.update(_CANONICAL_DEPARTMENT_TO_JSON_KEY.values())
    if candidate in known:
        return candidate
    keys = match_department_keys_exclusive(label)
    if len(keys) == 1:
        return keys[0]
    return None
