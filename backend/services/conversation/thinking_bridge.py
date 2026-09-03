"""Short spoken thinking-bridge sentences. Deterministic; no extra LLM."""

from __future__ import annotations

import re

_FALLBACK = {
    "en": "Let me bring that together for you.",
    "kn": "ನಾನು ಅದನ್ನು ನಿಮಗಾಗಿ ಒಟ್ಟುಗೂಡಿಸುತ್ತೇನೆ.",
    "hi": "मैं वह आपके लिए एक साथ लाती हूँ।",
    "ta": "அதை உங்களுக்காக ஒன்றாகத் தொகுக்கிறேன்.",
    "te": "దాన్ని మీ కోసం సమీకరిస్తాను.",
    "ml": "അത് നിങ്ങൾക്കായി ഒരുമിച്ച് ശേഖരിക്കാം.",
}

_BY_TOPIC: dict[str, dict[str, str]] = {
    "college": {
        "en": "Let me bring together some of the best things about the college for you.",
        "kn": "ಕಾಲೇಜಿನ ಉತ್ತಮ ಅಂಶಗಳನ್ನು ನಿಮಗಾಗಿ ಒಟ್ಟುಗೂಡಿಸುತ್ತೇನೆ.",
        "hi": "कॉलेज की अच्छी बातें आपके लिए एक साथ लाती हूँ।",
        "ta": "கல்லூரியின் சிறப்பானவற்றை உங்களுக்காகத் தொகுக்கிறேன்.",
        "te": "కళాశాల మంచి అంశాలను మీ కోసం సమీకరిస్తాను.",
        "ml": "കോളേജിന്റെ നല്ല കാര്യങ്ങൾ നിങ്ങൾക്കായി ഒരുമിച്ച് ശേഖരിക്കാം.",
    },
    "course": {
        "en": "Let me pull together the key details about that course for you.",
        "kn": "ಆ ಕೋರ್ಸ್‌ನ ಮುಖ್ಯ ವಿವರಗಳನ್ನು ನಿಮಗಾಗಿ ತರುತ್ತೇನೆ.",
        "hi": "उस कोर्स की मुख्य बातें आपके लिए लाती हूँ।",
        "ta": "அந்த பாடநெறியின் முக்கிய விவரங்களைத் தொகுக்கிறேன்.",
        "te": "ఆ కోర్సు ముఖ్య వివరాలను మీ కోసం సమీకరిస్తాను.",
        "ml": "ആ കോഴ്സിന്റെ പ്രധാന വിവരങ്ങൾ ഒരുമിച്ച് ശേഖരിക്കാം.",
    },
    "fees": {
        "en": "Let me check the fee details for the program you are asking about.",
        "kn": "ನೀವು ಕೇಳುತ್ತಿರುವ ಕಾರ್ಯಕ್ರಮದ ಶುಲ್ಕವನ್ನು ನೋಡುತ್ತೇನೆ.",
        "hi": "जिस कार्यक्रम के बारे में पूछा है, उसकी फीस देखती हूँ।",
        "ta": "நீங்கள் கேட்கும் பாடநெறியின் கட்டணத்தைப் பார்க்கிறேன்.",
        "te": "మీరు అడుగుతున్న కోర్సు ఫీజును చూస్తాను.",
        "ml": "നിങ്ങൾ ചോദിക്കുന്ന പ്രോഗ്രാമിന്റെ ഫീസ് നോക്കാം.",
    },
    "hod": {
        "en": "Let me bring up the details about the department head.",
        "kn": "ವಿಭಾಗದ ಮುಖ್ಯಸ್ಥರ ವಿವರವನ್ನು ತರುತ್ತೇನೆ.",
        "hi": "विभाग प्रमुख का विवरण आपके लिए लाती हूँ।",
        "ta": "துறைத் தலைவர் விவரத்தைக் கொண்டு வருகிறேன்.",
        "te": "విభాగ అధిపతి వివరాలు తెస్తాను.",
        "ml": "വിഭാഗ മേധാവിയുടെ വിവരങ്ങൾ കൊണ്ടുവരാം.",
    },
    "admissions": {
        "en": "Let me bring together the admission details you need.",
        "kn": "ನಿಮಗೆ ಬೇಕಾದ ಪ್ರವೇಶ ವಿವರಗಳನ್ನು ಒಟ್ಟುಗೂಡಿಸುತ್ತೇನೆ.",
        "hi": "प्रवेश से जुड़ी बातें आपके लिए लाती हूँ।",
        "ta": "சேர்க்கை விவரங்களை உங்களுக்காகத் தொகுக்கிறேன்.",
        "te": "ప్రవేశ వివరాలను మీ కోసం సమీకరిస్తాను.",
        "ml": "പ്രവേശന വിവരങ്ങൾ ഒരുമിച്ച് ശേഖരിക്കാം.",
    },
    "placements": {
        "en": "Let me bring together the placement highlights for you.",
        "kn": "ಪ್ಲೇಸ್‌ಮೆಂಟ್ ಮುಖ್ಯ ಅಂಶಗಳನ್ನು ನಿಮಗಾಗಿ ತರುತ್ತೇನೆ.",
        "hi": "प्लेसमेंट की मुख्य बातें आपके लिए लाती हूँ।",
        "ta": "வேலைவாய்ப்பு சிறப்பம்சங்களைத் தொகுக்கிறேன்.",
        "te": "ప్లేస్‌మెంట్ ముఖ్యాంశాలను సమీకరిస్తాను.",
        "ml": "പ്ലേസ്‌മെന്റ് ഹൈലൈറ്റുകൾ ഒരുമിച്ച് ശേഖരിക്കാം.",
    },
    "transport": {
        "en": "Let me bring together the transport details for you.",
        "kn": "ಸಾರಿಗೆ ವಿವರಗಳನ್ನು ನಿಮಗಾಗಿ ತರುತ್ತೇನೆ.",
        "hi": "परिवहन की जानकारी आपके लिए लाती हूँ।",
        "ta": "போக்குவரத்து விவரங்களைத் தொகுக்கிறேன்.",
        "te": "రవాణా వివరాలను సమీకరిస్తాను.",
        "ml": "ഗതാഗത വിവരങ്ങൾ ഒരുമിച്ച് ശേഖരിക്കാം.",
    },
    "campus": {
        "en": "Let me show you what you need to know about the campus.",
        "kn": "ಕ್ಯಾಂಪಸ್ ಬಗ್ಗೆ ನಿಮಗೆ ಬೇಕಾದುದನ್ನು ತೋರಿಸುತ್ತೇನೆ.",
        "hi": "कैंपस के बारे में जरूरी बातें बताती हूँ।",
        "ta": "வளாகம் பற்றித் தெரிந்துகொள்ள வேண்டியதைக் காட்டுகிறேன்.",
        "te": "క్యాంపస్ గురించి మీకు కావాల్సినవి చూపిస్తాను.",
        "ml": "ക്യാമ്പസിനെക്കുറിച്ച് അറിയേണ്ടത് കാണിച്ചുതരാം.",
    },
    "faculty": {
        "en": "Let me find the details about the person you are asking about.",
        "kn": "ನೀವು ಕೇಳುತ್ತಿರುವ ವ್ಯಕ್ತಿಯ ವಿವರವನ್ನು ತರುತ್ತೇನೆ.",
        "hi": "जिस व्यक्ति के बारे में पूछा है, उनका विवरण लाती हूँ।",
        "ta": "நீங்கள் கேட்கும் நபரின் விவரத்தைக் கொண்டு வருகிறேன்.",
        "te": "మీరు అడుగుతున్న వ్యక్తి వివరాలు తెస్తాను.",
        "ml": "നിങ്ങൾ ചോദിക്കുന്ന വ്യക്തിയുടെ വിവരങ്ങൾ കൊണ്ടുവരാം.",
    },
    "followup": {
        "en": "Yes, let me explain that part a little more clearly.",
        "kn": "ಹೌದು, ಆ ಭಾಗವನ್ನು ಇನ್ನಷ್ಟು ಸ್ಪಷ್ಟವಾಗಿ ಹೇಳುತ್ತೇನೆ.",
        "hi": "हाँ, उस हिस्से को और साफ़ करके बताती हूँ।",
        "ta": "ஆம், அந்தப் பகுதியை இன்னும் தெளிவாகச் சொல்கிறேன்.",
        "te": "అవును, ఆ భాగాన్ని మరింత స్పష్టంగా చెప్తాను.",
        "ml": "അതെ, ആ ഭാഗം കൂടുതൽ വ്യക്തമായി പറയാം.",
    },
    "general": dict(_FALLBACK),
}

_COLLEGE_WITH_NAME = {
    "en": "Let me bring together some of the best things about the college for you, {name}.",
    "kn": "ಕಾಲೇಜಿನ ಉತ್ತಮ ಅಂಶಗಳನ್ನು ನಿಮಗಾಗಿ ಒಟ್ಟುಗೂಡಿಸುತ್ತೇನೆ, {name}.",
    "hi": "कॉलेज की अच्छी बातें आपके लिए एक साथ लाती हूँ, {name}।",
    "ta": "கல்லூரியின் சிறப்பானவற்றை உங்களுக்காகத் தொகுக்கிறேன், {name}.",
    "te": "కళాశాల మంచి అంశాలను మీ కోసం సమీకరిస్తాను, {name}.",
    "ml": "കോളേജിന്റെ നല്ല കാര്യങ്ങൾ നിങ്ങൾക്കായി ഒരുമിച്ച് ശേഖരിക്കാം, {name}.",
}


def infer_thinking_topic(raw: str) -> str:
    q = (raw or "").lower()
    if re.search(r"\b(hod|head of|principal|trustee|vice.?principal)\b", q) or re.search(
        r"ಮುಖ್ಯಸ್ಥ|विभाग प्रमुख|துறைத் தலைவர்|అధిపతి|മേധാവി|ಸಚಿವ", raw or ""
    ):
        return "hod"
    if re.search(r"\b(fee|fees|shulk|tuition)\b", q) or re.search(r"ಶುಲ್ಕ|फीस|கட்டணம்|ఫీజు|ഫീസ്", raw or ""):
        return "fees"
    if re.search(r"\b(placement|placements|package|recruit)\b", q) or re.search(
        r"ಪ್ಲೇಸ್|प्लेसमेंट|வேலைவாய்ப்பு|ప్లేస్|പ്ലേസ്", raw or ""
    ):
        return "placements"
    if re.search(r"\b(bus|buses|transport|route)\b", q) or re.search(r"ಬಸ್|बस|பேருந்து|బస్సు|ബസ്", raw or ""):
        return "transport"
    if re.search(r"\b(hostel|canteen|campus|room)\b", q) or re.search(
        r"ಹಾಸ್ಟೆಲ್|कैंपस|விடுதி|హాస్టల్|ഹോസ്റ്റൽ|ಕ್ಯಾಂಪಸ್", raw or ""
    ):
        return "campus"
    if re.search(r"\b(document|documents|admission|apply|eligibility)\b", q) or re.search(
        r"ಪ್ರವೇಶ|प्रवेश|சேர்க்கை|ప్రవేశం|പ്രവേശന", raw or ""
    ):
        return "admissions"
    if re.search(r"\b(course|cse|ise|ece|mba|data science|aiml|department)\b", q) or re.search(
        r"ಕೋರ್ಸ್|कोर्स|பாடநெறி|కోర్సు|കോഴ്സ്|ವಿಭಾಗ", raw or ""
    ):
        return "course"
    if re.search(r"\b(college|svit|how good|ranking|best)\b", q) or re.search(
        r"ಕಾಲೇಜು|कॉलेज|கல்லூரி|కళాశాల|കോളേജ്", raw or ""
    ):
        return "college"
    if re.search(r"\b(more about (him|her|them)|tell me more)\b", q):
        return "faculty"
    return "general"


def compose_thinking_bridge(raw_text: str, lang_key: str, guest_name: str | None = None) -> str:
    key = (lang_key or "en").strip().lower()[:2]
    if key not in _FALLBACK:
        key = "en"
    topic = infer_thinking_topic(raw_text or "")
    name = (guest_name or "").strip()
    if name and topic == "college":
        tmpl = _COLLEGE_WITH_NAME.get(key) or _COLLEGE_WITH_NAME["en"]
        return tmpl.replace("{name}", name)
    table = _BY_TOPIC.get(topic) or _BY_TOPIC["general"]
    return table.get(key) or _FALLBACK[key]
