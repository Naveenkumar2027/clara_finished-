import { describe, expect, it } from 'vitest';

import { uiText } from '../uiCopy';

describe('Telugu and Malayalam UI localization', () => {
  it('uses Telugu instead of the English fallback', () => {
    expect(uiText('Telugu', 'cards.faculty')).toBe('అధ్యాపకులు');
    expect(uiText('te-IN', 'error.no_speech')).toMatch(/[\u0C00-\u0C7F]/u);
    expect(uiText('Telugu', 'action.department', { department: 'CSE' })).toContain('CSE');
  });

  it('uses Malayalam instead of the English fallback', () => {
    expect(uiText('Malayalam', 'cards.faculty')).toBe('അധ്യാപകർ');
    expect(uiText('ml-IN', 'error.no_speech')).toMatch(/[\u0D00-\u0D7F]/u);
    expect(uiText('Malayalam', 'action.department', { department: 'CSE' })).toContain('CSE');
  });
});
