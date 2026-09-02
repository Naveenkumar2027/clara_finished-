"""Shared fixed UI localization contract for backend and frontend consumers.

Contract:
  - ui_text("kn", path), ui_text("hi", path), ui_text("te", path), and
    ui_text("ml", path) return the exact localized
    scalar. Neither silently falls back to English when that locale exists.
  - ui_text accepts the canonical short code ("kn", "en") and the
    display name ("Kannada", "English") interchangeably. Case-
    insensitive and locale-suffix variants ("kn-IN", "kn_IN", "KN",
    "kannada") all normalize to "kn".
  - load_ui_locales() is cached; reload_ui_locales() invalidates the
    cache and re-reads the file so an updated ui.json is picked up by
    the running process without a restart.
  - Placeholders like {department} are preserved when no variable is
    passed, and substituted only when the caller passes the value.
  - The returned locale dict is a defensive deep copy, so consumer
    mutation does not corrupt the cache.
"""

from __future__ import annotations

import copy
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

_UI_LOCALE_PATH = Path(__file__).resolve().parents[1] / "data" / "locales" / "ui.json"

# Canonical short code -> no remap. We accept both the short code and
# the display name as input, and normalize to a single short code.
_DISPLAY_NAME_TO_KEY = {
    "english": "en",
    "kannada": "kn",
    "hindi": "hi",
    "tamil": "ta",
    "telugu": "te",
    "malayalam": "ml",
}

# Languages the runtime recognizes (used to validate explicit kn/en
# requests; everything else is a contract violation).
_VALID_LANG_KEYS = frozenset({"en", "kn", "hi", "ta", "te", "ml"})


def ui_language_key(language: str | None) -> str:
    """Normalize any accepted language identifier to a canonical short code.

    Accepts:
      - canonical short codes: en, kn, hi, ta, te, ml
      - case-insensitive variants: EN, KN, Kannada, KANNADA
      - locale-suffix variants: kn-IN, kn_IN, en-IN, en_US
      - display names: English, Kannada, Hindi, Tamil, Telugu, Malayalam
    """
    if language is None:
        return "en"
    value = str(language).strip()
    if not value:
        return "en"
    # Strip locale suffix: "kn-IN" -> "kn", "en_US" -> "en".
    if "-" in value:
        value = value.split("-", 1)[0]
    if "_" in value:
        value = value.split("_", 1)[0]
    low = value.strip().lower()
    if low in _VALID_LANG_KEYS:
        return low
    if low in _DISPLAY_NAME_TO_KEY:
        return _DISPLAY_NAME_TO_KEY[low]
    # Unknown identifier. We return "en" for forward compatibility with
    # the existing English-passthrough contract, but we log a warning so
    # the bug is visible. Callers that require strict validation should
    # call is_valid_language_key() first.
    logger.warning(
        "ui_language_key: unknown language identifier %r; falling back to 'en'",
        language,
    )
    return "en"


def is_valid_language_key(language: str | None) -> bool:
    """Return True iff the identifier normalizes to a recognized language."""
    if language is None:
        return False
    value = str(language).strip()
    if not value:
        return False
    if "-" in value:
        value = value.split("-", 1)[0]
    if "_" in value:
        value = value.split("_", 1)[0]
    low = value.strip().lower()
    if low in _VALID_LANG_KEYS:
        return True
    if low in _DISPLAY_NAME_TO_KEY:
        return True
    return False


@lru_cache(maxsize=1)
def _load_ui_locales_cached() -> tuple[str, dict[str, Any]]:
    """Read the ui.json file once and cache the parsed dict.

    Returns a tuple of (file_mtime, deep_copy) so the cache is
    invalidated automatically when the on-disk file changes.
    """
    raw = _UI_LOCALE_PATH.read_text(encoding="utf-8")
    mtime = str(_UI_LOCALE_PATH.stat().st_mtime_ns)
    data = json.loads(raw)
    return mtime, copy.deepcopy(data)


def load_ui_locales() -> dict[str, Any]:
    """Return a defensive deep copy of the parsed ui.json.

    The cache uses (file mtime, data) as the key. If the file has
    been modified on disk, the cache is invalidated and the new
    content is loaded. Callers receive a fresh deep copy, so they may
    safely mutate the returned dict without affecting the cache or
    other consumers.
    """
    mtime = str(_UI_LOCALE_PATH.stat().st_mtime_ns)
    cached_mtime, cached_data = _load_ui_locales_cached()
    if cached_mtime != mtime:
        # File changed; force a reload.
        _load_ui_locales_cached.cache_clear()
        cached_mtime, cached_data = _load_ui_locales_cached()
    return copy.deepcopy(cached_data)


def reload_ui_locales() -> dict[str, Any]:
    """Invalidate the ui.json cache and return the freshly loaded data.

    Use this when ui.json has been updated and the running process
    must pick up the new content without a restart.
    """
    _load_ui_locales_cached.cache_clear()
    return load_ui_locales()


class _KannadaKeyMissing(KeyError):
    """Raised when a requested key is absent from the Kannada locale.

    Subclasses KeyError so existing `except KeyError` handlers catch
    it, but the message and the `.path` attribute identify the
    language and the missing path so the diagnostic is unambiguous.
    """

    def __init__(self, path: str) -> None:
        super().__init__(f"Kannada (kn) key not found: {path!r}")
        self.path = path


def ui_text(language: str | None, path: str, **variables: object) -> str:
    """Return an exact fixed UI string for the requested language.

    Contract:
      - For "kn" (or any normalized Kannada identifier), the function
        returns the exact ui.json["kn"] scalar at `path`. If the path
        is absent in kn, it raises _KannadaKeyMissing; it does NOT
        silently fall back to English.
      - For any locale present in ui.json, the
        function returns that locale's exact scalar and raises KeyError for
        a missing path.
      - For unknown languages, the function falls back to "en" with a
        warning (preserved for forward compatibility with the existing
        English-passthrough contract).
      - Placeholders like {department} are preserved when no value is
        passed, and substituted only when the caller passes variables.
    """
    locale = load_ui_locales()
    lang_key = ui_language_key(language)
    if lang_key == "kn":
        node: object = locale.get("kn", {})
        # Walk the path; if any segment is missing, raise a diagnostic
        # error. Do NOT silently fall back to English.
        try:
            current = node
            for part in path.split("."):
                current = current[part]  # type: ignore[index]
        except (KeyError, TypeError) as exc:
            raise _KannadaKeyMissing(path) from exc
    else:
        selected_key = lang_key if lang_key in locale else "en"
        node = locale.get(selected_key, {})
        try:
            current = node
            for part in path.split("."):
                current = current[part]  # type: ignore[index]
        except (KeyError, TypeError) as exc:
            raise KeyError(
                f"{selected_key} UI localization path not found: {path!r}"
            ) from exc
    if not isinstance(current, str):
        raise TypeError(f"UI localization path is not text: {path}")
    text = current
    for name, value in variables.items():
        text = text.replace("{" + name + "}", str(value))
    return text
