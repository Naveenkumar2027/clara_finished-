import { useId, useMemo } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import type { Language } from '../../context/LanguageContext';
import { getScriptTypography } from '../../features/chat/typography';

type Props = {
  sentence: string;
  language: Language;
};

type SentenceParts = {
  before: string;
  name: string | null;
  after: string;
};

/** Softly emphasize a trailing guest name when it already appears in the bridge. */
export function splitTrailingName(sentence: string): SentenceParts {
  const text = (sentence || '').trim();
  const match = text.match(/^(.*?)(,\s+)([A-Za-z\u0900-\u0D7F][\w\u0900-\u0D7F'-]{0,40})(\.?)$/u);
  if (!match) return { before: text, name: null, after: '' };
  return {
    before: `${match[1]}${match[2]}`,
    name: match[3] ?? null,
    after: match[4] ?? '',
  };
}

function ThinkingAmbientBackground({ uid }: { uid: string }) {
  const trailA = `thinkTrailA-${uid}`;
  const trailB = `thinkTrailB-${uid}`;
  const spark = `thinkSpark-${uid}`;
  return (
    <div className="clara-thinking-ambient" aria-hidden>
      <div className="clara-thinking-bloom clara-thinking-bloom-tl" />
      <div className="clara-thinking-bloom clara-thinking-bloom-tr" />
      <div className="clara-thinking-bloom clara-thinking-bloom-bl" />
      <div className="clara-thinking-bloom clara-thinking-bloom-br" />
      <svg className="clara-thinking-trails" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice">
        <defs>
          <linearGradient id={trailA} x1="0%" y1="100%" x2="55%" y2="0%">
            <stop offset="0%" stopColor="#a78bfa" stopOpacity="0" />
            <stop offset="35%" stopColor="#c4b5fd" stopOpacity="0.55" />
            <stop offset="70%" stopColor="#67e8f9" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
          </linearGradient>
          <linearGradient id={trailB} x1="100%" y1="100%" x2="45%" y2="0%">
            <stop offset="0%" stopColor="#7c3aed" stopOpacity="0" />
            <stop offset="40%" stopColor="#818cf8" stopOpacity="0.5" />
            <stop offset="75%" stopColor="#e879f9" stopOpacity="0.28" />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
          </linearGradient>
          <radialGradient id={spark} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.95" />
            <stop offset="55%" stopColor="#c4b5fd" stopOpacity="0.45" />
            <stop offset="100%" stopColor="#c4b5fd" stopOpacity="0" />
          </radialGradient>
        </defs>
        <g className="clara-thinking-trail-group clara-thinking-trail-left">
          <path
            d="M -40 820 C 180 760 260 620 220 480 C 180 340 40 260 -20 120"
            fill="none"
            stroke={`url(#${trailA})`}
            strokeWidth="22"
            strokeLinecap="round"
            opacity="0.32"
          />
          <path
            d="M -20 860 C 220 790 310 650 270 500 C 230 360 90 280 10 140"
            fill="none"
            stroke={`url(#${trailA})`}
            strokeWidth="8"
            strokeLinecap="round"
            opacity="0.72"
          />
          <path
            d="M 30 880 C 260 820 340 680 300 540 C 260 390 140 300 70 180"
            fill="none"
            stroke={`url(#${trailA})`}
            strokeWidth="2.8"
            strokeLinecap="round"
            opacity="0.85"
          />
        </g>
        <g className="clara-thinking-trail-group clara-thinking-trail-right">
          <path
            d="M 1640 820 C 1420 760 1340 620 1380 480 C 1420 340 1560 260 1620 120"
            fill="none"
            stroke={`url(#${trailB})`}
            strokeWidth="22"
            strokeLinecap="round"
            opacity="0.32"
          />
          <path
            d="M 1620 860 C 1380 790 1290 650 1330 500 C 1370 360 1510 280 1590 140"
            fill="none"
            stroke={`url(#${trailB})`}
            strokeWidth="8"
            strokeLinecap="round"
            opacity="0.72"
          />
          <path
            d="M 1570 880 C 1340 820 1260 680 1300 540 C 1340 390 1460 300 1530 180"
            fill="none"
            stroke={`url(#${trailB})`}
            strokeWidth="2.8"
            strokeLinecap="round"
            opacity="0.85"
          />
        </g>
        {Array.from({ length: 14 }).map((_, i) => (
          <circle
            key={i}
            className={`clara-thinking-dust clara-thinking-dust-${i % 5}`}
            cx={120 + (i * 97) % 1360}
            cy={140 + (i * 73) % 620}
            r={1.2 + (i % 3) * 0.55}
            fill={`url(#${spark})`}
          />
        ))}
      </svg>
    </div>
  );
}

function ThinkingCore({ uid, reducedMotion }: { uid: string; reducedMotion: boolean }) {
  const petal = `thinkPetal-${uid}`;
  const ribbon = `thinkRibbon-${uid}`;
  const core = `thinkCore-${uid}`;
  const bloom = `thinkBloom-${uid}`;
  const soft = `thinkSoft-${uid}`;

  return (
    <motion.div
      className="clara-thinking-mark"
      aria-hidden
      initial={reducedMotion ? false : { opacity: 0, scale: 0.82, filter: 'blur(12px)' }}
      animate={
        reducedMotion
          ? { opacity: 1, scale: 1, filter: 'blur(0px)' }
          : {
              opacity: 1,
              scale: [1, 1.035, 1],
              filter: 'blur(0px)',
            }
      }
      transition={
        reducedMotion
          ? { duration: 0.4 }
          : {
              opacity: { duration: 0.62, ease: [0.22, 1, 0.36, 1], delay: 0.05 },
              filter: { duration: 0.62, ease: [0.22, 1, 0.36, 1], delay: 0.05 },
              scale: { duration: 4.8, repeat: Infinity, ease: 'easeInOut', delay: 0.7 },
            }
      }
    >
      <svg viewBox="0 0 240 240" className="clara-thinking-svg">
        <defs>
          <radialGradient id={bloom} cx="50%" cy="48%" r="52%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.95" />
            <stop offset="28%" stopColor="#e9d5ff" stopOpacity="0.55" />
            <stop offset="58%" stopColor="#a78bfa" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#a78bfa" stopOpacity="0" />
          </radialGradient>
          <radialGradient id={core} cx="42%" cy="38%" r="62%">
            <stop offset="0%" stopColor="#ffffff" />
            <stop offset="32%" stopColor="#f5d0fe" />
            <stop offset="62%" stopColor="#a78bfa" />
            <stop offset="100%" stopColor="#4c1d95" stopOpacity="0.85" />
          </radialGradient>
          <linearGradient id={petal} x1="15%" y1="10%" x2="90%" y2="90%">
            <stop offset="0%" stopColor="#67e8f9" stopOpacity="0.55" />
            <stop offset="42%" stopColor="#a78bfa" stopOpacity="0.72" />
            <stop offset="78%" stopColor="#e879f9" stopOpacity="0.45" />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0.15" />
          </linearGradient>
          <linearGradient id={ribbon} x1="0%" y1="30%" x2="100%" y2="70%">
            <stop offset="0%" stopColor="#67e8f9" stopOpacity="0.85" />
            <stop offset="50%" stopColor="#818cf8" stopOpacity="0.75" />
            <stop offset="100%" stopColor="#f0abfc" stopOpacity="0.65" />
          </linearGradient>
          <filter id={soft} x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="2.2" />
          </filter>
        </defs>

        <circle cx="120" cy="120" r="88" fill={`url(#${bloom})`} className="clara-think-atmosphere" />

        <g className="clara-think-orbit clara-think-orbit-a">
          <ellipse cx="120" cy="120" rx="86" ry="34" fill="none" stroke={`url(#${ribbon})`} strokeWidth="1.4" opacity="0.7" />
          <circle cx="206" cy="120" r="2.4" fill="#ffffff" opacity="0.9" />
        </g>
        <g className="clara-think-orbit clara-think-orbit-b">
          <ellipse cx="120" cy="120" rx="38" ry="82" fill="none" stroke="#67e8f9" strokeWidth="1.1" opacity="0.45" />
          <circle cx="120" cy="38" r="2" fill="#c4b5fd" opacity="0.85" />
        </g>
        <g className="clara-think-orbit clara-think-orbit-c">
          <ellipse
            cx="120"
            cy="120"
            rx="74"
            ry="52"
            fill="none"
            stroke="#e9d5ff"
            strokeWidth="0.9"
            opacity="0.55"
            transform="rotate(28 120 120)"
          />
        </g>

        <g className="clara-think-petals" filter={`url(#${soft})`}>
          <path
            className="clara-think-petal clara-think-petal-a"
            d="M120 46 C158 58 176 96 120 168 C64 96 82 58 120 46 Z"
            fill={`url(#${petal})`}
            opacity="0.72"
          />
          <path
            className="clara-think-petal clara-think-petal-b"
            d="M120 52 C168 78 176 124 120 176 C64 124 72 78 120 52 Z"
            fill={`url(#${core})`}
            opacity="0.55"
            transform="rotate(48 120 120)"
          />
          <path
            className="clara-think-petal clara-think-petal-c"
            d="M120 58 C152 70 164 108 120 162 C76 108 88 70 120 58 Z"
            fill={`url(#${petal})`}
            opacity="0.48"
            transform="rotate(-42 120 120)"
          />
        </g>

        <circle className="clara-think-core-glow" cx="120" cy="116" r="28" fill={`url(#${bloom})`} />
        <circle className="clara-think-core" cx="120" cy="116" r="14" fill={`url(#${core})`} />
        <circle className="clara-think-core-spark" cx="116" cy="110" r="4.5" fill="#ffffff" opacity="0.9" />

        <g className="clara-think-orbit-particles">
          <circle className="clara-think-node clara-think-node-a" cx="188" cy="92" r="2.2" fill="#ffffff" />
          <circle className="clara-think-node clara-think-node-b" cx="74" cy="168" r="1.8" fill="#a5f3fc" />
          <circle className="clara-think-node clara-think-node-c" cx="156" cy="176" r="1.6" fill="#e9d5ff" />
        </g>
      </svg>
    </motion.div>
  );
}

function ThinkingDivider() {
  return (
    <div className="clara-thinking-divider" aria-hidden>
      <span className="clara-thinking-divider-line" />
      <span className="clara-thinking-divider-spark" />
      <span className="clara-thinking-divider-line" />
    </div>
  );
}

/**
 * Premium CLARA thinking interlude — visual stage only.
 * TTS / gate timing remain owned by ChatScreen.
 */
export default function ThinkingInterlude({ sentence, language }: Props) {
  const typography = getScriptTypography(language);
  const uid = useId().replace(/:/g, '');
  const reducedMotion = useReducedMotion() === true;
  const parts = useMemo(() => splitTrailingName(sentence), [sentence]);

  // Script fonts only — width/size come from fullscreen CSS, not answer-card containerWidthCss.
  const sentenceStyle = {
    fontFamily: typography.fontFamily,
    fontWeight: Math.min(600, typography.fontWeight),
    lineHeight: Math.max(1.28, typography.lineHeight * 0.92),
    letterSpacing: typography.letterSpacing,
  } as const;

  return (
    <motion.div
      className={`${typography.cssClass} clara-thinking-stage`}
      data-testid="clara-thinking"
      data-clara-thinking-fullscreen="true"
      initial={reducedMotion ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={reducedMotion ? { opacity: 0 } : { opacity: 0, y: -10, filter: 'blur(8px)' }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
    >
      <ThinkingAmbientBackground uid={uid} />

      <div className="clara-thinking-composition">
        <ThinkingCore uid={uid} reducedMotion={reducedMotion} />

        <motion.p
          className="clara-thinking-sentence"
          style={sentenceStyle}
          initial={reducedMotion ? false : { opacity: 0, y: 18, filter: 'blur(8px)' }}
          animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
          transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1], delay: 0.22 }}
        >
          {parts.name ? (
            <>
              {parts.before}
              <span className="clara-thinking-name">{parts.name}</span>
              {parts.after}
            </>
          ) : (
            sentence
          )}
        </motion.p>

        <motion.div
          initial={reducedMotion ? false : { opacity: 0, scaleX: 0.7 }}
          animate={{ opacity: 1, scaleX: 1 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1], delay: 0.38 }}
        >
          <ThinkingDivider />
        </motion.div>
      </div>
    </motion.div>
  );
}
