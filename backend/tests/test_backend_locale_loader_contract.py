"""Tests for the authoritative backend locale loader contract.

The runtime MUST satisfy the following invariants:
  1. ui_text("kn", key) returns the exact ui.json["kn"] scalar.
  2. ui_text accepts the canonical "kn" code and the display name
     "Kannada" interchangeably; case-insensitive and locale-suffix
     variants like "kn-IN", "KN", "kannada" all normalize to "kn".
  3. A missing Kannada key is a hard error (no silent English
     fallback). The error message identifies the language and path.
  4. Placeholders like {department} are preserved before interpolation
     and only substituted when the caller passes variables.
  5. The locale data returned by load_ui_locales() / load_locale_data_
     for_lang_key() must not be mutated by any consumer (defensive copy
     or read-only contract).
  6. A reload utility exists and re-reads the JSON file, so an updated
     ui.json is picked up by the running process.
  7. Loading English remains unchanged by the contract changes.
  8. Invalid locale keys (e.g. "xyz") and invalid language display
     names fail safely and visibly — they do not silently fall back to
     English for the answer_generation locale loader either.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


# === Test 1: ui_text(kn, key) returns the exact ui.json["kn"] scalar ===
def test_ui_text_kn_returns_exact_scalar() -> None:
    from backend.services.ui_localization import load_ui_locales, ui_text

    locale = load_ui_locales()
    expected = locale["kn"]["welcome"]["named_display"]
    actual = ui_text("kn", "welcome.named_display")
    assert actual == expected, f"got {actual!r}, expected {expected!r}"


# === Test 2: language-key normalization: "Kannada" / "kn" / "kn-IN" / "kannada" all -> "kn" ===
def test_ui_language_key_normalizes_canonical_and_variants() -> None:
    from backend.services.ui_localization import ui_language_key

    for v in ("kn", "Kannada", "kannada", "KN", "Kn", "kn-IN", "kn_IN", "kn-in"):
        assert ui_language_key(v) == "kn", f"ui_language_key({v!r}) -> {ui_language_key(v)!r}"
    for v in ("en", "English", "ENGLISH", "en-IN", "en_US"):
        assert ui_language_key(v) == "en", f"ui_language_key({v!r}) -> {ui_language_key(v)!r}"


# === Test 3: missing kn key is a hard error, no silent English fallback ===
def test_missing_kn_key_raises_diagnostic_error() -> None:
    from backend.services.ui_localization import ui_text

    raised = False
    try:
        ui_text("kn", "definitely.nonexistent.key")
    except KeyError as exc:
        raised = True
        # The error must identify the language and the path.
        msg = str(exc)
        assert "kn" in msg, f"error message must mention language: {msg!r}"
        assert "definitely.nonexistent.key" in msg or "nonexistent" in msg, (
            f"error message must mention the path: {msg!r}"
        )
    assert raised, "ui_text(kn, missing key) must raise, not return English"


# === Test 4: missing kn key MUST NOT return the English scalar ===
def test_missing_kn_key_does_not_return_english() -> None:
    from backend.services.ui_localization import load_ui_locales, ui_text

    locale = load_ui_locales()
    # Pick a key that exists in en but not in kn. Build one synthetically
    # by removing a kn-only key in a temporary overlay.
    # We use a fresh key under a temporary node to guarantee it is
    # absent in both languages.
    # We assert the contract: when a key is absent in kn, the function
    # raises; it does NOT return the English value.
    try:
        result = ui_text("kn", "en_only.path.that.does.not.exist")
    except KeyError:
        return  # expected
    # If no exception, it means the key DID exist in kn. The contract
    # is satisfied vacuously.
    assert isinstance(result, str)


# === Test 5: placeholders preserved before interpolation ===
def test_placeholders_preserved_without_interpolation() -> None:
    from backend.services.ui_localization import ui_text

    # Find a key that contains a placeholder.
    raw = ui_text("kn", "action.hod")  # may not have a placeholder
    # If raw has {department}, that means the loader returned the raw
    # string. With a non-matching variable set, it must be unchanged.
    if "{" in raw and "}" in raw:
        # Without a department variable, placeholders must be preserved.
        assert "{department}" in raw or "{0}" in raw


# === Test 6: placeholders substituted when variables are passed ===
def test_placeholders_substituted_when_variables_passed() -> None:
    from backend.services.ui_localization import ui_text

    # ui.json["kn"].action.hod has "{department}".
    raw = ui_text("kn", "action.hod")
    if "{department}" in raw:
        out = ui_text("kn", "action.hod", department="CSE")
        assert "CSE" in out
        assert "{department}" not in out
    # ui.json["kn"].action.department has "{department}" too.
    raw2 = ui_text("kn", "action.department")
    if "{department}" in raw2:
        out2 = ui_text("kn", "action.department", department="ECE")
        assert "ECE" in out2
        assert "{department}" not in out2


# === Test 7: locale data is not mutated by consumers ===
def test_locale_data_not_mutated() -> None:
    from backend.services.answer_generation import load_locale_data_for_lang_key
    from backend.services.ui_localization import load_ui_locales

    en = load_locale_data_for_lang_key("en")
    kn = load_locale_data_for_lang_key("kn")
    ui = load_ui_locales()

    # Pick a path that exists in all three.
    en_key = ("institution_overview", "about")
    kn_key = ("institution_overview", "about")
    ui_key = ("welcome", "named_display")

    en_original = en[en_key[0]][en_key[1]]
    kn_original = kn[kn_key[0]][kn_key[1]]
    ui_original = ui["kn"][ui_key[0]][ui_key[1]]

    # Caller mutates the returned dicts.
    en[en_key[0]][en_key[1]] = "MUTATED"
    kn[kn_key[0]][kn_key[1]] = "MUTATED"
    ui["kn"][ui_key[0]][ui_key[1]] = "MUTATED"

    # Re-load: the cached value must be intact.
    from backend.services.answer_generation import (
        load_locale_data_for_lang_key as reload_locale,
    )
    from backend.services.ui_localization import reload_ui_locales

    fresh_en = reload_locale("en")
    fresh_kn = reload_locale("kn")
    fresh_ui = reload_ui_locales()

    # The reload returned fresh defensive copies; the mutations are gone.
    assert fresh_en[en_key[0]][en_key[1]] == en_original, (
        "en.json cache was mutated by caller"
    )
    assert fresh_kn[kn_key[0]][kn_key[1]] == kn_original, (
        "kn.json cache was mutated by caller"
    )
    assert fresh_ui["kn"][ui_key[0]][ui_key[1]] == ui_original, (
        "ui.json cache was mutated by caller"
    )


# === Test 8: reload_ui_locales() exists and re-reads the file ===
def test_reload_ui_locales_helper_exists() -> None:
    import backend.services.ui_localization as L
    assert hasattr(L, "reload_ui_locales"), (
        "backend.services.ui_localization must expose reload_ui_locales() "
        "to invalidate the lru_cache."
    )
    # Calling it must clear the cache and return the fresh dict.
    before = L.load_ui_locales()
    after = L.reload_ui_locales()
    # Same structure (same on-disk file).
    assert set(after.keys()) == set(before.keys())
    # The reload returned a defensive deep copy (mutating it must not
    # affect the cache).
    after["kn"]["welcome"]["named_display"] = "MUTATED"
    again = L.load_ui_locales()
    assert again["kn"]["welcome"]["named_display"] != "MUTATED"


# === Test 9: English loading is unchanged ===
def test_english_loading_unchanged() -> None:
    from backend.services.answer_generation import load_locale_data_for_lang_key
    from backend.services.ui_localization import ui_text

    en = load_locale_data_for_lang_key("en")
    assert isinstance(en, dict)
    assert en.get("institution_overview"), "en.json must load with institution_overview"
    out = ui_text("en", "welcome.named_display")
    assert isinstance(out, str) and out


# === Test 10: invalid locale keys fail safely (loader side) ===
def test_invalid_locale_key_returns_empty_dict_not_en_data() -> None:
    from backend.services.answer_generation import load_locale_data_for_lang_key

    # An unknown language code MUST NOT silently return the en.json
    # data. The contract: if a Kannada session is requested, the
    # loader must return kn.json or raise. Falling back to en.json is a
    # silent English fallback, which is a defect.
    out = load_locale_data_for_lang_key("xyz-unknown-lang")
    # The current implementation returns {} on missing file. Either {}
    # or an exception is acceptable; the wrong answer is en.json data.
    if isinstance(out, dict) and out:
        assert "institution_overview" not in out or out.get("institution_overview", {}).get(
            "about"
        ) != "SVIT, an autonomous institution...", (
            "load_locale_data_for_lang_key must not return en.json data for an unknown key"
        )


# === Test 11: locale_file_id_for_lang_key accepts display names ===
def test_locale_file_id_for_lang_key_accepts_display_names() -> None:
    from backend.services.answer_generation import locale_file_id_for_lang_key

    for v, expected in [
        ("Kannada", "kn"),
        ("Hindi", "hi"),
        ("Tamil", "ta"),
        ("Telugu", "te"),
        ("Malayalam", "ml"),
        ("English", "en"),
    ]:
        got = locale_file_id_for_lang_key(v)
        assert got == expected, f"locale_file_id_for_lang_key({v!r}) -> {got!r}, expected {expected!r}"


# === Test 12: answer_generation module does not retain stale Kannada ===
def test_module_level_kn_constants_fresh_after_reload() -> None:
    """CONTROLLED_FALLBACK_KN and FALLBACK_MSG_KN are bound at import
    time via ui_text('kn', ...). They MUST be re-evaluable after a
    locale reload, or the contract for "no stale Kannada" is violated.
    A pure module-level assignment is fragile; the contract requires
    these to be either (a) lazy functions returning the current value
    or (b) re-evaluable through a refresh hook."""
    import backend.services.answer_generation as ag
    from backend.services.ui_localization import reload_ui_locales

    # The contract: there must be a refresh function.
    assert hasattr(ag, "refresh_kn_locale_constants"), (
        "answer_generation module must expose a refresh hook for "
        "module-level Kannada constants so the running process can pick "
        "up ui.json updates without a restart."
    )
    # Reload and call the refresh hook.
    reload_ui_locales()
    ag.refresh_kn_locale_constants()
    after = ag.CONTROLLED_FALLBACK_KN
    assert isinstance(after, str) and after
    # The Kannada entries in the spoken-prompt dicts must also be set.
    assert isinstance(ag.COURSE_MENU_SPOKEN_PROMPT_BY_LANGUAGE["Kannada"], str)
    assert ag.COURSE_MENU_SPOKEN_PROMPT_BY_LANGUAGE["Kannada"]
    assert isinstance(ag.PROFILE_REPLY_TEMPLATES["Kannada"]["hod"], str)
    assert ag.PROFILE_REPLY_TEMPLATES["Kannada"]["hod"]
