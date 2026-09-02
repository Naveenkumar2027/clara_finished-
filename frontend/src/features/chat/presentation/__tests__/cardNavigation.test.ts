import { describe, expect, it } from 'vitest';
import { parseCardNavigationCommand } from '../cardNavigation';

describe('parseCardNavigationCommand', () => {
  it.each([
    ['next', 'next'],
    ['ಮುಂದೆ', 'next'],
    ['अगला', 'next'],
    ['తదుపరి', 'next'],
    ['తర్వాత', 'next'],
    ['ముందుకు', 'next'],
    ['அடுத்து', 'next'],
    ['അടുത്ത', 'next'],
    ['അടുത്തത്', 'next'],
    ['മുന്നോട്ട്', 'next'],
    ['पुढे', 'next'],
    ['previous', 'previous'],
    ['ಹಿಂದೆ', 'previous'],
    ['पिछला', 'previous'],
    ['वापस', 'previous'],
    ['మునుపటి', 'previous'],
    ['వెనక్కి', 'previous'],
    ['முந்தைய', 'previous'],
    ['മുമ്പത്തെ', 'previous'],
    ['പിന്നോട്ട്', 'previous'],
    ['मागे', 'previous'],
  ])('maps %s without changing queue identity', (text, expected) => {
    expect(parseCardNavigationCommand(text)).toBe(expected);
  });

  it('accepts harmless punctuation and spacing', () => {
    expect(parseCardNavigationCommand('  NEXT! ')).toBe('next');
  });

  it('does not steal a new natural-language request containing a direction word', () => {
    expect(parseCardNavigationCommand('next show ECE fees')).toBeNull();
    expect(parseCardNavigationCommand('ಮುಂದೆ ECE fees ತೋರಿಸಿ')).toBeNull();
  });
});
