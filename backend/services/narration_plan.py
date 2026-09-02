"""Deterministic narration segments aligned with on-screen kiosk cards (parity with frontend TS)."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.app.audio_utils import normalize_tts_pronunciation

from backend.services.answer_generation import (
    _CANONICAL_DEPARTMENT_TO_JSON_KEY,
    DEPARTMENT_JSON_KEY_ORDER,
    INTENT_ADMISSIONS,
    INTENT_COLLEGE_OVERVIEW,
    INTENT_COURSE_MENU,
    INTENT_DEPARTMENT_FEES,
    INTENT_DEPARTMENT_OVERVIEW,
    INTENT_DEPARTMENT_COMPARISON,
    INTENT_DOCUMENTS,
    INTENT_HOD_PROFILE,
    INTENT_PLACEMENTS,
    INTENT_PRINCIPAL_PROFILE,
    INTENT_TRUSTEES_PROFILE,
    INTENT_VICE_PRINCIPAL_PROFILE,
    department_label_to_json_key,
    get_course_menu_spoken_prompt,
    load_locale_data_for_lang_key,
    locale_file_id_for_lang_key,
    _wants_all_departments_narration,
)
from backend.config.settings import ENABLE_NARRATION_PLAN as SETTINGS_ENABLE_FLAG
from backend.services.ui_localization import ui_text

logger = logging.getLogger(__name__)

STATIC_CARDS_PATH = Path(__file__).resolve().parent.parent / "data" / "narration" / "static_cards.json"
COMPARISON_DEFAULTS_PATH = Path(__file__).resolve().parent.parent / "data" / "comparison_insight_defaults.json"

LANG_KEY_FALLBACK_ORDER = ("en", "hi", "kn", "ta", "te", "ml")

_FEES_AMOUNT_BY_KEY: dict[str, int] = {
    "cse": 325000,
    "cse_aiml": 325000,
    "cse_cysec": 325000,
    "cse_ds": 300000,
    "cse_bs": 275000,
    "ece": 250000,
    "civil": 125000,
    "mechanical": 125000,
}

_DEPT_DISPLAY: dict[str, dict[str, str]] = {
    "en": {
        "cse": "CSE",
        "ise": "ISE",
        "cse_aiml": "CSE (AI & ML)",
        "cse_ds": "CSE (Data Science)",
        "cse_cysec": "CSE (Cyber Security)",
        "cse_bs": "CSE (Business Systems)",
        "ece": "ECE",
        "civil": "Civil",
        "mechanical": "Mechanical",
        "mba": "MBA",
        "basic_sciences": "Basic Sciences",
    },
    "kn": {
        "cse": "ಕಂಪ್ಯೂಟರ್ ಸೈನ್ಸ್ (CSE)",
        "ise": "ಐಎಸ್‌ಇ (ISE)",
        "cse_aiml": "CSE (AI & ML)",
        "cse_ds": "CSE (ಡೇಟಾ ಸೈನ್ಸ್)",
        "cse_cysec": "CSE (ಸೈಬರ್ ಸೆಕ್ಯುರಿಟಿ)",
        "cse_bs": "CSE (ಬಿಸಿನೆಸ್ ಸಿಸ್ಟಮ್ಸ್)",
        "ece": "ಎಲೆಕ್ಟ್ರಾನಿಕ್ಸ್ (ECE)",
        "civil": "ಸಿವಿಲ್",
        "mechanical": "ಮೆಕಾನಿಕಲ್",
        "mba": "MBA (MBA)",
        "basic_sciences": "ಮೂಲ ವಿಜ್ಞಾನಗಳು",
    },
    "hi": {
        "cse": "कंप्यूटर साइंस (CSE)",
        "ise": "आईएसई (ISE)",
        "cse_aiml": "CSE (AI & ML)",
        "cse_ds": "CSE (डेटा साइंस)",
        "cse_cysec": "CSE (साइबर सिक्योरिटी)",
        "cse_bs": "CSE (बिज़नेस सिस्टम्स)",
        "ece": "इलेक्ट्रॉनिक्स (ECE)",
        "civil": "सिविल",
        "mechanical": "मैकेनिकल",
        "mba": "MBA (MBA)",
        "basic_sciences": "बेसिक साइंसेस",
    },
    "ta": {
        "cse": "கம்ப்யூட்டர் சயின்ஸ் (CSE)",
        "ise": "ஐஎஸ்இ (ISE)",
        "cse_aiml": "CSE (AI & ML)",
        "cse_ds": "CSE (டேட்டா சயின்ஸ்)",
        "cse_cysec": "CSE (சைபர் செக்யூரிட்டி)",
        "cse_bs": "CSE (பிஸினஸ் சிஸ்டம்ஸ்)",
        "ece": "எலெக்ட்ரானிக்ஸ் (ECE)",
        "civil": "சிவில்",
        "mechanical": "மெக்கானிக்கல்",
        "mba": "MBA (MBA)",
        "basic_sciences": "அடிப்படை அறிவியல்",
    },
    "te": {
        "cse": "కంప్యూటర్ సైన్స్ (CSE)",
        "ise": "ఐఎస్‌ఇ (ISE)",
        "cse_aiml": "CSE (AI & ML)",
        "cse_ds": "CSE (డేటా సైన్స్)",
        "cse_cysec": "CSE (సైబర్ సెక్యూరిటీ)",
        "cse_bs": "CSE (బిజినెస్ సిస్టమ్స్)",
        "ece": "ఎలక్ట్రానిక్స్ (ECE)",
        "civil": "సివిల్",
        "mechanical": "మెకానికల్",
        "mba": "MBA (MBA)",
        "basic_sciences": "బేసిక్ సైన్సెస్",
    },
    "ml": {
        "cse": "കമ്പ്യൂട്ടർ സയൻസ് (CSE)",
        "ise": "ഐഎസ്ഇ (ISE)",
        "cse_aiml": "CSE (AI & ML)",
        "cse_ds": "CSE (ഡാറ്റ സയൻസ്)",
        "cse_cysec": "CSE (സൈബർ സെക്യൂരിറ്റി)",
        "cse_bs": "CSE (ബിസിനസ് സിസ്റ്റംസ്)",
        "ece": "ഇലക്ട്രോണിക്സ് (ECE)",
        "civil": "സിവിൽ",
        "mechanical": "മെക്കാനിക്കൽ",
        "mba": "MBA (MBA)",
        "basic_sciences": "ബേസിക് സയൻസസ്",
    },
}

_FEES_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "title": "Fees",
        "description": "Department-wise annual fee reference for the current academic intake.",
        "selectedDepartment": "Selected Department",
        "department": "Department",
        "managementQuotaFee": "Management Quota Fee",
        "otherQuotas": "Other Quotas",
        "officeContact": "Please contact the admission office for precise information.",
    },
    "kn": {
        "title": ui_text("kn", "cards.fees"),
        "description": ui_text("kn", "cards.fee_description"),
        "selectedDepartment": ui_text("kn", "cards.selected_department"),
        "department": ui_text("kn", "cards.department"),
        "managementQuotaFee": ui_text("kn", "cards.management_quota_fee"),
        "otherQuotas": ui_text("kn", "cards.other_quotas"),
        "officeContact": ui_text("kn", "cards.admission_office_contact"),
    },
    "hi": {
        "title": "फीस",
        "description": "वर्तमान शैक्षणिक प्रवेश के लिए विभाग-वार वार्षिक फीस संदर्भ।",
        "selectedDepartment": "चयनित विभाग",
        "department": "विभाग",
        "managementQuotaFee": "मैनेजमेंट कोटा फीस",
        "otherQuotas": "अन्य कोटा",
        "officeContact": "सटीक जानकारी के लिए कृपया एडमिशन ऑफिस से संपर्क करें।",
    },
    "ta": {
        "title": "கட்டணம்",
        "description": "தற்போதைய கல்வி சேர்க்கைக்கான துறைவாரியான ஆண்டு கட்டண குறிப்புகள்.",
        "selectedDepartment": "தேர்ந்தெடுத்த துறை",
        "department": "துறை",
        "managementQuotaFee": "மேலாண்மை ஒதுக்கீடு கட்டணம்",
        "otherQuotas": "மற்ற ஒதுக்கீடுகள்",
        "officeContact": "துல்லியமான தகவலுக்கு சேர்க்கை அலுவலகத்தை தொடர்புகொள்ளவும்.",
    },
    "te": {
        "title": "ఫీజులు",
        "description": "ప్రస్తుత విద్యా ప్రవేశానికి విభాగాల వారీగా వార్షిక ఫీజు సూచన.",
        "selectedDepartment": "ఎంచుకున్న విభాగం",
        "department": "విభాగం",
        "managementQuotaFee": "మేనేజ్‌మెంట్ కోటా ఫీజు",
        "otherQuotas": "ఇతర కోటాలు",
        "officeContact": "ఖచ్చితమైన సమాచారం కోసం అడ్మిషన్ కార్యాలయాన్ని సంప్రదించండి.",
    },
    "ml": {
        "title": "ഫീസ്",
        "description": "നിലവിലെ അക്കാദമിക് അഡ്മിഷനുള്ള വിഭാഗംപ്രകാരമുള്ള വാർഷിക ഫീസ് വിവരം.",
        "selectedDepartment": "തിരഞ്ഞെടുത്ത വിഭാഗം",
        "department": "വിഭാഗം",
        "managementQuotaFee": "മാനേജ്മെന്റ് ക്വോട്ട ഫീസ്",
        "otherQuotas": "മറ്റ് ക്വോട്ടകൾ",
        "officeContact": "കൃത്യമായ വിവരങ്ങൾക്ക് അഡ്മിഷൻ ഓഫീസുമായി ബന്ധപ്പെടുക.",
    },
}

DOCUMENT_ITEMS: dict[str, list[str]] = {
    "en": [
        "10th Marks Card",
        "12th / II PUC Marks Card",
        "CET / COMEDK Rank Card + Allotment Letter",
        "Transfer Certificate (TC)",
        "Conduct / Character Certificate",
        "Caste / Income Certificate (if applicable)",
        "Aadhaar Card Copy",
        "Passport Size Photos (6–10)",
        "Migration Certificate (for other board students)",
        "VTU Eligibility Certificate (if required)",
    ],
    "kn": [
        ui_text("kn", "documents.items.marks_10"),
        ui_text("kn", "documents.items.marks_12"),
        ui_text("kn", "documents.items.rank_allotment"),
        ui_text("kn", "documents.items.transfer"),
        ui_text("kn", "documents.items.conduct"),
        ui_text("kn", "documents.items.caste_income"),
        ui_text("kn", "documents.items.aadhaar"),
        ui_text("kn", "documents.items.photos"),
        ui_text("kn", "documents.items.migration"),
        ui_text("kn", "documents.items.vtu_eligibility"),
    ],
    "hi": [
        "दसवीं की मार्क्स कार्ड",
        "बारहवीं या द्वितीय पीयूसी मार्क्स कार्ड",
        "सीईटी या कॉमेडके रैंक कार्ड और अलॉटमेंट लेटर",
        "ट्रांसफर सर्टिफिकेट",
        "कंडक्ट या कैरेक्टर सर्टिफिकेट",
        "आवश्यक होने पर जाति या आय प्रमाणपत्र",
        "आधार कार्ड की प्रति",
        "पासपोर्ट साइज फोटो छह से दस",
        "अन्य बोर्ड छात्रों के लिए माइग्रेशन सर्टिफिकेट",
        "आवश्यक होने पर वीटीयू एलिजिबिलिटी सर्टिफिकेट",
    ],
    "ta": [
        "10ஆம் வகுப்பு மதிப்பெண் அட்டை",
        "12ஆம் அல்லது இரண்டாம் PUC மதிப்பெண் அட்டை",
        "CET அல்லது COMEDK தரவரிசை அட்டை மற்றும் ஒதுக்கீட்டு கடிதம்",
        "மாற்றுச் சான்றிதழ்",
        "நடத்தை அல்லது குணச் சான்றிதழ்",
        "தேவையெனில் சாதி அல்லது வருமானச் சான்றிதழ்",
        "ஆதார் அட்டை நகல்",
        "பாஸ்போர்ட் அளவு புகைப்படங்கள் ஆறு முதல் பத்து",
        "பிற வாரிய மாணவர்களுக்கு மைக்ரேஷன் சான்றிதழ்",
        "தேவையெனில் VTU தகுதி சான்றிதழ்",
    ],
    "te": [
        "10వ తరగతి మార్క్స్ కార్డు",
        "12వ లేదా II PUC మార్క్స్ కార్డు",
        "CET లేదా COMEDK ర్యాంక్ కార్డు మరియు అలాట్‌మెంట్ లెటర్",
        "ట్రాన్స్‌ఫర్ సర్టిఫికేట్",
        "కండక్ట్ లేదా క్యారెక్టర్ సర్టిఫికేట్",
        "అవసరమైతే కులం లేదా ఆదాయం సర్టిఫికేట్",
        "ఆధార్ కార్డు కాపీ",
        "పాస్‌పోర్ట్ సైజ్ ఫోటోలు ఆరు నుండి పది",
        "ఇతర బోర్డు విద్యార్థులకు మైగ్రేషన్ సర్టిఫికేట్",
        "అవసరమైతే VTU ఎలిజిబిలిటీ సర్టిఫికేट్",
    ],
    "ml": [
        "10ാം ക്ലാസ് മാർക്ക് കാർഡ്",
        "12ാം അല്ലെങ്കിൽ II PUC മാർക്ക് കാർഡ്",
        "CET അല്ലെങ്കിൽ COMEDK റാങ്ക് കാർഡ് കൂടാതെ അലോട്ട്മെന്റ് ലെറ്റർ",
        "ട്രാൻസ്ഫർ സർട്ടിഫിക്കറ്റ്",
        "കണ്ടക്റ്റ് അല്ലെങ്കിൽ കാരക്ടർ സർട്ടിഫിക്കറ്റ്",
        "ആവശ്യമായാൽ ജാതി അല്ലെങ്കിൽ വരുമാന സർട്ടിഫിക്കറ്റ്",
        "ആധാർ കാർഡ് പകർപ്പ്",
        "പാസ്‌പോർട്ട് സൈസ് ഫോട്ടോകൾ ആറ് മുതൽ പത്ത് വരെ",
        "മറ്റ് ബോർഡ് വിദ്യാർത്ഥികൾക്ക് മൈഗ്രേഷൻ സർട്ടിഫിക്കറ്റ്",
        "ആവശ്യമായാൽ VTU യോഗ്യത സർട്ടിഫിക്കറ്റ്",
    ],
}

DOCUMENT_TITLES: dict[str, str] = {
    "en": "Required Documents",
    "kn": ui_text("kn", "documents.title"),
    "hi": "आवश्यक दस्तावेज़",
    "ta": "தேவையான ஆவணங்கள்",
    "te": "అవసరమైన పత్రాలు",
    "ml": "ആവശ്യമായ രേഖകൾ",
}


def _effective_lang(locale_id: str) -> str:
    lid = locale_id.lower()
    return lid if lid in LANG_KEY_FALLBACK_ORDER else "en"


LANG_KEY_TO_DISPLAY_NAME: dict[str | None, str] = {
    None: "English",
    "en": "English",
    "hi": "Hindi",
    "kn": "Kannada",
    "ta": "Tamil",
    "te": "Telugu",
    "ml": "Malayalam",
}


@lru_cache(maxsize=1)
def _load_static_cards() -> dict[str, Any]:
    if not STATIC_CARDS_PATH.is_file():
        logger.warning("static_cards.json missing: %s", STATIC_CARDS_PATH)
        return {}
    try:
        return json.loads(STATIC_CARDS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not parse static_cards.json: %s", exc)
        return {}


@lru_cache(maxsize=2)
def _load_comparison_defaults() -> dict[str, Any]:
    if not COMPARISON_DEFAULTS_PATH.is_file():
        logger.warning("comparison_insight_defaults.json missing: %s", COMPARISON_DEFAULTS_PATH)
        return {}
    try:
        return json.loads(COMPARISON_DEFAULTS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not parse comparison_insight_defaults.json: %s", exc)
        return {}


def _clean(val: Any) -> str:
    return re.sub(r"\s+", " ", str(val or "").strip())


def _dedupe_join(lines: list[str]) -> str:
    seen: set[str] = set()
    out: list[str] = []
    for ln in lines:
        k = ln.lower().strip()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(ln.strip())
    return "\n".join(out)


def _split_bullets(value: str) -> list[str]:
    raw = (value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not raw:
        return []
    out: list[str] = []
    for line in raw.split("\n"):
        ln = line.strip()
        ln = re.sub(r"^[•\-\u2022]+\s*", "", ln).strip()
        if ln:
            out.append(ln)
    return out


def _compact_list(items: list[str], *, max_items: int) -> str:
    picked = [it.strip() for it in items if it and it.strip()][:max_items]
    if not picked:
        return ""
    return ", ".join(picked)


_STOPWORDS = {
    "and",
    "or",
    "with",
    "for",
    "to",
    "of",
    "in",
    "on",
    "the",
    "a",
    "an",
    "your",
    "student",
    "roles",
    "role",
    "positions",
    "position",
    "teams",
    "team",
    "basics",
    "fundamentals",
    "foundations",
}


def _short_phrase(value: str, *, max_words: int = 3) -> str:
    """
    Aggressive compression for comparison narration:
    keep 2–3 keywords per bullet so the full compare fits under 20–30s.
    """
    s = _clean(value)
    if not s:
        return ""
    # Split on common separators and keep the first meaningful chunk.
    s = re.split(r"[/,;]|\\band\\b|\\b&\\b", s, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    words = [w for w in re.split(r"\\s+", s) if w]
    kept: list[str] = []
    for w in words:
        w0 = re.sub(r"[^a-zA-Z0-9+]+", "", w).strip()
        if not w0:
            continue
        if w0.lower() in _STOPWORDS:
            continue
        kept.append(w0)
        if len(kept) >= max_words:
            break
    if not kept:
        return words[0] if words else ""
    return " ".join(kept)


def _format_inr(value: int) -> str:
    return f"₹{value:,}"


def _clip_caption(text: str, max_len: int = 240) -> str:
    s = _clean(text)
    if len(s) <= max_len:
        return s
    # Only emit complete words. This also prevents truncation between a
    # Kannada base character and its dependent vowel/virama marks.
    window = s[: max_len - 1]
    boundaries = [window.rfind(mark) for mark in (" ", ".", "?", "!", ";", ",")]
    boundary = max(boundaries)
    if boundary < max_len // 2:
        return s
    return window[:boundary].rstrip() + "…"


def _pick_department_prompt_hod(locale_id: str) -> str:
    lk = _effective_lang(locale_id)
    return {
        "en": "Please say or choose a department to hear the Head of Department and vision.",
        "kn": ui_text("kn", "clarification.hod_card"),
        "hi": "विभाग प्रमुख और विज़न सुनने के लिए कृपया विभाग का नाम बताएं या चुनें।",
        "ta": "தலைமை மற்றும் பார்வைக்கு துறையைச் சொல்லுங்கள் அல்லது தேர்ந்தெடுக்கவும்.",
        "te": "HOD మరియు దృష్టికోసం దయచేసి విభాగం పేరు చెప్పండి లేదా ఎంచుకోండి.",
        "ml": "HOD-യും വീക്ഷണവും കേൾക്കാൻ ഒരു വിഭാഗം പേര് പറയുക അല്ലെങ്കിൽ തിരഞ്ഞെടുക്കുക.",
    }.get(lk, "Please say or choose a department to hear the Head of Department and vision.")


def _pick_department_prompt_fees(locale_id: str) -> str:
    lk = _effective_lang(locale_id)
    return {
        "en": "Tap or say a department to focus fees, or listen to the full fee overview on screen.",
        "kn": ui_text("kn", "clarification.fees_card"),
        "hi": "शुल्क के लिए विभाग चुनें, या पूरी सूची स्क्रीन पर देखें।",
        "ta": "கட்டணத்திற்கு துறையைத் தேர்ந்தெடுக்கவும், அல்லது முழு பட்டியலைத் திரையில் பார்க்கவும்.",
        "te": "ఫీజు కోసం విభాగాన్ని ఎంచుకోండి లేదా పూర్తి జాబితాను స్క్రీన్‌లో చూడండి.",
        "ml": "ഫീസിനായി ഒരു വിഭാഗം തിരഞ്ഞെടുക്കുക, അല്ലെങ്കിൽ സ്ക്രീനിലെ മുഴുവൻ പട്ടിക കാണുക.",
    }.get(lk, "Tap or say a department to focus fees, or listen to the full fee overview on screen.")


def _fallback_college_card_line(locale_id: str) -> str:
    lk = _effective_lang(locale_id)
    return {
        "en": "College overview. Please read the highlights on the screen.",
        "kn": "ಕಾಲೇಜು ಅವಲೋಕನ. ಪ್ರಮುಖ ಅಂಶಗಳನ್ನು ಪರದೆಯಲ್ಲಿ ನೋಡಿ.",
        "hi": "कॉलेज अवलोकन। मुख्य बिंदु स्क्रीन पर देखें।",
        "ta": "கல்லூரி அறிமுகம். முக்கிய விவரங்களைத் திரையில் பார்க்கவும்.",
        "te": "కాలేజ్ అవలోకనం. ప్రధాన అంశాలను స్క్రీన్‌లో చూడండి.",
        "ml": "കോളേജ് അവലോകനം. പ്രധാന കാര്യങ്ങൾ സ്ക്രീനിൽ കാണുക.",
    }.get(lk, "College overview. Please read the highlights on the screen.")


def _fallback_trustees_card_line(locale_id: str) -> str:
    lk = _effective_lang(locale_id)
    return {
        "en": "Trustees and governance. Please see the cards on screen.",
        "kn": "ಟ್ರಸ್ಟಿಗಳು ಮತ್ತು ಆಡಳಿತ. ಪರದೆಯಲ್ಲಿರುವ ಕಾರ್ಡ್‌ಗಳನ್ನು ನೋಡಿ.",
        "hi": "ट्रस्टी और प्रशासन। स्क्रीन पर कार्ड देखें।",
        "ta": "ரொக்கிகள் மற்றும் நிர்வாகம். திரையில் அட்டைகளைப் பார்க்கவும்.",
        "te": "ట్రస్టీలు మరియు నిర్వహణ. స్క్రీన్‌పై కార్డ్‌లను చూడండి.",
        "ml": "ട്രസ്റ്റികളും ഭരണവും. സ്ക്രീനിലെ കാർഡുകൾ കാണുക.",
    }.get(lk, "Trustees and governance. Please see the cards on screen.")


def _loose_resolve_department_json_key(
    user_text: str,
    detected_department_label: str | None,
    deps: dict[str, Any],
) -> str | None:
    """Resolve department json key when strict canonical label match fails (e.g. 'data science')."""
    direct = department_label_to_json_key(detected_department_label)
    if direct:
        return direct
    for probe in (
        detected_department_label,
        user_text,
        f"{detected_department_label or ''} {user_text or ''}",
    ):
        if not probe or not isinstance(probe, str):
            continue
        j = department_label_to_json_key(probe.strip())
        if j:
            return j

    blob = f"{user_text or ''} {detected_department_label or ''}".lower()
    for canon, jkey in _CANONICAL_DEPARTMENT_TO_JSON_KEY.items():
        if len(canon) >= 3 and canon.lower() in blob:
            return jkey

    if re.search(r"\b(data\s*science|cse\s*ds|ds\s*department)\b", blob) and not any(
        x in blob for x in ("ece department", "mechanical department", "civil department", "mba only")
    ):
        return "cse_ds"
    if any(x in blob for x in ("ai & ml", "ai and ml", "aiml", "cse (ai")):
        return "cse_aiml"
    if any(x in blob for x in ("cyber security", "cybersecurity", "cse (cyber")):
        return "cse_cysec"
    if "business system" in blob:
        return "cse_bs"

    best_k = None
    best_score = 0
    if isinstance(deps, dict):
        blob_words = set(re.findall(r"[a-z0-9]+", blob))
        for kk in DEPARTMENT_JSON_KEY_ORDER:
            d = deps.get(kk)
            if not isinstance(d, dict):
                continue
            name = _clean(d.get("name"))
            nw = set(re.findall(r"[a-z0-9]+", name.lower()))
            score = len(blob_words & nw)
            if score > best_score:
                best_score = score
                best_k = kk
    if best_score >= 2 and best_k:
        return best_k
    return None


def _build_all_departments_segments(deps: dict[str, Any], lk_eff: str) -> list[NarrationSegment]:
    segs: list[NarrationSegment] = []
    L = dept_labels(lk_eff)
    for idx, kk in enumerate(DEPARTMENT_JSON_KEY_ORDER):
        d = deps.get(kk)
        if not isinstance(d, dict):
            continue
        name = _clean(d.get("name")) or kk.upper()
        intro = _clean(d.get("intro")) or L["notAvail"]
        txt = _clip_caption(f"{name}\n{intro}".strip(), 280)
        segs.append(
            NarrationSegment(
                display_text=txt,
                card_index=idx,
                card_id="dept_summary",
                section_id=f"dept_{kk}",
            )
        )
    return segs


# Intents that should prefer locale/card narration over raw LLM chunking when pre-plan is empty.
NARRATION_CARD_INTENTS: frozenset[str] = frozenset(
    {
        INTENT_COLLEGE_OVERVIEW,
        INTENT_TRUSTEES_PROFILE,
        INTENT_PRINCIPAL_PROFILE,
        INTENT_VICE_PRINCIPAL_PROFILE,
        INTENT_DEPARTMENT_FEES,
        INTENT_DOCUMENTS,
        INTENT_COURSE_MENU,
        INTENT_PLACEMENTS,
        INTENT_ADMISSIONS,
        INTENT_DEPARTMENT_OVERVIEW,
        INTENT_HOD_PROFILE,
    }
)


@dataclass
class NarrationSegment:
    """One visible + spoken beat (teleprompter window or one carousel slide)."""

    segment_id: str = ""
    display_text: str = ""
    tts_text: str = ""
    card_index: int | None = None
    card_id: str | None = None
    is_final_segment: bool = False
    # Stable meaning key for scene sync (not overwritten by finalize segment_id).
    section_id: str | None = None
    # Stable content identity for unit-backed composition/activation (additive for M5.2).
    unit_id: str | None = None
    # Canonical renderer identity. Never localized and never derived from display text.
    canonical_card_id: str | None = None

    def finalize(self, turn_id: str, index: int, total: int) -> None:
        self.segment_id = f"{turn_id}:seg:{index}"
        self.is_final_segment = index == total - 1
        # Preserve explicitly supplied tts_text (M5.2 unit-backed body-only).
        # Legacy builders that leave tts_text empty still derive from display_text.
        explicit = (self.tts_text or "").strip()
        if explicit:
            self.tts_text = normalize_tts_pronunciation(explicit)
        else:
            self.tts_text = normalize_tts_pronunciation(self.display_text)

    def public_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "segmentId": self.segment_id,
            "displayText": self.display_text,
            "ttsText": self.tts_text,
            "cardIndex": self.card_index,
            "cardId": self.card_id,
            "isFinalSegment": self.is_final_segment,
        }
        if self.section_id:
            out["sectionId"] = self.section_id
        if self.unit_id:
            out["unitId"] = self.unit_id
        if self.canonical_card_id:
            out["canonicalCardId"] = self.canonical_card_id
        return out


def finalize_segment_list(turn_id: str, segments: list[NarrationSegment]) -> None:
    n = len(segments)
    for i, seg in enumerate(segments):
        if seg.card_index is None:
            seg.card_index = i
        if not (seg.section_id or "").strip():
            # Best-effort meaning key for legacy builders (card_id or seg_i).
            cid = (seg.card_id or "").strip()
            seg.section_id = cid if cid else f"seg_{i}"
        seg.finalize(turn_id, i, n)


def chunk_plain_text(reply_text: str, *, max_chars: int = 220, max_hard_lines: int = 6) -> list[str]:
    """Split reply into paragraphs for teleprompter + TTS: sentence-safe, capped by chars/lines."""
    text = (reply_text or "").strip()
    if not text:
        return []
    normalized = text.replace("\u0964", ".")
    sentences = [p.strip() for p in re.split(r"(?<=[.!?।])\s+", normalized) if p.strip()]
    if len(sentences) <= 1 and "\n" in text:
        sentences = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if not sentences:
        return [text]

    buckets: list[str] = []
    cur: list[str] = []
    for s in sentences:
        trial = " ".join(cur + [s]) if cur else s
        line_est = trial.count("\n") + max(1, len(trial) // 55)
        if cur and (len(trial) > max_chars or line_est > max_hard_lines):
            buckets.append(" ".join(cur).strip())
            cur = [s]
        else:
            cur.append(s)
    if cur:
        buckets.append(" ".join(cur).strip())
    return [b for b in buckets if b]


def slides_from_cards(cards: list[dict[str, str]], *, card_type: str) -> list[NarrationSegment]:
    out: list[NarrationSegment] = []
    for i, row in enumerate(cards):
        title = _clean(row.get("title"))
        body = _clean(row.get("content"))
        text = f"{title}\n{body}".strip()
        out.append(NarrationSegment(display_text=text, card_index=i, card_id=card_type))
    return out


def dept_labels(lang_key_effective: str) -> dict[str, str]:
    lk = lang_key_effective if lang_key_effective in LANG_KEY_FALLBACK_ORDER else "en"
    dept_w = {
        "en": "Department",
        "kn": ui_text("kn", "cards.department"),
        "hi": "विभाग",
        "ta": "துறை",
        "te": "విభాగం",
        "ml": "വിഭാഗം",
    }
    return {
        "department": dept_w.get(lk, dept_w["en"]),
        "hodAndVision": {
            "en": "HOD & Vision",
            "kn": ui_text("kn", "cards.hod_and_vision"),
            "hi": "HOD और दृष्टिकोण",
            "ta": "HOD மற்றும் பார்வை",
            "te": "HOD మరియు దృక్పథం",
            "ml": "HOD ഉം വീക്ഷണവും",
        }.get(lk, "HOD & Vision"),
        "achievements": {
            "en": "Achievements",
            "kn": ui_text("kn", "cards.achievements"),
            "hi": "उपलब्धियां",
            "ta": "சாதனைகள்",
            "te": "సాధనలు",
            "ml": "നേട്ടങ്ങൾ",
        }.get(lk, "Achievements"),
        "placements": {
            "en": "Placements",
            "kn": ui_text("kn", "cards.placements"),
            "hi": "प्लेसमेंट",
            "ta": "வேலைவாய்ப்பு",
            "te": "ప్లేస్‌మెంట్‌లు",
            "ml": "പ്ലേസ്‌മെന്റുകൾ",
        }.get(lk, "Placements"),
        "fees": {
            "en": "Fee Structure",
            "kn": ui_text("kn", "cards.fees"),
            "hi": "शुल्क संरचना",
            "ta": "கட்டண விவரம்",
            "te": "ఫీజు నిర్మాణం",
            "ml": "ഫീസ് രൂപരേഖ",
        }.get(lk, "Fee Structure"),
        "leadAndVision": {
            "en": "Leadership & Vision",
            "kn": ui_text("kn", "cards.leadership_and_vision"),
            "hi": "नेतृत्व और दृष्टिकोण",
            "ta": "தலைமை மற்றும் பார்வை",
            "te": "నాయకత్వం మరియు దృక్పథం",
            "ml": "നേതൃത്വവും വീക്ഷണവും",
        }.get(lk, "Leadership & Vision"),
        "notAvail": {
            "en": "Information not available",
            "kn": ui_text("kn", "cards.information_unavailable"),
            "hi": "जानकारी उपलब्ध नहीं है",
            "ta": "தகவல் கிடைக்கவில்லை",
            "te": "సమాచారం అందుబాటులో లేదు",
            "ml": "വിവരം ലഭ്യമല്ല",
        }.get(lk, "Information not available"),
        "unlisted": {
            "en": "This department is not listed in the campus knowledge file yet.",
            "kn": ui_text("kn", "availability.missing_source").replace("\n", " "),
            "hi": "यह विभाग अभी कैंपस नॉलेज में सूचीबद्ध नहीं है।",
            "ta": "இந்தத் துறை இன்னும் கேம்பஸ் அறிவில் பட்டியலிடப்படவில்லை.",
            "te": "ఈ విభాగం ఇంకా క్యాంపస్ నాలెడ్జ్‌లో జాబితా చేయబడలేదు.",
            "ml": "ഈ വിഭാഗം ഇതുവരെ ക്യാമ്പസ് അറിവിൽ ലിസ്റ്റ് ചെയ്തിട്ടില്ല.",
        }.get(lk, "This department is not listed in the campus knowledge file yet."),
    }


_DEPT_SLIDE_SECTION_IDS = ("intro", "hod_voice", "achievements", "placement", "fees")


def build_department_slide_segments(
    dept: dict[str, Any] | None, json_key: str, locale_id: str
) -> list[NarrationSegment]:
    lk = _effective_lang(locale_id)
    labels = dept_labels(lk)
    if not dept:
        txt = f'{labels["department"]}\n{labels["unlisted"]}'
        return [
            NarrationSegment(
                display_text=txt,
                card_index=0,
                card_id="dept",
                section_id="unlisted",
            )
        ]
    name = _clean(dept.get("name")) or json_key.upper()
    intro = _clean(dept.get("intro")) or labels["notAvail"]
    hod_voice = _clean(dept.get("hod_voice")) or labels["notAvail"]
    achievements_txt = _clean(dept.get("achievements")) or labels["notAvail"]
    placement = _clean(dept.get("placement")) or labels["notAvail"]
    fees_txt = _clean(dept.get("fees")) or labels["notAvail"]
    slides_txt = [
        (name, intro),
        (labels["hodAndVision"], hod_voice),
        (labels["achievements"], achievements_txt),
        (labels["placements"], placement),
        (labels["fees"], fees_txt),
    ]
    segments: list[NarrationSegment] = []
    for i, (t, body) in enumerate(slides_txt):
        raw_line = f"{t}\n{_clip_caption(body, 280)}".strip()
        segments.append(
            NarrationSegment(
                display_text=_clip_caption(raw_line, 320),
                card_index=i,
                card_id="dept_slide",
                section_id=_DEPT_SLIDE_SECTION_IDS[i],
            )
        )
    return segments


def build_placement_segments(data: dict[str, Any], locale_id: str) -> list[NarrationSegment]:
    lk = _effective_lang(locale_id)
    L = {
        "en": ("Training & placement objectives", "Training programs", "Support at a glance"),
        "kn": ("ತರಬೇತಿ ಮತ್ತು ಪ್ಲೇಸ್‌ಮೆಂಟ್ ಉದ್ದೇಶಗಳು", "ತರಬೇತಿ ಕಾರ್ಯಕ್ರಮಗಳು", "ಸಂಕ್ಷಿಪ್ತ ನೋಟ"),
        "hi": ("प्रशिक्षण और प्लेसमेंट उद्देश्य", "प्रशिक्षण कार्यक्रम", "संक्षिप्त अवलोकन"),
        "ta": ("பயிற்சி மற்றும் பிளேஸ்மென்ட் நோக்கங்கள்", "பயிற்சித் திட்டங்கள்", "சுருக்கப் பார்வை"),
        "te": ("శిక్షణ మరియు ప్లేస్‌మెంట్ లక్ష్యాలు", "శిక్షణ కార్యక్రమాలు", "సంక్షిప్త దృష్టి"),
        "ml": ("പരിശീലനവും പ്ലേസ്മെന്റ് ലക്ഷ്യങ്ങളും", "പരിശീലന പരിപാടികൾ", "ചുരുക്കക്കാഴ്ച"),
    }.get(
        lk,
        ("Training & placement objectives", "Training programs", "Support at a glance"),
    )
    fallback = (
        "Please visit the Training & Placement cell for the latest information.",
        "Please visit the Training & Placement cell for the latest information.",
        "Please visit the Training & Placement cell for the latest information.",
    )

    pt = data.get("placements_and_training")
    if not isinstance(pt, dict):
        segs = [
            NarrationSegment(display_text=f"{L[0]}\n{fallback[0]}", card_index=0, card_id="placement"),
            NarrationSegment(display_text=f"{L[1]}\n{fallback[1]}", card_index=1, card_id="placement"),
            NarrationSegment(display_text=f"{L[2]}\n{fallback[2]}", card_index=2, card_id="placement"),
        ]
        return segs

    obj_body = _clean(pt.get("objectives"))
    extra = pt.get("additional_details")
    if isinstance(extra, dict) and isinstance(extra.get("objectives"), list):
        obj_body = _dedupe_join([_clean(x) for x in extra["objectives"]]) or obj_body

    train_body = _clean(pt.get("training_programs"))
    if isinstance(extra, dict) and isinstance(extra.get("training_programs"), list):
        train_body = _dedupe_join([_clean(x) for x in extra["training_programs"]]) or train_body

    def clip(s: str, n: int = 280) -> str:
        s = _clean(s)
        return s[: n - 1] + "…" if len(s) > n else s

    summary_lines = []
    if obj_body:
        summary_lines.append(clip(obj_body))
    if train_body:
        summary_lines.append(clip(train_body))

    fallback_obj = (
        "Placement support and career guidance are central to SVIT."
        if lk == "en"
        else obj_body or "Placement support."
    )
    fallback_train = (
        "Aptitude, technical, soft skills, and mock interviews — see T&P cell."
        if lk == "en"
        else train_body or "Training programs."
    )
    fallback_sum = (
        "For company visits, drives, and statistics, meet the T&P team."
        if lk == "en"
        else "\n\n".join(summary_lines) or fallback_train
    )

    slides = (
        obj_body or fallback_obj,
        train_body or fallback_train,
        "\n\n".join(summary_lines) if summary_lines else fallback_sum,
    )
    return [
        NarrationSegment(display_text=f"{L[0]}\n{slides[0]}", card_index=0, card_id="placement"),
        NarrationSegment(display_text=f"{L[1]}\n{slides[1]}", card_index=1, card_id="placement"),
        NarrationSegment(display_text=f"{L[2]}\n{slides[2]}", card_index=2, card_id="placement"),
    ]


def _admissions_slides(data: dict[str, Any], locale_id: str) -> list[tuple[str, str]]:
    """Return (title, body) tuples mirroring frontend buildAdmissionsCardsFromLocale."""
    lk = _effective_lang(locale_id)
    admissions = data.get("admissions_and_fees")
    LABELS_MAP = {
        "en": (
            ("Eligibility", "Entrance exams", "UG fees (reference)", "MBA / PG fees", "Scholarships"),
        ),
    }
    L_base = LABELS_MAP["en"][0]
    LANG_LABELS = {
        "kn": (
            ui_text("kn", "cards.eligibility"),
            ui_text("kn", "cards.entrance_exams"),
            ui_text("kn", "cards.ug_fees"),
            ui_text("kn", "cards.pg_fees"),
            ui_text("kn", "cards.scholarships"),
        ),
        "hi": ("पात्रता", "प्रवेश परीक्षाएँ", "यूजी शुल्क (संदर्भ)", "MBA / पीजी शुल्क", "छात्रवृत्तियाँ"),
        "ta": ("தகுதி", "நுழைவுத் தேர்வுகள்", "முதுநிலை முன் கட்டணம்", "MBA / முதுநிலை கட்டணம்", "உதவித்தொகைகள்"),
        "te": ("అర్హత", "ప్రవేశ పరీక్షలు", "యుజి ఫీజు (సూచన)", "MBA / పిజి ఫీజు", "విద్యార్థి వేతనాలు"),
        "ml": ("അർഹത", "പ്രവേശന പരീക്ഷകൾ", "യുജി ഫീസ്", "MBA / പിജി ഫീസ്", "സ്കോളർഷിപ്പുകൾ"),
        "en": L_base,
    }
    labs = LANG_LABELS.get(lk, LANG_LABELS["en"])
    if not isinstance(admissions, dict):
        fb = ("Please visit the Admission Block for the latest details.")
        body = fb[0] if isinstance(fb[0], str) else "See Admission Block."
        return [(labs[0], body)]

    rec = admissions
    extra = rec.get("additional_details") if isinstance(rec.get("additional_details"), dict) else {}
    admission_elig = extra.get("admission_and_eligibility") if isinstance(extra, dict) else {}
    fees_struct_extra = extra.get("fees_structure") if isinstance(extra, dict) else {}

    elig_parts = []
    if _clean(rec.get("eligibility")):
        elig_parts.append(_clean(rec.get("eligibility")))
    if isinstance(admission_elig, dict):
        be = admission_elig.get("be_programs") if isinstance(admission_elig.get("be_programs"), dict) else {}
        mba_prog = admission_elig.get("mba_programs") if isinstance(admission_elig.get("mba_programs"), dict) else {}
        if be:
            for k in ("qualification", "compulsory_subjects", "optional_subjects", "requirements_general", "requirements_reserved"):
                cv = _clean(be.get(k))
                if cv:
                    elig_parts.append(cv)
            for arr_key in ("entrance_exams",):
                if isinstance(be.get(arr_key), list):
                    elig_parts.extend([_clean(x) for x in be[arr_key]])
        if mba_prog:
            q = _clean(mba_prog.get("qualification"))
            if q:
                elig_parts.append(f"MBA: {q}")
            if _clean(mba_prog.get("expected_cutoff")):
                elig_parts.append(_clean(mba_prog.get("expected_cutoff")))

    elig_body = _dedupe_join(elig_parts) or (
        _clean(rec.get("eligibility")) or "See Admission Block for eligibility."
    )

    exams: list[str] = []
    if isinstance(rec.get("entrance_exams"), list):
        exams.extend([_clean(x) for x in rec["entrance_exams"]])
    if isinstance(admission_elig, dict) and isinstance(admission_elig.get("be_programs"), dict):
        ber = admission_elig["be_programs"]
        if isinstance(ber.get("entrance_exams"), list):
            exams.extend([_clean(x) for x in ber["entrance_exams"]])

    entr_body = _dedupe_join(exams)
    entr_body = entr_body or "KCET, COMEDK, and Management Quota — see Admission Block."

    fee_rec = rec.get("fee_structures") if isinstance(rec.get("fee_structures"), dict) else {}
    ug_body = _clean(fee_rec.get("ug_kcet")) if isinstance(fee_rec, dict) else ""
    mg = fees_struct_extra.get("management_quota_engineering_annual") if isinstance(fees_struct_extra, dict) else None
    if isinstance(mg, dict):
        ug_body = (
            ug_body
            + "\nManagement quota (annual, indicative):\n"
            + "\n".join(f"{k}: {v}" for k, v in mg.items())
        ).strip()

    pg_body = _clean(fee_rec.get("pg_mba")) if isinstance(fee_rec, dict) else ""
    if lk == "kn":
        blocked_fees = ui_text("kn", "availability.official_fact_blocked")
        ug_body = blocked_fees
        pg_body = blocked_fees

    scholarships_lines: list[str] = []
    if _clean(rec.get("scholarships")):
        scholarships_lines.append(_clean(rec.get("scholarships")))
    if isinstance(fees_struct_extra, dict) and isinstance(fees_struct_extra.get("scholarships"), list):
        scholarships_lines.extend([_clean(x) for x in fees_struct_extra["scholarships"]])
    schol_body = _dedupe_join(scholarships_lines)

    slides: list[tuple[str, str]] = [
        (labs[0], elig_body),
        (labs[1], entr_body),
        (labs[2], ug_body or "See Admission Block."),
        (labs[3], pg_body or "See Admission Block."),
    ]
    if schol_body:
        slides.append((labs[4], schol_body))
    return slides


EXEC_PRINCIPAL: dict[str, dict[str, str]] = {}
EXEC_VICE: dict[str, dict[str, str]] = {}


def _init_executive_profiles() -> None:
    """Populate from kiosk executiveLeadershipLocale (minimal duplication)."""
    global EXEC_PRINCIPAL, EXEC_VICE
    if EXEC_PRINCIPAL:
        return

    EXEC_PRINCIPAL = {
        "en": {
            "label": "Executive Profile",
            "name": "Dr. Manjunath T N",
            "title": "Principal",
            "bio": "Dr. Manjunath T N, Principal of Sai Vidya Institute of Technology, is an experienced academic and administrator with strong contributions to engineering education, research promotion, and institutional development, focusing on quality teaching, discipline, and holistic student growth while leading key initiatives that strengthen the college’s academic standards and industry relevance.",
        },
        "kn": {
            "label": "ನಾಯಕತ್ವ ಪ್ರೊಫೈಲ್",
            "name": "ಡಾ. ಮಂಜುನಾಥ್ ಟಿ ಎನ್",
            "title": "ಪ್ರಾಂಶುಪಾಲರು",
            "bio": "ಡಾ. ಮಂಜುನಾಥ್ ಟಿ ಎನ್ ಅವರು ಸಾಯಿ ವಿದ್ಯಾ ಇಂಜಿನಿಯರಿಂಗ್ ಕಾಲೇಜಿನ ಪ್ರಾಂಶುಪಾಲರು. ಇಂಜಿನಿಯರಿಂಗ್ ಶಿಕ್ಷಣ, ಸಂಶೋಧನಾ ಉತ್ತೇಜನೆ ಮತ್ತು ಸಂಸ್ಥೆಯ ಬೆಳವಣಿಗೆಯಲ್ಲಿ ಗಣನೀಯ ಕೊಡುಗೆ ನೀಡಿರುವ ಹಿರಿಯ ಶೈಕ್ಷಣಿಕ ಮತ್ತು ಆಡಳಿತಗಾರರು.",
        },
        "hi": {
            "label": "प्रोफ़ाइल",
            "name": "डॉ. मंजुनाथ टी एन",
            "title": "प्राचार्य",
            "bio": "डॉ. मंजुनाथ टी एन साई विद्या इंस्टीट्यूट ऑफ टेक्नोलॉजी के प्राचार्य हैं.",
        },
        "ta": {
            "label": "தலைமை அறிமுகம்",
            "name": "டாக்டர் மஞ்சுநாத் டி என்",
            "title": "முதல்வர்",
            "bio": "டாக்டர் மஞ்சுநாத் டி என் அவர்கள் சாயி வித்யா இன்ஸ்ட்டிட்யூட் ஆப் டெக்னாலஜியின் முதல்வர்.",
        },
        "te": {
            "label": "నాయకత్వ ప్రొఫైల్",
            "name": "డాక్టర్ మంజునాథ్ టి ఎన్",
            "title": "ప్రిన్సిపాల్",
            "bio": "డాక్టర్ మంజునాథ్ టి ఎన్ సాయి విద్యా ఇన్‌స్టిట్యూట్ ఆఫ్ టెక్నాలజీ ప్రిన్సిపాల్ గా ఉన్నారు.",
        },
        "ml": {
            "label": "നേതൃ പ്രൊഫൈൽ",
            "name": "ഡോ. മഞ്ജുനാഥ് ടി എൻ",
            "title": "പ്രിൻസിപ്പൽ",
            "bio": "ഡോ. മഞ്ജുനാഥ് ടി എൻ സായി വിദ്യാ ഇൻസ്റ്റിറ്റ്യൂറ്റ് ഒഫ് ടെക്നോളജിയുടെ പ്രിൻസിപ്പലാണ്.",
        },
    }

    EXEC_VICE = {
        "en": {
            "label": "Executive Profile",
            "name": "Dr. Lakshminarayanachari K",
            "title": "Vice Principal & Dean Academics",
            "bio": "Dr. Lakshminarayanachari K serves as Vice Principal and Dean Academics at SVIT, supporting academic planning, curriculum implementation, and teaching quality enhancement.",
        },
        "kn": {
            "label": "ನಾಯಕತ್ವ ಪ್ರೊಫೈಲ್",
            "name": "ಡಾ. ಲಕ್ಷ್ಮಿನಾರಾಯಣಾಚಾರಿ ಕೆ",
            "title": "ಉಪ ಪ್ರಾಂಶುಪಾಲರು ಹಾಗೂ ಶೈಕ್ಷಣಿಕ ಡೀನ್",
            "bio": "ಡಾ. ಲಕ್ಷ್ಮಿನಾರಾಯಣಾಚಾರಿ ಕೆ ಅವರು ಎಸ್ವಿಐಟಿಯಲ್ಲಿ ಉಪ ಪ್ರಾಂಶುಪಾಲರು ಮತ್ತು ಶೈಕ್ಷಣಿಕ ಡೀನ್ ಆಗಿ ಕಾರ್ಯನಿರ್ವಹಿಸುತ್ತಾರೆ.",
        },
        "hi": {
            "label": "प्रोफ़ाइल",
            "name": "डॉ. लक्ष्मीनारायणाचारी के",
            "title": "उप प्राचार्य और शैक्षणिक डीन",
            "bio": "डॉ. लक्ष्मीनारायणाचारी के एसवीआईटी में उप प्राचार्य और शैक्षणिक डीन हैं।",
        },
        "ta": {
            "label": "தலைமை அறிமுகம்",
            "name": "டாக்டர் லக்ஷ்மிநாராயணச்சாரி கே",
            "title": "துணை முதல்வர் மற்றும் கல்வி டீன்",
            "bio": "டாக்டர் லக்ஷ்மிநாராயணச்சாரி கே SVIT இல் துணை முதல்வரும் கல்வி டீனுமாக செயல்படுகிறார்.",
        },
        "te": {
            "label": "నాయకత్వ ప్రొఫైల్",
            "name": "డాక్టర్ లక్ష్మీనారాయణాచారి కె",
            "title": "ఉప ప్రిన్సిపాల్ మరియు డీన్ ఎకడెమిక్స్",
            "bio": "డాక్టర్ లక్ష్మీనారాయణాచారి కె SVIT లో ఉప ప్రిన్సిపాల్ మరియు డీన్ ఎకడెమిక్స్ గా ఉన్నారు.",
        },
        "ml": {
            "label": "നേതൃ പ്രൊഫൈൽ",
            "name": "ഡോ. ലക്ഷ്മീനാരായണാചാരി കെ",
            "title": "ഉപ പ്രിൻസിപ്പൽ, അക്കാദമിക് ഡീൻ",
            "bio": "ഡോ. ലക്ഷ്മീനാരായണാചാരി കെ SVIT ലെ ഉപ പ്രിൻസിപ്പലും അക്കാദമിക് ഡീനുമാണ്.",
        },
    }


def segment_executiveprincipal(locale_id: str) -> NarrationSegment:
    _init_executive_profiles()
    lk = _effective_lang(locale_id)
    p = EXEC_PRINCIPAL.get(lk) or EXEC_PRINCIPAL["en"]
    text = f'{p["label"]}\n{p["name"]}\n{p["title"]}\n{p["bio"]}'
    return NarrationSegment(display_text=text.strip(), card_index=0, card_id="principal")


def segment_exec_vice(locale_id: str) -> NarrationSegment:
    _init_executive_profiles()
    lk = _effective_lang(locale_id)
    p = EXEC_VICE.get(lk) or EXEC_VICE["en"]
    text = f'{p["label"]}\n{p["name"]}\n{p["title"]}\n{p["bio"]}'
    return NarrationSegment(display_text=text.strip(), card_index=0, card_id="vice_principal")


def segment_fees(locale_id: str, department_json_key: str | None) -> NarrationSegment:
    lk = _effective_lang(locale_id)
    labels = _FEES_LABELS.get(lk) or _FEES_LABELS["en"]
    display_names = _DEPT_DISPLAY.get(lk) or _DEPT_DISPLAY["en"]

    sel_key = department_json_key or ""
    dept_line = ""
    if sel_key:
        dept_line = f'{labels["selectedDepartment"]}: {display_names.get(sel_key, sel_key)}'

    rows: list[str] = []
    for k in ("cse", "ise", "cse_aiml", "cse_ds", "cse_cysec", "cse_bs", "ece", "civil", "mechanical"):
        amt = _FEES_AMOUNT_BY_KEY.get(k)
        row_name = display_names.get(k, k)
        amount_str = _format_inr(amt) if amt else labels["officeContact"]
        rows.append(f"{row_name}. {labels['managementQuotaFee']}: {amount_str}")

    txt = (
        f'{labels["title"]}\n{labels["description"]}\n{dept_line}\n'.strip()
        + "\n\n"
        + "\n".join(rows)
        + "\n\n"
        + labels["officeContact"]
    ).strip()

    return NarrationSegment(display_text=txt, card_index=0, card_id="fees")


def segment_documents(locale_id: str) -> list[NarrationSegment]:
    lk = _effective_lang(locale_id)
    title = DOCUMENT_TITLES.get(lk, DOCUMENT_TITLES["en"])
    items = DOCUMENT_ITEMS.get(lk) or DOCUMENT_ITEMS["en"]
    # Two segments: title + intro list first half, remainder (mirrors kiosk scroll)
    per = max(4, len(items) // 2 + 1)
    out: list[NarrationSegment] = []
    seg_ix = 0
    for i in range(0, len(items), per):
        chunk = items[i : i + per]
        body = "\n".join(f"• {_clean(x)}" for x in chunk)
        txt = title + "\n" + body if i == 0 else body
        out.append(NarrationSegment(display_text=txt, card_index=seg_ix, card_id="documents"))
        seg_ix += 1
    return out


def build_department_comparison_segments(
    department_ids: list[str],
    locale_id: str,
) -> list[NarrationSegment]:
    """
    Token-efficient comparison plan (UI sync via tts_chunk_index):
    - Phase 1: ONE short 'learns' line per dept (3 subjects max)
    - Phase 2: ONE short 'jobs' line per dept (2 roles max)
    """
    lk = _effective_lang(locale_id)
    data = _load_comparison_defaults()
    deps = data.get("departments") if isinstance(data, dict) else None
    if not isinstance(deps, dict) or not department_ids:
        return [
            NarrationSegment(
                display_text=_clip_caption("Comparison will appear on screen shortly.", 120),
                card_index=0,
                card_id="comparison_learning",
            )
        ]

    segs: list[NarrationSegment] = []
    name_map = _DEPT_DISPLAY.get(lk, _DEPT_DISPLAY["en"])

    def dept_name(did: str) -> str:
        return name_map.get(did, did.replace("_", " ").upper())

    # Phase 1: learning
    for i, did in enumerate(department_ids):
        row = deps.get(did) if isinstance(deps.get(did), dict) else {}
        learn_pack = row.get("student_learning_4y") if isinstance(row, dict) else None
        learn_raw = ""
        if isinstance(learn_pack, dict):
            learn_raw = str(learn_pack.get(lk) or learn_pack.get("en") or "")
        learn_items = [_short_phrase(x, max_words=3) for x in _split_bullets(learn_raw)]
        learn_short = _compact_list([x for x in learn_items if x], max_items=3)
        txt = _clip_caption(f"{dept_name(did)}: {learn_short}".strip(" :"), 90)
        segs.append(NarrationSegment(display_text=txt, card_index=i, card_id="comparison_learning"))

    # Phase 2: jobs
    for i, did in enumerate(department_ids):
        row = deps.get(did) if isinstance(deps.get(did), dict) else {}
        jobs_pack = row.get("future_job_opportunities") if isinstance(row, dict) else None
        jobs_raw = ""
        if isinstance(jobs_pack, dict):
            jobs_raw = str(jobs_pack.get(lk) or jobs_pack.get("en") or "")
        job_items = [_short_phrase(x, max_words=3) for x in _split_bullets(jobs_raw)]
        jobs_short = _compact_list([x for x in job_items if x], max_items=2)
        txt = _clip_caption(f"{dept_name(did)} jobs: {jobs_short}".strip(" :"), 90)
        segs.append(NarrationSegment(display_text=txt, card_index=i, card_id="comparison_jobs"))

    return segs


def segment_hod_single(dept_rec: dict[str, Any], json_key: str, locale_id: str) -> NarrationSegment:
    lk = _effective_lang(locale_id)
    lbl = dept_labels(lk)
    name = _clean(dept_rec.get("name")) or json_key.upper()
    hod_voice = _clean(dept_rec.get("hod_voice")) or lbl["notAvail"]
    department_label = lbl["department"]
    lead_lbl = lbl["leadAndVision"]
    txt = f"{department_label}: {name}\n{lead_lbl}: {hod_voice}".strip()
    return NarrationSegment(display_text=txt, card_index=0, card_id="hod")


def build_pre_llm_narration_plan(
    intent: str,
    lang_key: str | None,
    *,
    user_text: str,
    detected_department_label: str | None,
    menu_department_json_key: str | None,
    comparison_department_ids: list[str] | None = None,
) -> list[NarrationSegment] | None:
    """Return narration segments before LLM for deterministic card flows; None = use legacy pipeline."""
    if not SETTINGS_ENABLE_FLAG:
        return None

    data = load_locale_data_for_lang_key(lang_key)
    locale_id = locale_file_id_for_lang_key(lang_key)
    lk_eff = _effective_lang(locale_id)
    deps = data.get("departments")
    dept_jkey = menu_department_json_key or department_label_to_json_key(detected_department_label)
    if isinstance(deps, dict) and not dept_jkey:
        dept_jkey = _loose_resolve_department_json_key(user_text, detected_department_label, deps)

    raw = _load_static_cards()
    locale_pack = raw.get(lk_eff) or raw.get("en") if isinstance(raw, dict) else None

    if intent == INTENT_COLLEGE_OVERVIEW:
        cards = locale_pack.get("college") if locale_pack else None
        if not isinstance(cards, list):
            return [
                NarrationSegment(
                    display_text=_fallback_college_card_line(locale_id),
                    card_index=0,
                    card_id="college",
                )
            ]
        return slides_from_cards(cards, card_type="college")

    if intent == INTENT_TRUSTEES_PROFILE:
        cards_t = locale_pack.get("trustees") if locale_pack else None
        if not isinstance(cards_t, list):
            return [
                NarrationSegment(
                    display_text=_fallback_trustees_card_line(locale_id),
                    card_index=0,
                    card_id="trustees",
                )
            ]
        return slides_from_cards(cards_t, card_type="trustees")

    if intent == INTENT_PRINCIPAL_PROFILE:
        return [segment_executiveprincipal(locale_id)]

    if intent == INTENT_VICE_PRINCIPAL_PROFILE:
        return [segment_exec_vice(locale_id)]

    if intent == INTENT_DEPARTMENT_FEES:
        return [segment_fees(locale_id, dept_jkey)]

    if intent == INTENT_DOCUMENTS:
        return segment_documents(locale_id)

    if intent == INTENT_COURSE_MENU:
        lang_name = LANG_KEY_TO_DISPLAY_NAME.get((lang_key or "").lower())
        spoken = get_course_menu_spoken_prompt(lang_name)
        return [
            NarrationSegment(
                display_text=spoken,
                card_index=0,
                card_id="course_menu",
            ),
        ]

    if intent == INTENT_PLACEMENTS:
        return build_placement_segments(data, locale_id)

    if intent == INTENT_ADMISSIONS:
        slides_pairs = _admissions_slides(data, locale_id)
        return [
            NarrationSegment(display_text=f"{t}\n{b}".strip(), card_index=i, card_id="admissions")
            for i, (t, b) in enumerate(slides_pairs)
        ]

    if intent == INTENT_DEPARTMENT_COMPARISON:
        ids = [x for x in (comparison_department_ids or []) if isinstance(x, str) and x.strip()]
        return build_department_comparison_segments(ids, locale_id)

    if intent == INTENT_DEPARTMENT_OVERVIEW:
        if not isinstance(deps, dict):
            return [
                NarrationSegment(
                    display_text=_clip_caption(
                        "Department information will appear on screen shortly.",
                        200,
                    ),
                    card_index=0,
                    card_id="dept",
                )
            ]
        if _wants_all_departments_narration(user_text) or not dept_jkey:
            segs = _build_all_departments_segments(deps, lk_eff)
            if segs:
                return segs
            return [
                NarrationSegment(
                    display_text=_clip_caption(
                        "Please see department information on the display.",
                        200,
                    ),
                    card_index=0,
                    card_id="dept",
                )
            ]

        dept_rec = deps.get(dept_jkey) if dept_jkey else None
        return build_department_slide_segments(
            dept_rec if isinstance(dept_rec, dict) else None,
            dept_jkey or "",
            locale_id,
        )

    if intent == INTENT_HOD_PROFILE:
        if not isinstance(deps, dict):
            return [
                NarrationSegment(
                    display_text=_pick_department_prompt_hod(locale_id),
                    card_index=0,
                    card_id="hod_pick",
                )
            ]
        if not dept_jkey:
            return [
                NarrationSegment(
                    display_text=_pick_department_prompt_hod(locale_id),
                    card_index=0,
                    card_id="hod_pick",
                )
            ]
        d = deps.get(dept_jkey)
        if isinstance(d, dict):
            return [segment_hod_single(d, dept_jkey, locale_id)]
        return [
            NarrationSegment(
                display_text=_pick_department_prompt_hod(locale_id),
                card_index=0,
                card_id="hod_pick",
            )
        ]

    return None


def post_llm_chunk_plan(reply_text: str) -> list[NarrationSegment]:
    return chunk_plan_with_card_index(reply_text, card_id=None)


def chunk_plan_with_card_index(reply_text: str, *, card_id: str | None = None) -> list[NarrationSegment]:
    buckets = chunk_plain_text(reply_text)
    return [
        NarrationSegment(display_text=b, card_index=i, card_id=card_id)
        for i, b in enumerate(buckets)
        if b.strip()
    ]
