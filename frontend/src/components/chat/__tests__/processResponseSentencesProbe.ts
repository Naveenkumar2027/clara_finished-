/**
 * Production-equivalent of `processResponseSentences` from ChatScreen.tsx.
 *
 * The frontend must never drop, reorder, or translate Kannada sentence
 * terminators. The regex below explicitly recognizes the Kannada danda
 * (U+0964) and double danda (U+0965) in addition to ASCII ".!?" so the
 * per-sentence reveal cadence fires for Indic text. Joining the
 * resulting sentences back together reproduces the source bytes
 * (including the danda characters).
 */
export function processResponseSentences(value: unknown): string[] {
  const text = String(value ?? '').replace(/\s+/g, ' ').trim();
  if (!text) return [];
  const matches = text.match(/[^.!?\u0964\u0965]+[.!?\u0964\u0965]+|[^.!?\u0964\u0965]+$/g) ?? [];
  return matches.map((sentence) => sentence.trim()).filter(Boolean);
}
