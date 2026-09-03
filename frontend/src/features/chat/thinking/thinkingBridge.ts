/**
 * Fast, language-aware thinking-bridge sentences.
 * Deterministic templates — no second LLM call, no system-status wording.
 */

import type { Language } from '../../../context/LanguageContext';

export type ThinkingTopic =
  | 'college'
  | 'course'
  | 'fees'
  | 'hod'
  | 'admissions'
  | 'placements'
  | 'transport'
  | 'campus'
  | 'faculty'
  | 'followup'
  | 'general';

const FALLBACK: Record<Language, string> = {
  English: 'Let me bring that together for you.',
  Kannada: 'ನಾನು ಅದನ್ನು ನಿಮಗಾಗಿ ಒಟ್ಟುಗೂಡಿಸುತ್ತೇನೆ.',
  Hindi: 'मैं वह आपके लिए एक साथ लाती हूँ।',
  Tamil: 'அதை உங்களுக்காக ஒன்றாகத் தொகுக்கிறேன்.',
  Telugu: 'దాన్ని మీ కోసం సమీకరిస్తాను.',
  Malayalam: 'അത് നിങ്ങൾക്കായി ഒരുമിച്ച് ശേഖരിക്കാം.',
};

const WITH_NAME: Partial<Record<ThinkingTopic, Record<Language, string>>> = {
  college: {
    English: 'Let me bring together some of the best things about the college for you, {name}.',
    Kannada: 'ಕಾಲೇಜಿನ ಉತ್ತಮ ಅಂಶಗಳನ್ನು ನಿಮಗಾಗಿ ಒಟ್ಟುಗೂಡಿಸುತ್ತೇನೆ, {name}.',
    Hindi: 'कॉलेज की अच्छी बातें आपके लिए एक साथ लाती हूँ, {name}।',
    Tamil: 'கல்லூரியின் சிறப்பானவற்றை உங்களுக்காகத் தொகுக்கிறேன், {name}.',
    Telugu: 'కళాశాల మంచి అంశాలను మీ కోసం సమీకరిస్తాను, {name}.',
    Malayalam: 'കോളേജിന്റെ നല്ല കാര്യങ്ങൾ നിങ്ങൾക്കായി ഒരുമിച്ച് ശേഖരിക്കാം, {name}.',
  },
};

const BY_TOPIC: Record<ThinkingTopic, Record<Language, string>> = {
  college: {
    English: 'Let me bring together some of the best things about the college for you.',
    Kannada: 'ಕಾಲೇಜಿನ ಉತ್ತಮ ಅಂಶಗಳನ್ನು ನಿಮಗಾಗಿ ಒಟ್ಟುಗೂಡಿಸುತ್ತೇನೆ.',
    Hindi: 'कॉलेज की अच्छी बातें आपके लिए एक साथ लाती हूँ।',
    Tamil: 'கல்லூரியின் சிறப்பானவற்றை உங்களுக்காகத் தொகுக்கிறேன்.',
    Telugu: 'కళాశాల మంచి అంశాలను మీ కోసం సమీకరిస్తాను.',
    Malayalam: 'കോളേജിന്റെ നല്ല കാര്യങ്ങൾ നിങ്ങൾക്കായി ഒരുമിച്ച് ശേഖരിക്കാം.',
  },
  course: {
    English: 'Let me pull together the key details about that course for you.',
    Kannada: 'ಆ ಕೋರ್ಸ್‌ನ ಮುಖ್ಯ ವಿವರಗಳನ್ನು ನಿಮಗಾಗಿ ತರುತ್ತೇನೆ.',
    Hindi: 'उस कोर्स की मुख्य बातें आपके लिए लाती हूँ।',
    Tamil: 'அந்த பாடநெறியின் முக்கிய விவரங்களைத் தொகுக்கிறேன்.',
    Telugu: 'ఆ కోర్సు ముఖ్య వివరాలను మీ కోసం సమీకరిస్తాను.',
    Malayalam: 'ആ കോഴ്സിന്റെ പ്രധാന വിവരങ്ങൾ ഒരുമിച്ച് ശേഖരിക്കാം.',
  },
  fees: {
    English: 'Let me check the fee details for the program you are asking about.',
    Kannada: 'ನೀವು ಕೇಳುತ್ತಿರುವ ಕಾರ್ಯಕ್ರಮದ ಶುಲ್ಕವನ್ನು ನೋಡುತ್ತೇನೆ.',
    Hindi: 'जिस कार्यक्रम के बारे में पूछा है, उसकी फीस देखती हूँ।',
    Tamil: 'நீங்கள் கேட்கும் பாடநெறியின் கட்டணத்தைப் பார்க்கிறேன்.',
    Telugu: 'మీరు అడుగుతున్న కోర్సు ఫీజును చూస్తాను.',
    Malayalam: 'നിങ്ങൾ ചോദിക്കുന്ന പ്രോഗ്രാമിന്റെ ഫീസ് നോക്കാം.',
  },
  hod: {
    English: 'Let me bring up the details about the department head.',
    Kannada: 'ವಿಭಾಗದ ಮುಖ್ಯಸ್ಥರ ವಿವರವನ್ನು ತರುತ್ತೇನೆ.',
    Hindi: 'विभाग प्रमुख का विवरण आपके लिए लाती हूँ।',
    Tamil: 'துறைத் தலைவர் விவரத்தைக் கொண்டு வருகிறேன்.',
    Telugu: 'విభాగ అధిపతి వివరాలు తెస్తాను.',
    Malayalam: 'വിഭാഗ മേധാവിയുടെ വിവരങ്ങൾ കൊണ്ടുവരാം.',
  },
  admissions: {
    English: 'Let me bring together the admission details you need.',
    Kannada: 'ನಿಮಗೆ ಬೇಕಾದ ಪ್ರವೇಶ ವಿವರಗಳನ್ನು ಒಟ್ಟುಗೂಡಿಸುತ್ತೇನೆ.',
    Hindi: 'प्रवेश से जुड़ी बातें आपके लिए लाती हूँ।',
    Tamil: 'சேர்க்கை விவரங்களை உங்களுக்காகத் தொகுக்கிறேன்.',
    Telugu: 'ప్రవేశ వివరాలను మీ కోసం సమీకరిస్తాను.',
    Malayalam: 'പ്രവേശന വിവരങ്ങൾ ഒരുമിച്ച് ശേഖരിക്കാം.',
  },
  placements: {
    English: 'Let me bring together the placement highlights for you.',
    Kannada: 'ಪ್ಲೇಸ್‌ಮೆಂಟ್ ಮುಖ್ಯ ಅಂಶಗಳನ್ನು ನಿಮಗಾಗಿ ತರುತ್ತೇನೆ.',
    Hindi: 'प्लेसमेंट की मुख्य बातें आपके लिए लाती हूँ।',
    Tamil: 'வேலைவாய்ப்பு சிறப்பம்சங்களைத் தொகுக்கிறேன்.',
    Telugu: 'ప్లేస్‌మెంట్ ముఖ్యాంశాలను సమీకరిస్తాను.',
    Malayalam: 'പ്ലേസ്‌മെന്റ് ഹൈലൈറ്റുകൾ ഒരുമിച്ച് ശേഖരിക്കാം.',
  },
  transport: {
    English: 'Let me bring together the transport details for you.',
    Kannada: 'ಸಾರಿಗೆ ವಿವರಗಳನ್ನು ನಿಮಗಾಗಿ ತರುತ್ತೇನೆ.',
    Hindi: 'परिवहन की जानकारी आपके लिए लाती हूँ।',
    Tamil: 'போக்குவரத்து விவரங்களைத் தொகுக்கிறேன்.',
    Telugu: 'రవాణా వివరాలను సమీకరిస్తాను.',
    Malayalam: 'ഗതാഗത വിവരങ്ങൾ ഒരുമിച്ച് ശേഖരിക്കാം.',
  },
  campus: {
    English: 'Let me show you what you need to know about the campus.',
    Kannada: 'ಕ್ಯಾಂಪಸ್ ಬಗ್ಗೆ ನಿಮಗೆ ಬೇಕಾದುದನ್ನು ತೋರಿಸುತ್ತೇನೆ.',
    Hindi: 'कैंपस के बारे में जरूरी बातें बताती हूँ।',
    Tamil: 'வளாகம் பற்றித் தெரிந்துகொள்ள வேண்டியதைக் காட்டுகிறேன்.',
    Telugu: 'క్యాంపస్ గురించి మీకు కావాల్సినవి చూపిస్తాను.',
    Malayalam: 'ക്യാമ്പസിനെക്കുറിച്ച് അറിയേണ്ടത് കാണിച്ചുതരാം.',
  },
  faculty: {
    English: 'Let me find the details about the person you are asking about.',
    Kannada: 'ನೀವು ಕೇಳುತ್ತಿರುವ ವ್ಯಕ್ತಿಯ ವಿವರವನ್ನು ತರುತ್ತೇನೆ.',
    Hindi: 'जिस व्यक्ति के बारे में पूछा है, उनका विवरण लाती हूँ।',
    Tamil: 'நீங்கள் கேட்கும் நபரின் விவரத்தைக் கொண்டு வருகிறேன்.',
    Telugu: 'మీరు అడుగుతున్న వ్యక్తి వివరాలు తెస్తాను.',
    Malayalam: 'നിങ്ങൾ ചോദിക്കുന്ന വ്യക്തിയുടെ വിവരങ്ങൾ കൊണ്ടുവരാം.',
  },
  followup: {
    English: 'Yes, let me explain that part a little more clearly.',
    Kannada: 'ಹೌದು, ಆ ಭಾಗವನ್ನು ಇನ್ನಷ್ಟು ಸ್ಪಷ್ಟವಾಗಿ ಹೇಳುತ್ತೇನೆ.',
    Hindi: 'हाँ, उस हिस्से को और साफ़ करके बताती हूँ।',
    Tamil: 'ஆம், அந்தப் பகுதியை இன்னும் தெளிவாகச் சொல்கிறேன்.',
    Telugu: 'అవును, ఆ భాగాన్ని మరింత స్పష్టంగా చెప్తాను.',
    Malayalam: 'അതെ, ആ ഭാഗം കൂടുതൽ വ്യക്തമായി പറയാം.',
  },
  general: {
    English: 'Let me bring that together for you.',
    Kannada: 'ನಾನು ಅದನ್ನು ನಿಮಗಾಗಿ ಒಟ್ಟುಗೂಡಿಸುತ್ತೇನೆ.',
    Hindi: 'मैं वह आपके लिए एक साथ लाती हूँ।',
    Tamil: 'அதை உங்களுக்காக ஒன்றாகத் தொகுக்கிறேன்.',
    Telugu: 'దాన్ని మీ కోసం సమీకరిస్తాను.',
    Malayalam: 'അത് നിങ്ങൾക്കായി ഒരുമിച്ച് ശേഖരിക്കാം.',
  },
};

export function inferThinkingTopic(raw: string): ThinkingTopic {
  const q = (raw || '').toLowerCase();
  if (!q.trim()) return 'general';
  if (/\b(more about (him|her|them)|tell me more|that part|follow ?up)\b/.test(q) || /ಹೆಚ್ಚು|और बता|மேலும்|మరింత|കൂടുതൽ/.test(raw)) {
    if (/\b(he|she|him|her|them)\b/.test(q) || /ಅವರು|उन|அவர்|ఆయన|അദ്ദേഹം/.test(raw)) return 'faculty';
    return 'followup';
  }
  if (/\b(hod|head of|principal|trustee|vice.?principal)\b/.test(q) || /ಮುಖ್ಯಸ್ಥ|विभाग प्रमुख|துறைத் தலைவர்|అధిపతి|മേധാവി|ಸಚಿವ/.test(raw)) {
    return 'hod';
  }
  if (/\b(fee|fees|shulk|tuition)\b/.test(q) || /ಶುಲ್ಕ|फीस|கட்டணம்|ఫీజు|ഫീസ്/.test(raw)) return 'fees';
  if (/\b(placement|placements|package|recruit)\b/.test(q) || /ಪ್ಲೇಸ್|प्लेसमेंट|வேலைவாய்ப்பு|ప్లేస్|പ്ലേസ്/.test(raw)) {
    return 'placements';
  }
  if (/\b(bus|buses|transport|route)\b/.test(q) || /ಬಸ್|बस|பேருந்து|బస్సు|ബസ്/.test(raw)) return 'transport';
  if (/\b(hostel|canteen|campus|room)\b/.test(q) || /ಹಾಸ್ಟೆಲ್|कैंपस|விடுதி|హాస్టల్|ഹോസ്റ്റൽ|ಕ್ಯಾಂಪಸ್/.test(raw)) {
    return 'campus';
  }
  if (/\b(document|documents|admission|apply|eligibility)\b/.test(q) || /ಪ್ರವೇಶ|प्रवेश|சேர்க்கை|ప్రవేశం|പ്രവേശന/.test(raw)) {
    return 'admissions';
  }
  if (/\b(course|cse|ise|ece|mba|data science|aiml|department)\b/.test(q) || /ಕೋರ್ಸ್|कोर्स|பாடநெறி|కోర్సు|കോഴ്സ്|ವಿಭಾಗ/.test(raw)) {
    return 'course';
  }
  if (/\b(college|svit|how good|ranking|best)\b/.test(q) || /ಕಾಲೇಜು|कॉलेज|கல்லூரி|కళాశాల|കോളേജ്/.test(raw)) {
    return 'college';
  }
  return 'general';
}

function shouldIncludeName(topic: ThinkingTopic, guestName: string | null | undefined): boolean {
  const name = (guestName || '').trim();
  if (!name) return false;
  return topic === 'college' || topic === 'general' || topic === 'followup';
}

export function composeThinkingBridge(opts: {
  query: string;
  language: Language;
  guestName?: string | null;
}): string {
  const language = opts.language || 'English';
  const topic = inferThinkingTopic(opts.query || '');
  const name = (opts.guestName || '').trim();
  if (name && shouldIncludeName(topic, name) && WITH_NAME[topic]) {
    const named = WITH_NAME[topic]![language] ?? WITH_NAME[topic]!.English;
    return named.replace('{name}', name);
  }
  const table = BY_TOPIC[topic] ?? BY_TOPIC.general;
  return table[language] ?? table.English ?? FALLBACK[language] ?? FALLBACK.English;
}

export function thinkingBridgeFallback(language: Language): string {
  return FALLBACK[language] ?? FALLBACK.English;
}
