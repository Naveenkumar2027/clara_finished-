import { describe, expect, it } from 'vitest';

import { errorCodeToMessage } from '../../hooks/useSpeechRecognition';
import { clipLocalizedText } from '../clipLocalizedText';
import { uiText } from '../uiCopy';
import { collegeDataForLanguage } from '../../hooks/useCollegeData';
import {
  buildAdmissionsCardsFromLocale,
  buildInstitutionCardsFromLocale,
  buildTrusteeCardsFromLocale,
} from '../../lib/collegeLocaleUtils';
import { selectFaqSuggestions } from '../../data/faqSuggestions';
import { getStaticCardsForTrigger } from '../../lib/cardData';

describe('Kannada UI authority and display fidelity', () => {
  it('returns the exact approved welcome and fixed states', () => {
    expect(uiText('Kannada', 'welcome.general_display')).toBe(
      'ಸ್ವಾಗತ.\nಇಂದು ನಿಮಗೆ ಯಾವ ಮಾಹಿತಿ ಬೇಕು?',
    );
    expect(uiText('Kannada', 'welcome.named_narration', { name: 'ಆಶಾ' })).toBe(
      'ಆಶಾ ಅವರೇ, ಸ್ವಾಗತ. ಇಂದು ನಿಮಗೆ ಯಾವ ಮಾಹಿತಿ ಬೇಕು?',
    );
    expect(uiText('Kannada', 'status.processing')).toBe(
      'ನಿಮ್ಮ ವಿನಂತಿಯನ್ನು ಪ್ರಕ್ರಿಯೆಗೊಳಿಸಲಾಗುತ್ತಿದೆ…',
    );
  });

  it('does not use English browser speech errors in Kannada mode', () => {
    for (const code of ['not-allowed', 'no-speech', 'network', 'audio-capture', 'service-not-allowed']) {
      const message = errorCodeToMessage(code, 'Kannada');
      expect(message).toMatch(/[\u0C80-\u0CFF]/u);
      expect(message).not.toMatch(/Try again|Microphone|Voice input|No speech/u);
    }
  });

  it('clips only at complete Kannada grapheme boundaries', () => {
    const text = 'ಕನ್ನಡ ಭಾಷೆಯನ್ನು ಸರಿಯಾಗಿ ಪ್ರದರ್ಶಿಸಬೇಕು';
    const clipped = clipLocalizedText(text, 12);
    expect(clipped.length).toBeGreaterThan(0);
    expect(text.startsWith(clipped)).toBe(true);
    expect(clipped).not.toMatch(/[್\u200c\u200d]$/u);
  });

  it('blocks conflicting fee dictionaries instead of rendering raw structures', () => {
    const cards = buildAdmissionsCardsFromLocale(collegeDataForLanguage('Kannada'), 'Kannada');
    const feeCards = cards.filter((card) => /ಶುಲ್ಕ/u.test(card.title));
    expect(feeCards.length).toBeGreaterThanOrEqual(2);
    for (const card of feeCards) {
      expect(card.content).toContain('ಅಧಿಕೃತವಾಗಿ ದೃಢೀಕರಿಸಲಾಗಿಲ್ಲ');
      expect(card.content).not.toMatch(/[{}]|'CSE'|ug_management/u);
    }
  });

  it('uses the clean authoritative FAQ catalog for Kannada suggestion chips', () => {
    const [suggestion] = selectFaqSuggestions('Kannada', ['college'], []);
    expect(suggestion.id).toBe('college-private');
    expect(suggestion.text).toBe('SVIT ಖಾಸಗಿ ಕಾಲೇಜೇ ಅಥವಾ ಸರ್ಕಾರಿ ಕಾಲೇಜೇ?');
    expect(suggestion.text).not.toContain('à');
  });

  it('uses canonical locale data for Kannada institution and trustee cards', () => {
    const data = collegeDataForLanguage('Kannada');
    const institution = buildInstitutionCardsFromLocale(data);
    const trustees = buildTrusteeCardsFromLocale(data);
    expect(institution[0].content).toMatch(/[ಀ-೿]/u);
    expect(trustees.length).toBeGreaterThanOrEqual(7);
    expect(trustees.every((card) => /[ಀ-೿]/u.test(card.content))).toBe(true);
    expect(getStaticCardsForTrigger('Kannada', 'college')).toBeNull();
  });

  it('centralizes Kannada document and comparison copy in the shared contract', () => {
    expect(uiText('Kannada', 'documents.title')).toBe('ಅಗತ್ಯ ದಾಖಲೆಗಳು');
    expect(uiText('Kannada', 'documents.items.aadhaar')).toBe('ಆಧಾರ್ ಕಾರ್ಡ್‌ನ ಪ್ರತಿ');
    expect(uiText('Kannada', 'comparison.heading')).toBe('ಕಾರ್ಯಕ್ರಮಗಳ ಹೋಲಿಕೆ');
  });
});
