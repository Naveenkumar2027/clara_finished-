import { describe, expect, it } from 'vitest';
import { campusUnitFromLocale } from '../campusUnitLocale';
import { uiText } from '../../../../../localization/uiCopy';

describe('campus unit locale cards', () => {
  it('keeps the same unitId across languages and marks sample content', () => {
    const en = campusUnitFromLocale('hostel.girls.rooms', 'English');
    const kn = campusUnitFromLocale('hostel.girls.rooms', 'Kannada');
    const hi = campusUnitFromLocale('hostel.girls.rooms', 'Hindi');
    expect(en?.content_status).toBe('SAMPLE_REPLACE_WITH_OFFICIAL');
    expect(kn?.content_status).toBe('SAMPLE_REPLACE_WITH_OFFICIAL');
    expect(en?.title).not.toBe(kn?.title);
    expect(kn?.title).toContain('ಕೊಠಡಿ');
    expect(en?.body).toBe(uiText('English', 'availability.official_fact_blocked'));
    expect(en?.tts_summary).not.toContain('SAMPLE_REPLACE_WITH_OFFICIAL');
    expect(kn?.tts_summary).not.toContain('Showing');
    expect(kn?.title).not.toContain('ಮಾದರಿ');
    expect(kn?.body).toBe(
      'ಈ ಮಾಹಿತಿಯನ್ನು ಇನ್ನೂ ಅಧಿಕೃತವಾಗಿ ದೃಢೀಕರಿಸಲಾಗಿಲ್ಲ.\nಹೆಚ್ಚಿನ ಮಾಹಿತಿಗಾಗಿ ಸಂಬಂಧಿತ ವಿಭಾಗವನ್ನು ಸಂಪರ್ಕಿಸಿ.',
    );
    expect(kn?.tts_summary).not.toContain('SAMPLE_REPLACE_WITH_OFFICIAL');
    expect(hi?.body).toBe(uiText('Hindi', 'availability.official_fact_blocked'));
    expect(hi?.body).toMatch(/[\u0900-\u097f]/u);
    expect(hi?.title).not.toContain('SAMPLE_REPLACE_WITH_OFFICIAL');
    expect(hi?.tts_summary).not.toContain('SAMPLE_REPLACE_WITH_OFFICIAL');
  });

  it('does not silently reuse another unit', () => {
    const rooms = campusUnitFromLocale('hostel.girls.rooms', 'English');
    const food = campusUnitFromLocale('hostel.girls.food', 'English');
    const boys = campusUnitFromLocale('hostel.boys.rooms', 'English');
    expect(rooms?.title).not.toBe(food?.title);
    expect(rooms?.title).not.toBe(boys?.title);
  });
});
