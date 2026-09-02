import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { containsIndic, indicLanguageFromText } from '../../../lib/indicUtils';
import AnimatedAiMessage from '../AnimatedAiMessage';

const CASES = [
  {
    language: 'kn',
    text: 'ದಯವಿಟ್ಟು ನಿಮ್ಮನ್ನು ಯಾವ ಹೆಸರಿನಿಂದ ಕರೆಯಬೇಕೆಂದು ತಿಳಿಸಿ.',
  },
  {
    language: 'kn',
    text: 'ಟ್ಟ ಮ್ಮ ನ್ನ ಕ್ಕ ಗ್ಗ ಚ್ಚ ಜ್ಜ ತ್ತ ದ್ದ ಪ್ಪ ಬ್ಬ ಸ್ಸ ಕ್ಷ ಜ್ಞ',
  },
  { language: 'hi', text: 'क्ष त्र ज्ञ प्र क्र श्र त्त न्न कृपया अपना नाम बताइए।' },
  { language: 'te', text: 'దయచేసి మీ పేరు చెప్పండి. క్క త్త' },
  { language: 'ta', text: 'தயவுசெய்து உங்கள் பெயரைச் சொல்லுங்கள்.' },
  { language: 'ml', text: 'ദയവായി നിങ്ങളുടെ പേര് പറയുക. ക്ക ന്ന' },
] as const;

describe('Indic message shaping structure', () => {
  it.each(CASES)('keeps $language text in one uninterrupted text node', ({ language, text }) => {
    const markup = renderToStaticMarkup(
      <AnimatedAiMessage text={text} className="bubble-clara" />,
    );

    expect(markup).toContain('indic-message-reveal');
    expect(markup).toContain(`lang="${language}"`);
    expect(markup).toContain(`>${text}</div>`);
    expect(markup).not.toContain('<span');
    expect(markup).not.toContain('letter-reveal');
    expect(markup).not.toContain('letter-reveal-sync');
    expect(markup).not.toContain('token-reveal');
  });

  it('detects all supported Indic scripts before animation tokenization', () => {
    for (const { language, text } of CASES) {
      expect(containsIndic(text)).toBe(true);
      expect(indicLanguageFromText(text)).toBe(language);
    }
    expect(containsIndic('English character animation stays enabled.')).toBe(false);
    expect(indicLanguageFromText('English character animation stays enabled.')).toBeNull();
  });
});
