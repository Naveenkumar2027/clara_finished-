/**
 * Production-equivalent of the "how many graphemes are visible at this
 * playback progress" calculation in `AnimatedAiMessage`.
 *
 * The frontend must never leave the last grapheme (a terminal danda,
 * a combining mark, or a ZWJ-joined grapheme) hidden. Once the
 * playback progress is at the natural 1.0 boundary, every grapheme of
 * the source must be marked visible. For very short sources
 * (totalGraphemes === 1) the floor formula would otherwise stay at 0
 * for any progress < 1, so we reveal all once progress is high enough
 * that only the last 1 grapheme would otherwise be hidden.
 */
export function resolvePlayableGraphemeCount(
  progress: number,
  totalGraphemes: number,
): number {
  if (!Number.isFinite(progress) || progress < 0) return 0;
  if (progress >= 0.999) return totalGraphemes;
  if (totalGraphemes > 0 && progress >= 1 - 1 / totalGraphemes) {
    return totalGraphemes;
  }
  return Math.floor(progress * totalGraphemes);
}
