import { useState, useEffect, useMemo, useCallback, type CSSProperties, type Key } from 'react';

interface AnimatedAiMessageProps {
  key?: Key;
  text: string;
  className?: string;
  style?: CSSProperties;
  isCardData?: boolean;
  animate?: boolean;
  audioDuration?: number;
  /** 0–1 live playback progress. When set, drives reveal instead of estimated stagger. */
  playbackProgress?: number;
}

export default function AnimatedAiMessage({
  text,
  className = '',
  style,
  isCardData: _isCardData = false,
  animate = true,
  audioDuration = 0,
  playbackProgress,
}: AnimatedAiMessageProps) {
  const [isReady, setIsReady] = useState(false);
  const usePlaybackSync = typeof playbackProgress === 'number' && Number.isFinite(playbackProgress);

  const toGraphemes = useCallback((value: string): string[] => {
    try {
      const SegmenterCtor = (Intl as unknown as {
        Segmenter?: new (
          locales?: string | string[],
          options?: { granularity: string },
        ) => { segment: (input: string) => Iterable<{ segment: string }> };
      }).Segmenter;
      if (typeof SegmenterCtor === 'function') {
        const segmenter = new SegmenterCtor(undefined, { granularity: 'grapheme' });
        return Array.from(segmenter.segment(value), (part) => String(part.segment));
      }
    } catch {
      // no-op: fallback below
    }
    return Array.from(value);
  }, []);

  useEffect(() => {
    if (!animate) {
      setIsReady(true);
      return;
    }
    const timer = setTimeout(() => {
      setIsReady(true);
    }, 0);
    return () => clearTimeout(timer);
  }, [animate]);

  const tokens = useMemo(() => text.split(/(\s+)/), [text]);
  const totalChars = useMemo(
    () => toGraphemes(text.replace(/\s+/g, '')).length,
    [text, toGraphemes],
  );

  // Fallback path (no live playback): estimate stagger from audioDuration.
  const expectedStagger = useMemo(() => {
    const tailMs = 600;
    const audioMs = Math.max(0, audioDuration * 1000);
    const budgetMs = audioMs > 0 ? Math.max(0, audioMs - tailMs) : 0;
    const base = budgetMs > 0 ? budgetMs / Math.max(totalChars, 1) : 18;
    return Math.max(10, Math.min(26, base));
  }, [audioDuration, totalChars]);

  const visibleGraphemes = useMemo(() => {
    if (!usePlaybackSync) return totalChars;
    const p = Math.min(1, Math.max(0, playbackProgress ?? 0));
    if (p >= 0.999) return totalChars;
    // When totalChars is small (e.g. 1), floor(p * 1) can stay at 0 even
    // for p close to 1.0, leaving the last (and only) grapheme hidden.
    // Reveal all once progress is high enough that only the last 1
    // grapheme would otherwise be hidden — preserves the trailing
    // punctuation / danda / combining mark / ZWJ-joined grapheme.
    if (totalChars > 0 && p >= 1 - 1 / totalChars) return totalChars;
    return Math.floor(p * totalChars);
  }, [usePlaybackSync, playbackProgress, totalChars]);

  if (!isReady) {
    return (
      <div className={`opacity-0 ${className}`} style={style}>
        {text}
      </div>
    );
  }

  let globalCharIndex = 0;

  return (
    <div
      className={className}
      style={{
        ...style,
        color: 'inherit',
      }}
    >
      {tokens.map((token: string, tIdx: number) => {
        if (/^\s+$/.test(token)) {
          return <span key={`space-${tIdx}`}>{token}</span>;
        }

        const isAsciiToken = /^[\x00-\x7F]+$/.test(token);
        const isClara = token.includes('CLARA');
        const tokenClass = isClara ? 'font-bold text-[#0F172A]' : 'text-[#0F172A]';

        return (
          <span
            key={`word-${tIdx}`}
            className={`${isAsciiToken ? 'inline-block whitespace-nowrap' : 'inline-block'} ${tokenClass}`}
          >
            {toGraphemes(token).map((char: string, cIdx: number) => {
              if (!animate) {
                return (
                  <span key={`char-${cIdx}`} className="inline-block">
                    {char}
                  </span>
                );
              }

              const charIndex = globalCharIndex;
              globalCharIndex += 1;

              if (usePlaybackSync) {
                const revealed = charIndex < visibleGraphemes;
                return (
                  <span
                    key={`char-${cIdx}`}
                    className={`letter-reveal-sync inline-block${revealed ? ' letter-reveal-sync--on' : ''}`}
                  >
                    {char}
                  </span>
                );
              }

              const delay = charIndex * expectedStagger;
              return (
                <span
                  key={`char-${cIdx}`}
                  className="letter-reveal inline-block"
                  style={{ animationDelay: `${delay}ms` }}
                >
                  {char}
                </span>
              );
            })}
          </span>
        );
      })}
    </div>
  );
}
