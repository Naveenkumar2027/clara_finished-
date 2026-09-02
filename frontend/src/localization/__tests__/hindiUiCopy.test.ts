import { describe, expect, it } from 'vitest';

import { errorCodeToMessage } from '../../hooks/useSpeechRecognition';
import { translations } from '../../context/LanguageContext';
import { uiText } from '../uiCopy';

describe('Hindi shared UI copy', () => {
  it('maps Hindi names and locale codes to Devanagari copy', () => {
    expect(uiText('Hindi', 'status.listening')).toBe('सुन रही हूँ…');
    expect(uiText('hi-IN', 'status.processing')).toMatch(/[\u0900-\u097f]/u);
    expect(uiText('HI_in', 'session.goodbye')).toBe('अलविदा।');
  });

  it('does not expose English speech errors in Hindi mode', () => {
    for (const code of ['not-allowed', 'no-speech', 'network', 'audio-capture', 'service-not-allowed']) {
      const message = errorCodeToMessage(code, 'Hindi');
      expect(message).toMatch(/[\u0900-\u097f]/u);
      expect(message).not.toMatch(/Try again|Microphone|Voice input|No speech/u);
    }
  });

  it('substitutes localized placeholders', () => {
    expect(uiText('Hindi', 'action.hod', { department: 'डेटा साइंस' })).toContain(
      'डेटा साइंस विभाग',
    );
  });

  it('keeps active shared labels on the authoritative Hindi locale', () => {
    expect(translations.selectLanguage.Hindi).toBe(uiText('Hindi', 'language.select'));
    expect(translations.listening.Hindi).toBe(uiText('Hindi', 'status.listening'));
    expect(translations.claraIsThinking.Hindi).toBe(uiText('Hindi', 'status.thinking'));
    expect(translations.tapToSpeak.Hindi).toBe(uiText('Hindi', 'status.tap_to_speak'));
    expect(translations.chatBack.Hindi).toBe(uiText('Hindi', 'session.back'));
    expect(translations.cardOpen.Hindi).toBe(uiText('Hindi', 'cards.open'));
    for (const path of ['cards.hostel', 'cards.canteen', 'cards.event']) {
      expect(uiText('Hindi', path)).toMatch(/[\u0900-\u097f]/u);
    }
  });
});
