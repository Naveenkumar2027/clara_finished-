import type { Language } from '../../../../context/LanguageContext';
import { collegeDataForLanguage } from '../../../../hooks/useCollegeData';
import type { CampusUnitRecord } from '../../../../types/collegeData';
import { SAMPLE_CONTENT_STATUS, uiText } from '../../../../localization/uiCopy';

export function campusUnitFromLocale(
  unitId: string,
  language: string | undefined,
): CampusUnitRecord | null {
  const lang = (language || 'English') as Language;
  const data = collegeDataForLanguage(
    ['English', 'Kannada', 'Hindi', 'Tamil', 'Telugu', 'Malayalam'].includes(lang)
      ? lang
      : 'English',
  );
  const row = data.campus_units?.[unitId];
  if (!row || typeof row !== 'object') return null;
  if (row.content_status === SAMPLE_CONTENT_STATUS) {
    return {
      ...row,
      title: String(row.title || unitId)
        .replace('(ಮಾದರಿ)', '')
        .replace('（ಮಾದರಿ）', '')
        .replace(/\((?:sample)\)/gi, '')
        .trim(),
      body: uiText(lang, 'availability.official_fact_blocked'),
      tts_summary: uiText(lang, 'availability.official_fact_blocked').replace('\n', ' '),
      points: [],
    };
  }
  return row;
}
