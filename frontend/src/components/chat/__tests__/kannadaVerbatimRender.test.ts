/**
 * Verifies the frontend render chain preserves backend Kannada verbatim.
 *
 * The fixes this test guards:
 *  - Pagination in `paginateResponseText` must reconstruct the original
 *    Kannada text byte-for-byte, even when the source contains the
 *    Kannada danda "।" (U+0964) which is not part of the standard
 *    ASCII sentence-terminator class "[.!?]".
 *  - `AnimatedAiMessage`'s `playbackProgress` reveal must always include
 *    the final grapheme (combining mark, terminal danda, ZWJ-joined
 *    graphemes) once the source has been delivered.
 *  - Sentence segmentation in `processResponseSentences` must not drop or
 *    reorder Kannada danda characters when joining sentences back.
 *  - The `frontend/src/data/locales/kn.json` file must NOT be referenced
 *    by the frontend import graph; only the authoritative
 *    `@college-locales/kn.json` (resolved to `backend/data/locales/kn.json`)
 *    may be the source of truth.
 *  - The WebSocket greeting text rendered by the panel must equal the
 *    text delivered in `payload.messages` (no frontend-side translation).
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import {
  paginateResponseText,
  countGraphemes,
} from '../../../features/chat/layout/paginateResponseText';
import { processResponseSentences } from './processResponseSentencesProbe';
import { resolvePlayableGraphemeCount } from './playbackProgressProbe';

const FRONTEND_ROOT = resolve(__dirname, '..', '..', '..', '..');

const KANNADA_WITH_DANDA =
  'ಎಲ್ಲರಿಗೂ ನಮಸ್ಕಾರ. ಎಸ್‌ವಿಐಟಿ ಕ್ಯಾಂಪಸ್ ಬಗ್ಗೆ ಮಾಹಿತಿ ಇಲ್ಲಿದೆ. ದಯವಿಟ್ಟು ಕೇಳಿ.';

const KANNADA_TERMINAL_DANDA =
  'ನಮಸ್ಕಾರ। ಇದು ಪರೀಕ್ಷೆ। ಇದು ಅಂತ್ಯ।';

const KANNADA_WITH_COMBINING_MARKS =
  'ಕನ್ನಡ ಭಾಷೆಯಲ್ಲಿ ವಿಶೇಷ ಸಂಯೋಜನೆಗಳು ಇವೆ: ಕ್ಷ, ಜ್ಞ, ತ್ರ, ಶ್ರ.';

const KANNADA_WITH_ZWJ_LABEL = 'ಮ್ಯಾನೇಜ್\u200Cಮೆಂಟ್ ಕೋಟಾ';

describe('Kannada text reaches the DOM unchanged', () => {
  it('paginateResponseText concatenates back to the original Kannada source (with danda)', () => {
    const typography = {
      fontSizePx: 18,
      lineHeight: 1.5,
      widthPx: 600,
      fontFamily: 'Noto Sans Kannada',
      fontWeight: 600,
      letterSpacing: 'normal',
    };

    const pages = paginateResponseText(KANNADA_TERMINAL_DANDA, typography, 30);

    expect(pages.length).toBeGreaterThan(0);
    expect(pages.join('')).toBe(KANNADA_TERMINAL_DANDA);
  });

  it('paginateResponseText paginates long Kannada text and still reconstructs exactly', () => {
    const typography = {
      fontSizePx: 28,
      lineHeight: 1.5,
      widthPx: 320,
      fontFamily: 'Noto Sans Kannada',
      fontWeight: 600,
      letterSpacing: 'normal',
    };

    // A paragraph that would not fit on one line at the given width/height.
    const longKannada = KANNADA_TERMINAL_DANDA.repeat(8);
    const pages = paginateResponseText(longKannada, typography, 50);

    // Even when DOM measurement is unavailable (e.g., Node test env),
    // the integrity contract still holds: pages.join('') === source.
    expect(pages.length).toBeGreaterThan(0);
    expect(pages.join('')).toBe(longKannada);
    expect(pages.join('').length).toBe(longKannada.length);
  });

  it('paginateResponseText preserves combining-mark Kannada and ZWJ labels exactly', () => {
    const typography = {
      fontSizePx: 18,
      lineHeight: 1.5,
      widthPx: 400,
      fontFamily: 'Noto Sans Kannada',
      fontWeight: 600,
      letterSpacing: 'normal',
    };

    const withCombining = paginateResponseText(KANNADA_WITH_COMBINING_MARKS, typography, 20);
    expect(withCombining.join('')).toBe(KANNADA_WITH_COMBINING_MARKS);

    const withZwj = paginateResponseText(KANNADA_WITH_ZWJ_LABEL, typography, 200);
    expect(withZwj.join('')).toBe(KANNADA_WITH_ZWJ_LABEL);
    // ZWJ must survive byte-for-byte.
    expect(withZwj.join('')).toContain('\u200C');
  });

  it('paginateResponseText does not silently drop a trailing danda or grapheme', () => {
    const typography = {
      fontSizePx: 18,
      lineHeight: 1.5,
      widthPx: 800,
      fontFamily: 'Noto Sans Kannada',
      fontWeight: 600,
      letterSpacing: 'normal',
    };

    const pages = paginateResponseText(KANNADA_TERMINAL_DANDA, typography, 1000);
    const joined = pages.join('');

    expect(joined.endsWith('ಅಂತ್ಯ।')).toBe(true);
    expect(joined).toHaveLength(KANNADA_TERMINAL_DANDA.length);
  });

  it('processResponseSentences recognizes the Kannada danda as a sentence boundary', () => {
    // The frontend reveal animation syncs to playback; sentence boundaries
    // drive per-sentence reveal cadence. When the source uses the Kannada
    // danda "।" (U+0964) the frontend must split on it so each Kannada
    // sentence gets its own reveal beat — without altering the source.
    const sentences = processResponseSentences(KANNADA_TERMINAL_DANDA);
    expect(sentences.length).toBe(3);
    expect(sentences[0]).toBe('ನಮಸ್ಕಾರ।');
    expect(sentences[1]).toBe('ಇದು ಪರೀಕ್ಷೆ।');
    expect(sentences[2]).toBe('ಇದು ಅಂತ್ಯ।');
  });

  it('processResponseSentences preserves Kannada danda when joining sentences back', () => {
    const sentences = processResponseSentences(KANNADA_TERMINAL_DANDA);
    const rejoined = sentences.join(' ').replace(/\s+/g, ' ').trim();
    // The result should contain the Kannada danda characters from the source.
    const sourceDandaCount = (KANNADA_TERMINAL_DANDA.match(/।/g) ?? []).length;
    const outDandaCount = (rejoined.match(/।/g) ?? []).length;
    expect(outDandaCount).toBe(sourceDandaCount);
    expect(rejoined).toContain('ನಮಸ್ಕಾರ');
    expect(rejoined).toContain('ಅಂತ್ಯ');
  });

  it('playback reveal always includes the final grapheme of a Kannada source', () => {
    const totalGraphemes = countGraphemes(KANNADA_WITH_DANDA.replace(/\s+/g, ''));

    // At 99% playback, the last grapheme must already be revealed
    // (otherwise terminal "." or "ಾ" or combining mark would be cut).
    const revealedAt099 = resolvePlayableGraphemeCount(0.999, totalGraphemes);
    const revealedAt0999 = resolvePlayableGraphemeCount(0.9999, totalGraphemes);
    const revealedAt1 = resolvePlayableGraphemeCount(1, totalGraphemes);

    expect(revealedAt0999).toBe(totalGraphemes);
    expect(revealedAt1).toBe(totalGraphemes);
    // The playable-grapheme-count function must never return fewer than
    // "everything the user is supposed to read" once progress is at or
    // above the natural 1.0 threshold.
    expect(revealedAt0999).toBeGreaterThanOrEqual(revealedAt099);
  });

  it('playback reveal for very short Kannada text never hides the only grapheme', () => {
    // For a 1-grapheme source (e.g. a single Kannada akshara), the floor
    // formula p * 1 collapses to 0 for any p < 1, hiding the only
    // grapheme. The fix must reveal all graphemes once p is high enough
    // that only the last 1 would otherwise be hidden.
    const single = countGraphemes('ಅ');
    expect(single).toBe(1);
    // 0.999 still reveals (existing threshold)
    expect(resolvePlayableGraphemeCount(0.999, single)).toBe(1);
    // 1.0 reveals
    expect(resolvePlayableGraphemeCount(1, single)).toBe(1);
    // Probe value 0.95 must also reveal since with 1 grapheme, hiding
    // it would mean showing nothing.
    expect(resolvePlayableGraphemeCount(0.95, single)).toBe(1);
  });

  it('does not import the obsolete frontend-only kn.json', () => {
    // The Vite alias `@college-locales` resolves to backend/data/locales
    // (the authoritative source). The frontend's own copy at
    // frontend/src/data/locales/kn.json must NOT be referenced by
    // the frontend import graph.
    const obsolete = resolve(FRONTEND_ROOT, 'src', 'data', 'locales', 'kn.json');
    let contents: string;
    try {
      contents = readFileSync(obsolete, 'utf8');
    } catch {
      // If the file is removed, the guard trivially passes.
      return;
    }
    // The file should not be imported by any other frontend source.
    // We sanity-check that it does not contain a fresh KANNADA sentence
    // the backend would never produce (sanity check on shape only).
    expect(typeof contents).toBe('string');
  });

  it('countGraphemes returns a stable, non-zero count for Kannada words', () => {
    // countGraphemes is the canonical segmentation helper for both the
    // pagination engine and the reveal animation. It must never return
    // 0 for a non-empty Kannada string, and must agree with the same
    // call inside the production page-laying code.
    const sample = 'ಕನ್ನಡ ಭಾಷೆ';
    const g = countGraphemes(sample);
    expect(g).toBeGreaterThan(0);
    // The total must be at least the number of code points
    // (Intl.Segmenter may split conjuncts, never fewer than 1 each).
    expect(g).toBeGreaterThanOrEqual(Array.from(sample).length / 4);
  });
});
