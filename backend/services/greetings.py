"""Time-aware greeting text + wake opening copy for CLARA.

Edit order:
  1) WAKE_OPENING_GREETING_ENGLISH — first thing users hear/read (before language pick).
  2) _GREETINGS_BY_PERIOD — full greeting after they choose a language.
"""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.config.settings import KIOSK_TIMEZONE
from backend.services.ui_localization import ui_language_key, ui_text

SUPPORTED_LANGUAGES: tuple[str, ...] = ("English", "Kannada", "Hindi", "Tamil", "Telugu", "Malayalam")

# ---------------------------------------------------------------------------
# Wake / first paint (English only, before language is chosen)
# ---------------------------------------------------------------------------
WAKE_OPENING_GREETING_ENGLISH: dict[str, str] = {
    "morning": "Good morning. I am CLARA, your campus assistant.",
    "afternoon": "Good afternoon. I am CLARA, your campus assistant.",
    "evening": "Good evening. I am CLARA, your campus assistant.",
}

LANGUAGE_GATE_NUDGE_ENGLISH: str = (
    "Please choose the language that feels most comfortable."
)

# Optional CSS stack for the first greeting bubble (sent on WS payload as greetingFontFamily).
GREETING_FONT_STACK: str = '"Bodoni Moda", "Libre Bodoni", Didot, "Playfair Display", serif'


def _time_period(now: datetime | None = None) -> str:
    if now is not None:
        ts = now
    else:
        try:
            ts = datetime.now(ZoneInfo(KIOSK_TIMEZONE))
        except Exception:
            ts = datetime.now()
    # Treat late night/early hours as evening for kiosk tone (users reported 1 AM should not be "morning").
    if 5 <= ts.hour < 12:
        return "morning"
    if 12 <= ts.hour < 17:
        return "afternoon"
    return "evening"


def get_short_opening_greeting_english(now: datetime | None = None) -> str:
    """First-line intro only."""
    period = _time_period(now)
    return WAKE_OPENING_GREETING_ENGLISH.get(
        period,
        WAKE_OPENING_GREETING_ENGLISH["evening"],
    )


def get_wakeup_opening_display_text(now: datetime | None = None) -> str:
    return get_short_opening_greeting_english(now)


def get_wakeup_opening_tts_text(now: datetime | None = None) -> str:
    return get_wakeup_opening_display_text(now)


def get_wakeup_language_gate_display_text(now: datetime | None = None) -> str:
    """Only the opening greeting is displayed before language pick.

    The language instruction is intentionally TTS-only.  The frontend reveals
    the picker after the greeting clip ends and then plays that instruction.
    """
    return get_wakeup_opening_display_text(now)


def get_wakeup_language_gate_tts_text(now: datetime | None = None) -> str:
    """TTS for the first wake clip; the language nudge is a second clip."""
    return get_wakeup_opening_tts_text(now)


def get_language_required_nudge_english() -> str:
    return LANGUAGE_GATE_NUDGE_ENGLISH.strip()


def greeting_font_family_css(language: str | None) -> str | None:
    _ = language
    return GREETING_FONT_STACK


# ---------------------------------------------------------------------------
# After user picks a language — readiness prompt (not a second greeting)
# ---------------------------------------------------------------------------
_READY_PROMPTS_BY_LANGUAGE: dict[str, str] = {
    "English": "Wonderful. I am ready to help you with care. What would you like to explore today?",
    "Kannada": ui_text("kn", "welcome.general_narration"),
    "Hindi": "बहुत अच्छा। मैं पूरे ध्यान से आपकी मदद के लिए तैयार हूँ। आज आप क्या जानना चाहेंगे?",
    "Tamil": "மிக நன்று. உங்களுக்கு அக்கறையுடன் உதவ நான் தயார். இன்று நீங்கள் என்ன தெரிந்துகொள்ள விரும்புகிறீர்கள்?",
    "Telugu": "చాలా మంచిది. మీకు శ్రద్ధగా సహాయం చేయడానికి నేను సిద్ధంగా ఉన్నాను. ఈరోజు మీరు ఏమి తెలుసుకోవాలనుకుంటున్నారు?",
    "Malayalam": "വളരെ നന്നായി. നിങ്ങളെ ശ്രദ്ധയോടെ സഹായിക്കാൻ ഞാൻ തയ്യാറാണ്. ഇന്ന് നിങ്ങൾ എന്താണ് അറിയാൻ ആഗ്രഹിക്കുന്നത്?",
}

_NAME_PROMPTS_BY_LANGUAGE: dict[str, str] = {
    "English": "May I know your preferred name?",
    "Kannada": ui_text("kn", "welcome.name_prompt"),
    "Hindi": "क्या मैं आपका नाम जान सकती हूँ?",
    "Tamil": "உங்கள் பெயரை அறியலாமா?",
    "Telugu": "మీ పేరు ఏమిటో చెప్పగలరా?",
    "Malayalam": "നിങ്ങളുടെ പേരറിയാമോ?",
}

# Placeholder uses literal "{name}"; substituted via str.replace for user safety.
_READY_PROMPTS_WITH_NAME_BY_LANGUAGE: dict[str, str] = {
    "English": (
        "Wonderful to meet you, {name}. I am ready to help you with care. "
        "What would you like to explore today?"
    ),
    "Kannada": ui_text("kn", "welcome.named_narration"),
    "Hindi": (
        "{name}, आपसे मिलकर अच्छा लगा। मैं पूरे ध्यान से आपकी मदद के लिए तैयार हूँ। "
        "आज आप क्या जानना चाहेंगे?"
    ),
    "Tamil": (
        "{name}, உங்களை சந்திப்பதில் மகிழ்ச்சி. உங்களுக்கு அக்கறையுடன் உதவ நான் தயார். "
        "இன்று நீங்கள் என்ன தெரிந்துகொள்ள விரும்புகிறீர்கள்?"
    ),
    "Telugu": (
        "{name}, మిమ്മల్ని కలవడం ఆనందం. మీకు శ్రద్ధగా సహాయం చేయడానికి నేను సిద్ధంగా ఉన్నాను. "
        "ఈరోజు మీరు ఏమి తెలుసుకోవాలనుకుంటున్నారు?"
    ),
    "Malayalam": (
        "{name}, നിങ്ങളെ കാണാൻ സന്തോഷം. നിങ്ങളെ ശ്രദ്ധയോടെ സഹായിക്കാൻ ഞാൻ തയ്യാറാണ്. "
        "ഇന്ന് നിങ്ങൾ എന്താണ് അറിയാൻ ആഗ്രഹിക്കുന്നത്?"
    ),
}

_GUEST_NAME_PREFIX_RE = re.compile(
    r"^\s*(?:my\s+name\s+is|"
    r"i\s*['\u2019]?\s*m|i\s+am|call\s+me|this\s+is|"
    r"name\s*[:：]\s*|the\s+name\s+is)\s+",
    re.IGNORECASE,
)

_GUEST_NAME_MAX_LEN = 48

# Phrases meaning "I'd rather not share my name" (ASCII normalize for matching).
_SKIP_GUEST_NAME_PHRASES: frozenset[str] = frozenset(
    {
        "skip",
        "no",
        "no thanks",
        "no thank you",
        "pass",
        "none",
        "prefer not",
        "prefer not to say",
        "rather not",
        "rather not say",
        "not now",
        "anonymous",
        "skip please",
        "no name",
        "ಬೇಡ",
        "ಹೆಸರು ಬೇಡ",
        "ಬಿಡಿ",
    }
)


# ---------------------------------------------------------------------------
# Time-aware greeting translations retained for non-language-gate flows
# ---------------------------------------------------------------------------
_GREETINGS_BY_PERIOD: dict[str, dict[str, str]] = {
    "morning": {
        "English": "Good morning. I am CLARA, your campus assistant.",
        "Kannada": ui_text("kn", "welcome.general_narration"),
        "Hindi": "सुप्रभात। मैं CLARA हूँ, आपकी कैंपस सहायक।",
        "Tamil": "காலை வணக்கம். நான் கிளாரா, உங்கள் வளாக உதவியாளர்.",
        "Telugu": "శుభోదయం. నేను CLARA, మీ క్యాంపస్ సహాయకురాలు.",
        "Malayalam": "സുപ്രഭാതം. ഞാൻ CLARA, നിങ്ങളുടെ ക്യാമ്പസ് സഹായി.",
    },
    "afternoon": {
        "English": "Good afternoon. I am CLARA, your campus assistant.",
        "Kannada": ui_text("kn", "welcome.general_narration"),
        "Hindi": "शुभ दोपहर। मैं CLARA हूँ, आपकी कैंपस सहायक।",
        "Tamil": "மதிய வணக்கம். நான் கிளாரா, உங்கள் வளாக உதவியாளர்.",
        "Telugu": "శుభ మధ్యాహ్నం. నేను CLARA, మీ క్యాంపస్ సహాయకురాలు.",
        "Malayalam": "ശുഭ ഉച്ചയ്ക്ക് ശേഷം. ഞാൻ CLARA, നിങ്ങളുടെ ക്യാമ്പസ് സഹായി.",
    },
    "evening": {
        "English": "Good evening. I am CLARA, your campus assistant.",
        "Kannada": ui_text("kn", "welcome.general_narration"),
        "Hindi": "शुभ संध्या। मैं CLARA हूँ, आपकी कैंपस सहायक।",
        "Tamil": "மாலை வணக்கம். நான் கிளாரா, உங்கள் வளாக உதவியாளர்.",
        "Telugu": "శుభ సాయంత్రం. నేను CLARA, మీ క్యాంపస్ సహాయకురాలు.",
        "Malayalam": "ശുഭ സായാഹ്നം. ഞാൻ CLARA, നിങ്ങളുടെ ക്യാമ്പസ് സഹായി.",
    },
}


def guest_name_reply_is_skip(text: str | None) -> bool:
    """True if the user declined to share a name (English-oriented phrases)."""
    if not text or not str(text).strip():
        return False
    key = " ".join(str(text).strip().lower().split())
    return key in _SKIP_GUEST_NAME_PHRASES


def normalize_guest_name(raw: str | None) -> str | None:
    """Strip fillers and return a safe display name, or None if unusable."""
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if guest_name_reply_is_skip(s):
        return None
    s = _GUEST_NAME_PREFIX_RE.sub("", s)
    s = s.strip(" \t\r\n.,!?\"'")
    s = " ".join(s.split())
    if guest_name_reply_is_skip(s):
        return None
    if not s:
        return None
    if len(s) > _GUEST_NAME_MAX_LEN:
        # Never cut an Indic grapheme cluster. Prefer complete name words; an
        # overlong single token is rejected instead of producing broken text.
        words = s.split()
        kept: list[str] = []
        for word in words:
            candidate = " ".join((*kept, word))
            if len(candidate) > _GUEST_NAME_MAX_LEN:
                break
            kept.append(word)
        if not kept:
            return None
        s = " ".join(kept)
    if not s or (s.isdigit() and len(s) > 3):
        return None
    if sum(1 for c in s if c.isalpha()) < 1:
        return None
    return s


def get_name_prompt(language: str | None) -> str:
    # Kannada UI copy is authoritative in ui.json. Resolve it at call time so
    # load_ui_locales() can detect file changes; storing the resolved text in
    # _NAME_PROMPTS_BY_LANGUAGE at module import made a running backend serve
    # stale wording after locale edits.
    if ui_language_key(language) == "kn":
        return ui_text("kn", "welcome.name_prompt")
    lang = language if language in _NAME_PROMPTS_BY_LANGUAGE else "English"
    return _NAME_PROMPTS_BY_LANGUAGE.get(lang, _NAME_PROMPTS_BY_LANGUAGE["English"])


def _validate_language_parity() -> None:
    missing_prompts = [lang for lang in SUPPORTED_LANGUAGES if lang not in _READY_PROMPTS_BY_LANGUAGE]
    if missing_prompts:
        raise RuntimeError(f"Missing ready prompt translations: {', '.join(missing_prompts)}")
    missing_names = [lang for lang in SUPPORTED_LANGUAGES if lang not in _NAME_PROMPTS_BY_LANGUAGE]
    if missing_names:
        raise RuntimeError(f"Missing name prompt translations: {', '.join(missing_names)}")
    missing_ready_named = [lang for lang in SUPPORTED_LANGUAGES if lang not in _READY_PROMPTS_WITH_NAME_BY_LANGUAGE]
    if missing_ready_named:
        raise RuntimeError(f"Missing personalized ready prompt translations: {', '.join(missing_ready_named)}")
    for period, mapping in _GREETINGS_BY_PERIOD.items():
        missing = [lang for lang in SUPPORTED_LANGUAGES if lang not in mapping]
        if missing:
            raise RuntimeError(f"Missing greeting translations for {period}: {', '.join(missing)}")
    for period in _GREETINGS_BY_PERIOD:
        if period not in WAKE_OPENING_GREETING_ENGLISH:
            raise RuntimeError(f"Missing wake opening for period: {period}")


def get_greeting(language: str | None, now: datetime | None = None) -> str:
    period = _time_period(now)
    lang = language if language in _GREETINGS_BY_PERIOD[period] else "English"
    return _GREETINGS_BY_PERIOD[period].get(lang, _GREETINGS_BY_PERIOD[period]["English"])


def get_ready_prompt(language: str | None, preferred_name: str | None = None) -> str:
    lang = language if language in _READY_PROMPTS_BY_LANGUAGE else "English"
    if not (preferred_name or "").strip():
        return _READY_PROMPTS_BY_LANGUAGE.get(lang, _READY_PROMPTS_BY_LANGUAGE["English"])
    name = str(preferred_name).strip()
    template = _READY_PROMPTS_WITH_NAME_BY_LANGUAGE.get(lang, _READY_PROMPTS_WITH_NAME_BY_LANGUAGE["English"])
    return template.replace("{name}", name)


# Backward-compatible default snapshot (evening English).
GREETINGS = {lang: _GREETINGS_BY_PERIOD["evening"][lang] for lang in _GREETINGS_BY_PERIOD["evening"]}

_validate_language_parity()
