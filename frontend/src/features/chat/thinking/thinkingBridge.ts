/**
 * Optimistic thinking-bridge fallback only.
 * Canonical sentence comes from the backend semantic-aware bridge via WebSocket.
 * Do NOT re-implement topic→template classification on the client.
 */

import type { Language } from '../../../context/LanguageContext';

const FALLBACK: Record<Language, string> = {
  English: 'Let me bring that together for you.',
  Kannada: 'ನಾನು ಅದನ್ನು ನಿಮಗಾಗಿ ಒಟ್ಟುಗೂಡಿಸುತ್ತೇನೆ.',
  Hindi: 'मैं वह आपके लिए एक साथ लाती हूँ।',
  Tamil: 'அதை உங்களுக்காக ஒன்றாகத் தொகுக்கிறேன்.',
  Telugu: 'దాన్ని మీ కోసం సమీకరిస్తాను.',
  Malayalam: 'അത് നിങ്ങൾക്കായി ഒരുമിച്ച് ശേഖരിക്കാം.',
};

/** Neutral placeholder until backend thinking_text arrives. */
export function composeThinkingBridge(_opts: {
  query: string;
  language: Language;
  guestName?: string | null;
}): string {
  return thinkingBridgeFallback(_opts.language);
}

export function thinkingBridgeFallback(language: Language): string {
  return FALLBACK[language] ?? FALLBACK.English;
}

/** @deprecated Backend owns topic inference via SemanticRequest. */
export function inferThinkingTopic(_raw: string): string {
  return 'general';
}
