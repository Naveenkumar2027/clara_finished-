"""Unicode-safe text helpers for M5.3 normalization.

Must keep Indic grapheme clusters (letters + virama/matras / Mn Mc Me).
Must not treat combining marks as punctuation.
"""

from __future__ import annotations

import re
import unicodedata


def strip_punctuation_keep_graphemes(text: str) -> str:
    """Replace punctuation/symbols with spaces; keep letters, marks, digits, &_()-."""
    if not text:
        return ""
    # Compatibility-normalize STT/IME output without transliterating Indic text.
    text = unicodedata.normalize("NFKC", text)
    out: list[str] = []
    for ch in text:
        if ch in {"\u200b", "\u200c", "\u200d", "\ufeff"}:
            continue
        cat = unicodedata.category(ch)
        if cat[0] in ("L", "N", "M") or ch.isspace() or ch in "&()_-":
            out.append(ch)
        else:
            out.append(" ")
    return collapse_ws("".join(out))


def collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def casefold_keep_scripts(text: str) -> str:
    return collapse_ws(strip_punctuation_keep_graphemes(text or "").casefold())


def is_latin_token_char(ch: str) -> bool:
    """ASCII letters, digits, and underscore — not Indic letters glued to Latin names."""
    return bool(ch) and ch.isascii() and (ch.isalnum() or ch == "_")


def latin_token_boundaries_ok(hay: str, start: int, end: int) -> bool:
    """Latin cues need Latin word boundaries so ``TechVidyaയെ`` still matches ``techvidya``."""
    chunk = hay[start:end]
    if not chunk or any(ord(ch) > 127 for ch in chunk):
        return True
    left_ok = start == 0 or not is_latin_token_char(hay[start - 1])
    right_ok = end >= len(hay) or not is_latin_token_char(hay[end])
    return left_ok and right_ok
