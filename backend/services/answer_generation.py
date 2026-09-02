"""
CLARA answer generation: intent detection, context selection, two-phase overview generation,
structured prompt building, and Digital Book page building with TTS for overview.
"""

import hashlib
import json
import logging
import re
import copy
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, List

from backend.utils.cache import TTLRUCache

# Digital Book: 5 content sections (Closing Assurance excluded). Same order as prompt.
DIGITAL_BOOK_SECTION_TITLES = [
    "About the Institution",
    "Academic Programs",
    "Quality & Infrastructure",
    "Achievements & Recognition",
    "Placement & Career Support",
]
DIGITAL_BOOK_COVER_TITLE = "Cover"
DIGITAL_BOOK_COVER_TEXT = "Institution Overview"

from backend.config.settings import RAG_MAX_TOKENS, RAG_TOP_K
from backend.core.rag import get_relevant_context
from backend.clients.provider_clients import get_groq_client
from backend.services.ui_localization import ui_text

logger = logging.getLogger(__name__)

_LOCALES_DIR = Path(__file__).resolve().parent.parent / "data" / "locales"
_locale_data_cache: dict[str, dict[str, Any]] = {}
_locale_data_mtime: dict[str, int] = {}

# Display name -> file id. Mirrors the same set accepted by
# ui_localization.ui_language_key. Callers that pass a display name
# (e.g. session["language"] == "Kannada") get the correct file id.
_DISPLAY_NAME_TO_FILE_ID = {
    "english": "en",
    "kannada": "kn",
    "hindi": "hi",
    "tamil": "ta",
    "telugu": "te",
    "malayalam": "ml",
}

# Same order as frontend DEPARTMENT_JSON_KEY_ORDER (kiosk HOD / summary cards).
DEPARTMENT_JSON_KEY_ORDER: tuple[str, ...] = (
    "cse",
    "ise",
    "cse_aiml",
    "cse_ds",
    "cse_cysec",
    "cse_bs",
    "ece",
    "civil",
    "mechanical",
    "mba",
    "basic_sciences",
)

# Maps detect_department_name() canonical labels to locale JSON department keys.
_CANONICAL_DEPARTMENT_TO_JSON_KEY: dict[str, str] = {
    "CSE": "cse",
    "ISE": "ise",
    "CSE (AI & ML)": "cse_aiml",
    "CSE (Data Science)": "cse_ds",
    "CSE (Cyber Security)": "cse_cysec",
    "CSE (Business Systems)": "cse_bs",
    "ECE": "ece",
    "Civil": "civil",
    "Mechanical": "mechanical",
    "MBA": "mba",
    "Basic Sciences": "basic_sciences",
}


def locale_file_id_for_lang_key(lang_key: str | None) -> str:
    """Basename (no .json) of the single college-data file: backend/data/locales/<id>.json.

    Accepted inputs (case-insensitive, locale-suffix tolerant):
      - short codes: en, kn, hi, ta, te, ml
      - locale-suffix variants: kn-IN, kn_IN, en-US
      - display names: English, Kannada, Hindi, Tamil, Telugu, Malayalam
      - case-insensitive variants: KN, kannada, KANNADA
    Unrecognized keys fall back to "en" with a logged warning.
    """
    if lang_key is None:
        return "en"
    lk = str(lang_key).strip()
    if not lk:
        return "en"
    if "-" in lk:
        lk = lk.split("-", 1)[0]
    if "_" in lk:
        lk = lk.split("_", 1)[0]
    low = lk.lower()
    mapping = {
        "en": "en",
        "hi": "hi",
        "kn": "kn",
        "ta": "ta",
        "te": "te",
        "ml": "ml",
    }
    if low in mapping:
        return mapping[low]
    if low in _DISPLAY_NAME_TO_FILE_ID:
        return _DISPLAY_NAME_TO_FILE_ID[low]
    logger.warning(
        "locale_file_id_for_lang_key: unknown language identifier %r; "
        "falling back to 'en'",
        lang_key,
    )
    return "en"


def load_locale_data_for_lang_key(lang_key: str | None) -> dict[str, Any]:
    """Load parsed locale JSON for the session language (cached, defensive).

    Contract:
      - The returned dict is a fresh deep copy on every call, so
        callers may mutate it freely without affecting the cache or
        other consumers.
      - If the on-disk file has been modified since the last load, the
        cache is invalidated automatically and the new content is
        loaded. Use reload_locale_data_for_lang_key() to force a
        refresh from outside the loader.
      - An unknown language identifier logs a warning and returns the
        English locale data (the existing passthrough contract for
        unknown languages is preserved). Callers that require strict
        kn-only behavior should call is_valid_locale_file_id() first.
    """
    locale = locale_file_id_for_lang_key(lang_key)
    path = _LOCALES_DIR / f"{locale}.json"
    try:
        mtime = path.stat().st_mtime_ns
    except FileNotFoundError:
        logger.warning("Narrator: locale file missing: %s", path)
        _locale_data_cache.pop(locale, None)
        return {}
    cached_mtime = _locale_data_mtime.get(locale)
    if locale in _locale_data_cache and cached_mtime == mtime:
        # Defensive copy: callers must not see the cached reference.
        return copy.deepcopy(_locale_data_cache[locale])
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            _locale_data_cache.pop(locale, None)
            _locale_data_mtime.pop(locale, None)
            return {}
        _locale_data_cache[locale] = data
        _locale_data_mtime[locale] = mtime
        return copy.deepcopy(data)
    except Exception as exc:
        logger.warning("Narrator: could not load %s: %s", path, exc)
        _locale_data_cache.pop(locale, None)
        _locale_data_mtime.pop(locale, None)
        return {}


def reload_locale_data_for_lang_key(lang_key: str | None) -> dict[str, Any]:
    """Invalidate the locale cache for the given language and re-read the file.

    Use this when backend/data/locales/<id>.json has been updated and
    the running process must pick up the new content without a
    restart. Equivalent to clearing the cache and calling
    load_locale_data_for_lang_key() again.
    """
    locale = locale_file_id_for_lang_key(lang_key)
    _locale_data_cache.pop(locale, None)
    _locale_data_mtime.pop(locale, None)
    return load_locale_data_for_lang_key(lang_key)


def is_valid_locale_file_id(lang_key: str | None) -> bool:
    """Return True iff the identifier normalizes to a known locale file id."""
    if lang_key is None:
        return False
    raw = str(lang_key).strip()
    if not raw:
        return False
    if "-" in raw:
        raw = raw.split("-", 1)[0]
    if "_" in raw:
        raw = raw.split("_", 1)[0]
    low = raw.lower()
    return low in {"en", "kn", "hi", "ta", "te", "ml"} or low in _DISPLAY_NAME_TO_FILE_ID


def refresh_kn_locale_constants() -> None:
    """Re-evaluate module-level Kannada constants that were bound at import.

    The module binds values like CONTROLLED_FALLBACK_KN and the
    "Kannada" entries in *_BY_LANGUAGE dicts to ui_text("kn", ...)
    at import time. If ui.json is updated, those bindings become
    stale. This function re-evaluates them against the current
    ui.json content.

    The dicts are mutated in place so any reference that has been
    already published (e.g. a global registry) sees the fresh value
    on its next access.
    """
    global CONTROLLED_FALLBACK_KN, FALLBACK_MSG_KN
    # Force a reload of the ui.json cache so the freshest file is read.
    try:
        from backend.services.ui_localization import reload_ui_locales
        reload_ui_locales()
    except Exception:
        pass
    CONTROLLED_FALLBACK_KN = ui_text(
        "kn", "availability.missing_source"
    ).replace("\n", " ")
    FALLBACK_MSG_KN = ui_text("kn", "error.backend")
    COURSE_MENU_SPOKEN_PROMPT_BY_LANGUAGE["Kannada"] = ui_text(
        "kn", "action.course_menu"
    )
    BUS_ROUTES_SPOKEN_PROMPT_BY_LANGUAGE["Kannada"] = ui_text(
        "kn", "action.bus_routes"
    )
    UNAVAILABLE_REPLY_BY_LANGUAGE["Kannada"] = ui_text(
        "kn", "availability.missing_source"
    ).replace("\n", " ")
    OFF_TOPIC_REPLY_BY_LANGUAGE["Kannada"] = ui_text(
        "kn", "availability.off_topic"
    )
    PROFILE_REPLY_TEMPLATES["Kannada"]["hod"] = ui_text("kn", "profile.hod")
    PROFILE_REPLY_TEMPLATES["Kannada"]["trustees"] = ui_text(
        "kn", "profile.trustees"
    )
    PROFILE_REPLY_TEMPLATES["Kannada"]["both"] = ui_text(
        "kn", "profile.hod_and_trustees"
    )


def department_label_to_json_key(label: str | None) -> str | None:
    if not label or not isinstance(label, str):
        return None
    stripped = label.strip()
    if stripped in _CANONICAL_DEPARTMENT_TO_JSON_KEY:
        return _CANONICAL_DEPARTMENT_TO_JSON_KEY[stripped]
    low = stripped.lower()
    for canon, jkey in _CANONICAL_DEPARTMENT_TO_JSON_KEY.items():
        if canon.lower() == low:
            return jkey
    return None


def _wants_all_departments_narration(user_text: str) -> bool:
    n = _normalize_text(user_text)
    if not n:
        return False
    return any(
        p in n
        for p in (
            "all department",
            "all departments",
            "every department",
            "each department",
            "list department",
            "list departments",
            "all branches",
            "every branch",
        )
    )


def _hod_slice_for_narrator(dept: Any) -> dict[str, Any]:
    if not isinstance(dept, dict):
        return {}
    out: dict[str, Any] = {}
    # Include both legacy field names AND actual locale-file field names.
    # Locale JSON files use: name, intro, hod_voice, achievements, placement, fees
    # Legacy / alternate names: hod, intake, duration, overview_and_focus
    scalar_keys = (
        "name", "hod", "intake", "duration", "overview_and_focus",
        "intro", "hod_voice", "achievements", "placement", "fees",
    )
    for k in scalar_keys:
        if k in dept and dept[k] is not None:
            v = dept[k]
            if isinstance(v, (list, dict)):
                continue
            out[k] = v
    fl = dept.get("faculty_list")
    if isinstance(fl, list) and fl:
        out["faculty_highlights"] = fl[:8]
    return out


def _role_holders_block(data: dict[str, Any]) -> dict[str, Any]:
    block = data.get("role_holders")
    return block if isinstance(block, dict) else {}


def _role_holders_block_with_en_fallback(data: dict[str, Any]) -> dict[str, Any]:
    primary = _role_holders_block(data)
    if primary:
        return primary
    en_data = load_locale_data_for_lang_key("en")
    return _role_holders_block(en_data)


def _build_hod_rows_from_role_holders(data: dict[str, Any], deps: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    role_holders = _role_holders_block_with_en_fallback(data)
    hod_by_department = role_holders.get("hod_by_department")
    if isinstance(hod_by_department, dict):
        for key in DEPARTMENT_JSON_KEY_ORDER:
            row = hod_by_department.get(key)
            if isinstance(row, dict):
                out[key] = {
                    "department_name": row.get("department_name"),
                    "name": row.get("hod_name"),
                    "title": row.get("hod_title"),
                    "bio": row.get("hod_bio"),
                    "aliases": row.get("aliases"),
                }
    if out:
        return out

    # Legacy fallback from departments[] for older locale files.
    for key in DEPARTMENT_JSON_KEY_ORDER:
        dept = deps.get(key)
        if isinstance(dept, dict):
            out[key] = {
                "department_name": dept.get("name"),
                "name": dept.get("hod"),
                "title": None,
                "bio": dept.get("hod_voice"),
            }
    return out


def build_target_card_payload(
    intent: str,
    *,
    lang_key: str | None,
    detected_department_label: str | None,
    user_text: str,
) -> dict[str, Any] | None:
    """
    Build the exact locale JSON slice the kiosk UI uses for this card intent.
    Returns None if intent is not a narrator intent.
    """
    if not is_narrator_intent(intent):
        return None
    data = load_locale_data_for_lang_key(lang_key)
    if not data:
        return {
            "presentation_type": intent.lower(),
            "locale": locale_file_id_for_lang_key(lang_key),
            "note": "Campus knowledge file unavailable; keep reply very brief and suggest Admission Block.",
        }

    locale_id = locale_file_id_for_lang_key(lang_key)
    deps = data.get("departments")
    if not isinstance(deps, dict):
        deps = {}

    if intent == INTENT_COLLEGE_OVERVIEW:
        return {
            "presentation_type": "college_overview",
            "locale": locale_id,
            "institution_overview": data.get("institution_overview"),
            "leadership": data.get("leadership"),
        }

    if intent == INTENT_DEPARTMENT_OVERVIEW:
        if _wants_all_departments_narration(user_text):
            ordered: dict[str, Any] = {}
            for k in DEPARTMENT_JSON_KEY_ORDER:
                if k in deps and isinstance(deps[k], dict):
                    ordered[k] = _hod_slice_for_narrator(deps[k])
            return {
                "presentation_type": "all_departments_overview",
                "locale": locale_id,
                "departments": ordered,
            }
        jkey = department_label_to_json_key(detected_department_label)
        if not jkey:
            # Align with narration_plan: when no department resolves, show the same all-departments deck.
            ordered_no_key: dict[str, Any] = {}
            for k in DEPARTMENT_JSON_KEY_ORDER:
                if k in deps and isinstance(deps[k], dict):
                    ordered_no_key[k] = _hod_slice_for_narrator(deps[k])
            return {
                "presentation_type": "all_departments_overview",
                "locale": locale_id,
                "departments": ordered_no_key,
            }
        dept = deps.get(jkey)
        return {
            "presentation_type": "single_department_overview",
            "locale": locale_id,
            "department_key": jkey,
            "department": _hod_slice_for_narrator(dept) if isinstance(dept, dict) else {},
        }

    if intent == INTENT_ADMISSIONS:
        return {
            "presentation_type": "admissions_and_fees",
            "locale": locale_id,
            "admissions_and_fees": data.get("admissions_and_fees"),
        }

    if intent == INTENT_PLACEMENTS:
        return {
            "presentation_type": "placements_and_training",
            "locale": locale_id,
            "placements_and_training": data.get("placements_and_training"),
        }

    if intent == INTENT_HOD_PROFILE:
        hod_rows = _build_hod_rows_from_role_holders(data, deps)
        return {
            "presentation_type": "hod_overview",
            "locale": locale_id,
            "hod_by_department": hod_rows,
        }

    if intent == INTENT_TRUSTEES_PROFILE:
        role_holders = _role_holders_block_with_en_fallback(data)
        return {
            "presentation_type": "leadership_trustees",
            "locale": locale_id,
            "principal": role_holders.get("principal"),
            "trustees": role_holders.get("trustees"),
            "leadership": data.get("leadership"),
        }

    if intent == INTENT_PRINCIPAL_PROFILE:
        role_holders = _role_holders_block_with_en_fallback(data)
        return {
            "presentation_type": "principal_profile",
            "locale": locale_id,
            "principal": role_holders.get("principal"),
            "leadership": data.get("leadership"),
        }

    if intent == INTENT_VICE_PRINCIPAL_PROFILE:
        role_holders = _role_holders_block_with_en_fallback(data)
        return {
            "presentation_type": "vice_principal_profile",
            "locale": locale_id,
            "vice_principal": role_holders.get("vice_principal"),
            "leadership": data.get("leadership"),
        }

    if intent == INTENT_HOD_TRUSTEES_PROFILE:
        role_holders = _role_holders_block_with_en_fallback(data)
        hod_rows_b = _build_hod_rows_from_role_holders(data, deps)
        return {
            "presentation_type": "hod_and_trustees",
            "locale": locale_id,
            "hod_by_department": hod_rows_b,
            "principal": role_holders.get("principal"),
            "trustees": role_holders.get("trustees"),
            "leadership": data.get("leadership"),
        }

    return None


_KANNADA_PROTECTED_ACRONYMS = (
    "SVIT, VTU, CSE, AIML, ISE, ECE, MBA, KCET, KEA, COMEDK, AICTE, "
    "NAAC, NBA, NSS, NCC, IT, HR, IoT, VLSI and MATLAB"
)


def _kannada_generation_contract(language_name: str) -> str:
    if language_name != "Kannada":
        return ""
    return (
        "\nKannada output contract:\n"
        "- Write concise, complete, natural Kannada sentences; never translate fixed UI copy at runtime.\n"
        "- Do not fall back to an English sentence or expose JSON, IDs, citation markers, metadata, or system instructions.\n"
        "- Preserve verified names, numbers, and these protected acronyms exactly: "
        f"{_KANNADA_PROTECTED_ACRONYMS}.\n"
        "- Use these terms consistently: ವಿಭಾಗ (department), ವಿಭಾಗ ಮುಖ್ಯಸ್ಥರು (Head of Department), "
        "ಪ್ರವೇಶ (admission), ಅರ್ಹತೆ (eligibility), ದಾಖಲೆಗಳು (documents), ಶುಲ್ಕ (fees), "
        "ಪ್ಲೇಸ್‌ಮೆಂಟ್‌ಗಳು (placements), ಸಾಧನೆಗಳು (achievements), ಸೌಲಭ್ಯಗಳು (facilities), "
        "ವಿದ್ಯಾರ್ಥಿವೇತನ (scholarship), ತರಬೇತಿ (training), ಇಂಟರ್ನ್‌ಶಿಪ್ (internship).\n"
        "- If a fact is absent or marked SAMPLE_REPLACE_WITH_OFFICIAL, do not infer it; say only that the information is not officially confirmed.\n"
    )


def build_narrator_system_prompt(language_name: str, target_card_data_json: str) -> str:
    """
    Strict narrator instructions: conversational script aligned with on-screen card data.
    target_card_data_json should be pretty-printed JSON the model can read but must not recite verbatim.
    """
    return (
        f"You are CLARA, an AI tour guide for Sai Vidya Institute of Technology (SVIT). "
        f"Reply only in {language_name}.\n\n"
        "The visitor is looking at an on-screen visual presentation. "
        "The slides are built from the following structured campus data (TARGET_CARD_DATA). "
        "This is the ONLY source of facts you may use for this turn.\n\n"
        "TARGET_CARD_DATA (JSON):\n"
        f"{target_card_data_json}\n\n"
        "Rules:\n"
        "- Your job is to NARRATE this information naturally, like a human guide—not like a Q&A bot reading a database.\n"
        "- Do NOT read raw JSON keys, field names, snake_case, or bracketed citation tags aloud.\n"
        "- Do NOT say things like 'HOD colon' or list labels; weave facts into full sentences.\n"
        "- Example style: instead of 'HOD: Dr. Smith. Intake: 120', say the department is led by Dr. Smith and takes about a hundred twenty students each year.\n"
        "- Follow the flow of the data: introduce the topic, then walk through the material in the same order a visitor would read the slides "
        "(overview → programmes or labs → outcomes or placements → distinctive strengths → a brief closing).\n"
        "- For multi-slide department or campus presentations, aim for **8 to 16 short sentences** so audio can span the full card deck without "
        "stopping after a single paragraph. Do not end as if the tour is finished while major sections of TARGET_CARD_DATA are still unused.\n"
        "- For very small single-fact cards, keep it to **3 to 5 short sentences**.\n"
        "- Plain text only. No markdown, no bullet points, no numbered lists.\n"
        "- If TARGET_CARD_DATA is empty or missing detail, give one short sentence and suggest visiting the Admission Block or the relevant office.\n"
        + _kannada_generation_contract(language_name)
    )


MULTI_ENTITY_RULE = (
    "If the user asks multiple distinct questions or about multiple distinct entities in a single sentence "
    "(for example, two different departments), you MUST provide a complete answer for ALL of them "
    "based strictly on the provided context."
)
CONCISE_VOICE_RULE = (
    "You are CLARA, a sweet, helpful, and highly direct AI assistant for SVIT. "
    "CRITICAL: Your responses MUST be extremely concise, punchy, and conversational. Maximum 2 to 3 short sentences. "
    "Do NOT output long lists, bullet points, or markdown formatting. "
    "If the user asks for fees or specific details, extract ONLY the exact number/fact from the context and deliver it immediately. "
    "Tone: Warm, direct, and highly impactful."
)

# Department comparison is the one intent where a longer spoken narration is required (TTS + on-screen table).
COMPARISON_VOICE_RULE = (
    "You are CLARA, a warm, clear campus guide for SVIT. "
    "Families see a side-by-side comparison on screen. "
    "Deliver ONE continuous spoken narration for text-to-speech that FULLY covers the comparison. "
    "Do NOT stop after a teaser, a generic opener, or only the first topic — you must cover every section and every program listed below. "
    "Follow the SAME section order as the headings in the facts block. "
    "For EACH section: (1) briefly name the theme in one short phrase, "
    "(2) then for EACH program give ONE smooth sentence that neatly explains what that program's sub-points mean in practice "
    "(paraphrase the ideas; do not read bullet symbols or labels robotically). "
    "Use flowing sentences suitable for listening aloud. Plain text only — no markdown, no headings syntax, no bullet characters, no emojis. "
    "Do NOT invent salaries, rankings, placement packages, or statistics that are not in the facts. "
    "If session hints mention recommend_focus, reflect that gently only when the facts support it; otherwise stay balanced. "
    "Aim for roughly 220–480 spoken words so nothing important is left unsaid."
)


def rag_language_enforcement_directive(language_name: str) -> str:
    """Strict single-language reply when using RAG context (voice/chat, non-card narrator)."""
    return (
        f"CRITICAL: You MUST answer the user's query entirely in {language_name}. "
        f"Use the provided context, which is already translated into {language_name}, to form your answer. "
        "Do not mix languages unless citing a specific technical English term like 'CSE' or 'KCET'."
        + _kannada_generation_contract(language_name)
    )


def multilingual_rag_reply_directive(language_name: str) -> str:
    """When retrieval used English chunks but the session speaks another language."""
    return (
        f"Answer this query naturally in conversational {language_name}. "
        "The college reference below may be English, or a mix of English retrieval and "
        f"{language_name} locale facts. Use it only for verified facts and respond entirely "
        f"in {language_name}. Do not mix languages except for standard abbreviations like CSE or KCET."
        + _kannada_generation_contract(language_name)
    )


def generated_reply_is_safe_for_language(text: str | None, language_key: str) -> bool:
    """Fail closed on raw metadata, placeholders, or whole-sentence English fallback."""
    value = str(text or "").strip()
    if not value:
        return False
    lowered = value.lower()
    if any(
        marker in lowered
        for marker in (
            "sample_replace_with_official",
            "[cite:",
            "[source:",
            "[citation:",
            "unit_id",
            "unitid",
            "system prompt",
            "```",
        )
    ):
        return False
    if "{" in value or "}" in value:
        return False
    if (value.startswith("{") and value.endswith("}")) or (
        value.startswith("[") and value.endswith("]")
    ):
        return False
    if language_key == "kn":
        return any("\u0c80" <= char <= "\u0cff" for char in value)
    return True


INTENT_COLLEGE_OVERVIEW = "COLLEGE_OVERVIEW"
INTENT_COURSE_MENU = "COURSE_MENU"
INTENT_DEPARTMENT_OVERVIEW = "DEPARTMENT_OVERVIEW"
INTENT_ADMISSIONS = "ADMISSIONS"
INTENT_PLACEMENTS = "PLACEMENTS"
INTENT_HOD_PROFILE = "HOD_PROFILE"
INTENT_TRUSTEES_PROFILE = "TRUSTEES_PROFILE"
INTENT_HOD_TRUSTEES_PROFILE = "HOD_TRUSTEES_PROFILE"
INTENT_DEPARTMENT_FEES = "DEPARTMENT_FEES"
INTENT_DOCUMENTS = "DOCUMENTS"
INTENT_BUS_ROUTES = "BUS_ROUTES"
INTENT_DEPARTMENT_COMPARISON = "DEPARTMENT_COMPARISON"
INTENT_PRINCIPAL_PROFILE = "PRINCIPAL_PROFILE"
INTENT_VICE_PRINCIPAL_PROFILE = "VICE_PRINCIPAL_PROFILE"
# Backward-compatible alias for legacy imports.
INTENT_FEES = INTENT_DEPARTMENT_FEES
INTENT_NORMAL_QUERY = "NORMAL_QUERY"
INTENT_OFF_TOPIC = "OFF_TOPIC"

NARRATOR_INTENTS: frozenset[str] = frozenset(
    {
        INTENT_COLLEGE_OVERVIEW,
        INTENT_DEPARTMENT_OVERVIEW,
        INTENT_ADMISSIONS,
        INTENT_PLACEMENTS,
        INTENT_HOD_PROFILE,
        INTENT_TRUSTEES_PROFILE,
        INTENT_HOD_TRUSTEES_PROFILE,
        INTENT_PRINCIPAL_PROFILE,
        INTENT_VICE_PRINCIPAL_PROFILE,
    }
)


def is_narrator_intent(intent: str) -> bool:
    """True when the voice turn should use presentation narrator mode (locale JSON only, no RAG)."""
    return intent in NARRATOR_INTENTS


# Structured (JSON-sourced) intents: English locale slices only — no full-locale dump to the LLM.
STRUCTURED_INTENTS: frozenset[str] = NARRATOR_INTENTS

# Open-ended retrieval: small context for latency.
RAG_PIPELINE_TOP_K = 4
RAG_PIPELINE_MAX_TOKENS = 1000

CONTROLLED_FALLBACK_EN = "I'm sorry, I don't have that information right now."
CONTROLLED_FALLBACK_KN = ui_text("kn", "availability.missing_source").replace("\n", " ")
FALLBACK_MSG = "I'm sorry, I couldn't process your request right now."
FALLBACK_MSG_KN = ui_text("kn", "error.backend")

_STRUCTURED_PROMPT_CACHE: TTLRUCache[str, str] = TTLRUCache[str, str](max_size=128, ttl_seconds=600.0)


COURSE_MENU_OPTIONS = [
    "CSE",
    "ISE",
    "CSE (AI & ML)",
    "CSE (Data Science)",
    "CSE (Cyber Security)",
    "CSE (Business Systems)",
    "ECE",
    "Civil",
    "Mechanical",
    "MBA",
    "Basic Sciences",
]

COURSE_MENU_SPOKEN_PROMPT_BY_LANGUAGE: dict[str, str] = {
    "English": "Here are the departments available at our college. Please select one.",
    "Kannada": ui_text("kn", "action.course_menu"),
    "Hindi": "हमारे कॉलेज में उपलब्ध विभाग यहां हैं। कृपया एक चुनें।",
    "Tamil": "எங்கள் கல்லூரியில் உள்ள துறைகள் இங்கே உள்ளன. தயவுசெய்து ஒன்றைத் தேர்வு செய்யுங்கள்.",
    "Telugu": "మా కాలేజీలో అందుబాటులో ఉన్న విభాగాలు ఇవి. దయచేసి ఒకదాన్ని ఎంచుకోండి.",
    "Malayalam": "ഞങ്ങളുടെ കോളേജിലെ ലഭ്യമായ വിഭാഗങ്ങൾ ഇതാ. ദയവായി ഒന്ന് തിരഞ്ഞെടുക്കൂ.",
}

BUS_ROUTES_SPOKEN_PROMPT_BY_LANGUAGE: dict[str, str] = {
    "English": "Here are our college bus routes. Select a route to see pickup stops and timings.",
    "Kannada": ui_text("kn", "action.bus_routes"),
    "Hindi": "यहाँ कॉलेज बस के रूट दिखा रही हूँ। स्टॉप और समय देखने के लिए एक रूट चुनें।",
    "Tamil": "கல்லூரி பேருந்து வழிகளைக் காட்டுகிறேன். நிறுத்தங்கள் மற்றும் நேரத்திற்கு ஒரு வழியைத் தேர்வு செய்யவும்.",
    "Telugu": "కాలేజీ బస్ రూట్లను చూపిస్తున్నాను. స్టాప్లు మరియు సమయాల కోసం ఒక రూట్‌ను ఎంచుకోండి.",
    "Malayalam": "കോളേജ് ബസ് റൂട്ടുകൾ കാണിക്കുന്നു. നിർത്തലിടങ്ങളും സമയവും കാണാൻ ഒരു റൂട്ട് തിരഞ്ഞെടുക്കൂ.",
}

# Minimum similarity for a fuzzy keyword hit to claim an intent.
# At the old 0.70, unrelated words stole card surfaces:
#   "france"      vs "branches"  = 0.714 → COURSE_MENU
#   "do students" vs "documents" = 0.737 → DOCUMENTS
# 0.88 still absorbs real ASR/typo variants ("documnts", "coures", "branchs").
_INTENT_FUZZY_MIN = 0.88

SUPPORTED_LANGUAGES = ("English", "Kannada", "Hindi", "Tamil", "Telugu", "Malayalam")
UNAVAILABLE_REPLY_BY_LANGUAGE: dict[str, str] = {
    "English": "I currently don't have that exact detail. Please contact the admission office for precise information.",
    "Kannada": ui_text("kn", "availability.missing_source").replace("\n", " "),
    "Hindi": ui_text("hi", "availability.missing_source").replace("\n", " "),
    "Tamil": "அந்த துல்லியமான தகவல் இப்போது என்னிடம் இல்லை. சரியான விவரங்களுக்கு அட்மிஷன் அலுவலகத்தை தொடர்புகொள்ளவும்.",
    "Telugu": "ఆ ఖచ్చితమైన వివరాలు ప్రస్తుతం నా వద్ద లేవు. సరైన సమాచారం కోసం దయచేసి అడ్మిషన్ కార్యాలయాన్ని సంప్రదించండి.",
    "Malayalam": "ആ കൃത്യമായ വിശദാംശം ഇപ്പോൾ എനിക്ക് ലഭ്യമല്ല. ദയവായി കൃത്യമായ വിവരങ്ങൾക്ക് അഡ്മിഷൻ ഓഫീസിനെ സമീപിക്കുക.",
}
# FALLBACK copy. Must stay distinct from UNAVAILABLE: "I cannot help with that" is a
# different statement from "I know this topic but not that exact figure".
OFF_TOPIC_REPLY_BY_LANGUAGE: dict[str, str] = {
    "English": "That's outside what I can help with. I can answer questions about SVIT — admissions, departments, fees, placements, faculty and campus facilities.",
    "Kannada": ui_text("kn", "availability.off_topic"),
    "Hindi": ui_text("hi", "availability.off_topic"),
    "Tamil": "அது நான் உதவக்கூடிய வரம்பிற்கு வெளியே உள்ளது. SVIT பற்றி — சேர்க்கை, துறைகள், கட்டணம், பிளேஸ்மென்ட், ஆசிரியர்கள் மற்றும் வளாக வசதிகள் பற்றி பதிலளிக்க முடியும்.",
    "Telugu": "అది నేను సహాయం చేయగల పరిధికి వెలుపల ఉంది. SVIT గురించి — ప్రవేశాలు, విభాగాలు, ఫీజులు, ప్లేస్‌మెంట్, అధ్యాపకులు మరియు క్యాంపస్ సౌకర్యాల గురించి నేను సమాధానం ఇవ్వగలను.",
    "Malayalam": "അത് എനിക്ക് സഹായിക്കാൻ കഴിയുന്ന പരിധിക്ക് പുറത്താണ്. SVIT-നെക്കുറിച്ച് — അഡ്മിഷൻ, ഡിപ്പാർട്ട്മെന്റുകൾ, ഫീസ്, പ്ലേസ്മെന്റ്, അധ്യാപകർ, ക്യാമ്പസ് സൗകര്യങ്ങൾ എന്നിവയെക്കുറിച്ച് എനിക്ക് ഉത്തരം നൽകാം.",
}


def _assert_language_parity(mapping: dict[str, Any], mapping_name: str) -> None:
    missing = [lang for lang in SUPPORTED_LANGUAGES if lang not in mapping]
    if missing:
        raise RuntimeError(f"{mapping_name} missing translations: {', '.join(missing)}")


_assert_language_parity(COURSE_MENU_SPOKEN_PROMPT_BY_LANGUAGE, "COURSE_MENU_SPOKEN_PROMPT_BY_LANGUAGE")
_assert_language_parity(UNAVAILABLE_REPLY_BY_LANGUAGE, "UNAVAILABLE_REPLY_BY_LANGUAGE")
_assert_language_parity(OFF_TOPIC_REPLY_BY_LANGUAGE, "OFF_TOPIC_REPLY_BY_LANGUAGE")

OVERVIEW_CONTEXT_MAX_TOKENS = 1000
OVERVIEW_TOP_K = 10
MODEL_CONTEXT_LIMIT = 128_000
MAX_INPUT_TOKEN_FRACTION = 0.7
GROQ_TEMPERATURE = 0.1
GROQ_TOP_P = 0.3
GROQ_MAX_TOKENS = 400

# Fixed query to retrieve overview-oriented chunks (establishment, affiliation, NAAC, programs, etc.)
OVERVIEW_QUERY = (
    "college overview establishment year affiliation VTU AICTE NAAC NBA location campus "
    "programs CSE AI ML data science ECE MBA achievements rankings infrastructure placement"
)

# Overview intent: English and regional phrases (college overview, brief about college, about SVIT, etc.)
OVERVIEW_KEYWORDS_EN = [
    "college overview",
    "brief about the college",
    "about svit",
    "college information",
    "overview of the college",
    "tell me about the college",
    "tell me about this college",
    "about this college",
    "institute overview",
    "about the college",
    "college brief",
    "overview of college",
    "information about college",
    "about the institute",
    "college details",
    "details about college",
    "tell me about svit college",
    "about your college",
    "college profile",
    "college summary",
    "college intro",
    "overview about college",
]
COLLEGE_ENTITY_KEYWORDS = [
    "college",
    "clg",
    "colg",
    "institute",
    "institution",
    "university",
    "campus",
    "svit",
    "sai vidya",
]

OVERVIEW_CUE_KEYWORDS = [
    "overview",
    "about",
    "information",
    "info",
    "details",
    "detail",
    "brief",
    "summary",
    "profile",
    "introduction",
    "history",
    "background",
    "tell",
    "explain",
    "describe",
    "say",
    "speak",
    "bagge",
    "baare",
    "pattri",
    "pathi",
    "pati",
    "patthi",
    "patti",
    "gurunchi",
    "gurinchi",
    "kurichu",
    "kurich",
    "helu",
    "heli",
    "elu",
    "eli",
    "tilisi",
    "batao",
    "bataye",
    "batayiye",
    "bolo",
    "sollu",
    "sollunga",
    "cholu",
    "chollu",
    "solu",
    "cholunga",
    "sol",
    "solunga",
    "vivara",
    "vivaralu",
    "maahiti",
    "samacharam",
    "cheppu",
    "cheppandi",
    "chepandi",
    "parayu",
    "parayoo",
    "vivaram",
]

COURSE_MENU_KEYWORDS_EN = [
    "what courses are available",
    "what courses do you have",
    "which course is available",
    "which courses are available",
    "which courses",
    "courses available",
    "courses in college",
    "show branches",
    "show courses",
    "list programs",
    "list courses",
    "list of courses",
    "what departments does the college have",
    "what departments are there",
    "what departments",
    "programs available",
    "courses offered",
    "branches available",
    # Kannada / mixed
    "course ide",
    "yava course",
    "course ideya",
    "courses en ide",
    "course ideya svit alli",
    # Hindi
    "course kya hai",
    "kaunse course",
    # Tamil
    "enna course",
    "course iruka",
    # Telugu
    "course enti",
    "course unnaya",
    "college ali yaav courses ide",
    "college alli yaava courses ide",
    "college ali yaav yaav departments aithe",
    "college alli yaava yaava departments ide",
    "yaav departments aithe",
    "yaava departments ide",
]

FEE_QUERY_KEYWORDS = [
    "fee",
    "fees",
    "fees eshtu",
    "fees bagge",
    "fees kitna",
    "fee kya hai",
    "fees evlo",
    "fees entha",
    "fees estu",
    "fee structure",
    "tuition",
    "cost",
    "price",
    "how much",
    "amount",
    "management quota",
    "estu",
    "yestu",
    "eshtu",
    "kitna",
    "evvalavu",
    "entha",
    "ethra",
    "bele",
    "rate",
    "duddu",
    "paise",
    "kaasu",
    "dabbu",
    "karchu",
    "evlo",
    "entha",
    "enu",
    "yaaru",
    "kaun",
    "evaru",
    # Kannada (script + transliteration)
    "ಶುಲ್ಕ",
    "ಶುಲ್ಕಗಳು",
    "ಫೀಸ್",
    "feesu",
    "shulka",
    "shulkagalu",
    # Hindi (script + transliteration)
    "फीस",
    "शुल्क",
    "shulk",
    # Tamil
    "கட்டணம்",
    "கட்டணங்கள்",
    "kattanam",
    # Telugu
    "ఫీజు",
    "ఫీజులు",
    "phiju",
    # Malayalam
    "ഫീസ്",
]

FEES_KEYWORDS = [
    "fees",
    "fee",
    "fee structure",
    "cost",
    "tuition",
    "price",
    # Regional scripts / mixed forms
    "ಶುಲ್ಕ",
    "ಫೀಸ್",
    "फीस",
    "शुल्क",
    "கட்டணம்",
    "ఫీజు",
    "ഫീസ്",
    "feesu",
    "feeu",
]

DEPARTMENT_SYNONYMS: dict[str, list[str]] = {
    "CSE (AI & ML)": [
        "cse ai",
        "cse ai ml",
        "cse (ai & ml)",
        "ai ml",
        "aiml",
        "ai&ml",
        "artificial intelligence",
        "machine learning",
    ],
    "CSE (Data Science)": [
        "cse ds",
        "cse data science",
        "cse (data science)",
        "data science",
        "datascience",
        "daascince",
        "datascince",
        "datscience",
    ],
    "CSE (Cyber Security)": [
        "cse cyber",
        "cse (cyber security)",
        "cyber security",
        "cybersecurity",
    ],
    "CSE (Business Systems)": [
        "cse business",
        "cse (business systems)",
        "business systems",
        "cs business",
    ],
    "CSE": ["cse", "computer science", "computer science engineering"],
    "ISE": ["ise", "information science", "information science engineering"],
    "ECE": ["ece", "electronics", "electronics and communication", "electronics & communication", "electronics communication"],
    "Civil": ["civil", "civil engineering"],
    "Mechanical": ["mechanical", "mechanical engineering", "mech"],
    "MBA": ["mba", "management", "business administration"],
    "Basic Sciences": ["basic sciences", "basic science", "science departments", "science department"],
    "Mathematics": ["mathematics", "maths", "math"],
    "Physics": ["physics"],
    "Chemistry": ["chemistry"],
}


@dataclass(frozen=True)
class QueryFeatures:
    has_department: bool
    department_name: str | None
    is_hod_query: bool
    is_fee_query: bool
    is_course_query: bool
    is_documents_query: bool
    is_bus_routes_query: bool
    is_placement_query: bool
    is_overview_query: bool
    is_comparison_query: bool
    is_comparison_recommendation: bool
    comparison_department_names: tuple[str, ...]


# Mirrors extract_features alias map — used to collect ALL department mentions in order.
_COMPARISON_DEPT_ALIASES: dict[str, list[str]] = {
    "CSE (Data Science)": [
        "cse data science",
        "cse datascience",
        "data science",
        "datascience",
        "dtascience",
        "ds",
    ],
    "CSE (AI & ML)": [
        "cse ai ml",
        "ai ml",
        "aiml",
        "aml",
        "a i m l",
        "artificial intelligence",
    ],
    "CSE (Cyber Security)": [
        "cse cyber security",
        "cyber security",
        "cybersecurity",
        "cyber",
    ],
    "CSE (Business Systems)": [
        "cse business systems",
        "business systems",
    ],
    "ISE": ["information science", "ise"],
    "ECE": ["electronics", "ece"],
    "Civil": ["civil"],
    "Mechanical": ["mechanical", "mech"],
    "MBA": ["mba", "business administration", "business studies"],
    "Basic Sciences": ["basic sciences"],
    "CSE": ["computer science", "computer science engineering", "cse", "csse"],
}


def extract_comparison_department_canonical_labels(text: str | None) -> list[str]:
    """Return ordered unique canonical department labels (e.g. CSE (AI & ML)) mentioned in text."""
    if not text or not isinstance(text, str):
        return []
    n = normalize_user_input(_inject_regional_department_tokens(text))
    joined = f" {n} " if n else ""
    dept_candidates: list[tuple[str, str]] = []
    for dept_name, aliases in _COMPARISON_DEPT_ALIASES.items():
        for alias in aliases:
            dept_candidates.append((alias, dept_name))
    dept_candidates.sort(key=lambda x: len(x[0]), reverse=True)
    hits: list[tuple[int, str]] = []
    for alias, dept_name in dept_candidates:
        a = alias.strip()
        if not a:
            continue
        start = 0
        needle = f" {a} "
        while joined and needle in joined[start:]:
            idx = joined.find(needle, start)
            if idx < 0:
                break
            hits.append((idx, dept_name))
            start = idx + max(len(needle) // 2, 1)

    hits.sort(key=lambda x: x[0])
    out: list[str] = []
    seen: set[str] = set()
    for _, dept in hits:
        if dept not in seen:
            seen.add(dept)
            out.append(dept)
    lone = detect_department_name(text)
    if lone and lone not in seen:
        out.append(lone)
    return out[:3]


def _comparison_intent_substrings_hits(normalized_joined: str) -> bool:
    """Substring cues for comparison / contrast / suitability (Latin + scripts)."""
    n = normalized_joined
    if not n:
        return False
    cues = [
        # English
        "compare",
        "comparison",
        "versus",
        " vs ",
        "difference",
        "differnce",
        "diffrence",
        "differnec",
        "different between",
        "diff between",
        "better than",
        "which is better",
        "which is best",
        # Avoid matching "which courses are available" → use explicit contrast phrasing instead.
        "which course is better",
        "which course is best",
        "which branch is better",
        "which branch is best",
        "what is better",
        "side by side",
        "between ",
        " v ",
        "harder branch",
        "easier branch",
        "easier ",
        "harder ",
        "future scope",
        # " placements " was here and turned every placements question into a
        # department comparison. Comparison needs an explicit contrast cue.
        "placement wise",
        "salary",
        " coding vs ",
        " vs coding",
        " ai vs ",
        "security vs",
        "analytics vs",
        "good for my child",
        "for my child",
        "for my kid",
        "suitability",
        "suitable for",
        "recommend you",
        "which should i",
        "which one should",
        "confused between",
        "help me choose",
        "which stream",
        "compare engineering",
        # Kannada (Romanized + script snippets)
        "hosadu",
        "honadu",
        "compare",
        "difference",
        "vyatyasa",
        "ವ್ಯತ್ಯಾಸ",
        "ಹೋಲಿಕೆ",
        "ಯಾವುದು ಉತ್ತಮ",
        "ಯಾವ ಕೋರ್ಸ್",
        "ಉತ್ತಮ",
        "ನನ್ನ ಮಗುವಿಗೆ",
        "ಯಾವುದು ತಗೆದುಕೊಳ್ಳಬೇಕು",
        # Hindi
        "antar",
        "फर्क",
        "अंतर",
        "तुलना",
        "कौन सा बेहतर",
        "कौन सा अच्छा",
        "मेरे बच्चे",
        "कौन सा कोर्स",
        "अंतर बताओ",
        # Tamil
        "வித்தியாசம்",
        "ஒப்பிடு",
        "எது சிறந்த",
        "என் குழந்தைக்கு",
        "எது சிறந்தது",
        # Telugu
        "తేడా",
        "పోల్చు",
        "ఏది మంచిది",
        "నా పిల్లలకు",
        "ఏ కోర్సు మంచిది",
        # Malayalam
        "വ്യത്യാസം",
        "താരതമ്യം",
        "ഏതാണ് നല്ലത്",
        "എന്റെ കുട്ടിക്ക്",
        "ഏത് കോഴ്സ് നല്ലത്",
        "സ്‌കോപ്പ്",
        "ഭാവി മൂല്യം",
    ]
    return any(c in n for c in cues)


def text_has_department_comparison_cue(text: str | None) -> bool:
    """
    True when user text clearly asks for contrast / comparison between options.
    Used to recover DEPARTMENT_COMPARISON if earlier pipeline steps collapse intent to NORMAL/COURSE_MENU.
    """
    if not text or not isinstance(text, str):
        return False
    s = text.strip()
    if not s:
        return False
    nx = normalize_user_input(s)
    if nx and _comparison_intent_substrings_hits(f" {nx} "):
        return True
    low = s.lower()
    return bool(
        re.search(
            r"\b(differences?|differen[tc]ce|differnce|diffrence|differnec|compares?|comparison|contrasts?|versus)\b",
            low,
        )
        or re.search(r"\bvs\.?\b", low)
        or (re.search(r"\bdiff\b", low) and re.search(r"\bbetween\b", low))
    )


def _comparison_recommendation_cue(normalized_joined: str, raw_lower: str) -> bool:
    n = normalized_joined
    r = raw_lower
    phrases = [
        "best for",
        "which is best",
        "which course is best",
        "which branch is best",
        "recommend a",
        "recommend the",
        "recommend me",
        "should i choose",
        "what would you recommend",
        "career growth",
        "more money",
        "higher package",
        "easy branch",
        "difficult branch",
        "ನನ್ನ ಮಗು",
        "ಮಗುವಿಗೆ",
        "बच्चे के लिए",
        "குழந்தைக்கு",
        "పిల్లలకు",
        "കുട്ടിക്ക്",
    ]
    return any(p in n for p in phrases) or any(p in r for p in phrases)


def _normalize_department_match_text(text: str | None) -> str:
    """Normalize text for deterministic longest-first department matching."""
    n = re.sub(r"\s+", " ", str(text or "").strip().lower())
    if not n:
        return ""
    n = n.replace("data science", "datascience")
    n = re.sub(r"\bdata\s*science\b", "datascience", n)
    n = re.sub(r"\bai\s*&?\s*ml\b", "aiml", n)
    return re.sub(r"\s+", " ", n.strip())


def _normalize_department_synonym(term: str) -> str:
    t = re.sub(r"\s+", " ", str(term or "").strip().lower())
    if not t:
        return ""
    t = t.replace("data science", "datascience")
    t = re.sub(r"\bdata\s*science\b", "datascience", t)
    t = re.sub(r"\bai\s*&?\s*ml\b", "aiml", t)
    return re.sub(r"\s+", " ", t.strip())


def _iter_department_candidates_longest_first() -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for dept, aliases in DEPARTMENT_SYNONYMS.items():
        for alias in aliases:
            norm_alias = _normalize_department_synonym(alias)
            if not norm_alias:
                continue
            item = (norm_alias, dept)
            if item in seen:
                continue
            seen.add(item)
            candidates.append(item)
    candidates.sort(key=lambda x: len(x[0]), reverse=True)
    return candidates


_DEPARTMENT_CANDIDATES_LONGEST_FIRST = _iter_department_candidates_longest_first()

HOD_PROFILE_KEYWORDS = [
    "hod",
    "hods",
    "hos",
    "h o d",
    "h.o.d",
    "hod name",
    "name of hod",
    "who is hod",
    "who is the hod",
    "hod of",
    "department head",
    "dept head",
    "head of",
    "head of department",
    "heads of department",
    "heads of the department",
    "yaaru",
    "kaun",
    "evaru",
    # Exact HOD role-title phrases already shipped in authoritative locale data.
    "ವಿಭಾಗದ ಮುಖ್ಯಸ್ಥರು",
    "विभागाध्यक्ष",
    "துறைத் தலைவர்",
    "విభాగం అధిపతి",
    "വിഭാഗത്തിന്റെ മേധാവി",
]

TRUSTEES_PROFILE_KEYWORDS = [
    "trustee",
    "trustees",
    "trusty",
    "trusties",
    "trustee name",
    "trustees name",
    "who are trustees",
    "who is trustee",
    "founder",
    "founders",
    "founder names",
    "management",
    "board",
    "chairman",
    "president",
    "board of trustees",
    "founder trustee",
    "founder trustees",
]

BOTH_PROFILE_KEYWORDS = [
    "both",
    "all of them",
    "two of them",
    "together",
    "ibbaru",
    "eradu",
    "dono",
    "iruvarum",
    "iddaru",
    "rendu",
    "randum",
]

PROFILE_GENERIC_KEYWORDS = [
    "profile",
    "profiles",
    "details",
    "information",
    "bagge",
    "baare",
    "pattri",
    "gurunchi",
    "kurichu",
    "vivara",
    "maahiti",
]

# Match before generic "principal" word checks (covers "vice principal", etc.).
VICE_PRINCIPAL_PROFILE_KEYWORDS = [
    "vice principal",
    "vice-principal",
    "associate principal",
    "deputy principal",
    "ಉಪ ಪ್ರಾಂಶುಪಾಲರು",
]

# Principal leadership queries (explicit phrases + multilingual snippets from regression tests).
PRINCIPAL_PROFILE_KEYWORDS = [
    "who is the principal",
    "principal details",
    "who runs this college",
    "college head",
    "principal of",
    "tell me about the principal",
    "who is the principle",
    "principal of svit",
    "ಪ್ರಿನ್ಸಿಪಾಲ್ ತಿಳಿಸಿ",
    "കോളേജിന് പ്രിൻസിപ്പൽ ആർ",
]


def normalized_text_for_executive_keyword_scan(text: str | None) -> str:
    """Normalize free text for deterministic executive-profile keyword scans (multilingual-safe)."""
    if not text or not isinstance(text, str):
        return ""
    return re.sub(r"\s+", " ", str(text).strip()).lower()


def maybe_override_intent_with_executive_profile(base_intent: str, raw_text: str | None) -> str:
    """If executive cues are present in user text, return the sharper profile intent."""
    scanned = normalized_text_for_executive_keyword_scan(raw_text)
    detected = _detect_profile_intent(scanned)
    if detected:
        return detected
    return base_intent


def _principal_word_intent_positive(normalized: str) -> bool:
    """English STT slips: principle/principal — never match when vice-principal wording won."""
    if not normalized:
        return False
    if _matches_any_phrase(normalized, VICE_PRINCIPAL_PROFILE_KEYWORDS):
        return False
    if re.search(r"\bprincipal\b", normalized):
        return True
    if re.search(r"\bprinciple\b", normalized):
        return True
    return False


def _default_profile_names() -> tuple[str, list[str]]:
    return (
        "Dr. Shashikumar D R",
        [
            "Prof. M. R. Holla",
            "Dr. Y. Jayasimha",
            "Prof. R C Shanmukhaswamy",
            "Dr. A. M. Padma Reddy",
        ],
    )


def _profile_names_from_en_locale() -> tuple[str, list[str]]:
    data = load_locale_data_for_lang_key("en")
    role_holders = _role_holders_block(data)
    hod_by_department = role_holders.get("hod_by_department")
    default_hod, default_trustees = _default_profile_names()
    if isinstance(hod_by_department, dict):
        cse = hod_by_department.get("cse")
        if isinstance(cse, dict):
            hod_name = str(cse.get("hod_name") or "").strip()
            if hod_name:
                default_hod = hod_name
    trustees = role_holders.get("trustees")
    if isinstance(trustees, list):
        names = [str(item.get("name") or "").strip() for item in trustees if isinstance(item, dict)]
        names = [n for n in names if n]
        if names:
            default_trustees = names
    return default_hod, default_trustees

PROFILE_REPLY_TEMPLATES: dict[str, dict[str, str]] = {
    "English": {
        "hod": "Sure. HOD name: {hod}.",
        "trustees": "Sure. Trustee names: {trustees}.",
        "both": "Sure. HOD: {hod}. Trustees: {trustees}.",
    },
    "Kannada": {
        "hod": ui_text("kn", "profile.hod"),
        "trustees": ui_text("kn", "profile.trustees"),
        "both": ui_text("kn", "profile.hod_and_trustees"),
    },
    "Hindi": {
        "hod": "ज़रूर। HOD का नाम: {hod}।",
        "trustees": "ज़रूर। ट्रस्टी के नाम: {trustees}।",
        "both": "ज़रूर। HOD: {hod}। ट्रस्टी: {trustees}।",
    },
    "Tamil": {
        "hod": "நிச்சயம். HOD பெயர்: {hod}.",
        "trustees": "நிச்சயம். அறங்காவலர் பெயர்கள்: {trustees}.",
        "both": "நிச்சயம். HOD: {hod}. அறங்காவலர்கள்: {trustees}.",
    },
    "Telugu": {
        "hod": "తప్పకుండా. HOD పేరు: {hod}.",
        "trustees": "తప్పకుండా. ట్రస్టీల పేర్లు: {trustees}.",
        "both": "తప్పకుండా. HOD: {hod}. ట్రస్టీలు: {trustees}.",
    },
    "Malayalam": {
        "hod": "തീർച്ചയായും. HOD പേര്: {hod}.",
        "trustees": "തീർച്ചയായും. ട്രസ്റ്റിമാരുടെ പേരുകൾ: {trustees}.",
        "both": "തീർച്ചയായും. HOD: {hod}. ട്രസ്റ്റിമാർ: {trustees}.",
    },
}


def _contains_phrase(normalized: str, phrase: str) -> bool:
    if not normalized or not phrase:
        return False
    p = phrase.strip().lower()
    if not p:
        return False
    # For non-ASCII phrases, substring matching is more reliable than \b boundaries.
    if not all(ord(ch) < 128 for ch in p):
        return p in normalized
    # Word-boundary matching avoids false positives like "hoodies" -> "hod".
    return bool(re.search(rf"\b{re.escape(p)}\b", normalized))


def _matches_any_phrase(normalized: str, phrases: list[str]) -> bool:
    return any(_contains_phrase(normalized, p) for p in phrases)


def _detect_profile_intent(normalized: str) -> str | None:
    if not normalized:
        return None
    # Fee queries should not be re-routed to profile cards.
    if any(_contains_phrase(normalized, k) for k in FEE_QUERY_KEYWORDS):
        return None
    if _matches_any_phrase(normalized, VICE_PRINCIPAL_PROFILE_KEYWORDS):
        return INTENT_VICE_PRINCIPAL_PROFILE
    if _matches_any_phrase(normalized, PRINCIPAL_PROFILE_KEYWORDS) or _principal_word_intent_positive(normalized):
        return INTENT_PRINCIPAL_PROFILE
    has_hod = _matches_any_phrase(normalized, HOD_PROFILE_KEYWORDS)
    has_trustees = _matches_any_phrase(normalized, TRUSTEES_PROFILE_KEYWORDS)
    # Common STT/typing slip: "trusted" instead of "trustees".
    if not has_trustees and _contains_phrase(normalized, "trusted"):
        if has_hod or _contains_phrase(normalized, "profile") or _contains_phrase(normalized, "profiles"):
            has_trustees = True

    if (
        (not has_hod and not has_trustees)
        and _matches_any_phrase(normalized, BOTH_PROFILE_KEYWORDS)
        and _matches_any_phrase(normalized, PROFILE_GENERIC_KEYWORDS)
    ):
        return INTENT_HOD_TRUSTEES_PROFILE

    if has_hod and has_trustees:
        return INTENT_HOD_TRUSTEES_PROFILE
    if has_hod:
        return INTENT_HOD_PROFILE
    if has_trustees:
        return INTENT_TRUSTEES_PROFILE
    return None


def get_unavailable_reply(language: str | None) -> str:
    if not language:
        return UNAVAILABLE_REPLY_BY_LANGUAGE["English"]
    return UNAVAILABLE_REPLY_BY_LANGUAGE.get(language, UNAVAILABLE_REPLY_BY_LANGUAGE["English"])


def get_off_topic_reply(language: str | None) -> str:
    if not language:
        return OFF_TOPIC_REPLY_BY_LANGUAGE["English"]
    return OFF_TOPIC_REPLY_BY_LANGUAGE.get(language, OFF_TOPIC_REPLY_BY_LANGUAGE["English"])


def build_receptionist_answer_system_prompt(
    language: str,
    unavailable_reply: str,
    off_topic_reply: str,
) -> str:
    """Groq system prompt for ResponseMode.ANSWER institutional turns."""
    kannada_contract = (
        " Write grammatically natural Kannada. Use honorific ಅವರು for people. "
        "Do not reply in English. Do not translate an English paragraph word-for-word. "
        "Keep official names, department codes, and CLARA in their original form."
        if language == "Kannada"
        else ""
    )
    return (
        f"You are CLARA, a warm and professional campus receptionist for "
        f"Sai Vidya Institute of Technology (SVIT). "
        "You understand English, Kannada, Hindi, Tamil, Telugu, and Malayalam equally — "
        "native script, romanized, and English code-switch. "
        f"Reply in {language}. If the visitor mixed English with {language}, a natural "
        f"code-switched {language} reply is allowed for campus English words (CSE, lab, HOD). "
        "Do not answer in English merely because some reference text is English. "
        "Do not write a longer regional-language answer than you would in English. "
        "Maximum 2 to 4 short sentences in every language. Plain text only — no markdown or bullet lists. "
        f"{kannada_contract}"
        "The visitor asked an institutional question about SVIT — faculty quality, campus life, "
        "facilities, culture, placements, internships, hackathons, or what makes the college special. "
        "Answer naturally as a helpful receptionist. Use the college reference below; you may "
        "synthesize a helpful overview from related facts (faculty profiles, department missions, "
        "infrastructure, achievements) even when the exact wording is not quoted. "
        "Do not invent specific numbers, dates, rankings, or personal names absent from the reference. "
        f"Use the unavailable sentence ONLY when the user needs a precise figure or fact that is "
        f"completely absent from the reference: {unavailable_reply}. "
        f"If the question is unrelated to SVIT or college life, say exactly: {off_topic_reply}"
    )


def get_profile_direct_reply(intent: str, language: str | None = None) -> str | None:
    lang = language if language in SUPPORTED_LANGUAGES else "English"
    templates = PROFILE_REPLY_TEMPLATES.get(lang, PROFILE_REPLY_TEMPLATES["English"])
    hod_name, trustee_names = _profile_names_from_en_locale()
    trustees_joined = ", ".join(trustee_names)
    if intent == INTENT_HOD_PROFILE:
        return templates["hod"].format(hod=hod_name, trustees=trustees_joined)
    if intent == INTENT_TRUSTEES_PROFILE:
        return templates["trustees"].format(hod=hod_name, trustees=trustees_joined)
    if intent == INTENT_HOD_TRUSTEES_PROFILE:
        return templates["both"].format(hod=hod_name, trustees=trustees_joined)
    return None


def get_course_menu_options() -> list[str]:
    return list(COURSE_MENU_OPTIONS)


def get_course_menu_spoken_prompt(language: str | None) -> str:
    if not language:
        return COURSE_MENU_SPOKEN_PROMPT_BY_LANGUAGE["English"]
    return COURSE_MENU_SPOKEN_PROMPT_BY_LANGUAGE.get(language, COURSE_MENU_SPOKEN_PROMPT_BY_LANGUAGE["English"])


def get_bus_routes_spoken_prompt(language: str | None) -> str:
    if not language:
        return BUS_ROUTES_SPOKEN_PROMPT_BY_LANGUAGE["English"]
    return BUS_ROUTES_SPOKEN_PROMPT_BY_LANGUAGE.get(
        language,
        BUS_ROUTES_SPOKEN_PROMPT_BY_LANGUAGE["English"],
    )


def detect_department_name(text: str | None) -> str | None:
    normalized = _normalize_department_match_text(text)
    return _detect_department(normalized)


def _detect_department(normalized: str) -> str | None:
    if not normalized:
        return None
    n = _normalize_department_match_text(normalized)
    if not n:
        return None
    for alias, dept in _DEPARTMENT_CANDIDATES_LONGEST_FIRST:
        if _contains_phrase(n, alias):
            return dept
    return None


def extract_features(query_en: str, department_hint: str | None = None) -> QueryFeatures:
    """
    Pure, deterministic feature extraction. No intent decisions here.
    """
    raw = str(query_en or "")
    lowered = raw.lower()
    # Remove common punctuation without stripping non-Latin script glyphs.
    cleaned = re.sub(r"[.,!?;:'\"()\[\]{}<>|/\\@#$%^&*_+=~`-]", " ", lowered)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    filler_words = {
        # English
        "what",
        "tell",
        "give",
        "about",
        "please",
        # Kannada
        "bagge",
        "helu",
        "tilsi",
        "enu",
        "yenu",
        # Hindi
        "ke",
        "ka",
        "hai",
        "kya",
        # Tamil
        "pathi",
        "solu",
        "enna",
        # Telugu
        "gurinchi",
        "cheppu",
        "enti",
        # Malayalam
        "kurich",
        "parayu",
        "entha",
    }

    raw_tokens = [tok for tok in cleaned.split(" ") if tok]
    tokens = [tok for tok in raw_tokens if tok not in filler_words]
    normalized = " ".join(tokens)

    def _sim(a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()

    def _fuzzy_match(word: str, keyword: str) -> bool:
        w = (word or "").strip()
        k = (keyword or "").strip()
        if not w or not k:
            return False
        if w == k:
            return True
        # Short department abbreviations ("ise", "ece", "cse"): token fuzzy match otherwise
        # false-positives on stopwords ("is" → "ise" at ratio 0.8).
        if len(k) <= 4:
            return False
        return _sim(w, k) > 0.7

    def _any_token_fuzzy_match(word_tokens: list[str], keywords: list[str]) -> bool:
        for tok in word_tokens:
            for kw in keywords:
                if _fuzzy_match(tok, kw):
                    return True
        return False

    def _any_hod_token_fuzzy_match(word_tokens: list[str], keywords: list[str]) -> bool:
        for tok in word_tokens:
            for kw in keywords:
                t = (tok or "").strip()
                k = (kw or "").strip()
                if not t or not k:
                    continue
                if t == k:
                    return True
                # Avoid aggressive false positives like "kaunse" -> "kaun".
                if len(k) <= 4:
                    continue
                if SequenceMatcher(None, t, k).ratio() > 0.82:
                    return True
        return False

    def _build_ngrams(word_tokens: list[str], max_n: int = 3) -> list[str]:
        out: list[str] = []
        if not word_tokens:
            return out
        for n in range(1, max_n + 1):
            for i in range(0, len(word_tokens) - n + 1):
                out.append(" ".join(word_tokens[i : i + n]))
        return out

    ngrams = _build_ngrams(tokens, max_n=3)
    token_and_phrase_units = list(dict.fromkeys(tokens + ngrams))

    fees_keywords = [
        "fee",
        "fees",
        "structure",
        "estu",
        "eshtu",
        "evlo",
        "entha",
        "kitna",
        "kattanam",
        "dabbulu",
        "feesu",
        "ಶುಲ್ಕ",
        "फीस",
        "கட்டணம்",
        "ఫీజు",
        "ഫീസ്",
    ]
    hod_keywords = [
        "hod",
        "hods",
        "head",
        "heads",
        "yaaru",
        "kaun",
        "yaar",
        "evaru",
        "aaranu",
        # Exact locale-backed native HOD phrases; deliberately no broad single-word
        # aliases such as generic "head" translations.
        "ವಿಭಾಗದ ಮುಖ್ಯಸ್ಥರು",
        "विभागाध्यक्ष",
        "துறைத் தலைவர்",
        "విభాగం అధిపతి",
        "വിഭാഗത്തിന്റെ മേധാവി",
    ]
    course_keywords = [
        "course",
        "courses",
        "program",
        "programs",
        "branch",
        "branches",
        # Omit bare "department(s)" — it matches exploratory lines like “tell me about the data …
        # department”, which must route to DEPARTMENT_OVERVIEW, not course menu (see comparator tests).
        "course enu",
        "courses en ide",
        "course kya",
        "kaunse courses",
        "course enna",
        "course pathi",
        "course enti",
        "courses enti",
        "course entha",
        "course kurich",
    ]
    documents_keywords = [
        "document",
        "documents",
        "documentsrequired",
        "admissiondocuments",
        "documentbagge",
        "documentsbeku",
        "dakhalegalu",
        "documentkyachahiye",
        "documentskaunse",
        "admissionkedocuments",
        "documentsennavenum",
        "documentsenti",
        "documentsentha",
        "documentskurich",
        # common misspellings
        "doccuments",
        "documnts",
        "doucments",
    ]

    dept_aliases: dict[str, list[str]] = {
        "CSE (Data Science)": [
            "cse data science",
            "cse datascience",
            "data science",
            "datascience",
            "dtascience",
            "ds",
        ],
        "CSE (AI & ML)": [
            "cse ai ml",
            "ai ml",
            "aiml",
            "aml",
        ],
        "CSE (Cyber Security)": [
            "cse cyber security",
            "cyber security",
            "cybersecurity",
            "cyber",
        ],
        "CSE (Business Systems)": [
            "cse business systems",
            "business systems",
        ],
        "ISE": ["information science", "ise"],
        "ECE": ["electronics", "ece"],
        "Civil": ["civil"],
        "Mechanical": ["mechanical", "mech"],
        "MBA": ["mba"],
        "Basic Sciences": ["basic sciences"],
        "CSE": ["computer science", "cse"],
    }

    hinted_department = department_label_from_preprocessor(department_hint)

    detected_department: str | None = None
    if hinted_department:
        detected_department = hinted_department
    else:
        # Longest phrase priority first.
        dept_candidates: list[tuple[str, str]] = []
        for dept_name, aliases in dept_aliases.items():
            for alias in aliases:
                dept_candidates.append((alias, dept_name))
        dept_candidates.sort(key=lambda x: len(x[0]), reverse=True)

        joined = f" {normalized} " if normalized else ""
        for alias, dept_name in dept_candidates:
            a = alias.strip()
            if not a:
                continue
            if f" {a} " in joined:
                detected_department = dept_name
                break

        if not detected_department:
            # Token/phrase fuzzy fallback for broken spellings.
            for alias, dept_name in dept_candidates:
                for unit in token_and_phrase_units:
                    if _fuzzy_match(unit, alias):
                        detected_department = dept_name
                        break
                if detected_department:
                    break

        if not detected_department:
            detected_department = _detect_department(normalize_user_input(raw))

    has_department = bool(detected_department)
    is_hod_query = _any_hod_token_fuzzy_match(tokens, hod_keywords)
    is_fee_query = _any_token_fuzzy_match(tokens, fees_keywords)
    def _matches_course_intent(units: list[str], keywords: list[str]) -> bool:
        for unit in units:
            u = (unit or "").strip()
            if not u:
                continue
            for kw in keywords:
                k = (kw or "").strip()
                if not k:
                    continue
                if u == k:
                    return True
                # Token-level fuzzy detection for multilingual mixed/broken input.
                if _sim(u, k) >= _INTENT_FUZZY_MIN:
                    return True
        return False

    def _matches_documents_intent(units: list[str], keywords: list[str]) -> bool:
        compact_units = [re.sub(r"\s+", "", u.strip()) for u in units if u and u.strip()]
        for unit in compact_units:
            for kw in keywords:
                k = re.sub(r"\s+", "", (kw or "").strip())
                if not k:
                    continue
                if unit == k:
                    return True
                if _sim(unit, k) >= _INTENT_FUZZY_MIN:
                    return True
        return False

    is_course_query = _matches_course_intent(token_and_phrase_units, course_keywords)
    # Phrase-level course menu (listings) without relying on the token "department" alone.
    if not is_course_query and _is_course_menu_query(normalized):
        is_course_query = True
    documents_flag = is_documents_query(raw) or _matches_documents_intent(
        token_and_phrase_units, documents_keywords
    )

    nx = normalize_user_input(raw)
    comp_labels = extract_comparison_department_canonical_labels(raw)
    comp_tuple = tuple(comp_labels[:3])
    spaced_nx = f" {nx} " if nx else ""
    is_comp_hit = bool(spaced_nx and _comparison_intent_substrings_hits(spaced_nx))
    is_rec_hit = _comparison_recommendation_cue(spaced_nx, lowered)

    fee_like = is_fee_query or _is_fee_query(normalized)
    # M5.4: naming two departments is not a comparison. "Tell me about CSE and AIML"
    # could equally be two decks or two overviews, so it must clarify rather than be
    # guessed into the comparison cinema. A contrast or recommendation cue is required.
    is_comparison_query = is_comp_hit or is_rec_hit

    is_bus_routes_query = text_has_bus_routes_cue(raw)

    return QueryFeatures(
        has_department=has_department,
        department_name=detected_department,
        is_hod_query=is_hod_query,
        is_fee_query=fee_like,
        is_course_query=is_course_query,
        is_documents_query=documents_flag,
        is_bus_routes_query=is_bus_routes_query,
        is_placement_query=_is_placements_query(normalized),
        is_overview_query=_is_college_overview_query(normalized),
        is_comparison_query=is_comparison_query,
        is_comparison_recommendation=is_rec_hit,
        comparison_department_names=comp_tuple,
    )


def _is_course_menu_query(normalized: str) -> bool:
    if not normalized:
        return False

    # 1) Check exact known phrases
    if any(k in normalized for k in COURSE_MENU_KEYWORDS_EN):
        return True
    if _contains_phrase(normalized, "courses in") or _contains_phrase(normalized, "course in"):
        return True
    if _contains_phrase(normalized, "courses") or _contains_phrase(normalized, "course"):
        return True

    # 2) Course/department entity + list/show cue (Latin script; robust to transliterated speech)
    course_entities = [
        "course",
        "courses",
        "department",
        "departments",
        "branch",
        "branches",
        "program",
        "programs",
        "stream",
        "streams",
    ]
    list_cues = [
        "available",
        "offer",
        "list",
        "show",
        "what",
        "which",
        "how many",
        "yava",
        "yaava",
        "yaav",
        "yav",
        "kaun",
        "kya",
        "enna",
        "emi",
        "emiti",
        "eth",
        "ethokke",
        "kodi",
        "heli",
        "batao",
        "sollu",
        "cheppu",
        "parayu",
        "ide",
        "ideya",
        "aithe",
        "alli",
        "ali",
    ]

    has_course = any(c in normalized for c in course_entities)
    has_list_cue = any(l in normalized for l in list_cues)

    if has_course and has_list_cue:
        return True

    return False


def _is_fee_query(normalized: str) -> bool:
    if not normalized:
        return False
    n = _normalize_text(normalized)
    fee_hit = any(_contains_phrase(n, k) for k in FEES_KEYWORDS) or any(
        _contains_phrase(n, k) for k in FEE_QUERY_KEYWORDS
    )
    if fee_hit:
        return True
    # Extra safety for common ASR misspellings around "fees"
    return bool(re.search(r"\bf(?:e|i){1,2}s\b", n))


EXPLICIT_ADMISSIONS_PHRASES: tuple[str, ...] = (
    "admission",
    "admissions",
    "admit",
    "apply",
    "application",
    "eligibility",
    "entrance",
    "entrance exam",
    "kcet",
    "comedk",
    "kea",
    "counseling",
    "counselling",
    "quota",
    "scholarship",
    "scholarships",
    "how to join",
    "how to get admission",
)


def has_explicit_admissions_cue(text: str) -> bool:
    """Match genuine admissions language, excluding fee-only legacy routing."""
    normalized = _normalize_text(text)
    return any(_contains_phrase(normalized, phrase) for phrase in EXPLICIT_ADMISSIONS_PHRASES)


def _is_admissions_query(normalized: str) -> bool:
    if not normalized:
        return False
    return _is_fee_query(normalized) or has_explicit_admissions_cue(normalized)


def _is_placements_query(normalized: str) -> bool:
    if not normalized:
        return False
    placement_phrases = [
        "placement",
        "placements",
        "campus drive",
        "campus placement",
        "recruiter",
        "recruitment",
        "job",
        "jobs",
        "hiring",
        "package",
        "salary",
        "ctc",
        "internship",
        "internships",
        "training program",
        "mock interview",
        "career",
        "placed",
        "companies visit",
        "tnp",
        "training and placement",
    ]
    return any(_contains_phrase(normalized, p) for p in placement_phrases)


def _is_college_overview_query(normalized: str) -> bool:
    if not normalized:
        return False

    if _matches_any_phrase(normalized, OVERVIEW_KEYWORDS_EN):
        return True

    has_college_entity = _matches_any_phrase(normalized, COLLEGE_ENTITY_KEYWORDS)
    has_overview_cue = _matches_any_phrase(normalized, OVERVIEW_CUE_KEYWORDS)
    return has_college_entity and has_overview_cue


def _normalize_text(text: str | None) -> str:
    """Lowercase, strip, collapse spaces. Safe for None."""
    if text is None or not isinstance(text, str):
        return ""
    return re.sub(r"\s+", " ", text.strip().lower())


def _inject_regional_department_tokens(text: str) -> str:
    """
    Map regional-script spellings of department names to English tokens so
    ``extract_entities`` / ``_detect_department`` can match (e.g. Kannada
    ``ಎ ಎಂ ಎಲ್`` spaced letters for AIML).
    """
    if not text or not isinstance(text, str):
        return ""
    out = text
    # (pattern, replacement) — order matters: longer / more specific first.
    regional: tuple[tuple[str, str], ...] = (
        # Kannada — AIML spelled as letters or words
        (r"ಎ\s*ಎಂ\s*ಎಲ್", " aiml "),
        (r"ಎಎಂಎಲ್", " aiml "),
        (r"ಎ\s*ಎಂ\s*ಎಲ್\s*ಡಿಪಾರ್ಟ್ಮೆಂಟ್", " aiml department "),
        (r"ಡೇಟಾ\s*ಸೈನ್ಸ್", " data science "),
        (r"ಡೇಟಾ\s*ಸಂಖ್ಯೆ", " data science "),
        # Browser/STT commonly separates each Kannada acronym syllable.
        (r"ಸಿ\s*ಎಸ್\s*ಇ", " cse "),
        (r"ಸಿಎಸ್\s*ಇ", " cse "),
        (r"ಸಿಎಸ್ಇ", " cse "),
        (r"ಸೈಬರ್\s*ಸೆಕ್ಯುರಿಟಿ", " cyber security "),
        (r"ಬಿಸಿನೆಸ್\s*ಸಿಸ್ಟಮ್ಸ್", " business systems "),
        (r"ಮಾಹಿತಿ\s*ವಿಜ್ಞಾನ", " information science "),
        (r"ಐಎಸ್ಇ", " ise "),
        (r"ಎಲೆಕ್ಟ್ರಾನಿಕ್ಸ್", " electronics "),
        (r"ಇಸಿಇ", " ece "),
        (r"ಸಿವಿಲ್", " civil "),
        (r"ಮೆಕ್ಯಾನಿಕಲ್", " mechanical "),
        # Tamil — common spellings
        (r"ஏ\s*ஐ\s*எம்\s*எல்", " aiml "),
        (r"டேட்டா\s*சயின்ஸ்", " data science "),
        (r"சைபர்\s*செக்யூரிட்டி", " cyber security "),
        (r"தகவல்\s*அறிவியல்", " information science "),
        (r"எலக்ட்ரானிக்ஸ்", " electronics "),
        # Telugu
        (r"ఎ\s*ఐ\s*ఎం\s*ఎల్", " aiml "),
        (r"డేటా\s*సైన్స్", " data science "),
        (r"సైబర్\s*సెక్యూరిటీ", " cyber security "),
        (r"ఎలక్ట్రానిక్స్", " electronics "),
        # Malayalam
        (r"എ\s*ഐ\s*എം\s*എൽ", " aiml "),
        (r"ഡാറ്റാ\s*സയൻസ്", " data science "),
        (r"സൈബർ\s*സെക്യൂരിറ്റി", " cyber security "),
        (r"ഇലക്ട്രോണിക്സ്", " electronics "),
        # Hindi / Devanagari
        (r"ए\s*आई\s*एम\s*एल", " aiml "),
        (r"एआईएमएल", " aiml "),
        (r"डेटा\s*साइंस", " data science "),
        (r"डाटा\s*साइंस", " data science "),
        # Hindi browser/STT acronym forms. Keep these at the normalization
        # boundary so typed and spoken input enter the same canonical parser.
        (r"ई\s*सी\s*ई", " ece "),
        (r"आई\s*एस\s*ई", " ise "),
        (r"एम\s*बी\s*ए", " mba "),
        (r"ए\s*आई\s*(?:(?:और|एवं)\s*)?एम\s*एल", " aiml "),
        (r"साइबर\s*सुरक्षा", " cyber security "),
        (r"साइबर\s*सिक्योरिटी", " cyber security "),
        (r"बिजनेस\s*सिस्टम्स", " business systems "),
        (r"बिज़नेस\s*सिस्टम्स", " business systems "),
        (r"सूचना\s*विज्ञान", " information science "),
        (r"इलेक्ट्रॉनिक्स", " electronics "),
        (r"सिविल", " civil "),
        (r"मैकेनिकल", " mechanical "),
        (r"सी\s*एस\s*ई", " cse "),
        (r"सीएसई", " cse "),
    )
    for pat, repl in regional:
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    return out


def normalize_query_to_english(text: str) -> str:
    """
    Normalize mixed-language query tokens (Hinglish/Kanglish/Tanglish/etc.) to
    simple English-friendly cues before intent/entity detection.
    """
    if text is None or not isinstance(text, str):
        return ""
    s = text.strip()
    if not s:
        return ""
    # Must run before lowercasing collapses meaning: map regional script → English dept tokens.
    s = _inject_regional_department_tokens(s)
    base = _normalize_text(s)
    if not base:
        return ""

    # Phrase-level conversions first.
    phrase_map: tuple[tuple[str, str], ...] = (
        (r"\bfees\s+enna\b", "fees what"),
    )
    out = base
    for pattern, repl in phrase_map:
        out = re.sub(pattern, repl, out, flags=re.IGNORECASE)

    # Token-level normalization + filler cleanup.
    token_map: dict[str, str] = {
        # Kannada
        "bagge": "about",
        "helu": "",
        "heli": "",
        "yaav": "which",
        "yaava": "which",
        "yav": "which",
        "ali": "in",
        "alli": "in",
        "aithe": "available",
        "ide": "available",
        "ideya": "available",
        "estu": "how much",
        "du": "",
        "enu": "what",
        "hegide": "how",
        "eshtu": "how much",
        # Tamil
        "enna": "what",
        "solu": "",
        "sollu": "",
        "sollunga": "",
        # Telugu
        "enti": "what",
        "cheppu": "",
        "cheppandi": "",
        # Hindi
        "kya": "what",
        "kitna": "how much",
        "batao": "",
        "bataye": "",
        "batayiye": "",
    }
    for src, dst in token_map.items():
        out = re.sub(rf"\b{re.escape(src)}\b", dst, out, flags=re.IGNORECASE)

    # Drop residual filler words.
    filler_words = (
        "pls",
        "please",
        "anna",
        "bro",
        "sir",
        "madam",
    )
    for w in filler_words:
        out = re.sub(rf"\b{re.escape(w)}\b", "", out, flags=re.IGNORECASE)

    # Grapheme-safe: `\w` excludes Indic combining marks (Mn/Mc), so a plain
    # [^\w\s] strip shreds "ಶುಲ್ಕ" into "ಶ ಲ ಕ" and destroys the fees cue.
    # Imported lazily: backend.services.content imports this module at package init.
    from backend.services.content.unicode_text import strip_punctuation_keep_graphemes

    out = strip_punctuation_keep_graphemes(out)
    return _normalize_text(out)


# Mixed-language → English-friendly cues before strict intent matching.
_MIXED_LANGUAGE_PHRASE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bbagge\s+helu\b", "tell me about"),
    (r"\bbagge\s+heli\b", "tell me about"),
    (r"\bhelu\b", "tell"),
    (r"\bhelid\b", "tell"),
    (r"\bkaise\s+hai\b", "how is"),
    (r"\bepdi\s+iruku\b", "how is"),
    (r"\beppidi\s+irukku\b", "how is"),
    (r"\bela\s+unnavu\b", "how is"),
    (r"\byaaru\b", "who"),
    (r"\byaar\b", "who"),
    (r"\byaarig\b", "who"),
    (r"\bkaun\b", "who"),
    (r"\bkon\s+ala\b", "who is"),
    (r"\bhod\s+yaaru\b", "hod who"),
    (r"\bhead\s+yaaru\b", "head who"),
    (r"\byaaru\b", "who"),
    (r"\bheli\b", ""),
)


def normalize_user_input(text: str | None) -> str:
    """
    Lowercase, collapse whitespace, and map common mixed-language phrases to English cues.
    Intended to run before ``extract_entities`` / ``detect_intent_with_priority`` (and on translated English for multilingual sessions).
    """
    if text is None or not isinstance(text, str):
        return ""
    s = text.strip()
    if not s:
        return ""
    s = normalize_query_to_english(s)
    for pattern, repl in _MIXED_LANGUAGE_PHRASE_PATTERNS:
        s = re.sub(pattern, repl, s, flags=re.IGNORECASE)
    return _normalize_text(s)


DEPARTMENT_KEYWORDS: dict[str, str] = {
    "data science": "CSE (Data Science)",
    "datascience": "CSE (Data Science)",
    "daascince": "CSE (Data Science)",
    "datascince": "CSE (Data Science)",
    "datscience": "CSE (Data Science)",
    "ds": "CSE (Data Science)",
    "cse ds": "CSE (Data Science)",
    "computer science": "CSE",
    "cse": "CSE",
    "aiml": "CSE (AI & ML)",
    "ai ml": "CSE (AI & ML)",
    "ece": "ECE",
    "ec": "ECE",
    "ise": "ISE",
    "civil": "Civil",
    "mechanical": "Mechanical",
    "mba": "MBA",
}


def extract_entities(query_normalized: str) -> dict[str, Any]:
    """
    Extract **entities first** (before intent). Works on normalized English-friendly text.

    Returns:
        ``department``: canonical label (e.g. ``\"CSE\"``, ``\"CSE (AI & ML)\"``) or ``None``.
        ``role``: ``\"HOD\"``, ``\"TRUSTEES\"``, ``\"BOTH\"``, or ``None``.
    """
    n = (query_normalized or "").strip()
    out: dict[str, Any] = {"department": None, "role": None}
    if not n:
        return out

    # Role detection FIRST.
    hod_terms = (
        "hod",
        "head of department",
        "department head",
        "head",
        "incharge",
        "hod who",
        "head who",
        "who is hod",
    )
    has_hod = any(_contains_phrase(n, term) for term in hod_terms) or _matches_any_phrase(n, HOD_PROFILE_KEYWORDS)
    has_tr = _matches_any_phrase(n, TRUSTEES_PROFILE_KEYWORDS)
    if not has_tr and _contains_phrase(n, "trusted"):
        if has_hod or _contains_phrase(n, "profile") or _contains_phrase(n, "profiles"):
            has_tr = True

    if has_hod and has_tr:
        out["role"] = "BOTH"
    elif has_hod:
        out["role"] = "HOD"
    elif has_tr:
        out["role"] = "TRUSTEES"

    # Strict department mapping for deterministic card routing.
    for key, mapped in DEPARTMENT_KEYWORDS.items():
        if key in n:
            out["department"] = mapped
            break

    # Backward-compatible fallback if strict map didn't match.
    if not out["department"]:
        dept = _detect_department(n)
        if dept:
            out["department"] = dept
    return out


def resolve_intent_from_features(features: QueryFeatures) -> str:
    """
    Final deterministic intent resolver from extracted features only.
    """
    if features.is_hod_query:
        return INTENT_HOD_PROFILE
    if features.is_documents_query:
        return INTENT_DOCUMENTS
    # Explicit bus/transport college shuttle queries before comparison/course routing.
    if features.is_bus_routes_query:
        return INTENT_BUS_ROUTES
    if features.is_comparison_query:
        return INTENT_DEPARTMENT_COMPARISON
    if features.is_fee_query and features.has_department:
        return INTENT_DEPARTMENT_FEES
    if features.is_course_query:
        return INTENT_COURSE_MENU
    if features.has_department:
        return INTENT_DEPARTMENT_OVERVIEW
    if features.is_fee_query:
        return INTENT_ADMISSIONS
    if features.is_placement_query:
        return INTENT_PLACEMENTS
    if features.is_overview_query:
        return INTENT_COLLEGE_OVERVIEW
    return INTENT_NORMAL_QUERY


def card_trigger_hints(intent: str, entities: dict[str, Any]) -> dict[str, Any]:
    """
    Compatibility wrapper — SurfaceSelector is the sole production owner of surface selection.
    Prefer select_surface() in new code.
    """
    from backend.services.content.surface_selector import select_surface, surface_selection_to_hints

    selection = select_surface(
        entities=entities,
        intent=intent,
        faq_matched=False,
        user_text="",
    )
    return surface_selection_to_hints(selection)


def detect_intent_strict(normalized: str) -> str:
    """
    Back-compat: entities first, then ``detect_intent_with_priority``.
    """
    n = (normalized or "").strip()
    if not n:
        return INTENT_NORMAL_QUERY
    feats = extract_features(n)
    return resolve_intent_from_features(feats)


def resolve_card_intent_and_department(
    raw_text: str,
    english_query: str | None,
    lang_key: str,
    *,
    preprocessor_intent_raw: str | None = None,
) -> tuple[str, str | None, str, dict[str, Any], QueryFeatures]:
    """
    Backend-only card routing: normalize → ``extract_entities`` → ``detect_intent_with_priority``.

    - Non-English: prefer ``english_query`` (translated) for detection when provided.
    - ``preprocessor_intent_raw`` may supply off-topic from ``normalize_and_classify_query``.
    """
    original_input = (raw_text or "").strip()
    base_in = (english_query or raw_text or "").strip() if lang_key != "en" else original_input
    query_en = normalize_user_input(base_in)
    raw_normalized = normalize_user_input(original_input)
    merged_query = _normalize_text(" ".join([q for q in (query_en, raw_normalized) if q]))
    entities = extract_entities(merged_query)
    features = extract_features(merged_query, department_hint=entities.get("department"))
    intent = resolve_intent_from_features(features)
    dept: str | None = features.department_name

    logger.info(
        "[INTENT_PRIORITY] original_input=%r query_en=%r raw_normalized=%r merged=%r features=%s intent=%s department=%r entities=%s",
        original_input,
        query_en,
        raw_normalized,
        merged_query,
        features,
        intent,
        dept,
        entities,
    )
    routed = maybe_override_intent_with_executive_profile(intent, merged_query)
    intent = routed
    logger.info("[INTENT_PRIORITY] card_hints=%s", card_trigger_hints(intent, entities))

    return intent, dept, query_en, entities, features


def infer_show_card_label(intent: str, detected_department: str | None) -> str | list[str] | None:
    """Human-readable showCard label(s) for logging only (mirrors main.py payload)."""
    if intent == INTENT_COLLEGE_OVERVIEW:
        return "college"
    if intent == INTENT_DEPARTMENT_FEES:
        return "department_fees"
    if intent == INTENT_ADMISSIONS:
        return "admissions"
    if intent == INTENT_PLACEMENTS:
        return "placements"
    if intent == INTENT_DEPARTMENT_OVERVIEW:
        return "department_overview"
    if intent == INTENT_HOD_PROFILE:
        return "hod"
    if intent == INTENT_TRUSTEES_PROFILE:
        return "trustees"
    if intent == INTENT_HOD_TRUSTEES_PROFILE:
        return ["hod", "trustees"]
    if intent == INTENT_COURSE_MENU:
        return "course_menu"
    if intent == INTENT_DOCUMENTS:
        return "documents"
    if intent == INTENT_BUS_ROUTES:
        return "bus_routes"
    if intent == INTENT_DEPARTMENT_COMPARISON:
        return "department_comparison"
    if intent == INTENT_PRINCIPAL_PROFILE:
        return "principal_profile"
    if intent == INTENT_VICE_PRINCIPAL_PROFILE:
        return "vice_principal_profile"
    return None


def text_has_bus_routes_cue(text: str | None) -> bool:
    """Multilingual deterministic cues for college bus / shuttle / pickup queries (avoid bare 'routes')."""
    if not text or not isinstance(text, str):
        return False
    raw = text.strip().lower()
    if not raw:
        return False
    t = re.sub(r"[.,!?;:'\"()\[\]{}<>|/\\@#$%^&*_+=~`-]", " ", raw)
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return False
    spaced = f" {t} "

    # Full phrases (mixed scripts; lower() is harmless for Unicode letters we use).
    if any(
        p in spaced
        for p in (
            "bus routes",
            "bus route",
            "transport facility",
            "college bus",
            "route availability",
            "pickup points",
            "pickup locations",
            "travel to college",
            "travel to svit",
            "bus for ",
            " bus from ",
            "transport from",
            "shuttle",
            "is there a bus ",
            "do you have transport",
            "how can my child travel",
            "how can child travel",
            "बस रूट",
            "कॉलेज बस",
            "परिवहन सुविधा",
            "ಬಸ್ ಮಾರ್ಗಗಳು",
            "ಕಾಲೇಜು ಬಸ್",
            "பேருந்து வழிகள்",
            "బస్ రూట్లు",
            "ബസ് റൂട്ടുകൾ",
        )
    ):
        return True

    # Latin anchors: must pair a transport/bus signal with commuting/listing cues (not lone "routes").
    bus_markers = (
        "bus",
        "buses",
        "shuttle",
        "transport",
        "pickup",
        "pick-up",
        "pick up",
    )
    commute_markers = (
        "route",
        "routes",
        "stop",
        "stops",
        "timing",
        "timings",
        "pickup",
        "pick up",
        "college",
        "svit",
        "campus",
        "child",
        "kid",
        "reach",
        "commute",
    )
    if any(m in spaced for m in bus_markers) and any(c in spaced for c in commute_markers):
        return True

    return False


def is_documents_query(text: str) -> bool:
    """
    Deterministic multilingual documents intent detector.
    Uses raw text (any language / mixed) with punctuation removed and spaces collapsed.
    Applies substring + fuzzy matching (>= 0.7) over compacted tokens.
    """
    raw = str(text or "").strip().lower()
    if not raw:
        return False
    # Keep non-Latin glyphs; remove common punctuation and collapse spaces.
    t = re.sub(r"[.,!?;:'\"()\[\]{}<>|/\\@#$%^&*_+=~`-]", " ", raw)
    t = re.sub(r"\s+", " ", t).strip()
    compact = re.sub(r"\s+", "", t)

    core_doc_words = [
        "document",
        "documents",
        "doc",
        "doucment",
        "documnts",
        "doccuments",
        "doucments",
        "dakhale",
        "dakhalegalu",
        "dastavej",
        "kagaz",
    ]

    doc_context_words = [
        "aavasyam",
        "venum",
        "entha",
        "beku",
        "bekagutte",
        "chahiye",
    ]

    admission_words = [
        "admission",
        "college",
        "joining",
        "ge",
        "beku",
        "yaav",
        "bekagutte",
        "chahiye",
        "ka",
        "ke",
        "venum",
        "seyyanum",
        "kavali",
        "venam",
    ]

    def fuzzy_any(words: list[str], haystack: str) -> bool:
        for w in words:
            w_norm = re.sub(r"\s+", "", str(w or "").strip().lower())
            if not w_norm:
                continue
            if w_norm in haystack:
                return True
            if SequenceMatcher(None, w_norm, haystack).ratio() >= _INTENT_FUZZY_MIN:
                return True
        return False

    # Direct doc-signal wins (must contain a core document marker).
    if fuzzy_any(core_doc_words, compact):
        return True
    # Context-only words must not accidentally trigger documents.
    # Require both admission context and some document-context cue (still no core marker).
    if fuzzy_any(doc_context_words, compact) and fuzzy_any(admission_words, compact):
        return True
    return False


def detect_intent(text: str) -> str:
    """Public API: normalize → ``extract_features`` → ``resolve_intent_from_features``."""
    if is_documents_query(text):
        return INTENT_DOCUMENTS
    query_en = normalize_user_input(text)
    if is_documents_query(query_en):
        return INTENT_DOCUMENTS
    features = extract_features(query_en)
    base = resolve_intent_from_features(features)
    # Same executive routing as multimodal kiosk path (`maybe_override_intent_with_executive_profile`).
    return maybe_override_intent_with_executive_profile(base, text)


def _strip_json_fence(text: str) -> str:
    s = text.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```\s*$", "", s)
    return s.strip()


def _coerce_preprocessor_intent(raw: str | None) -> str:
    if raw is None:
        return INTENT_NORMAL_QUERY
    s = str(raw).strip().upper().replace("-", "_")
    if s.startswith("INTENT_"):
        s = s[7:]
    aliases: dict[str, str] = {
        "COLLEGE_OVERVIEW": INTENT_COLLEGE_OVERVIEW,
        "COURSE_MENU": INTENT_COURSE_MENU,
        "DOCUMENTS": INTENT_DOCUMENTS,
        "DEPARTMENT_OVERVIEW": INTENT_DEPARTMENT_OVERVIEW,
        "FEES": INTENT_DEPARTMENT_FEES,
        "DEPARTMENT_FEES": INTENT_DEPARTMENT_FEES,
        "ADMISSIONS": INTENT_ADMISSIONS,
        "PLACEMENTS": INTENT_PLACEMENTS,
        "HOD_PROFILE": INTENT_HOD_PROFILE,
        "TRUSTEES_PROFILE": INTENT_TRUSTEES_PROFILE,
        "HOD_TRUSTEES_PROFILE": INTENT_HOD_TRUSTEES_PROFILE,
        "NORMAL_QUERY": INTENT_NORMAL_QUERY,
        "OFF_TOPIC": INTENT_OFF_TOPIC,
        "DEPARTMENT_COMPARISON": INTENT_DEPARTMENT_COMPARISON,
    }
    return aliases.get(s, INTENT_NORMAL_QUERY)


def department_label_from_preprocessor(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in ("null", "none", "n/a", "-", ""):
        return None
    for canon in DEPARTMENT_SYNONYMS:
        if canon.lower() == s.lower():
            return canon
    return _detect_department(_normalize_text(s))


async def normalize_and_classify_query(user_text: str, session_lang: str) -> dict[str, Any]:
    """
    Translate mixed-language input to English and optionally hint department.
    Intent from this helper is advisory only and must not drive final routing.
    """
    from backend.config.settings import MULTILINGUAL_PREPROCESSOR_MAX_TOKENS, MULTILINGUAL_PREPROCESSOR_MODEL

    text = (user_text or "").strip()
    fallback: dict[str, Any] = {"english_translation": text, "target_department": None}
    if not text:
        return fallback
    try:
        client = await get_groq_client()
        if not client:
            return fallback
        allowed = (
            "COLLEGE_OVERVIEW, COURSE_MENU, DEPARTMENT_OVERVIEW, ADMISSIONS, PLACEMENTS, "
            "HOD_PROFILE, TRUSTEES_PROFILE, HOD_TRUSTEES_PROFILE, NORMAL_QUERY, OFF_TOPIC"
        )
        system_prompt = (
            "You are a linguistic translation and classification engine for a college kiosk (SVIT). "
            f"The user's session language label is: {session_lang}. "
            "The user text may mix that language with English (code-switching).\n"
            "1) Translate the user's query into clear, concise English (one short sentence). "
            "For OFF_TOPIC intent, you may use a minimal English placeholder such as the user's topic in English.\n"
            f"2) Classify intent as exactly one of: {allowed}. "
            "Use OFF_TOPIC only when the query is completely unrelated to SVIT, college admissions, education at this "
            "institute, campus life, placements, departments, fees, or polite greetings/small talk that do not ask for "
            "college facts (e.g. weather elsewhere, politics, unrelated trivia). Greetings like hello/hi asking for help "
            "about the college should be NORMAL_QUERY or another in-scope intent, not OFF_TOPIC.\n"
            "3) If the question targets a specific academic department or branch, set target_department to one of: "
            "CSE, ISE, CSE (AI & ML), CSE (Data Science), CSE (Cyber Security), CSE (Business Systems), "
            "ECE, Civil, Mechanical, MBA, Basic Sciences, Mathematics, Physics, Chemistry. Otherwise JSON null. "
            "For OFF_TOPIC, set target_department to null.\n"
            "Output ONLY one JSON object, no markdown fences, no extra keys, with exactly: "
            "english_translation (string), intent (string), target_department (string or null)."
        )
        completion = await client.chat.completions.create(
            model=MULTILINGUAL_PREPROCESSOR_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            temperature=0.0,
            top_p=0.2,
            max_tokens=MULTILINGUAL_PREPROCESSOR_MAX_TOKENS,
        )
        raw = (completion.choices[0].message.content or "").strip()
        logger.info(f"[NLP_TRACE] LLM Preprocessor Output: {raw}")
        payload = json.loads(_strip_json_fence(raw))
        if not isinstance(payload, dict):
            return fallback
        en = (payload.get("english_translation") or "").strip()
        if not en:
            en = text
        dept = department_label_from_preprocessor(payload.get("target_department"))
        return {"english_translation": en, "target_department": dept}
    except Exception as e:
        logger.warning(f"[NLP_TRACE] normalize_and_classify_query failed: {e}", exc_info=True)
        return fallback


FALLBACK_CONTEXT_PREFIX = "I am having trouble processing that right now, please try again. "
FALLBACK_CONTEXT_MAX_CHARS = 600


def controlled_fallback_reply(language: str | None) -> str:
    if language == "Kannada":
        return CONTROLLED_FALLBACK_KN
    return CONTROLLED_FALLBACK_EN


def process_fallback_reply(language: str | None) -> str:
    if language == "Kannada":
        return FALLBACK_MSG_KN
    return FALLBACK_MSG


def _fallback_reply(context: str, language: str | None = None) -> str:
    """Return safe fallback when LLM fails. Never returns None."""
    _ = context
    return process_fallback_reply(language)


def build_overview_context(lang_key: str | None = None) -> str:
    """
    Return overview-oriented RAG context, hard-capped at OVERVIEW_CONTEXT_MAX_TOKENS (1000).
    Uses fixed canonical query; rows are filtered by locale metadata when lang_key is set.
    """
    return get_relevant_context(
        OVERVIEW_QUERY,
        top_k=OVERVIEW_TOP_K,
        max_tokens=OVERVIEW_CONTEXT_MAX_TOKENS,
        lang_key=lang_key,
    )


def build_normal_context(query: str, lang_key: str | None = None) -> str:
    """Thin wrapper around get_relevant_context for normal (non-overview) queries."""
    return get_relevant_context(
        query,
        top_k=RAG_TOP_K,
        max_tokens=RAG_MAX_TOKENS,
        lang_key=lang_key,
    )


def build_system_prompt(intent: str, language: str, context: str | None) -> str:
    """
    Build system prompt for Groq. COLLEGE_OVERVIEW: strict 6-section English-only.
    NORMAL_QUERY: existing CLARA style with reply in selected language.
    """
    ctx = (context or "").strip()
    if intent == INTENT_COLLEGE_OVERVIEW:
        prefix = (
            CONCISE_VOICE_RULE
            + " "
            + rag_language_enforcement_directive(language)
            + " "
            "Give a short college overview in 2-3 sentences using only verified context. "
            "Plain text only. No markdown. No bullets. No emojis. "
            "If information is missing, explicitly state 'Information not available.' "
            + MULTI_ENTITY_RULE
        )
        return f"{prefix}\n\nCollege information:\n{ctx}" if ctx else prefix
    if intent == INTENT_DEPARTMENT_OVERVIEW:
        prefix = (
            CONCISE_VOICE_RULE
            + "\n\n"
            + rag_language_enforcement_directive(language)
            + "\n\n"
            "Give a short department snapshot in 2-3 sentences using only verified department data.\n"
            "No markdown. No bullets.\n"
            "If missing, say 'Information not available.'\n"
            + MULTI_ENTITY_RULE
            + "\n\n"
            "Department information:\n"
        )
        return f"{prefix}{ctx}" if ctx else prefix.rstrip()
    if intent == INTENT_ADMISSIONS:
        prefix = (
            CONCISE_VOICE_RULE
            + "\n\n"
            + rag_language_enforcement_directive(language)
            + "\n\n"
            "The user is asking about admissions, fees, eligibility, or entrance exams. "
            "Reply in 2-3 very short sentences using only the context. No markdown or bullets. "
            "Direct them to the Admission Block if exact numbers are uncertain.\n"
            + MULTI_ENTITY_RULE
            + "\n\nAdmissions and fees information:\n"
        )
        return f"{prefix}{ctx}" if ctx else prefix.rstrip()
    if intent == INTENT_PLACEMENTS:
        prefix = (
            CONCISE_VOICE_RULE
            + "\n\n"
            + rag_language_enforcement_directive(language)
            + "\n\n"
            "The user is asking about placements, jobs, internships, or training. "
            "Reply in 2-3 very short sentences using only the context. No markdown or bullets.\n"
            + MULTI_ENTITY_RULE
            + "\n\nPlacements and training information:\n"
        )
        return f"{prefix}{ctx}" if ctx else prefix.rstrip()
    if intent == INTENT_DEPARTMENT_COMPARISON:
        prefix = (
            COMPARISON_VOICE_RULE
            + "\n\n"
            + rag_language_enforcement_directive(language)
            + "\n\n"
            "The on-screen table shows the same three insight topics for each program (typically: what students learn across four years; "
            "future job directions; outlook for roughly the next five to ten years). "
            "Use ONLY the facts in the block below — they are authoritative for this narration.\n"
            + MULTI_ENTITY_RULE
            + "\n\nProgram comparison insights:\n"
        )
        return f"{prefix}{ctx}" if ctx else prefix.rstrip()
    # NORMAL_QUERY
    unavailable_reply = get_unavailable_reply(language)
    off_topic_reply = get_off_topic_reply(language)
    if ctx:
        return (
            f"{CONCISE_VOICE_RULE} "
            f"{rag_language_enforcement_directive(language)} "
            f"Reply only in {language}. "
            f"For college-related emotional or opinion questions (for example, 'is this a good college?'), reply with a reassuring, polite tone in one or two short sentences. "
            f"Use ONLY the following college information when it is relevant to the user's question. "
            f"Do not invent or assume college-specific facts; only use what is in the College information below. "
            f"{MULTI_ENTITY_RULE} "
            f"If the answer is not in the context, reply exactly: '{unavailable_reply}' "
            f"If the question is outside SVIT/college domain, reply exactly: '{off_topic_reply}' "
            f"Default to one short sentence, maximum two short sentences only if truly needed. "
            f"Avoid fillers, backstory, and generic introductions. "
            f"For name/list questions, return just the names in one line.\n\nCollege information:\n{ctx}"
        )
    return (
        f"{CONCISE_VOICE_RULE} "
        f"{rag_language_enforcement_directive(language)} "
        f"Reply only in {language}. "
        f"For college-related emotional or opinion questions, respond politely in one or two short sentences. "
        f"{MULTI_ENTITY_RULE} "
        f"For questions about the college or campus, if details are unavailable reply exactly: '{unavailable_reply}' "
        f"For non-college topics, reply exactly: '{off_topic_reply}' "
        f"Default to one short sentence, maximum two short sentences only if needed."
    )


def _count_tokens(text: str) -> int:
    """Return token count using tiktoken cl100k_base. Returns 0 on error."""
    if not text:
        return 0
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return 0


def _trim_to_tokens(text: str, max_tokens: int) -> str:
    """Trim text to at most max_tokens. Returns text unchanged if already within limit."""
    if max_tokens <= 0 or not text:
        return text
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return enc.decode(tokens[:max_tokens])
    except Exception:
        return text


def generate_structured_overview(
    system_prompt: str,
    context: str,
    groq_client: Any,
    model: str,
) -> str:
    """
    Phase 1: Generate structured college overview in English only.
    Uses low temperature (GROQ_TEMPERATURE), top_p=GROQ_TOP_P, max_tokens=400. On failure returns empty string (caller uses fallback).
    """
    if not groq_client or not model:
        return ""
    try:
        prompt_tokens = _count_tokens(system_prompt) + _count_tokens("Provide the college overview in the required structure.")
        if prompt_tokens > int(MODEL_CONTEXT_LIMIT * MAX_INPUT_TOKEN_FRACTION):
            system_prompt = _trim_to_tokens(system_prompt, int(MODEL_CONTEXT_LIMIT * MAX_INPUT_TOKEN_FRACTION) - 50)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Provide the college overview in the required structure."},
        ]
        completion = groq_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=GROQ_TEMPERATURE,
            top_p=GROQ_TOP_P,
            max_tokens=GROQ_MAX_TOKENS,
        )
        out = (completion.choices[0].message.content or "").strip()
        if out:
            logger.info("Overview generated model=%s tokens_approx=%d", model, prompt_tokens)
        return out
    except Exception as e:
        logger.error("LLM failure (structured overview): %s", e, exc_info=True)
        return ""


def generate_structured_department_overview(
    system_prompt: str,
    department_name: str,
    groq_client: Any,
    model: str,
) -> str:
    """
    Generate structured department overview in English only.
    Uses low temperature (GROQ_TEMPERATURE), top_p=GROQ_TOP_P, max_tokens=400. On failure returns empty string.
    """
    if not groq_client or not model:
        return ""
    try:
        user_msg = f"Provide the {department_name} department overview in the required structure."
        prompt_tokens = _count_tokens(system_prompt) + _count_tokens(user_msg)
        if prompt_tokens > int(MODEL_CONTEXT_LIMIT * MAX_INPUT_TOKEN_FRACTION):
            system_prompt = _trim_to_tokens(system_prompt, int(MODEL_CONTEXT_LIMIT * MAX_INPUT_TOKEN_FRACTION) - 50)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ]
        completion = groq_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=GROQ_TEMPERATURE,
            top_p=GROQ_TOP_P,
            max_tokens=GROQ_MAX_TOKENS,
        )
        out = (completion.choices[0].message.content or "").strip()
        if out:
            logger.info("Department overview generated dept=%s model=%s tokens_approx=%d", department_name, model, prompt_tokens)
        return out
    except Exception as e:
        logger.error("LLM failure (department overview): %s", e, exc_info=True)
        return ""


def _parse_overview_to_sections(reply_text: str) -> List[dict]:
    """Parse overview reply into 5 sections (title + text). Section 6 Closing Assurance excluded."""
    raw = (reply_text or "").strip()
    if not raw:
        return [{"title": t, "text": "Information not available."} for t in DIGITAL_BOOK_SECTION_TITLES]
    split_re = re.compile(r"\n\s*\d+[.)]\s*")
    segments = [s.strip() for s in split_re.split(raw) if s.strip()]
    # First segment may be intro; we want sections 1-5 (last 6 segments, then take first 5)
    section_texts = (segments[-6:])[:5] if len(segments) >= 5 else segments[:5]
    result = []
    for i, title in enumerate(DIGITAL_BOOK_SECTION_TITLES):
        text = (section_texts[i].strip()) if i < len(section_texts) else "Information not available."
        result.append({"title": title, "text": text or "Information not available."})
    return result


def build_overview_pages(
    reply_text: str,
    language_code: str,
    tts_callback: Callable[[str, str], str | None],
) -> dict:
    """
    Build overview pages payload: pages with title, text, and pre-generated audio (base64) for content pages.
    Cover has audio: null. Used only for COLLEGE_OVERVIEW.
    Per-section TTS failures are caught so we always return a full book (missing audio as null) for all languages.
    """
    sections = _parse_overview_to_sections(reply_text)
    pages = [
        {"title": DIGITAL_BOOK_COVER_TITLE, "text": DIGITAL_BOOK_COVER_TEXT, "audio": None},
    ]
    for sec in sections:
        audio_b64 = None
        if sec.get("text"):
            try:
                audio_b64 = tts_callback(sec["text"], language_code)
            except Exception as e:
                logger.warning("TTS for digital book section %s failed: %s", sec.get("title"), e)
        pages.append({"title": sec["title"], "text": sec["text"], "audio": audio_b64})
    return {"pages": pages}


def translate_preserving_structure(
    english_text: str,
    target_language: str,
    groq_client: Any,
    model: str,
) -> str:
    """
    Phase 2: Translate English overview into target_language, preserving structure.
    On failure logs warning and returns english_text (graceful fallback).
    """
    from backend.services.runtime.translation_cache import get_cached_translation, put_cached_translation

    if not english_text or not target_language or target_language.lower() == "english":
        return english_text or ""
    if not groq_client or not model:
        return english_text
    hit = get_cached_translation(target_language, english_text)
    if hit:
        return hit
    try:
        system_content = (
            f"Translate the following text into {target_language}. "
            "Preserve structure, sentence count, and meaning exactly. Do not expand or shorten. Output only the translation."
        )
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": english_text},
        ]
        completion = groq_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=GROQ_TEMPERATURE,
            top_p=GROQ_TOP_P,
            max_tokens=GROQ_MAX_TOKENS,
        )
        out = (completion.choices[0].message.content or "").strip()
        if out:
            put_cached_translation(target_language, english_text, out)
            return out
        return english_text
    except Exception as e:
        logger.warning("Translation fallback to English: %s", e)
        return english_text


def extract_structured_json_context(
    intent: str,
    query_en: str,
    detected_department_label: str | None,
) -> dict[str, Any] | None:
    """
    Load English locale JSON only; return a minimal dict for the intent.
    Does not pass the full locale file to callers.
    """
    data = load_locale_data_for_lang_key("en")
    if not data:
        return None
    deps = data.get("departments")
    if not isinstance(deps, dict):
        deps = {}

    if intent == INTENT_COLLEGE_OVERVIEW:
        io = data.get("institution_overview")
        program_names = {k: (v.get("name") if isinstance(v, dict) else None) for k, v in deps.items()}
        return {
            "institution_overview": io,
            "programs_offered": program_names,
            "placements_and_training": data.get("placements_and_training"),
        }

    if intent == INTENT_DEPARTMENT_OVERVIEW:
        if _wants_all_departments_narration(query_en):
            ordered: dict[str, Any] = {}
            for k in DEPARTMENT_JSON_KEY_ORDER:
                if k in deps and isinstance(deps[k], dict):
                    ordered[k] = _hod_slice_for_narrator(deps[k])
            return {"all_departments": ordered}
        jkey = department_label_to_json_key(detected_department_label or detect_department_name(query_en))
        dept = deps.get(jkey)
        if not isinstance(dept, dict):
            return None
        return {"department_key": jkey, "department": _hod_slice_for_narrator(dept)}

    if intent == INTENT_ADMISSIONS:
        return {"admissions_and_fees": data.get("admissions_and_fees")}

    if intent == INTENT_PLACEMENTS:
        return {"placements_and_training": data.get("placements_and_training")}

    if intent == INTENT_HOD_PROFILE:
        hod_rows: dict[str, Any] = {}
        for k in DEPARTMENT_JSON_KEY_ORDER:
            d = deps.get(k)
            if isinstance(d, dict):
                hod_rows[k] = {"name": d.get("name"), "hod": d.get("hod"), "intake": d.get("intake")}
        return {"hod_by_department": hod_rows}

    if intent == INTENT_TRUSTEES_PROFILE:
        lead = data.get("leadership")
        if isinstance(lead, list):
            return {"leadership": lead[:12]}
        return {"leadership": lead}

    if intent == INTENT_HOD_TRUSTEES_PROFILE:
        hod_rows_b: dict[str, Any] = {}
        for k in DEPARTMENT_JSON_KEY_ORDER:
            d = deps.get(k)
            if isinstance(d, dict):
                hod_rows_b[k] = {"name": d.get("name"), "hod": d.get("hod"), "intake": d.get("intake")}
        lead_b = data.get("leadership")
        out: dict[str, Any] = {"hod_by_department": hod_rows_b}
        if isinstance(lead_b, list):
            out["leadership"] = lead_b[:12]
        else:
            out["leadership"] = lead_b
        return out

    return None


def _build_structured_english_system_prompt(intent: str) -> str:
    base = (
        "You are CLARA, a campus assistant for Sai Vidya Institute of Technology (SVIT).\n"
        "Rules:\n"
        "- Use ONLY the DATA section below. Do NOT hallucinate. Do NOT add external information.\n"
        "- Reply in clear English only. Plain text. No markdown code fences. No emojis.\n"
        "- Be concise. Prefer 2–4 short sentences unless a numbered outline is required.\n"
        "- If DATA is missing or insufficient for the question, reply exactly: "
        f"{CONTROLLED_FALLBACK_EN}\n"
    )
    if intent == INTENT_COLLEGE_OVERVIEW:
        return (
            base
            + "Format your answer with exactly these numbered sections (each 1–2 short sentences):\n"
            "1) About the Institution\n"
            "2) Academic Programs\n"
            "3) Infrastructure & Quality\n"
            "4) Achievements\n"
            "5) Placements\n"
        )
    if intent == INTENT_DEPARTMENT_OVERVIEW:
        return (
            base
            + "Format your answer with exactly these numbered sections (each 1–2 short sentences):\n"
            "1) Overview\n"
            "2) Academics\n"
            "3) Facilities\n"
            "4) Achievements\n"
            "5) Career Scope\n"
        )
    return base + "Answer the visitor's question directly using DATA.\n"


def _english_normal_query_system_with_rag(ctx: str) -> str:
    ctx_stripped = (ctx or "").strip()
    return (
        "You are CLARA, a campus assistant for Sai Vidya Institute of Technology (SVIT).\n"
        "Rules:\n"
        "- Use ONLY the English reference chunks below. Do NOT hallucinate.\n"
        "- Reply in English only. Plain text. 2–3 short sentences unless a tight list is required.\n"
        "- If the answer is not in the reference, reply exactly: "
        f"{CONTROLLED_FALLBACK_EN}\n"
        f"{MULTI_ENTITY_RULE}\n\n"
        "College reference:\n"
        f"{ctx_stripped}"
    )


def _english_normal_query_system_empty() -> str:
    return (
        "You are CLARA, a campus assistant for SVIT.\n"
        "No reference data is available for this question.\n"
        f"Reply in English only with exactly: {CONTROLLED_FALLBACK_EN}\n"
    )


def compose_llm_system_prompt_for_turn(
    *,
    intent: str,
    rag_query: str,
    user_text: str,
    lang_key: str,
    lang_name: str,
    detected_department: str | None,
) -> tuple[str, dict[str, Any] | None, str]:
    """
    English-first pipeline: build the Groq system prompt and optional narrator card payload.

    Returns (system_prompt, narrator_payload_or_none, context_source).
    context_source is one of: structured_json | structured_json_cached | structured_empty | rag | rag_empty
    """
    _ = lang_name  # reserved for future prompt personalization

    if is_narrator_intent(intent):
        narrator_payload = build_target_card_payload(
            intent,
            lang_key=lang_key,
            detected_department_label=detected_department,
            user_text=user_text,
        )
        if narrator_payload is None:
            narrator_payload = {}
        structured = extract_structured_json_context(intent, rag_query.strip(), detected_department)
        cache_key = ""
        if structured is not None:
            cache_key = f"{intent}|{hashlib.sha256(json.dumps(structured, sort_keys=True, ensure_ascii=True).encode()).hexdigest()}"
            cached = _STRUCTURED_PROMPT_CACHE.get(cache_key)
            if cached:
                return cached, narrator_payload, "structured_json_cached"

        if structured is None:
            sp = _build_structured_english_system_prompt(intent) + f"\n\nDATA:\n{{}}\n"
            return sp, narrator_payload, "structured_empty"

        data_text = json.dumps(structured, ensure_ascii=False, indent=2)
        if len(data_text) > 14000:
            data_text = data_text[:14000] + "\n...[truncated]"
        sp = _build_structured_english_system_prompt(intent) + "\n\nDATA (JSON):\n" + data_text
        if cache_key:
            _STRUCTURED_PROMPT_CACHE.set(cache_key, sp)
        return sp, narrator_payload, "structured_json"

    # Non-narrator intents should use compose_llm_system_prompt_open_ended_from_context() with
    # RAG text retrieved on the caller side (e.g. asyncio.to_thread in main).
    raise ValueError(
        "compose_llm_system_prompt_for_turn() is for structured (narrator) intents only; "
        "use compose_llm_system_prompt_open_ended_from_context(precomputed_rag_context) for open-ended queries."
    )


def compose_llm_system_prompt_open_ended_from_context(precomputed_rag_context: str) -> tuple[str, None, str]:
    """Build English-first system prompt for NORMAL_QUERY / open-ended turns from retrieved RAG text."""
    ctx = (precomputed_rag_context or "").strip()
    if not ctx:
        return _english_normal_query_system_empty(), None, "rag_empty"
    return _english_normal_query_system_with_rag(ctx), None, "rag"


async def translate_reply_to_session_language_async(
    reply_en: str,
    lang_name: str,
    client: Any,
    model: str,
) -> str:
    """Translate an English-only model reply into the session language; preserves structure."""
    from backend.services.runtime.translation_cache import get_cached_translation, put_cached_translation

    if not reply_en or not client or not model:
        return reply_en or ""
    if (lang_name or "").strip() == "English":
        return reply_en
    hit = get_cached_translation(lang_name, reply_en)
    if hit:
        return hit
    try:
        completion = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Translate the following text into {lang_name}. "
                        "Preserve numbering, line breaks, and sentence boundaries. "
                        "Do not expand or shorten. Output only the translation."
                    ),
                },
                {"role": "user", "content": reply_en},
            ],
            temperature=GROQ_TEMPERATURE,
            top_p=GROQ_TOP_P,
            max_tokens=min(800, GROQ_MAX_TOKENS * 2),
        )
        out = (completion.choices[0].message.content or "").strip()
        if out:
            put_cached_translation(lang_name, reply_en, out)
            return out
    except Exception as e:
        logger.warning("translate_reply_to_session_language_async: %s", e)
    return reply_en


def generate_reply(
    intent: str,
    text: str,
    context: str,
    language: str,
    session_messages: List[dict],
    groq_client: Any,
    model: str,
    tts_callback: Callable[[str, str], str | None] | None = None,
    language_code: str | None = None,
    query_en: str | None = None,
) -> str | dict:
    """
    English-first pipeline: structured intents use filtered English JSON; open-ended uses RAG (small top_k).
    Non-English replies are produced by translate_preserving_structure after the English LLM output.
    The legacy ``context`` argument is ignored (retrieval is driven by ``query_en`` / ``text``); kept for API compatibility.
    """
    _ = context
    _ = tts_callback
    _ = language_code
    unavailable = get_unavailable_reply(language)
    if intent == INTENT_OFF_TOPIC:
        return get_off_topic_reply(language)
    if not groq_client or not model:
        return unavailable

    lang_key_for_locale = "hi" if (language or "").strip().lower() == "hindi" else "en"
    qen = (query_en or text or "").strip()

    if intent == INTENT_COURSE_MENU:
        return "COURSE_MENU"

    if intent == INTENT_DEPARTMENT_FEES:
        fee_base = normalize_user_input(qen)
        fee_entities = extract_entities(fee_base)
        fee_dept = fee_entities.get("department")
        if not fee_dept:
            return "Please specify the department to view fee structure."
        # Keep spoken reply short; UI renders the strict fee card.
        return f"Showing fee structure for {fee_dept}."

    if is_narrator_intent(intent):
        dept_label = detect_department_name(text)
        system_prompt, _, src = compose_llm_system_prompt_for_turn(
            intent=intent,
            rag_query=qen,
            user_text=text or "",
            lang_key=lang_key_for_locale,
            lang_name=language or "English",
            detected_department=dept_label,
        )
        try:
            if _count_tokens(system_prompt) > int(MODEL_CONTEXT_LIMIT * MAX_INPUT_TOKEN_FRACTION):
                system_prompt = _trim_to_tokens(
                    system_prompt,
                    int(MODEL_CONTEXT_LIMIT * MAX_INPUT_TOKEN_FRACTION) - 80,
                )
            messages = [{"role": "system", "content": system_prompt}]
            for m in session_messages or []:
                role = "assistant" if m.get("role") == "clara" else "user"
                messages.append({"role": role, "content": m.get("text", "") or ""})
            messages.append({"role": "user", "content": qen})
            completion = groq_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=GROQ_TEMPERATURE,
                top_p=GROQ_TOP_P,
                max_tokens=GROQ_MAX_TOKENS,
            )
            out_en = (completion.choices[0].message.content or "").strip()
            if out_en:
                logger.info("Reply generated narrator intent=%s model=%s src=%s", intent, model, src)
            if not out_en:
                return unavailable
            if (language or "").strip() == "English":
                return out_en
            return translate_preserving_structure(out_en, language, groq_client, model)
        except Exception as e:
            logger.error("LLM failure (narrator): %s", e, exc_info=True)
            return unavailable

    try:
        ctx = get_relevant_context(
            qen,
            top_k=RAG_PIPELINE_TOP_K,
            max_tokens=RAG_PIPELINE_MAX_TOKENS,
            lang_key="en",
        )
        system_prompt, _, src = compose_llm_system_prompt_open_ended_from_context(ctx)
        rest_tokens = sum(_count_tokens(m.get("text", "") or "") for m in (session_messages or [])) + _count_tokens(qen)
        total_tokens = _count_tokens(system_prompt) + rest_tokens
        max_allowed = int(MODEL_CONTEXT_LIMIT * MAX_INPUT_TOKEN_FRACTION)
        if total_tokens > max_allowed:
            system_prompt = _trim_to_tokens(system_prompt, max(500, max_allowed - rest_tokens - 50))
            logger.info("System prompt truncated for token limit; src=%s", src)
        messages = [{"role": "system", "content": system_prompt}]
        for m in session_messages or []:
            role = "assistant" if m.get("role") == "clara" else "user"
            messages.append({"role": role, "content": m.get("text", "") or ""})
        messages.append({"role": "user", "content": qen})

        completion = groq_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=GROQ_TEMPERATURE,
            top_p=GROQ_TOP_P,
            max_tokens=GROQ_MAX_TOKENS,
        )
        out_en = (completion.choices[0].message.content or "").strip()
        if out_en:
            logger.info("Reply generated intent=%s model=%s src=%s", intent, model, src)
        if not out_en:
            return unavailable
        if (language or "").strip() == "English":
            return out_en
        return translate_preserving_structure(out_en, language, groq_client, model)
    except Exception as e:
        logger.error("LLM failure (normal query): %s", e, exc_info=True)
        return unavailable
