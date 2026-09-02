export type IndicLanguageCode = 'hi' | 'kn' | 'ta' | 'te' | 'ml';

const INDIC_SCRIPT_PATTERNS: ReadonlyArray<{
  language: IndicLanguageCode;
  pattern: RegExp;
}> = [
  { language: 'kn', pattern: /[\u0C80-\u0CFF]/u },
  { language: 'te', pattern: /[\u0C00-\u0C7F]/u },
  { language: 'ta', pattern: /[\u0B80-\u0BFF]/u },
  { language: 'ml', pattern: /[\u0D00-\u0D7F]/u },
  // Devanagari text maps to Hindi, CLARA's supported Devanagari language.
  { language: 'hi', pattern: /[\u0900-\u097F\uA8E0-\uA8FF]/u },
];

export function indicLanguageFromText(value: string): IndicLanguageCode | null {
  for (const script of INDIC_SCRIPT_PATTERNS) {
    if (script.pattern.test(value)) return script.language;
  }
  return null;
}

export function containsIndic(value: string): boolean {
  return indicLanguageFromText(value) !== null;
}

/** Backward-compatible name for callers created during the first remediation. */
export const isIndic = containsIndic;
