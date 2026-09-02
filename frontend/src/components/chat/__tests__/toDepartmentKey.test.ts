import { describe, expect, it } from 'vitest';
import { hodCopyFromUnitCard, toDepartmentKey } from '../LeadershipOverview';
import type { PresentationCardModel } from '../../../features/chat/presentation/PresentationCardModel';

describe('toDepartmentKey', () => {
  it('keeps cse_aiml and cse_ds distinct (does not collapse to cse)', () => {
    expect(toDepartmentKey('cse_aiml')).toBe('cse_aiml');
    expect(toDepartmentKey('cse_ds')).toBe('cse_ds');
    expect(toDepartmentKey('cse')).toBe('cse');
    expect(toDepartmentKey('cse_bs')).toBe('cse_bs');
    expect(toDepartmentKey('CSE (Business Systems)')).toBe('cse_bs');
  });
});

describe('hodCopyFromUnitCard', () => {
  const knModel: PresentationCardModel = {
    cardId: 'hod_profile',
    unitId: 'cse_ds.hod',
    sectionId: 'hod_voice',
    cardType: 'hod',
    departmentId: 'cse_ds',
    title: 'HOD ಮತ್ತು ದೃಷ್ಟಿಕೋನ',
    content: 'ಡಾ. ನಾಗಶ್ರೀ ಎನ್ ಅವರು ಅತ್ಯಾಧುನಿಕ ಪರಿಕಲ್ಪನೆಗಳು',
    cardIndex: 0,
    slotIndex: 1,
  };

  it('uses localized ContentUnit body and never English HOD_FALLBACK', () => {
    const copy = hodCopyFromUnitCard(knModel, null);
    expect(copy.unitId).toBe('cse_ds.hod');
    expect(copy.bio).toContain('ನಾಗಶ್ರೀ');
    expect(copy.bio).not.toMatch(/Shashikumar|extensive teaching and research/i);
    expect(copy.label).toContain('ದೃಷ್ಟಿಕೋನ');
  });

  it('may decorate name from current-language locale row without replacing body', () => {
    const copy = hodCopyFromUnitCard(knModel, {
      hod_name: 'ಡಾ. ನಾಗಶ್ರೀ ಎನ್',
      hod_title: 'HOD, CSE (Data Science)',
    });
    expect(copy.name).toContain('ನಾಗಶ್ರೀ');
    expect(copy.bio).toContain('ನಾಗಶ್ರೀ');
    expect(copy.bio).not.toMatch(/extensive teaching and research/i);
  });
});
