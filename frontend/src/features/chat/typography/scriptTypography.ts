import type { CSSProperties } from 'react';
import type { Language } from '../../../context/LanguageContext';

export type ScriptTypographyPreset = {
  fontFamily: string;
  fontWeight: number;
  /** Multiplies resolved base px; English = 1 */
  sizeMultiplier: number;
  lineHeight: number;
  letterSpacing: string;
  containerWidthCss: string;
  cssClass: string;
};

const ENGLISH_PRESET: ScriptTypographyPreset = {
  fontFamily: 'inherit',
  fontWeight: 700,
  sizeMultiplier: 1,
  lineHeight: 1.42,
  letterSpacing: '-0.02em',
  containerWidthCss: 'min(900px, 75%)',
  cssClass: 'script-typo-en',
};

const INDIC_WIDTH = 'min(980px, 88%)';

const PRESETS: Record<Language, ScriptTypographyPreset> = {
  English: ENGLISH_PRESET,
  Kannada: {
    fontFamily: '"Noto Sans Kannada", "Nirmala UI", Tunga, sans-serif',
    fontWeight: 600,
    sizeMultiplier: 1,
    lineHeight: 1.52,
    letterSpacing: 'normal',
    containerWidthCss: INDIC_WIDTH,
    cssClass: 'script-typo-kn',
  },
  Tamil: {
    fontFamily: '"Noto Sans Tamil", "Nirmala UI", Latha, sans-serif',
    fontWeight: 600,
    sizeMultiplier: 1,
    lineHeight: 1.52,
    letterSpacing: 'normal',
    containerWidthCss: INDIC_WIDTH,
    cssClass: 'script-typo-ta',
  },
  Telugu: {
    fontFamily: '"Noto Sans Telugu", "Nirmala UI", Gautami, sans-serif',
    fontWeight: 600,
    sizeMultiplier: 1,
    lineHeight: 1.55,
    letterSpacing: 'normal',
    containerWidthCss: INDIC_WIDTH,
    cssClass: 'script-typo-te',
  },
  Hindi: {
    fontFamily: '"Noto Sans Devanagari", "Nirmala UI", Mangal, sans-serif',
    fontWeight: 600,
    sizeMultiplier: 1,
    lineHeight: 1.5,
    letterSpacing: 'normal',
    containerWidthCss: INDIC_WIDTH,
    cssClass: 'script-typo-hi',
  },
  Malayalam: {
    fontFamily: '"Noto Sans Malayalam", "Nirmala UI", Kartika, sans-serif',
    fontWeight: 600,
    sizeMultiplier: 1,
    lineHeight: 1.55,
    letterSpacing: 'normal',
    containerWidthCss: INDIC_WIDTH,
    cssClass: 'script-typo-ml',
  },
};

export function getScriptTypography(language: Language): ScriptTypographyPreset {
  return PRESETS[language] ?? ENGLISH_PRESET;
}

/** Inline styles for FULL_TEXT answer / measure fidelity (English leaves size to CSS clamp). */
export function scriptTypographyToAnswerStyle(
  preset: ScriptTypographyPreset,
  overrides?: { fontSizePx?: number; lineHeight?: number },
): CSSProperties {
  const style: CSSProperties = {
    fontWeight: preset.fontWeight,
    letterSpacing: preset.letterSpacing,
    lineHeight: overrides?.lineHeight ?? preset.lineHeight,
  };
  if (preset.fontFamily !== 'inherit') {
    style.fontFamily = preset.fontFamily;
  }
  if (typeof overrides?.fontSizePx === 'number' && overrides.fontSizePx > 0) {
    const scaled = overrides.fontSizePx * preset.sizeMultiplier;
    style.fontSize = `${scaled}px`;
  }
  return style;
}
