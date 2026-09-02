import React from 'react';
import { motion } from 'motion/react';
import SiriOrb from '../../components/SiriOrb';
import HorizontalVoiceAnalyser from '../../components/voice/HorizontalVoiceAnalyser';
import { useLanguage } from '../../context/LanguageContext';
import { uiText } from '../../localization/uiCopy';
import { getScriptTypography } from '../../features/chat/typography/scriptTypography';

export type ChatOrbState = 'idle' | 'listening' | 'processing' | 'speaking' | 'ready' | 'completed';

type ChatOrbControlProps = {
  orbState: ChatOrbState;
  isProcessing: boolean;
  amplitude: number;
  frequencyDataRef?: React.RefObject<Uint8Array | null>;
  onTap: () => void;
  bottomClassName: string;
  compact?: boolean;
  /** Shrinks / lowers orb when department comparison panel is dominant */
  comparisonMode?: boolean;
};

export default function ChatOrbControl({
  orbState,
  isProcessing,
  amplitude,
  frequencyDataRef,
  onTap,
  bottomClassName,
  compact = false,
  comparisonMode = false,
}: ChatOrbControlProps) {
  const { language, t } = useLanguage();
  const scriptClass = getScriptTypography(language).cssClass;
  const isListening = orbState === 'listening';

  const aria =
    isProcessing
      ? uiText(language, 'status.thinking')
      : isListening
        ? uiText(language, 'status.listening')
        : t('tapToSpeak');

  const isCompactLayout = compact || comparisonMode;
  const targetWidth = isCompactLayout ? 290 : 420;
  const targetHeight = isCompactLayout ? 100 : 140;

  return (
    <motion.div
      className="relative flex flex-col items-center group"
      initial={false}
      animate={{
        scale: comparisonMode ? 0.72 : compact ? 0.62 : 1,
        y: comparisonMode ? 12 : 0,
      }}
      transition={{ duration: 0.55, ease: [0.16, 1, 0.28, 1] }}
      style={{ transformOrigin: '50% 100%', pointerEvents: 'none' }}
    >
      {/* Container morphs width between circular 200px (Sleep/Idle) and horizontal span (Listening) */}
      <motion.div
        className="relative shrink-0 flex items-center justify-center"
        initial={false}
        animate={{
          width: isListening ? targetWidth : 200,
          height: 200,
        }}
        transition={{ duration: 0.48, ease: [0.16, 1, 0.3, 1] }}
        style={{ pointerEvents: 'none' }}
      >
        {/* ─── 1. FROZEN CLARA ORB (SiriOrb) ─── */}
        {/* Seamlessly covered by uncoiling shuriken during activation, smoothly re-emerges on fold */}
        <motion.div
          className="absolute inset-0 flex items-center justify-center"
          initial={false}
          animate={{
            opacity: isListening ? 0 : 1,
            scale: isListening ? 0.88 : 1,
            rotate: isListening ? 90 : 0,
          }}
          transition={{ duration: isListening ? 0.36 : 0.46, ease: [0.16, 1, 0.3, 1] }}
          style={{ pointerEvents: 'none' }}
        >
          <SiriOrb
            state={isListening ? 'listening' : isProcessing ? 'processing' : 'idle'}
            amplitude={amplitude}
          />
        </motion.div>

        {/* ─── 2. STRAIGHT HORIZONTAL VOICE ANALYSER ─── */}
        {/* Opening shuriken unrolls directly from the 63px center nucleus into the liquid wave ribbon */}
        <motion.div
          className="absolute inset-0 flex items-center justify-center"
          initial={false}
          animate={{
            opacity: isListening ? 1 : 0,
            scale: isListening ? 1 : 0.94,
          }}
          transition={{ duration: isListening ? 0.46 : 0.38, ease: [0.16, 1, 0.3, 1] }}
          style={{ pointerEvents: 'none' }}
        >
          <HorizontalVoiceAnalyser
            isListening={isListening}
            amplitude={amplitude}
            frequencyDataRef={frequencyDataRef}
            compact={isCompactLayout}
            width={targetWidth}
            height={targetHeight}
          />
        </motion.div>

        {/* ─── 3. INTERACTION TOUCH TARGET ─── */}
        <motion.button
          type="button"
          tabIndex={0}
          data-testid="chat-orb"
          data-orb-state={isProcessing ? 'processing' : orbState}
          aria-label={aria}
          initial={false}
          animate={{
            width: isListening ? Math.min(targetWidth - 20, 380) : 140,
            height: isListening ? 80 : 140,
            borderRadius: isListening ? 40 : 70,
          }}
          transition={{ duration: 0.48, ease: [0.16, 1, 0.3, 1] }}
          className="absolute left-1/2 top-1/2 z-20 -translate-x-1/2 -translate-y-1/2 cursor-pointer border-0 bg-transparent p-0 outline-offset-4"
          style={{ pointerEvents: 'auto' }}
          onClick={(event) => {
            if (import.meta.env.DEV) {
              const el = event.target as HTMLElement;
              // eslint-disable-next-line no-console
              console.debug('[CLARA_AGENT]', 'A', 'orb_hit_click', {
                orbState,
                isProcessing,
                targetTag: el?.tagName,
              });
            }
            onTap();
          }}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault();
              onTap();
            }
          }}
        />
      </motion.div>

      {/* ─── 4. STATUS LABEL ─── */}
      <div className={bottomClassName} style={{ pointerEvents: 'none' }}>
        <span
          className={`${scriptClass} whitespace-nowrap text-[11px] font-bold uppercase tracking-[0.3em] transition-colors ${
            isListening
              ? 'animate-pulse text-indigo-500'
              : isProcessing
              ? 'animate-pulse text-amber-500'
              : 'text-slate-400 group-hover:text-indigo-500'
          }`}
          style={{
            opacity: comparisonMode ? 0.88 : isProcessing || isListening ? 0.9 : 0.7,
          }}
        >
          {isProcessing
            ? uiText(language, 'status.thinking')
            : isListening
              ? uiText(language, 'status.listening')
              : t('tapToSpeak')}
        </span>
      </div>
    </motion.div>
  );
}
