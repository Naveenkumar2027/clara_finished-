"""Purpose-tagged multilingual cues. Variants exist only with a semantic reason."""

from __future__ import annotations

from backend.services.content.semantic_vocab.types import VocabEntry

# Canonical topic / scope / unsupported IDs (language-independent).
TOPIC_OVERVIEW = "overview"
TOPIC_HOD = "hod"
TOPIC_FEES = "fees"
TOPIC_ACHIEVEMENTS = "achievements"
TOPIC_PLACEMENTS = "placements"
TOPIC_FACULTY = "faculty"
TOPIC_CONTACT = "contact"
SCOPE_FULL = "full_department"
SCOPE_SINGLE = "single"
UNSUPPORTED_BUS = "bus"
UNSUPPORTED_DOCUMENTS = "documents"

_ENTRIES: tuple[VocabEntry, ...] = (
    # --- TOPIC: fees (English + existing production native/romanized cues) ---
    VocabEntry("fees", "en", "fees", "TOPIC", "english_topic"),
    VocabEntry("fees", "en", "fee", "TOPIC", "english_topic"),
    VocabEntry("fees", "en", "tuition", "TOPIC", "english_topic"),
    VocabEntry("fees", "en", "fee structure", "TOPIC", "english_topic"),
    VocabEntry("fees", "*", "yestu", "ROMANIZED", "kannada_how_much"),
    VocabEntry("fees", "*", "estu", "ROMANIZED", "kannada_how_much"),
    VocabEntry("fees", "*", "eshtu", "ROMANIZED", "kannada_how_much"),
    VocabEntry("fees", "*", "kitna", "ROMANIZED", "hindi_how_much"),
    VocabEntry("fees", "*", "evlo", "ROMANIZED", "tamil_how_much"),
    VocabEntry("fees", "*", "entha", "ROMANIZED", "telugu_how_much"),
    VocabEntry("fees", "*", "ethra", "ROMANIZED", "malayalam_how_much"),
    VocabEntry("fees", "*", "kattanam", "ROMANIZED", "tamil_fee_word"),
    VocabEntry("fees", "kn", "ಶುಲ್ಕ", "TOPIC", "kannada_script_fee"),
    VocabEntry("fees", "kn", "ಶುಲ್ಕಗಳು", "TOPIC", "kannada_script_fee"),
    VocabEntry("fees", "kn", "ಫೀಸ್", "TOPIC", "kannada_script_fee"),
    VocabEntry("fees", "hi", "फीस", "TOPIC", "hindi_script_fee"),
    VocabEntry("fees", "hi", "शुल्क", "TOPIC", "hindi_script_fee"),
    VocabEntry("fees", "ta", "கட்டணம்", "TOPIC", "tamil_script_fee"),
    VocabEntry("fees", "te", "ఫీజు", "TOPIC", "telugu_script_fee"),
    VocabEntry("fees", "ml", "ഫീസ്", "TOPIC", "malayalam_script_fee"),
    # --- TOPIC: HOD ---
    VocabEntry("hod", "en", "hod", "TOPIC", "english_topic"),
    VocabEntry("hod", "en", "h o d", "TOPIC", "english_stt_spaced_acronym"),
    VocabEntry("hod", "en", "hods", "TOPIC", "english_topic_plural"),
    VocabEntry("hod", "en", "head of department", "TOPIC", "english_topic"),
    VocabEntry("hod", "en", "head of the department", "TOPIC", "english_topic"),
    VocabEntry("hod", "en", "head of", "TOPIC", "english_topic"),
    VocabEntry("hod", "kn", "ಮುಖ್ಯಸ್ಥರು", "TOPIC", "kannada_script_hod"),
    VocabEntry("hod", "kn", "ಮುಖ್ಯಸ್ಥ", "TOPIC", "kannada_script_hod"),
    VocabEntry("hod", "kn", "ವಿಭಾಗದ ಮುಖ್ಯಸ್ಥರು", "TOPIC", "kannada_script_hod"),
    # Observed Kannada browser-STT variants of HOD / head of department.
    VocabEntry("hod", "kn", "ಹೋಡ್", "TOPIC", "kannada_stt_hod"),
    VocabEntry("hod", "kn", "ಹೆಡ್", "TOPIC", "kannada_stt_head"),
    VocabEntry("hod", "kn", "ಹೆಚ್ಒಡಿ", "TOPIC", "kannada_stt_hod_spelled"),
    VocabEntry("hod", "kn", "ಹೆಚ್ಓಡಿ", "TOPIC", "kannada_stt_hod_spelled"),
    VocabEntry("hod", "kn", "ವಿಭಾಗದ ಹೆಡ್", "TOPIC", "kannada_stt_department_head"),
    VocabEntry("hod", "kn", "ಸಚಿವರು", "TOPIC", "kannada_stt_hod_misrecognition", "high"),
    VocabEntry("hod", "hi", "विभागाध्यक्ष", "TOPIC", "hindi_locale_hod_title"),
    VocabEntry("hod", "hi", "विभाग प्रमुख", "TOPIC", "hindi_script_hod"),
    VocabEntry("hod", "hi", "विभाग के प्रमुख", "TOPIC", "hindi_script_hod_postposition"),
    VocabEntry("hod", "hi", "एचओडी", "TOPIC", "hindi_stt_hod_spelled"),
    VocabEntry("hod", "hi", "एच ओ डी", "TOPIC", "hindi_stt_hod_spaced"),
    VocabEntry("hod", "hi", "होद", "TOPIC", "hindi_stt_hod_phonetic"),
    VocabEntry("hod", "ta", "துறைத் தலைவர்", "TOPIC", "tamil_locale_hod_title"),
    VocabEntry("hod", "te", "విభాగం అధిపతి", "TOPIC", "telugu_locale_hod_title"),
    VocabEntry("hod", "ml", "വിഭാഗത്തിന്റെ മേധാവി", "TOPIC", "malayalam_locale_hod_title"),
    VocabEntry("hod", "kn", "ಎಚ್ ಓ ಡಿ", "TOPIC", "kannada_stt_hod_spelled"),
    VocabEntry("hod", "kn", "ಹೆಚ್ ಓ ಡಿ", "TOPIC", "kannada_stt_hod_spelled"),
    VocabEntry("hod", "*", "yaaru", "QUESTION", "kannada_who", "low"),
    VocabEntry("hod", "*", "yaar", "QUESTION", "tamil_who", "low"),
    VocabEntry("hod", "*", "kaun", "QUESTION", "hindi_who", "low"),
    VocabEntry("hod", "*", "evaru", "QUESTION", "telugu_who", "low"),
    VocabEntry("hod", "*", "aaranu", "QUESTION", "malayalam_who", "low"),
    # --- TOPIC: overview (explicit word only; generic "about" stays a SCOPE cue) ---
    VocabEntry("overview", "en", "overview", "TOPIC", "english_topic"),
    VocabEntry("overview", "en", "over view", "TOPIC", "english_topic"),
    VocabEntry("overview", "kn", "ಅವಲೋಕನ", "TOPIC", "kannada_script_overview"),
    VocabEntry("overview", "hi", "अवलोकन", "TOPIC", "hindi_script_overview"),
    VocabEntry("overview", "ta", "கண்ணோட்டம்", "TOPIC", "tamil_script_overview"),
    VocabEntry("overview", "te", "అవలోకనం", "TOPIC", "telugu_script_overview"),
    VocabEntry("overview", "ml", "അവലോകനം", "TOPIC", "malayalam_script_overview"),
    # --- TOPIC: placements ---
    VocabEntry("placements", "en", "placements", "TOPIC", "english_topic"),
    VocabEntry("placements", "en", "placement", "TOPIC", "english_topic"),
    VocabEntry("placements", "kn", "ಪ್ಲೇಸ್‌ಮೆಂಟ್", "TOPIC", "kannada_script_placement"),
    VocabEntry("placements", "kn", "ಪ್ಲೇಸ್ಮೆಂಟ್", "TOPIC", "kannada_script_placement"),
    VocabEntry("placements", "kn", "ಉದ್ಯೋಗಾವಕಾಶ", "TOPIC", "kannada_script_placement"),
    VocabEntry("placements", "hi", "प्लेसमेंट", "TOPIC", "hindi_script_placement"),
    VocabEntry("placements", "ta", "பிளேஸ்மென்ட்", "TOPIC", "tamil_script_placement"),
    VocabEntry("placements", "ta", "வேலைவாய்ப்பு", "TOPIC", "tamil_script_placement"),
    VocabEntry("placements", "te", "ప్లేస్‌మెంట్", "TOPIC", "telugu_script_placement"),
    VocabEntry("placements", "ml", "പ്ലേസ്‌മെന്റ്", "TOPIC", "malayalam_script_placement"),
    VocabEntry("placements", "ml", "പ്ലേസ്മെന്റ്", "TOPIC", "malayalam_script_placement"),
    # These concepts are parsed even when a deployment has no corresponding
    # ContentUnit. Unit selection can then report CARD_NOT_REGISTERED instead of
    # silently opening the department overview.
    VocabEntry("faculty", "en", "faculty", "TOPIC", "english_topic"),
    VocabEntry("faculty", "en", "teachers", "TOPIC", "english_topic"),
    VocabEntry("faculty", "kn", "ಬೋಧಕರು", "TOPIC", "kannada_script_faculty"),
    VocabEntry("faculty", "hi", "शिक्षक", "TOPIC", "hindi_script_faculty"),
    VocabEntry("faculty", "hi", "अध्यापक", "TOPIC", "hindi_script_faculty"),
    VocabEntry("faculty", "hi", "फैकल्टी", "TOPIC", "hindi_script_faculty_loanword"),
    VocabEntry("faculty", "te", "అధ్యాపకులు", "TOPIC", "telugu_script_faculty"),
    VocabEntry("faculty", "ta", "ஆசிரியர்கள்", "TOPIC", "tamil_script_faculty"),
    VocabEntry("faculty", "ml", "അധ്യാപകർ", "TOPIC", "malayalam_script_faculty"),
    VocabEntry("contact", "en", "contact details", "TOPIC", "english_topic"),
    VocabEntry("contact", "en", "contact", "TOPIC", "english_topic"),
    VocabEntry("contact", "kn", "ಸಂಪರ್ಕ", "TOPIC", "kannada_script_contact"),
    VocabEntry("contact", "hi", "संपर्क", "TOPIC", "hindi_script_contact"),
    VocabEntry("contact", "te", "సంప్రదింపు", "TOPIC", "telugu_script_contact"),
    VocabEntry("contact", "ta", "தொடர்பு", "TOPIC", "tamil_script_contact"),
    VocabEntry("contact", "ml", "ബന്ധപ്പെടാൻ", "TOPIC", "malayalam_script_contact"),
    # --- TOPIC: achievements (English-only in Stage A evidence; keep purpose-tagged) ---
    VocabEntry("achievements", "en", "achievements", "TOPIC", "english_topic"),
    VocabEntry("achievements", "en", "achievement", "TOPIC", "english_topic"),
    VocabEntry("achievements", "en", "rankings", "TOPIC", "english_topic"),
    VocabEntry("achievements", "en", "ranking", "TOPIC", "english_topic"),
    VocabEntry("achievements", "kn", "ಸಾಧನೆ", "TOPIC", "kannada_script_achievement"),
    VocabEntry("achievements", "hi", "उपलब्धि", "TOPIC", "hindi_script_achievement"),
    VocabEntry("achievements", "ta", "சாதனை", "TOPIC", "tamil_script_achievement"),
    VocabEntry("achievements", "te", "సాధన", "TOPIC", "telugu_script_achievement"),
    VocabEntry("achievements", "ml", "നേട്ടം", "TOPIC", "malayalam_script_achievement"),
    # --- SCOPE: full-department overview (not generic "about"/"overview") ---
    VocabEntry("full_department", "en", "tell me about", "SCOPE", "full_overview"),
    VocabEntry("full_department", "en", "tell me", "SCOPE", "full_overview"),
    VocabEntry("full_department", "en", "explain", "SCOPE", "full_overview"),
    VocabEntry("full_department", "en", "describe", "SCOPE", "full_overview"),
    VocabEntry("full_department", "*", "bagge", "CODE-SWITCH", "kannada_about"),
    VocabEntry("full_department", "*", "helu", "CODE-SWITCH", "kannada_tell"),
    VocabEntry("full_department", "*", "heli", "CODE-SWITCH", "kannada_tell"),
    VocabEntry("full_department", "*", "baare", "CODE-SWITCH", "hindi_about"),
    VocabEntry("full_department", "*", "batao", "CODE-SWITCH", "hindi_tell"),
    VocabEntry("full_department", "*", "pattri", "CODE-SWITCH", "tamil_about"),
    VocabEntry("full_department", "*", "tilisi", "CODE-SWITCH", "tamil_tell"),
    VocabEntry("full_department", "*", "gurunchi", "CODE-SWITCH", "telugu_about"),
    VocabEntry("full_department", "*", "gurinchi", "CODE-SWITCH", "telugu_about"),
    VocabEntry("full_department", "*", "kurichu", "CODE-SWITCH", "telugu_tell"),
    VocabEntry("full_department", "*", "parayoo", "CODE-SWITCH", "malayalam_tell"),
    VocabEntry("full_department", "*", "paray", "CODE-SWITCH", "malayalam_tell"),
    # --- UNSUPPORTED for unit selector ---
    VocabEntry("bus", "en", "bus routes", "UNSUPPORTED", "not_unit_owned"),
    VocabEntry("bus", "en", "bus route", "UNSUPPORTED", "not_unit_owned"),
    VocabEntry("documents", "en", "documents", "UNSUPPORTED", "not_unit_owned"),
    VocabEntry("documents", "en", "document", "UNSUPPORTED", "not_unit_owned"),
    # --- DEPARTMENT aliases (identity via exclusive longest-span, never substring) ---
    VocabEntry("cse_ds", "en", "cse data science", "DEPARTMENT", "compound_identity"),
    VocabEntry("cse_ds", "en", "cse (data science)", "DEPARTMENT", "canonical_label"),
    VocabEntry("cse_ds", "en", "cse datascience", "DEPARTMENT", "compound_identity"),
    VocabEntry("cse_ds", "en", "data science", "DEPARTMENT", "compound_identity"),
    VocabEntry("cse_ds", "en", "datascience", "DEPARTMENT", "compound_identity"),
    VocabEntry("cse_ds", "en", "cse ds", "DEPARTMENT", "compound_identity"),
    VocabEntry("cse_ds", "en", "cse_ds", "DEPARTMENT", "json_key"),
    VocabEntry("cse_ds", "kn", "ಡೇಟಾ ಸಂಖ್ಯೆ", "DEPARTMENT", "kannada_stt_data_science_misrecognition", "high"),
    VocabEntry("cse_ds", "ml", "ഡാറ്റ സയൻസ്", "DEPARTMENT", "malayalam_common_name"),
    VocabEntry("cse_aiml", "en", "cse ai ml", "DEPARTMENT", "compound_identity"),
    VocabEntry("cse_aiml", "en", "cse (ai & ml)", "DEPARTMENT", "canonical_label"),
    VocabEntry("cse_aiml", "en", "cse aiml", "DEPARTMENT", "compound_identity"),
    VocabEntry("cse_aiml", "en", "ai ml", "DEPARTMENT", "compound_identity"),
    VocabEntry("cse_aiml", "en", "ai & ml", "DEPARTMENT", "compound_identity"),
    VocabEntry("cse_aiml", "en", "aiml", "DEPARTMENT", "compound_identity"),
    VocabEntry("cse_aiml", "en", "cse_aiml", "DEPARTMENT", "json_key"),
    VocabEntry("cse_cysec", "en", "cse cyber security", "DEPARTMENT", "compound_identity"),
    VocabEntry("cse_cysec", "en", "cyber security", "DEPARTMENT", "compound_identity"),
    VocabEntry("cse_cysec", "en", "cybersecurity", "DEPARTMENT", "compound_identity"),
    VocabEntry("cse_cysec", "en", "cse_cysec", "DEPARTMENT", "json_key"),
    VocabEntry("cse_bs", "en", "cse business systems", "DEPARTMENT", "compound_identity"),
    VocabEntry("cse_bs", "en", "business systems", "DEPARTMENT", "compound_identity"),
    VocabEntry("cse_bs", "en", "cse_bs", "DEPARTMENT", "json_key"),
    VocabEntry("cse", "en", "computer science and engineering", "DEPARTMENT", "full_name"),
    VocabEntry("cse", "en", "computer science & engineering", "DEPARTMENT", "full_name"),
    VocabEntry("cse", "en", "computer science engineering", "DEPARTMENT", "full_name"),
    VocabEntry("cse", "en", "computer science", "DEPARTMENT", "full_name"),
    VocabEntry("cse", "en", "cse", "DEPARTMENT", "acronym"),
    VocabEntry("cse", "en", "c s e", "DEPARTMENT", "english_stt_spaced_acronym"),
    VocabEntry("cse", "kn", "ಸಿಎಸ್ಇ", "DEPARTMENT", "kannada_script_acronym"),
    VocabEntry("cse", "kn", "ಸಿಎಸ್‌ಇ", "DEPARTMENT", "kannada_script_acronym"),
    VocabEntry("cse", "kn", "ಸಿಎಸ್ ಇ", "DEPARTMENT", "kannada_spaced_acronym"),
    VocabEntry("cse", "hi", "सीएसई", "DEPARTMENT", "hindi_script_acronym"),
    VocabEntry("cse", "hi", "सी एस ई", "DEPARTMENT", "hindi_spaced_acronym"),
    VocabEntry("cse", "hi", "कंप्यूटर साइंस", "DEPARTMENT", "hindi_common_name"),
    VocabEntry("ise", "en", "information science", "DEPARTMENT", "full_name"),
    VocabEntry("ise", "en", "ise", "DEPARTMENT", "acronym"),
    VocabEntry("ece", "en", "electronics", "DEPARTMENT", "full_name", "medium"),
    VocabEntry("ece", "en", "ece", "DEPARTMENT", "acronym"),
    VocabEntry("ece", "en", "e c e", "DEPARTMENT", "english_stt_spaced_acronym"),
    VocabEntry("ece", "hi", "ईसीई", "DEPARTMENT", "hindi_script_acronym"),
    VocabEntry("ece", "hi", "ई सी ई", "DEPARTMENT", "hindi_spaced_acronym"),
    VocabEntry("civil", "en", "civil", "DEPARTMENT", "acronym"),
    VocabEntry("mechanical", "en", "mechanical", "DEPARTMENT", "full_name"),
    VocabEntry("mechanical", "hi", "मेकेनिकल", "DEPARTMENT", "hindi_stt_variant"),
    VocabEntry("mechanical", "hi", "मैकैनिकल", "DEPARTMENT", "hindi_stt_variant"),
    VocabEntry("mba", "en", "mba", "DEPARTMENT", "acronym"),
    VocabEntry("mba", "hi", "एमबीए", "DEPARTMENT", "hindi_script_acronym"),
    VocabEntry("mba", "hi", "एम बी ए", "DEPARTMENT", "hindi_spaced_acronym"),
    VocabEntry("basic_sciences", "en", "basic sciences", "DEPARTMENT", "full_name"),
)


def all_entries() -> tuple[VocabEntry, ...]:
    return _ENTRIES


def entries_for(*, category: str | None = None, canonical: str | None = None) -> tuple[VocabEntry, ...]:
    rows = _ENTRIES
    if category:
        rows = tuple(e for e in rows if e.category == category)
    if canonical:
        rows = tuple(e for e in rows if e.canonical == canonical)
    return rows
