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
