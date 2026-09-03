import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { AnimatePresence, motion, useAnimationFrame, useMotionValue, useTransform } from 'motion/react';
import { Sparkles, Home, MapPinned, MessageSquareText, Square, Volume2, FileText, X } from 'lucide-react';
import { useLanguage, type Language } from '../context/LanguageContext';
import { uiText } from '../localization/uiCopy';
import { languageToCode } from '../session/languageCodes';
import {
  getVisitorLanguage,
  getVisitorSessionId,
  isWelcomeCompleted,
  markWelcomeCompleted,
} from '../session/visitorSession';
import whatsappBgImage from '../assets/whatsapp_bg.png';
import fullTextBgImage from '../assets/full_text_bg.png';
import collegeBrochurePdfUrl from '../assets/College brochure/svit_brochure.pdf?url';
import {
  type ChatMessage,
  type OrbState,
  type TextMessage,
  isTextMessage,
} from '../types/chat';
import { useVoiceFrequencyAnalyser } from '../hooks/useVoiceAnalyser';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';
import AnimatedAiMessage from '../components/chat/AnimatedAiMessage';
import CourseMenuComponent from '../components/chat/CourseMenuComponent';
import DepartmentCardStage from '../components/chat/DepartmentCardStage';
import DepartmentCardFactory from '../components/chat/cards/DepartmentCards/DepartmentCardFactory';
import LeadershipOverview from '../components/chat/LeadershipOverview';
import DepartmentFeesCard from '../components/chat/cards/DepartmentFeesCard';
import PremiumPrincipalCard from '../components/chat/cards/DepartmentCards/PremiumPrincipalCard';
import PremiumVicePrincipalCard from '../components/chat/cards/DepartmentCards/PremiumVicePrincipalCard';
import DocumentsBlock from '../components/chat/cards/DocumentsBlock';
import Trustees from '../components/chat/cards/Trustees/Trustees';
import CampusUnitCard from '../components/chat/cards/CampusUnitCard/CampusUnitCard';
import DepartmentComparisonCinema from '../components/comparison/DepartmentComparisonCinema';
import BusRoutesFullscreen from '../components/bus/BusRoutesFullscreen';
import ChatOrbControl from './chat/ChatOrbControl';
import { useChatLayoutReducer, type ChatLayoutMode } from './chat/useChatLayoutReducer';
import { countGraphemes, useResponseLayout } from '../features/chat/layout';
import {
  FAQ_TICKER_SPEED_PX_PER_MS,
  useFaqTickerLayout,
  type FaqTickerLayout,
} from '../features/chat/faq';
import { getScriptTypography } from '../features/chat/typography';
import { resolvePagedPlayback, useAudioPlaybackClock } from '../features/chat/reveal';
import { usePresentationController } from '../features/chat/presentation';
import { parseCardNavigationCommand } from '../features/chat/presentation/cardNavigation';
import {
  departmentIdFromUnitId,
  factoryDepartmentLabelFromJsonKey,
  hasDepartmentPlacementUnit,
  presentationCardsFromNarrationSegments,
  shouldUseCollegeWidePlacementDeck,
  type PresentationCardModel,
} from '../features/chat/presentation/PresentationCardModel';
import {
  findClipIndexForTarget,
  segmentKeysFromPlayhead,
  unitIdForCardIndex,
} from '../features/chat/presentation/playbackSeek';
import {
  shouldAllowLegacySingle,
  shouldLoadUnitPlan,
  unitIdsFromSegments,
} from '../features/chat/presentation/presentationOwnership';
import {
  assertLivePresentationOwnership,
  canChangeLanguageNow,
  choosePresentationFallback,
  freezeLocalization,
  localizationCodeKey,
  patchConversationRuntime,
  pushRuntimeEvent,
  releaseLocalizationFreeze,
  validatePresentationContract,
} from '../runtime';
import {
  isUnitBackedNarrationPlan,
  type TtsClipStatus,
} from '../lib/ws/ttsClipSlots';
import {
  TURN_FENCE_PENDING,
  adoptTurnOwner,
  shouldApplyUnitBackedPlan,
  shouldIgnorePayloadTurn,
} from '../lib/ws/turnFence';
import { engageCardUiLockState } from '../lib/ui/cardUiLock';
import {
  ANSWER_TTS_WATCHDOG_MS,
  shouldCommitAnswerMessages,
  shouldFocusAssistantAnswer,
  showThinkingOverlay,
} from '../lib/chat/answerVisibility';
import { createAckPlayer } from '../lib/tts/ackAudio';
import { createResponseTtsScheduler } from '../lib/tts/responseTtsScheduler';
import ThinkingInterlude from '../components/chat/ThinkingInterlude';
import {
  attachThinkingSentence,
  beginThinkingTurn,
  canStartResponsePlayback,
  EMPTY_THINKING_GATE,
  markResponseStarted,
  markThinkingTtsFailed,
  markThinkingTtsFinished,
  markThinkingTtsPlaying,
  rebindThinkingTurn,
  resetThinkingGate,
  shouldBlockResponsePlayback,
  shouldShowThinkingInterlude,
  THINKING_TTS_WATCHDOG_MS,
} from '../features/chat/thinking/thinkingGate';
import {
  composeThinkingBridge,
  thinkingBridgeFallback,
} from '../features/chat/thinking/thinkingBridge';
import { createThinkingTtsPlayer } from '../features/chat/thinking/thinkingTtsPlayer';
import { LANGUAGE_OPTIONS } from './LanguageSelect';
import { getStaticCardsForTrigger, type CardDataItem } from '../lib/cardData';
import {
  buildAllDepartmentSummaryCardsFromLocale,
  buildAllHodCardsFromLocale,
  buildInstitutionCardsFromLocale,
  buildTrusteeCardsFromLocale,
  buildDepartmentSlideForUnit,
  buildDepartmentSlidesFromRecord,
  buildPlacementCardsFromLocale,
  getDepartmentRecord,
  menuLabelToJsonKey,
  type DepartmentStageSlide,
} from '../lib/collegeLocaleUtils';
import { useCollegeData } from '../hooks/useCollegeData';
import {
  CAMPUS_DIRECTIONS,
  type CampusDirection,
  type CampusMatchApiRoom,
  type CampusNavigationRouteMode,
  type CampusRouteResult,
  CampusNavigationMapOnly,
  campusDirectionFromMapMatch,
  campusLabels,
  campusSpeechText,
  getCampusRouteApi,
  legacyCampusIndexForCode,
  localizedCampusSteps,
  matchCampusTranscriptApi,
} from '../campus-navigation';
import { parseRoomCodeFromDestinationLabel } from '../campus-navigation/campusMapGeometry';

function campusNavigationRouteModeToApi(mode: CampusNavigationRouteMode): string {
  switch (mode) {
    case 'accessible':
      return 'accessible';
    case 'lift':
      return 'lift';
    case 'stairs':
      return 'stairs';
    default:
      return 'shortest';
  }
}
import {
  inferFaqCategories,
  selectFaqSuggestions,
  type FaqSuggestionCategory,
} from '../data/faqSuggestions';
import type { ExecutiveLeadershipKind } from '../lib/executiveLeadershipIntent';
import type { ClaraChatSurface } from '../types/chatSurface';
import type { FaceChannel } from '../hooks/useFaceChannel';
import { inferEmotionFromPayload } from '../lib/faceEmotion';

declare global {
  interface Window {
    __CLARA_TEST_SEND_MESSAGE?: (text: string) => void;
    __CLARA_M52_END_CLIP?: () => void;
    __CLARA_M52_DEBUG?: () => {
      cardIndex: number;
      slideCount: number;
      hodCount: number;
      hodDepartments: string[];
      feesDepartmentId: string | null;
      isFeesStage: boolean;
      isHodStage: boolean;
      isDepartmentOverviewStage: boolean;
      isInfoSlideStage: boolean;
      unitIds: string[] | null;
      cardIds: string[] | null;
      unitCardContents?: Array<{ unitId: string; title: string; content: string }>;
      visibleUnitId?: string | null;
      playhead: number;
      queueLength: number;
      queueUnitIds: Array<string | null>;
      playbackUnitId: string | null;
      engineUnitId: string | null;
      engineState: string;
      playbackGen: number;
      hasCurrentAudio: boolean;
      clipStatuses?: Array<string | null>;
    };
  }
}

const SPLIT_IDLE_TIMEOUT_MS = 30_000;
const CARD_AUDIO_START_DELAY_MS = 220;
const FULL_TEXT_AUDIO_START_DELAY_MS = 0;
const DEFAULT_COURSE_MENU_OPTIONS = [
  'CSE',
  'ISE',
  'CSE (AI & ML)',
  'CSE (Data Science)',
  'CSE (Cyber Security)',
  'CSE (Business Systems)',
  'ECE',
  'Civil',
  'Mechanical',
  'MBA',
  'Basic Sciences',
];

const LANGUAGE_FROM_CODE_KEY: Record<string, Language> = {
  en: 'English',
  hi: 'Hindi',
  kn: 'Kannada',
  ta: 'Tamil',
  te: 'Telugu',
  ml: 'Malayalam',
};

function languageFromPayload(payload: any): Language | null {
  const name = payload?.language_name;
  if (
    name === 'English' ||
    name === 'Kannada' ||
    name === 'Hindi' ||
    name === 'Tamil' ||
    name === 'Telugu' ||
    name === 'Malayalam'
  ) {
    return name;
  }
  const code = String(payload?.language_code_key || '').trim().toLowerCase();
  return LANGUAGE_FROM_CODE_KEY[code] ?? null;
}

const DEPARTMENT_UNIT_CARD_TYPES = new Set([
  'overview',
  'hod',
  'achievements',
  'placements',
  'department_fees',
]);

const CAMPUS_UNIT_CARD_TYPES = new Set([
  'hostel', 'canteen', 'event', 'faculty', 'location', 'global_placements', 'admissions',
]);

const INFO_STAGE_CHIPS: Record<Language, { placements: string }> = {
  English: { placements: 'Placements & training' },
  Kannada: { placements: uiText('Kannada', 'cards.placements_training') },
  Hindi: { placements: uiText('Hindi', 'cards.placements_training') },
  Tamil: { placements: 'பிளேஸ்மென்ட் மற்றும் பயிற்சி' },
  Telugu: { placements: 'ప్లేస్‌మెంట్ మరియు శిక్షణ' },
  Malayalam: { placements: 'പ്ലേസ്മെന്റും പരിശീലനവും' },
};

type PendingAudio = {
  audioBase64: string;
  segmentKey: string;
  turnId: string;
  isOverview: boolean;
  cardsToSync: any[] | null;
  targetLayout: 'FULL_TEXT' | 'SPLIT_CARDS';
};

/** Response TTS is owned by the scheduler; never play it through the ACK/pending-audio path. */
function shouldDeferAssistantTtsToStream(p: unknown): boolean {
  if (!p || typeof p !== 'object') return false;
  return (p as Record<string, unknown>).type === 'assistant_audio_update';
}

type VisibleFaqSuggestion = {
  id: string;
  text: string;
};

type NarrationPlan = {
  turnId: string;
  mode: 'card_narration';
  language?: string;
  cards?: Array<{
    cardId: string;
    departmentId?: string | null;
    entityId?: string | null;
    unitId?: string | null;
  }>;
  activeIndex?: number;
  segments: {
    segmentId: string;
    displayText: string;
    ttsText: string;
    cardIndex: number | null;
    cardId: string | null;
    isFinalSegment: boolean;
    sectionId?: string | null;
    unitId?: string | null;
    canonicalCardId?: string | null;
  }[];
};

const FAQ_CAROUSEL_INTERVAL_MS = 3600;
const GENERAL_FAQ_CATEGORIES: FaqSuggestionCategory[] = ['college', 'campus', 'admissions', 'placements'];
/** Must match `row_order.length` in `departmentComparison.json` (3 narrative beats). */
const COMPARISON_NARRATION_SECTIONS = 3;

function processResponseSentences(value: unknown): string[] {
  const text = String(value ?? '').replace(/\s+/g, ' ').trim();
  if (!text) return [];
  // Kannada (and Devanagari) use U+0964 "।" as a sentence terminator
  // in addition to ASCII ".!?" — it must be recognized as a boundary
  // so per-sentence reveal cadence fires for Indic text. U+0965 is the
  // double danda used for paragraph-style breaks.
  const matches = text.match(/[^.!?\u0964\u0965]+[.!?\u0964\u0965]+|[^.!?\u0964\u0965]+$/g) ?? [];
  return matches.map((sentence) => sentence.trim()).filter(Boolean);
}

function payloadResponseText(payload: any, fallback: string): string {
  if (payload?.event === 'error' || payload?.errorCode) return fallback ?? '';
  return String(payload?.responseText ?? payload?.assistantText ?? fallback ?? '');
}

/** Face lip-sync needs text; streaming often plays audio before `responseText` is populated. */
function payloadAssistantSpeechText(payload: any): string {
  const direct = payloadResponseText(payload, '').trim();
  if (direct.length > 0) return direct;
  const messages = Array.isArray(payload?.messages) ? payload.messages : [];
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i] as { role?: string; text?: string; isHidden?: boolean; isCardData?: boolean };
    if (!m || String(m.role ?? '').toLowerCase() !== 'clara') continue;
    if (m.isHidden || m.isCardData) continue;
    const t = typeof m.text === 'string' ? m.text.trim() : '';
    if (t.length > 0) return t;
  }
  const spoken = typeof payload?.spokenText === 'string' ? payload.spokenText.trim() : '';
  if (spoken.length > 0) return spoken;
  return '';
}

function finitePositiveMs(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : null;
}

function fallbackSentenceDurationMs(sentence: string): number {
  return Math.max(600, sentence.length * 40);
}

function allocateSentenceDurations(sentences: string[], totalMs: number | null): number[] {
  if (!sentences.length) return [];
  if (!totalMs || totalMs <= 0) {
    return sentences.map(fallbackSentenceDurationMs);
  }

  const roundedTotal = Math.max(sentences.length, Math.round(totalMs));
  const weights = sentences.map((sentence) => Math.max(1, sentence.replace(/\s+/g, '').length));
  const weightTotal = weights.reduce((sum, weight) => sum + weight, 0);
  const durations = weights.map((weight) => Math.max(1, Math.round((roundedTotal * weight) / weightTotal)));
  let delta = roundedTotal - durations.reduce((sum, duration) => sum + duration, 0);
  let i = 0;
  while (delta !== 0 && durations.length > 0) {
    const idx = i % durations.length;
    const step = delta > 0 ? 1 : -1;
    if (durations[idx] + step > 0) {
      durations[idx] += step;
      delta -= step;
    }
    i += 1;
  }
  return durations;
}

// #region agent log
const _agentDbg = (
  hypothesisId: string,
  location: string,
  message: string,
  data: Record<string, unknown>,
  runId = 'pre',
) => {
  if (!import.meta.env.DEV) return;
  // eslint-disable-next-line no-console
  console.debug('[CLARA_AGENT]', hypothesisId, message, { ...data, location, runId });
};
// #endregion

function FaqTickerCard({
  suggestion,
  index,
  layout,
  cycleLength,
  x,
  onSelect,
  scriptClass,
}: {
  suggestion: VisibleFaqSuggestion;
  index: number;
  layout: FaqTickerLayout;
  cycleLength: number;
  x: ReturnType<typeof useMotionValue<number>>;
  onSelect: (id: string, question: string) => void;
  scriptClass: string;
}) {
  const totalWidth = Math.max(1, layout.totalTrackWidth);
  const center = layout.viewportWidth / 2;
  const itemWidth = layout.widths[index % cycleLength] ?? 160;
  const itemOffset = layout.offsets[index % cycleLength] ?? 0;
  const cycleIndex = Math.floor(index / cycleLength);
  const baseOffset = itemOffset + cycleIndex * totalWidth;

  const distanceFromCenter = useTransform(x, (value) => {
    const raw = baseOffset + itemWidth / 2 + value;
    const wrapped = ((raw % totalWidth) + totalWidth) % totalWidth;
    const direct = Math.abs(wrapped - center);
    return Math.min(direct, Math.abs(direct - totalWidth));
  });
  const span = Math.max(120, itemWidth);
  // Milder peak scale so variable-width group stays optically centered without clipping.
  const scale = useTransform(distanceFromCenter, [0, span * 1.25], [1.12, 0.88]);
  const opacity = useTransform(distanceFromCenter, [0, span * 1.4], [1, 0.65]);
  const filter = useTransform(distanceFromCenter, (distance) =>
    distance > span * 0.85 ? 'blur(0.6px)' : 'blur(0px)',
  );

  return (
    <motion.button
      type="button"
      className={`faq-suggestion-pill ${scriptClass}`}
      style={{ scale, opacity, filter, width: itemWidth, minWidth: itemWidth }}
      whileHover={{ scale: 1.04 }}
      whileTap={{ scale: 0.98 }}
      onClick={(event) => {
        event.stopPropagation();
        onSelect(suggestion.id, suggestion.text);
      }}
    >
      {suggestion.text}
    </motion.button>
  );
}

const estimateWavDurationSeconds = (audioBase64: string): number | null => {
  try {
    const binary = atob(audioBase64);
    if (binary.length < 44 || binary.slice(0, 4) !== 'RIFF' || binary.slice(8, 12) !== 'WAVE') {
      return null;
    }
    const view = new DataView(new ArrayBuffer(binary.length));
    for (let i = 0; i < binary.length; i += 1) {
      view.setUint8(i, binary.charCodeAt(i));
    }
    const sampleRate = view.getUint32(24, true);
    const byteRate = view.getUint32(28, true);
    const dataSize = view.getUint32(40, true);
    const rate = byteRate || sampleRate;
    if (!rate || !dataSize) return null;
    return dataSize / rate;
  } catch {
    return null;
  }
};

const normalizeDepartmentMenuKey = (departmentId: string): string | null => {
  const raw = (departmentId || '').trim();
  const value = raw.toLowerCase();
  if (!value) return null;
  if (value.includes('basic')) return 'Basic Sciences';
  if (value.includes('mba') || value.includes('management')) return 'MBA';
  if (value.includes('mechanical') || value === 'mech') return 'Mechanical';
  if (value.includes('civil')) return 'Civil';
  if (value.includes('ece') || value.includes('electronics')) return 'ECE';
  if (value.includes('ise') || value.includes('information science')) return 'ISE';
  if (value.includes('cyber security') || value.includes('cybersecurity')) return 'CSE (Cyber Security)';
  if (value.includes('business system')) return 'CSE (Business Systems)';
  if (value.includes('data science')) return 'CSE (Data Science)';
  if ((value.includes('ai') && value.includes('ml')) || value.includes('aiml') || value.includes('ai & ml')) {
    return 'CSE (AI & ML)';
  }
  if (value.includes('cse') || value.includes('computer')) return 'CSE';
  return raw;
};

const getPayloadMessageText = (m: unknown): string => {
  if (!m || typeof m !== 'object') return '';
  const o = m as { text?: unknown; content?: unknown };
  if (typeof o.text === 'string') return o.text;
  if (typeof o.content === 'string') return o.content;
  return '';
};

const normalizeCardTrigger = (trigger: unknown): string | null => {
  if (typeof trigger !== 'string') return null;
  const n = trigger.trim().toLowerCase();
  if (!n) return null;
  if (n === 'hod_info' || n === 'head_of_department' || n === 'hod_profile') return 'hod';
  if (n === 'dept' || n === 'department') return 'department_overview';
  if (n === 'fees') return 'department_fees';
  if (
    n === 'principal_profile' ||
    n === 'principal' ||
    n === 'principle' ||
    n === 'college_principal' ||
    n === 'principal_card' ||
    n === 'principle_profile' ||
    n === 'principle_card'
  ) {
    return 'principal_profile';
  }
  if (
    n === 'vice_principal_profile' ||
    n === 'vice_principal' ||
    n === 'dean_academics' ||
    n === 'dean_academic' ||
    n === 'dean_of_academics' ||
    n === 'academic_dean'
  ) {
    return 'vice_principal_profile';
  }
  if (n === 'bus_route' || n === 'bus_routes' || n === 'college_bus_routes') {
    return 'bus_routes';
  }
  return n;
};

interface ChatScreenProps {
  messages: ChatMessage[];
  isListening?: boolean;
  isSpeaking?: boolean;
  isProcessing?: boolean;
  isConnected?: boolean;
  voiceInputMode?: 'browser' | 'backend';
  payload?: any | null;
  /** When true, after the first greeting an in-chat language picker is shown. */
  inlineLanguageGate?: boolean;
  onInlineLanguageResolved?: () => void;
  onBack: () => void;
  onHome?: () => void;
  onOrbTap: () => void;
  /** Kiosk: reset 1-minute inactivity-to-sleep timer on real user intent. */
  onChatUserActivity?: () => void;
  /** When true, App pauses chat→sleep idle countdown (e.g. college brochure overlay). */
  onChatIdleOverlayChange?: (active: boolean) => void;
  sendMessage: (msg: object) => void;
  /** When true, discard payload-driven updates (ghost session prevention). */
  isPayloadStale?: (p: unknown) => boolean;
  faceChannel?: FaceChannel;
}

export default function ChatScreen({
  messages: payloadMessages,
  isListening: propIsListening = false,
  isSpeaking: propIsSpeaking = false,
  isProcessing = false,
  isConnected = true,
  voiceInputMode = 'browser',
  payload,
  inlineLanguageGate = false,
  onInlineLanguageResolved,
  onBack,
  onHome,
  onOrbTap,
  onChatUserActivity,
  onChatIdleOverlayChange,
  sendMessage,
  isPayloadStale,
  faceChannel,
}: ChatScreenProps) {
  const { language, setLanguage, selectLanguageCode, t } = useLanguage();
  const presentationLanguage = languageFromPayload(payload) ?? language;
  const scrollRef = useRef<HTMLDivElement>(null);
  const [displayMessages, setDisplayMessages] = useState<ChatMessage[]>(payloadMessages);
  
  // Layout Management State
  const { layoutMode, setLayoutMode } = useChatLayoutReducer('FULL_TEXT');
  const [activeCards, setActiveCards] = useState<any[] | null>(null);
  const [currentCardIdx, setCurrentCardIdx] = useState(0);
  const [narrationCaption, setNarrationCaption] = useState<string>('');
  const narrationPlanRef = useRef<NarrationPlan | null>(null);
  const [suppressedTurnId, setSuppressedTurnId] = useState<string | null>(null);
  const [currentAudioDuration, setCurrentAudioDuration] = useState<number>(0);
  const [courseMenuOptions, setCourseMenuOptions] = useState<string[]>([]);
  const [activeDepartmentId, setActiveDepartmentId] = useState<string | null>(null);
  const [isDepartmentOverviewStage, setIsDepartmentOverviewStage] = useState(false);
  const [isInfoSlideStage, setIsInfoSlideStage] = useState(false);
  const [infoSlideChip, setInfoSlideChip] = useState('');
  const [infoSlides, setInfoSlides] = useState<{ title: string; content: string }[]>([]);
  const [isHodStage, setIsHodStage] = useState(false);
  const [executiveLeadershipKind, setExecutiveLeadershipKind] = useState<ExecutiveLeadershipKind | null>(
    null,
  );
  const [isFeesStage, setIsFeesStage] = useState(false);
  const [activeFeesDepartmentId, setActiveFeesDepartmentId] = useState<string | null>(null);
  const [isDocumentsStage, setIsDocumentsStage] = useState(false);
  const [isCampusNavigationStage, setIsCampusNavigationStage] = useState(false);
  const [isTrusteesStage, setIsTrusteesStage] = useState(false);
  const [selectedCampusIndex, setSelectedCampusIndex] = useState(0);
  const [isCampusSpeaking, setIsCampusSpeaking] = useState(false);
  const [hasCampusRoomSelection, setHasCampusRoomSelection] = useState(false);
  const [campusRouteMode, setCampusRouteMode] = useState<CampusNavigationRouteMode>('default');
  const [campusRouteResult, setCampusRouteResult] = useState<CampusRouteResult | null>(null);
  const [campusDirectionOverride, setCampusDirectionOverride] = useState<CampusDirection | null>(null);
  const [surface, setSurface] = useState<ClaraChatSurface>('chat');
  const departmentComparisonOpen = surface === 'department_comparison';
  const isBrochureOpen = surface === 'brochure';
  const isBusRoutesSurface = surface === 'bus_routes';

  const [comparisonDeptIds, setComparisonDeptIds] = useState<string[]>([]);
  const [comparisonHighlightId, setComparisonHighlightId] = useState<string | null>(null);
  const [comparisonRecommendFocus, setComparisonRecommendFocus] = useState<string | null>(null);
  const [comparisonNarrationSection, setComparisonNarrationSection] = useState(0);
  const comparisonLayoutSnapRef = useRef<ChatLayoutMode | null>(null);
  const comparisonSlideSinkRef = useRef<(idx: number) => void>(() => {});

  const presentation = usePresentationController();
  const presentationRef = useRef(presentation);
  presentationRef.current = presentation;
  const [showLanguageOverlay, setShowLanguageOverlay] = useState(false);
  const [languageGateSatisfied, setLanguageGateSatisfied] = useState(() => !inlineLanguageGate);
  const openingLanguageNudgePlayedRef = useRef<string | null>(null);
  const isE2EFlow = useMemo(() => {
    if (typeof window === 'undefined') return false;
    return new URLSearchParams(window.location.search).has('e2e');
  }, []);

  // Response Priority Lock (CARD > UI > TEXT)
  const currentUiLockRef = useRef<'CARD' | 'TEXT' | 'IDLE'>('IDLE');
  /** Turn that owns the CARD lock; prevents a prior CARD turn from blocking a new ANSWER turn. */
  const cardLockTurnIdRef = useRef<string | null>(null);
  const engageCardUiLock = useCallback((ownerTurnId: string) => {
    const next = engageCardUiLockState(ownerTurnId, lastPayloadTurnIdRef.current);
    currentUiLockRef.current = next.lock;
    cardLockTurnIdRef.current = next.turnId;
  }, []);
  const lastSuggestionIdsRef = useRef<string[]>([]);
  const lastSuggestionTurnIdRef = useRef<string | null>(null);
  const [faqSuggestions, setFaqSuggestions] = useState<VisibleFaqSuggestion[]>(() =>
    selectFaqSuggestions('English', GENERAL_FAQ_CATEGORIES, []),
  );
  const [faqCarouselIndex, setFaqCarouselIndex] = useState(0);
  const [isFaqCarouselPaused, setIsFaqCarouselPaused] = useState(false);
  const [busRoutesMountKey, setBusRoutesMountKey] = useState(0);
  const [busRoutesHighlightQuery, setBusRoutesHighlightQuery] = useState<string | null>(null);
  const lastPayloadTurnIdRef = useRef<string | null>(null);
  const busRoutesDismissedTurnIdRef = useRef<string | null>(null);
  const closingBusRef = useRef(false);
  const lastTrusteeNarrationKeyRef = useRef<string | null>(null);

  useEffect(() => {
    onChatIdleOverlayChange?.(isBrochureOpen || isBusRoutesSurface);
  }, [isBrochureOpen, isBusRoutesSurface, onChatIdleOverlayChange]);

  useEffect(
    () => () => {
      onChatIdleOverlayChange?.(false);
    },
    [onChatIdleOverlayChange],
  );
  const tickerX = useMotionValue(0);
  const scriptPreset = useMemo(() => getScriptTypography(language), [language]);
  const [faqViewportWidth, setFaqViewportWidth] = useState(() =>
    typeof window !== 'undefined' ? Math.min(980, window.innerWidth * 0.92) : 900,
  );
  useEffect(() => {
    const update = () => setFaqViewportWidth(Math.min(980, window.innerWidth * 0.92));
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);
  const faqTickerLayout = useFaqTickerLayout(faqSuggestions, language, faqViewportWidth);
  const ensureSuggestions = useCallback(
    (nextSuggestions?: VisibleFaqSuggestion[]) => {
      const base = (nextSuggestions && nextSuggestions.length > 0)
        ? nextSuggestions
        : selectFaqSuggestions(language, GENERAL_FAQ_CATEGORIES, lastSuggestionIdsRef.current);
      const safe = (base.length ? base : selectFaqSuggestions('English', GENERAL_FAQ_CATEGORIES, []))
        .slice(0, 5);
      setFaqSuggestions(safe);
      setFaqCarouselIndex(0);
      tickerX.set(0);
      setIsFaqCarouselPaused(false);
    },
    [language, tickerX],
  );

  const clearSuggestionLayer = useCallback(() => {
    ensureSuggestions();
    lastSuggestionTurnIdRef.current = null;
  }, [ensureSuggestions]);

  const [activeTargetDepartment, setActiveTargetDepartment] = useState<string | null>(null);
  const [activeHodDepartments, setActiveHodDepartments] = useState<string[]>([]);
  const [departmentOverviewDeckUnitIds, setDepartmentOverviewDeckUnitIds] = useState<
    string[] | null
  >(null);
  /** M5.2 unit-backed composition models (null = legacy / non-unit path). */
  const [unitBackedCards, setUnitBackedCards] = useState<PresentationCardModel[] | null>(null);
  /** Turn id owning sticky fees under department_overview showCard. */
  const feesStickyTurnIdRef = useRef<string | null>(null);
  /**
   * Department label of the last explicit course-menu click. A unit-less
   * department_overview turn may only render a full deck for this click; voice
   * turns without unitIds render no card (M5.4 fail-closed).
   */
  const uiClickDeckDepartmentRef = useRef<string | null>(null);


  const collegeData = useCollegeData(presentationLanguage);

  // Interaction State
  const [orbState, setOrbState] = useState<OrbState>('idle');
  const [isPlayingBackendAudio, setIsPlayingBackendAudio] = useState(false);
  const [audioPendingTimedOut, setAudioPendingTimedOut] = useState(false);
  const isResponsePending = showThinkingOverlay({
    isProcessing: Boolean(isProcessing),
    audioPending: Boolean(payload?.audioPending) && !audioPendingTimedOut,
    audioUnavailable: payload?.audioUnavailable === true,
    watchdogRecovered: audioPendingTimedOut,
  });
  const [thinkingGate, setThinkingGate] = useState(EMPTY_THINKING_GATE);
  const thinkingGateRef = useRef(EMPTY_THINKING_GATE);
  thinkingGateRef.current = thinkingGate;
  const [thinkingEpoch, setThinkingEpoch] = useState(0);
  const thinkingWatchdogRef = useRef<number | null>(null);
  const guestNameRef = useRef<string | null>(null);
  const displayMessagesRef = useRef(displayMessages);
  displayMessagesRef.current = displayMessages;
  const showThinkingStage = (() => {
    const gate = thinkingGate;
    if (gate.turnId) {
      if (gate.ttsFailed || gate.responseStarted) return false;
      if (shouldShowThinkingInterlude(gate)) return true;
      return Boolean(isProcessing) && !gate.ttsFailed;
    }
    return isResponsePending;
  })();
  const [hasGreeted, setHasGreeted] = useState(false);
  const [showUnmuteHint, setShowUnmuteHint] = useState(false);
  const [pendingAudio, setPendingAudio] = useState<PendingAudio | null>(null);
  const [visuallyFocusedMessage, setVisuallyFocusedMessage] = useState<ChatMessage | null>(null);
  const [sentenceRevealText, setSentenceRevealText] = useState('');
  const [sentenceRevealTurnId, setSentenceRevealTurnId] = useState<string | null>(null);
  const [isAwaitingReadyPrompt, setIsAwaitingReadyPrompt] = useState(false);
  const hasStartedRef = useRef(false);
  const prevLayoutModeRef = useRef<'FULL_TEXT' | 'SPLIT_CARDS'>('FULL_TEXT');
  const languagePickInFlightRef = useRef(false);
  const wasPlayingAudioRef = useRef(false);
  const isPendingListeningRef = useRef(false);
  const deferredMessagesRef = useRef<ChatMessage[] | null>(null);
  const deferredTurnIdRef = useRef<string | null>(null);
  const savedChatFocusRef = useRef<ChatMessage | null>(null);
  const campusTtsSerialRef = useRef(0);
  const processCampusVoiceTranscriptRef = useRef<(transcript: string) => void>(() => {});
  const cardNavigationRef = useRef<(idx: number) => void>(() => {});
  const audioPrimedRef = useRef(false);
  const sentenceRevealAbortRef = useRef(0);
  const sentenceRevealKeyRef = useRef<string | null>(null);
  const fullTextScrollRef = useRef<HTMLDivElement | null>(null);
  const latestPayloadRef = useRef<any | null>(payload ?? null);
  const faceChannelRef = useRef<FaceChannel | undefined>(faceChannel);

  // Audio Playback Ref
  const playedSegmentKeysRef = useRef<Set<string>>(new Set());
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const streamAudioLayoutRef = useRef<{
    isOverview: boolean;
    cardsToSync: any[] | null;
    targetLayout: 'FULL_TEXT' | 'SPLIT_CARDS';
    turnId: string;
  } | null>(null);
  const ttsStreamQueueRef = useRef<
    {
      audioBase64: string;
      segmentKey: string;
      isOverview: boolean;
      cardsToSync: any[] | null;
      turnId: string;
      totalDurationEstimateMs?: number | null;
      /** Chunk index at enqueue time (fallback only). */
      chunkIndex?: number | null;
      sectionId?: string | null;
      segmentId?: string | null;
      unitId?: string | null;
      status?: TtsClipStatus;
    }[]
  >([]);
  /** Index into ttsStreamQueueRef of the clip that is playing or next to play. Never a second queue. */
  const ttsPlayheadRef = useRef(0);
  /** Bumped on cancel/seek so a stale audio.onended cannot advance the new target. */
  const playbackGenRef = useRef(0);
  const appliedBackendTtsQueueLenRef = useRef(0);
  const lastBackendTtsStreamTurnRef = useRef<string>('');
  const receivedTtsChunkIndicesRef = useRef<Set<number>>(new Set());
  const firstTtsChunkSeenAtRef = useRef<number | null>(null);
  const ttsBufferTimerRef = useRef<number | null>(null);
  const pendingFinalBackupRef = useRef<{
    audioBase64: string;
    segmentKey: string;
    turnId: string;
  } | null>(null);
  const audioLockRef = useRef(false);
  const responseTtsSchedulerRef = useRef(createResponseTtsScheduler());
  const ackPlayerRef = useRef(createAckPlayer());
  const thinkingPlayerRef = useRef(createThinkingTtsPlayer());
  const responseWatchdogTimerRef = useRef<number | null>(null);
  const handleAudioPlaybackRef = useRef<
    | ((
        audioBase64: string,
        segmentKey: string,
        isOverview: boolean,
        cardsToSync: any[] | null,
        _turnId?: string | null,
        audioChainFollowUp?: boolean,
        totalDurationEstimateMs?: number | null,
        clipMeta?: {
          channel?: 'ack' | 'response';
          sequence?: number;
          watchdogMs?: number;
          chunkIndex?: number | null;
          sectionId?: string | null;
          segmentId?: string | null;
          unitId?: string | null;
        },
      ) => void)
    | null
  >(null);
  const playQueuedClipRef = useRef<(followUp: boolean) => void>(() => {});
  /** Server `turn_id` for the in-flight assistant reply (claimed from the first current-turn frame). */
  const assistantAudioTurnOwnerRef = useRef<string | null>(null);
  const previousAudioTurnOwnerRef = useRef<string | null>(null);
  const thinkingAudioPlayedRef = useRef<string | null>(null);
  const heldResponsePayloadRef = useRef<any | null>(null);

  const lastLoadedPresentationTurnRef = useRef<string | null>(null);

  useEffect(() => {
    latestPayloadRef.current = payload ?? null;
    const gen =
      typeof payload?.session_gen === 'number' && Number.isFinite(payload.session_gen)
        ? payload.session_gen
        : undefined;
    if (typeof gen === 'number') {
      patchConversationRuntime({
        generation: gen,
        turnId: typeof payload?.turn_id === 'string' ? payload.turn_id : undefined,
        currentLanguage: language,
        currentIntent: typeof payload?.intent === 'string' ? payload.intent : undefined,
      });
    }

    const plan = payload?.narration_plan;
    if (plan && typeof plan === 'object' && plan.mode === 'card_narration' && Array.isArray(plan.segments)) {
      const payloadTid =
        typeof payload?.turn_id === 'string' && payload.turn_id.trim()
          ? payload.turn_id.trim()
          : typeof plan.turnId === 'string'
            ? plan.turnId
            : '';
      if (shouldIgnorePayloadTurn(
        assistantAudioTurnOwnerRef.current,
        payloadTid,
        previousAudioTurnOwnerRef.current,
      )) {
        return;
      }
      narrationPlanRef.current = plan as NarrationPlan;
      const incomingCardModels = presentationCardsFromNarrationSegments(plan.segments);
      if (incomingCardModels.length > 0) {
        setUnitBackedCards(incomingCardModels);
        const allHod = incomingCardModels.every((model) => model.cardType === 'hod');
        const allFees = incomingCardModels.every((model) => model.cardType === 'department_fees');
        setIsHodStage(allHod);
        setIsFeesStage(allFees);
        if (allHod) {
          const departments = incomingCardModels.map((model) => model.departmentId);
          setActiveHodDepartments(departments);
          setActiveTargetDepartment(departments[0] ?? null);
        } else {
          setActiveHodDepartments([]);
        }
        if (allFees && incomingCardModels.length === 1) {
          setActiveFeesDepartmentId(incomingCardModels[0]!.departmentId);
        } else if (!allFees) {
          setActiveFeesDepartmentId(null);
        }
      }
      const turnId = typeof plan.turnId === 'string' ? plan.turnId : '';
      const incomingUnitIds = unitIdsFromSegments(plan.segments);
      const loadedIds = (presentationRef.current.snapshot.scenes || [])
        .map((s) => (typeof s.unitId === 'string' ? s.unitId.trim() : ''))
        .filter(Boolean);
      const replaceWithUnitPlan = shouldLoadUnitPlan({
        incomingTurnId: turnId,
        lastLoadedTurnId: lastLoadedPresentationTurnRef.current,
        incomingUnitIds,
        loadedSceneUnitIds: loadedIds,
      });

      if (!replaceWithUnitPlan && lastLoadedPresentationTurnRef.current === turnId) {
        return;
      }

      const localeKey = localizationCodeKey(
        presentationLanguage,
        typeof payload?.language_code_key === 'string' ? payload.language_code_key : null,
      );

      if (incomingUnitIds.length > 0 && (replaceWithUnitPlan || lastLoadedPresentationTurnRef.current !== turnId)) {
        lastLoadedPresentationTurnRef.current = turnId;
        const est = finitePositiveMs(payload?.tts_total_duration_estimate_ms);
        const ctrl = presentationRef.current;
        freezeLocalization(presentationLanguage, localeKey);
        ctrl.setSceneAdvanceMode('per_clip');
        const presentationId = ctrl.loadPresentation({
          kind: 'plan',
          plan: {
            turnId,
            mode: 'card_narration',
            segments: plan.segments,
          },
          estimatedTotalDurationMs: est,
        });
        patchConversationRuntime({
          turnId,
          activePresentationId: presentationId,
          runtimeState: 'presenting',
          ...(typeof gen === 'number' ? { generation: gen } : {}),
        });
        ctrl.play();
        return;
      }

      if (!turnId || lastLoadedPresentationTurnRef.current === turnId) {
        return;
      }

      const cardsLen =
        Array.isArray(activeCards) && activeCards.length > 0 ? activeCards.length : null;
      const contract = validatePresentationContract({
        plan: {
          turnId,
          mode: 'card_narration',
          segments: plan.segments,
        },
        cardsToSyncLength: cardsLen,
      });

      if (!contract.ok) {
        lastLoadedPresentationTurnRef.current = turnId;
        const fallback = choosePresentationFallback({
          hasSingleCardSurface:
            cardsLen === 1 ||
            isFeesStage ||
            isHodStage ||
            isDocumentsStage ||
            Boolean(executiveLeadershipKind),
          canUseFullText: true,
        });
        pushRuntimeEvent(
          fallback === 'single_card'
            ? 'PRESENTATION_FALLBACK_SINGLE'
            : fallback === 'full_text'
              ? 'PRESENTATION_FALLBACK_FULL_TEXT'
              : 'PRESENTATION_FALLBACK_CONCISE',
          { turnId, reason: contract.failures[0]?.reason },
        );
        const ctrl = presentationRef.current;
        ctrl.cancel();
        releaseLocalizationFreeze();
        if (fallback === 'single_card' && shouldAllowLegacySingle(incomingUnitIds)) {
          freezeLocalization(presentationLanguage, localeKey);
          ctrl.loadPresentation({
            kind: 'single',
            cardId: 'stage',
            turnId,
            caption: '',
            spokenSummary: '',
          });
          ctrl.play();
        } else if (fallback === 'full_text') {
          setLayoutMode('FULL_TEXT');
        }
        return;
      }

      lastLoadedPresentationTurnRef.current = turnId;
      const est = finitePositiveMs(payload?.tts_total_duration_estimate_ms);
      const ctrl = presentationRef.current;
      freezeLocalization(presentationLanguage, localeKey);
      ctrl.setSceneAdvanceMode('per_clip');
      const presentationId = ctrl.loadPresentation({
        kind: 'plan',
        plan: {
          turnId,
          mode: 'card_narration',
          segments: plan.segments,
        },
        estimatedTotalDurationMs: est,
      });
      patchConversationRuntime({
        turnId,
        activePresentationId: presentationId,
        runtimeState: 'presenting',
        ...(typeof gen === 'number' ? { generation: gen } : {}),
      });
      ctrl.play();
    }
  }, [
    payload,
    language,
    presentationLanguage,
    activeCards,
    isFeesStage,
    isHodStage,
    isDocumentsStage,
    executiveLeadershipKind,
    setLayoutMode,
  ]);

  // PresentationEngine is the sole source of card index / caption / comparison section.
  useEffect(() => {
    const snap = presentation.snapshot;
    if (
      snap.engineState === 'IDLE' ||
      snap.engineState === 'CANCELLED' ||
      snap.engineState === 'LOADING_PLAN'
    ) {
      return;
    }
    if (
      snap.presentationId &&
      !assertLivePresentationOwnership({
        snapshotPresentationId: snap.presentationId,
        loadedTurnId: lastLoadedPresentationTurnRef.current,
      })
    ) {
      return;
    }
    setCurrentCardIdx(snap.cardIndex);
    patchConversationRuntime({
      activePresentationId: snap.presentationId,
      activeScene: snap.sceneIndex,
    });
    if (snap.engineState === 'PRESENTATION_COMPLETE') {
      setNarrationCaption('');
      releaseLocalizationFreeze();
    } else {
      setNarrationCaption(snap.displayCaption);
    }
    setComparisonNarrationSection(snap.comparisonSection);
  }, [
    presentation.snapshot.engineState,
    presentation.snapshot.cardIndex,
    presentation.snapshot.displayCaption,
    presentation.snapshot.comparisonSection,
    presentation.snapshot.sceneIndex,
    presentation.snapshot.presentationId,
  ]);

  useEffect(() => {
    faceChannelRef.current = faceChannel;
  }, [faceChannel]);

  // Face display: push "thinking" state as soon as backend marks turn processing.
  useEffect(() => {
    if (!payload || isPayloadStale?.(payload)) return;
    if (payload.isProcessing !== true) return;
    const tid = typeof payload.turn_id === 'string' ? payload.turn_id.trim() : '';
    if (!tid) return;
    faceChannelRef.current?.postThinking?.(tid);
  }, [payload, isPayloadStale]);

  const clearCardStages = useCallback(() => {
    setActiveCards(null);
    setCurrentCardIdx(0);
    setSuppressedTurnId(null);
    setCourseMenuOptions([]);
    setActiveDepartmentId(null);
    setIsDepartmentOverviewStage(false);
    setIsInfoSlideStage(false);
    setInfoSlides([]);
    setInfoSlideChip('');
    setIsHodStage(false);
    setActiveHodDepartments([]);
    setDepartmentOverviewDeckUnitIds(null);
    setUnitBackedCards(null);
    feesStickyTurnIdRef.current = null;
    setExecutiveLeadershipKind(null);
    setIsFeesStage(false);
    setActiveFeesDepartmentId(null);
    setIsDocumentsStage(false);
    cardLockTurnIdRef.current = null;
  }, []);

  /** Single turn-boundary reset for TTS + card presentation state. */
  const resetTurnPresentationState = useCallback(
    (opts: { resetLayout?: boolean } = {}) => {
      const resetLayout = opts.resetLayout !== false;
      appliedBackendTtsQueueLenRef.current = 0;
      ttsStreamQueueRef.current = [];
      ttsPlayheadRef.current = 0;
      playbackGenRef.current += 1;
      lastBackendTtsStreamTurnRef.current = '';
      receivedTtsChunkIndicesRef.current.clear();
      firstTtsChunkSeenAtRef.current = null;
      if (ttsBufferTimerRef.current) {
        window.clearTimeout(ttsBufferTimerRef.current);
        ttsBufferTimerRef.current = null;
      }
      if (responseWatchdogTimerRef.current) {
        window.clearTimeout(responseWatchdogTimerRef.current);
        responseWatchdogTimerRef.current = null;
      }
      pendingFinalBackupRef.current = null;
      ackPlayerRef.current.stop();
      responseTtsSchedulerRef.current.reset();
      presentationRef.current.audioManager.current?.invalidate();
      presentationRef.current.cancel();
      lastLoadedPresentationTurnRef.current = null;
      narrationPlanRef.current = null;
      setNarrationCaption('');
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
        currentAudioRef.current = null;
      }
      audioLockRef.current = false;
      setIsPlayingBackendAudio(false);
      streamAudioLayoutRef.current = null;
      const leaving = assistantAudioTurnOwnerRef.current;
      if (leaving && leaving !== TURN_FENCE_PENDING) {
        previousAudioTurnOwnerRef.current = leaving;
      }
      assistantAudioTurnOwnerRef.current = TURN_FENCE_PENDING;
      playedSegmentKeysRef.current.clear();
      setAudioPendingTimedOut(false);
      if (resetLayout) {
        comparisonLayoutSnapRef.current = null;
        busRoutesDismissedTurnIdRef.current = null;
        setBusRoutesHighlightQuery(null);
        setLayoutMode('FULL_TEXT');
        setActiveTargetDepartment(null);
        setIsCampusNavigationStage(false);
        clearCardStages();
        setIsTrusteesStage(false);
        currentUiLockRef.current = 'IDLE';
      }
    },
    [clearCardStages, setLayoutMode],
  );

  const bumpThinkingEpoch = useCallback(() => {
    setThinkingEpoch((n) => n + 1);
  }, []);

  const clearThinkingWatchdog = useCallback(() => {
    if (thinkingWatchdogRef.current) {
      window.clearTimeout(thinkingWatchdogRef.current);
      thinkingWatchdogRef.current = null;
    }
  }, []);

  const armThinkingWatchdog = useCallback((turnId: string) => {
    clearThinkingWatchdog();
    thinkingWatchdogRef.current = window.setTimeout(() => {
      const g = thinkingGateRef.current;
      if (g.turnId !== turnId || g.ttsFinished || g.ttsFailed) return;
      thinkingPlayerRef.current?.stop();
      const next = markThinkingTtsFailed(g, turnId);
      thinkingGateRef.current = next;
      setThinkingGate(next);
      setThinkingEpoch((n) => n + 1);
      playQueuedClipRef.current(false);
    }, THINKING_TTS_WATCHDOG_MS);
  }, [clearThinkingWatchdog]);

  const startThinkingInterlude = useCallback((query: string) => {
    const tp = thinkingPlayerRef.current;
    if (tp && typeof tp.reset === 'function') tp.reset();
    else tp?.stop();
    heldResponsePayloadRef.current = null;
    thinkingAudioPlayedRef.current = null;
    const sentence = composeThinkingBridge({
      query,
      language,
      guestName: guestNameRef.current,
    }) || thinkingBridgeFallback(language);
    const turnId = `pending:${Date.now()}`;
    const next = beginThinkingTurn(thinkingGateRef.current, { turnId, sentence });
    thinkingGateRef.current = next;
    setThinkingGate(next);
    armThinkingWatchdog(turnId);
  }, [armThinkingWatchdog, language]);

  const abortThinkingInterlude = useCallback(() => {
    clearThinkingWatchdog();
    const tp = thinkingPlayerRef.current;
    if (tp && typeof tp.reset === 'function') tp.reset();
    else tp?.stop();
    heldResponsePayloadRef.current = null;
    thinkingAudioPlayedRef.current = null;
    const next = resetThinkingGate();
    thinkingGateRef.current = next;
    setThinkingGate(next);
    bumpThinkingEpoch();
  }, [bumpThinkingEpoch, clearThinkingWatchdog]);

  const scheduleThinkingAudio = useCallback((audioBase64: string, turnId: string, spokenText?: string) => {
    const attempt = () => {
      const g = thinkingGateRef.current;
      if (!g.turnId) return;
      if (g.ttsFinished || g.ttsFailed || g.responseStarted) return;
      if (g.turnId !== turnId && !g.turnId.startsWith('pending:')) return;
      if (thinkingPlayerRef.current?.playing()) return;

      const rebound = rebindThinkingTurn(g, turnId);
      const withText =
        spokenText && spokenText.trim()
          ? attachThinkingSentence(rebound, spokenText)
          : rebound;
      const playing = markThinkingTtsPlaying(withText);
      thinkingGateRef.current = playing;
      setThinkingGate(playing);

      const canonical = (spokenText || playing.sentence || '').trim();
      if (import.meta.env.DEV) {
        console.debug('[clara-thinking-tts]', {
          event: 'playback_start',
          thinking_turn_id: turnId,
          thinking_text_length: canonical.length,
          thinking_text: canonical,
          audio_b64_len: audioBase64.length,
        });
      }
      thinkingPlayerRef.current?.play(audioBase64, turnId, { text: canonical });
    };

    // ACK must finish (or be skipped) before thinking speaks — never clip mid-sentence.
    if (ackPlayerRef.current.playing()) {
      ackPlayerRef.current.whenIdle(attempt);
      return;
    }
    attempt();
  }, []);

  useEffect(() => {
    const player = createThinkingTtsPlayer({
      onEnded: (tid) => {
        if (import.meta.env.DEV) {
          console.debug('[clara-thinking-tts]', {
            event: 'playback_ended',
            thinking_turn_id: tid,
          });
        }
        const next = markThinkingTtsFinished(thinkingGateRef.current, tid);
        thinkingGateRef.current = next;
        setThinkingGate(next);
        if (thinkingWatchdogRef.current) {
          window.clearTimeout(thinkingWatchdogRef.current);
          thinkingWatchdogRef.current = null;
        }
        setThinkingEpoch((n) => n + 1);
        playQueuedClipRef.current(false);
      },
      onError: (tid) => {
        if (import.meta.env.DEV) {
          console.debug('[clara-thinking-tts]', {
            event: 'playback_error',
            thinking_turn_id: tid,
          });
        }
        const next = markThinkingTtsFailed(thinkingGateRef.current, tid);
        thinkingGateRef.current = next;
        setThinkingGate(next);
        if (thinkingWatchdogRef.current) {
          window.clearTimeout(thinkingWatchdogRef.current);
          thinkingWatchdogRef.current = null;
        }
        setThinkingEpoch((n) => n + 1);
        playQueuedClipRef.current(false);
      },
      onStarted: (tid, meta) => {
        if (import.meta.env.DEV) {
          console.debug('[clara-thinking-tts]', {
            event: 'playback_playing',
            thinking_turn_id: tid,
            thinking_text_length: meta?.text?.length ?? 0,
            audio_bytes: meta?.audioBytes,
          });
        }
      },
    });
    thinkingPlayerRef.current = player;
    return () => {
      player.reset();
    };
  }, []);

  // Wraps original sendMessage to sniff for intents dynamically on dispatch.
  // Deterministic FAQ answers are resolved by the backend before Groq/RAG.
  const interceptAndSendMessage = useCallback((msg: any, source: 'VOICE' | 'UI' = 'VOICE') => {
    if (msg?.action === 'user_message' && typeof msg.text === 'string') {
      const trimmed = msg.text.trim();
      if (source === 'VOICE' && isCampusNavigationStage && trimmed) {
        processCampusVoiceTranscriptRef.current(trimmed);
        return;
      }
      const cardDirection = parseCardNavigationCommand(trimmed);
      if (cardDirection && Array.isArray(unitBackedCards) && unitBackedCards.length > 0) {
        const delta = cardDirection === 'next' ? 1 : -1;
        const targetIndex = Math.min(
          unitBackedCards.length - 1,
          Math.max(0, currentCardIdx + delta),
        );
        cardNavigationRef.current(targetIndex);
        onChatUserActivity?.();
        return;
      }
      clearSuggestionLayer();
      if (source === 'VOICE') {
        setSurface('chat');
      }
      // Rule 5: explicit UI menu navigation (localIntent) keeps layout; all other turns reset.
      const preserveLayoutForUiNav = source === 'UI' && Boolean(msg?.localIntent);
      resetTurnPresentationState({ resetLayout: !preserveLayoutForUiNav });
      if (source === 'VOICE') {
        setActiveCards(null);
        setCurrentCardIdx(0);
        setSuppressedTurnId(null);
        setCourseMenuOptions([]);
      }

      // Backend is authoritative for intent routing on voice turns.
      // Frontend localIntent is allowed only for explicit UI command flows.
      if (source === 'UI' && msg?.localIntent) {
        if (import.meta.env.DEV) {
          console.log(
            `[CLARA_PIPELINE] UI localIntent forwarded type=${msg.localIntent?.type ?? 'unknown'} dept=${msg.localIntent?.departmentLabel ?? 'none'}`
          );
        }
      }

      const text = typeof msg.text === 'string' ? msg.text : '';
      const isBackgroundNoiseDummy =
        text.includes('BACKGROUND_NOISE') || text.includes('**BACKGROUND_NOISE**');
      if (!isBackgroundNoiseDummy) {
        onChatUserActivity?.();
        const msgs = displayMessagesRef.current;
        const awaitingName =
          msgs.some((m: any) => m?.id === 'name_prompt') &&
          !msgs.some((m: any) => m?.id === 'ready_prompt');
        if (!inlineLanguageGate && !awaitingName) {
          startThinkingInterlude(text);
        }
      }
    }
    sendMessage(msg);
  }, [clearSuggestionLayer, resetTurnPresentationState, sendMessage, onChatUserActivity, isCampusNavigationStage, unitBackedCards, currentCardIdx, inlineLanguageGate, startThinkingInterlude]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.__CLARA_TEST_SEND_MESSAGE = (text: string) => {
      interceptAndSendMessage({ action: 'user_message', text }, 'VOICE');
    };
    return () => {
      delete window.__CLARA_TEST_SEND_MESSAGE;
    };
  }, [interceptAndSendMessage]);

  // Prime browser audio on first user gesture to reduce autoplay blocks in demos/kiosk.
  useEffect(() => {
    const primeAudio = () => {
      if (audioPrimedRef.current) return;
      audioPrimedRef.current = true;
      const probe = new Audio(
        'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA='
      );
      probe.muted = true;
      probe
        .play()
        .then(() => {
          probe.pause();
          probe.currentTime = 0;
        })
        .catch(() => {
          // Best effort only; fallback hint remains in regular playback path.
        });
    };
    window.addEventListener('pointerdown', primeAudio, { once: true });
    window.addEventListener('keydown', primeAudio, { once: true });
    return () => {
      window.removeEventListener('pointerdown', primeAudio);
      window.removeEventListener('keydown', primeAudio);
    };
  }, []);


  // Intent Classifier & Speech Hooks
  const isMicListening = orbState === 'listening' || Boolean(propIsListening);
  const voiceAnalyser = useVoiceFrequencyAnalyser(isMicListening);
  // Browser Speech Rec fallback (used if not relying on backend voice activity detection)
  const handleEmptyTranscript = useCallback(() => {
    if (isCampusNavigationStage) return;
    setShowUnmuteHint(false);
    setIsDepartmentOverviewStage(false);
    setActiveDepartmentId(null);
    interceptAndSendMessage({
      action: 'user_message',
      text: '**BACKGROUND_NOISE** No words detected, returning to idle state.',
    });
  }, [interceptAndSendMessage, isCampusNavigationStage]);

  const handleSpeechError = useCallback((errorCode: string, userMessage: string) => {
    if (errorCode === 'aborted' || !userMessage?.trim()) return;
    if (import.meta.env.DEV) {
      console.warn('[CLARA_SPEECH] browser speech error', { errorCode, userMessage });
    }
    // Ensure UI can recover immediately from browser speech failures.
    setIsCampusSpeaking(false);
    setIsPlayingBackendAudio(false);
    setHasGreeted(true);
    const errorBubble: ChatMessage = {
      id: `speech-error-${Date.now()}`,
      role: 'clara',
      text: userMessage || uiText(language, 'error.voice_failed'),
    };
    setDisplayMessages((prev) => [...prev, errorBubble]);
    setVisuallyFocusedMessage(errorBubble);

    // Transient browser-STT failures should not permanently own the kiosk answer stage.
    if (errorCode === 'network' || errorCode === 'no-speech') {
      window.setTimeout(() => {
        setVisuallyFocusedMessage((current) =>
          current?.id === errorBubble.id ? null : current,
        );
      }, 4500);
    }
  }, [language]);

  const { startListening: startSpeechRecognition, stopListening, isListening: speechListening } = useSpeechRecognition(
    interceptAndSendMessage,
    language,
    handleSpeechError,
    handleEmptyTranscript
  );

  // Keep chat history stable when backend emits partial payloads without `messages`.
  useEffect(() => {
    if (payload && isPayloadStale?.(payload)) return;
    if (Array.isArray(payload?.messages)) {
      const incomingMessages = payload.messages as ChatMessage[];
      const hasReadyPrompt = incomingMessages.some((m: any) => m?.id === 'ready_prompt');
      const hasNamePrompt = incomingMessages.some((m: any) => m?.id === 'name_prompt');
      if (
        hasReadyPrompt ||
        hasNamePrompt ||
        payload?.turn_id === 'ready_after_language_pick' ||
        payload?.turn_id === 'name_after_language_pick'
      ) {
        setIsAwaitingReadyPrompt(false);
      }
      const hasAudio = typeof payload?.audioBase64 === 'string' && payload.audioBase64.length > 0;
      const hasQueue =
        Array.isArray(payload?.tts_audio_queue) && payload.tts_audio_queue.some((x: unknown) => typeof x === 'string' && x.length > 0);
      const hasSlots =
        Array.isArray(payload?.tts_clip_slots) &&
        payload.tts_clip_slots.some(
          (slot: { audioBase64?: unknown; status?: unknown }) =>
            slot?.status === 'PLAYABLE' || (typeof slot?.audioBase64 === 'string' && slot.audioBase64.length > 0),
        );
      const isWaitingForAudio = Boolean(payload?.audioPending);
      const isTerminalTurn = payload?.isProcessing === false;
      const isCardTurn = Boolean(payload?.showCard);
      if (shouldCommitAnswerMessages({
        hasMessages: incomingMessages.length > 0,
        audioPending: isWaitingForAudio,
        audioUnavailable: payload?.audioUnavailable === true,
        audioReady: (hasAudio || hasQueue || hasSlots) && !isWaitingForAudio,
        watchdogRecovered: audioPendingTimedOut,
      }) && !shouldBlockResponsePlayback(thinkingGateRef.current)) {
        deferredMessagesRef.current = null;
        deferredTurnIdRef.current = null;
        setDisplayMessages(incomingMessages);
        if (isTerminalTurn && (hasAudio || isWaitingForAudio)) {
          deferredMessagesRef.current = incomingMessages;
          deferredTurnIdRef.current = payload?.turn_id ?? null;
        }
      }
      if (isCardTurn) {
        setVisuallyFocusedMessage(null);
      } else if (shouldFocusAssistantAnswer({
        isCardTurn,
        isProcessing: payload?.isProcessing === true,
        audioPending: isWaitingForAudio,
      })) {
        const latestAssistant = [...incomingMessages]
          .reverse()
          .find((m: any) => m?.role === 'clara' && typeof m?.text === 'string' && !(m as any)?.isHidden && !(m as any)?.isCardData);
        setVisuallyFocusedMessage((latestAssistant as ChatMessage) ?? null);
      }
    }
  }, [
    payload,
    isPayloadStale,
    audioPendingTimedOut,
    thinkingEpoch,
  ]);

  useEffect(() => {
    setLanguageGateSatisfied(!inlineLanguageGate);
    languagePickInFlightRef.current = false;
    if (!inlineLanguageGate) {
      setShowLanguageOverlay(false);
    } else {
      setHasGreeted(false);
    }
  }, [inlineLanguageGate]);

  // Keep the wake text visible until local TTS playback has fully ended, then crossfade to the picker.
  useEffect(() => {
    if (payload && isPayloadStale?.(payload)) return;
    if (!inlineLanguageGate || languageGateSatisfied) {
      if (!inlineLanguageGate) setShowLanguageOverlay(false);
      return;
    }
    const hasAssistant = displayMessages.some(
      (m) =>
        ('role' in m && m.role === 'clara') &&
        !(m as { isHidden?: boolean }).isHidden &&
        typeof (m as { text?: string }).text === 'string'
    );
    if (!hasAssistant || isResponsePending) return;

    const openingTurn = payload?.turn_id === 'greeting_opening';
    const hasOpeningAudio = typeof payload?.audioBase64 === 'string' && payload.audioBase64.length > 0;
    const shouldRevealPicker = isE2EFlow || hasGreeted || (openingTurn && !hasOpeningAudio);
    if (!shouldRevealPicker) return;

    setShowLanguageOverlay(true);
  }, [
    inlineLanguageGate,
    languageGateSatisfied,
    displayMessages,
    isResponsePending,
    hasGreeted,
    isE2EFlow,
    payload?.turn_id,
    payload?.audioBase64,
    isPayloadStale,
  ]);

  // The language instruction is spoken only after the greeting clip has ended.
  // It is never added to displayMessages, so the visible opening remains the
  // greeting while the picker is shown separately.
  useEffect(() => {
    if (payload && isPayloadStale?.(payload)) return;
    if (!inlineLanguageGate || languageGateSatisfied) return;
    if (payload?.turn_id !== 'greeting_opening') return;
    const nudgeAudio = payload?.languageGateNudgeAudioBase64;
    if (typeof nudgeAudio !== 'string' || nudgeAudio.length === 0) return;
    const hasOpeningAudio = typeof payload?.audioBase64 === 'string' && payload.audioBase64.length > 0;
    const greetingComplete = hasGreeted || !hasOpeningAudio;
    if (!greetingComplete) return;
    const key = `${payload.turn_id}:${nudgeAudio.slice(0, 24)}:${nudgeAudio.length}`;
    if (openingLanguageNudgePlayedRef.current === key) return;
    openingLanguageNudgePlayedRef.current = key;
    const audio = new Audio(`data:audio/wav;base64,${nudgeAudio}`);
    audio.dataset.claraChannel = 'legacy';
    audio.dataset.turnId = 'language_gate_nudge';
    audio.play().catch((error) => {
      console.warn('[CLARA_TTS] language gate nudge playback failed', error);
    });
    return () => {
      audio.pause();
      audio.currentTime = 0;
    };
  }, [
    payload,
    payload?.turn_id,
    payload?.audioBase64,
    payload?.languageGateNudgeAudioBase64,
    hasGreeted,
    inlineLanguageGate,
    languageGateSatisfied,
    isPayloadStale,
  ]);

  const handleInlineLanguagePick = useCallback(
    (lang: Language) => {
      // K1: one tap produces exactly one selection transition; rapid double
      // taps (or a re-fired callback) must not duplicate state changes or
      // welcome requests.
      if (languageGateSatisfied || languagePickInFlightRef.current) return;
      languagePickInFlightRef.current = true;
      onChatUserActivity?.();
      if (!canChangeLanguageNow()) {
        pushRuntimeEvent('LOCALE_CHANGE_BLOCKED', { language: lang, reason: 'frozen' });
        languagePickInFlightRef.current = false;
        return;
      }
      presentationRef.current.cancel();
      lastLoadedPresentationTurnRef.current = null;
      setNarrationCaption('');
      releaseLocalizationFreeze();
      const code = languageToCode(lang);
      selectLanguageCode(code);
      patchConversationRuntime({ currentLanguage: lang });
      markWelcomeCompleted();
      setIsAwaitingReadyPrompt(true);
      clearSuggestionLayer();
      setVisuallyFocusedMessage(null);
      const visitorId = getVisitorSessionId();
      sendMessage({
        action: 'language_selected',
        language: lang,
        language_code_key: code,
        ...(visitorId ? { visitor_session_id: visitorId } : {}),
      });
      setShowLanguageOverlay(false);
      setLanguageGateSatisfied(true);
      onInlineLanguageResolved?.();
    },
    [
      clearSuggestionLayer,
      sendMessage,
      selectLanguageCode,
      languageGateSatisfied,
      onInlineLanguageResolved,
      onChatUserActivity,
    ]
  );

  const resolveCardsFromTrigger = useCallback((trigger: unknown): CardDataItem[] | null => {
    const mapSingleTrigger = (key: string): CardDataItem[] | null => {
      const n = key.toLowerCase();
      if (n === 'hod' || n === 'hod_profile' || n === 'head_of_department') {
        const c = buildAllHodCardsFromLocale(collegeData, language);
        return c.length ? c : null;
      }
      if (n === 'dept' || n === 'department' || n === 'department_overview') {
        const c = buildAllDepartmentSummaryCardsFromLocale(collegeData, language);
        return c.length ? c : null;
      }
      if (['college', 'college_overview', 'overview', 'institution'].includes(n)) {
        const c = buildInstitutionCardsFromLocale(collegeData);
        return c.length ? c : null;
      }
      if (['trustees', 'trustee', 'trustees_profile', 'trustee_profile'].includes(n)) {
        const c = buildTrusteeCardsFromLocale(collegeData);
        return c.length ? c : null;
      }
      return getStaticCardsForTrigger(language, key);
    };

    const triggerList = Array.isArray(trigger) ? trigger : [trigger];
    const merged: CardDataItem[] = [];
    for (const item of triggerList) {
      if (typeof item !== 'string') continue;
      const cards = mapSingleTrigger(item);
      if (cards && cards.length) {
        merged.push(...cards);
      }
    }
    if (!merged.length) return null;

    return merged.filter((card, idx) => {
      const signature = `${card?.title ?? ''}|${card?.type ?? ''}`;
      return (
        idx ===
        merged.findIndex(
          (x) => `${x?.title ?? ''}|${x?.type ?? ''}` === signature
        )
      );
    });
  }, [language, collegeData]);

  const handleCloseDepartmentComparison = useCallback(() => {
    presentationRef.current.cancel();
    setComparisonNarrationSection(0);
    setSurface('chat');
    const snap = comparisonLayoutSnapRef.current;
    if (snap !== null) setLayoutMode(snap);
    comparisonLayoutSnapRef.current = null;
  }, [setLayoutMode]);

  const handleCloseBusRoutes = useCallback(() => {
    if (closingBusRef.current) return;
    closingBusRef.current = true;
    const tid = lastPayloadTurnIdRef.current;
    if (tid !== null) busRoutesDismissedTurnIdRef.current = tid;
    setSurface('chat');
    setBusRoutesHighlightQuery(null);
    currentUiLockRef.current = 'IDLE';
    const scrollEl = fullTextScrollRef.current;
    if (scrollEl) scrollEl.scrollTop = 0;
    window.setTimeout(() => {
      closingBusRef.current = false;
    }, 220);
  }, []);
  useEffect(() => {
    comparisonSlideSinkRef.current = (idx: number) => {
      setComparisonNarrationSection((prev) => {
        const next = Math.max(0, Math.min(COMPARISON_NARRATION_SECTIONS - 1, idx));
        return prev === next ? prev : next;
      });
    };
  }, []);

  const applyComparisonNarrationSegment = useCallback(
    (seg: NarrationPlan['segments'][number], segmentIndex: number) => {
      if (!seg || typeof seg !== 'object') return;
      const pid = presentationRef.current.snapshot.presentationId;
      if (
        pid &&
        !assertLivePresentationOwnership({
          snapshotPresentationId: pid,
          loadedTurnId: lastLoadedPresentationTurnRef.current,
        })
      ) {
        return;
      }
      const unitId =
        typeof seg.unitId === 'string' && seg.unitId.trim() ? seg.unitId.trim() : null;
      if (unitId) {
        presentationRef.current.activateByUnitId(unitId);
        return;
      }
      const sectionId =
        typeof seg.sectionId === 'string' && seg.sectionId.trim()
          ? seg.sectionId.trim()
          : typeof seg.cardId === 'string' && seg.cardId.trim()
            ? seg.cardId.trim()
            : `seg_${segmentIndex}`;
      presentationRef.current.activateBySectionId(sectionId);
    },
    [],
  );

  useEffect(() => {
    if (!departmentComparisonOpen) {
      setComparisonNarrationSection(0);
    }
  }, [departmentComparisonOpen]);

  const stopCampusSpeech = useCallback(() => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    setIsPlayingBackendAudio(false);
    setIsCampusSpeaking(false);
  }, []);

  const stopTextReveal = useCallback((clearText = false) => {
    sentenceRevealAbortRef.current += 1;
    sentenceRevealKeyRef.current = null;
    if (clearText) {
      setSentenceRevealText('');
      setSentenceRevealTurnId(null);
    }
  }, []);

  const handleHomeClick = useCallback(() => {
    clearSuggestionLayer();
    stopTextReveal(true);
    setPendingAudio(null);
    appliedBackendTtsQueueLenRef.current = 0;
    ttsStreamQueueRef.current = [];
    ttsPlayheadRef.current = 0;
    playbackGenRef.current += 1;
    lastBackendTtsStreamTurnRef.current = '';
    streamAudioLayoutRef.current = null;
    assistantAudioTurnOwnerRef.current = null;
    playedSegmentKeysRef.current.clear();
    presentationRef.current.cancel();
    lastLoadedPresentationTurnRef.current = null;
    setNarrationCaption('');
    stopListening();
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    setIsPlayingBackendAudio(false);
    setIsCampusSpeaking(false);
    abortThinkingInterlude();
    setSurface('chat');
    comparisonLayoutSnapRef.current = null;
    busRoutesDismissedTurnIdRef.current = null;
    setBusRoutesHighlightQuery(null);
    if (onHome) onHome();
  }, [clearSuggestionLayer, stopTextReveal, stopListening, onHome, abortThinkingInterlude]);

  const requestCampusTts = useCallback((text: string, key: string) => {
    const cleanText = text.trim();
    if (!cleanText) return;

    stopCampusSpeech();
    onChatUserActivity?.();
    setIsCampusSpeaking(true);
    campusTtsSerialRef.current += 1;
    sendMessage({
      action: 'campus_navigation_tts',
      language,
      text: cleanText,
      turn_id: `campus-${key}-${language}-${campusTtsSerialRef.current}`,
    });
  }, [language, onChatUserActivity, sendMessage, stopCampusSpeech]);

  const speakCampusDirection = useCallback(
    (index?: number) => {
      const direction =
        index !== undefined
          ? (CAMPUS_DIRECTIONS[index] ?? CAMPUS_DIRECTIONS[0])
          : (campusDirectionOverride ?? (CAMPUS_DIRECTIONS[selectedCampusIndex] ?? CAMPUS_DIRECTIONS[0]));
      if (!direction) return;
      const key = index !== undefined ? `nav-${index}` : `nav-${selectedCampusIndex}-cur`;
      requestCampusTts(campusSpeechText(direction, language), key);
    },
    [language, requestCampusTts, selectedCampusIndex, campusDirectionOverride],
  );

  const processCampusVoiceTranscript = useCallback(
    async (transcript: string) => {
      const match = await matchCampusTranscriptApi(transcript);
      const labels = campusLabels(language);
      if (!match?.matched || !match.room) {
        requestCampusTts(
          labels.selectRoomPrompt || "Sorry, I couldn't match that to a campus room. Try a room code.",
          'campus-no-match',
        );
        return;
      }
      const direction = campusDirectionFromMapMatch(match.room);
      setCampusDirectionOverride(direction);
      const idx = legacyCampusIndexForCode(match.room.code);
      if (idx !== null) setSelectedCampusIndex(idx);
      setHasCampusRoomSelection(true);
      requestCampusTts(campusSpeechText(direction, language), 'nav-voice');
    },
    [language, requestCampusTts],
  );

  const handleMappedCampusRoomSelect = useCallback(
    (room: CampusMatchApiRoom) => {
      const direction = campusDirectionFromMapMatch(room);
      setCampusDirectionOverride(direction);
      const idx = legacyCampusIndexForCode(room.code, room.floor_id as 'GF' | 'FF' | 'SF');
      if (idx !== null) setSelectedCampusIndex(idx);
      setCampusRouteResult(null);
      setHasCampusRoomSelection(true);
      requestCampusTts(campusSpeechText(direction, language), `nav-map-${room.code}`);
    },
    [language, requestCampusTts],
  );

  useEffect(() => {
    processCampusVoiceTranscriptRef.current = (text: string) => {
      void processCampusVoiceTranscript(text);
    };
  }, [processCampusVoiceTranscript]);

  const promptCampusRoomSelection = useCallback(() => {
    const labels = campusLabels(language);
    requestCampusTts(labels.selectRoomPrompt || labels.selectPrompt, 'select-room');
  }, [language, requestCampusTts]);

  const handleTrusteeNarration = useCallback(
    (summary: string, trusteeIndex: number) => {
      const cleanSummary = summary.trim();
      if (!isTrusteesStage || !cleanSummary) return;
      const key = `${trusteeIndex}:${cleanSummary}`;
      if (lastTrusteeNarrationKeyRef.current === key) return;
      lastTrusteeNarrationKeyRef.current = key;
      const turnId = `trustee-card-${trusteeIndex}-${language}-${Date.now()}`;
      const ctrl = presentationRef.current;
      ctrl.setSceneAdvanceMode('per_clip');
      ctrl.loadPresentation({
        kind: 'single',
        turnId,
        cardId: 'trustee',
        caption: cleanSummary,
        spokenSummary: cleanSummary,
      });
      ctrl.play();
      lastLoadedPresentationTurnRef.current = turnId;
      sendMessage({
        action: 'campus_navigation_tts',
        language,
        text: cleanSummary,
        turn_id: turnId,
      });
    },
    [isTrusteesStage, language, sendMessage],
  );

  const openCampusNavigation = useCallback(() => {
    onChatUserActivity?.();
    stopListening();
    clearSuggestionLayer();
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
      setIsPlayingBackendAudio(false);
    }
    engageCardUiLock(lastPayloadTurnIdRef.current ?? 'ui-local');
    const latestVisibleClara = [...displayMessages]
      .reverse()
      .find((m) => isTextMessage(m) && m.role === 'clara' && !(m as any).isHidden && !(m as any).isCardData) as ChatMessage | undefined;
    const latestUser = [...displayMessages]
      .reverse()
      .find((m) => isTextMessage(m) && m.role === 'user') as ChatMessage | undefined;
    savedChatFocusRef.current =
      visuallyFocusedMessage ??
      latestVisibleClara ??
      (latestUser && isTextMessage(latestUser)
        ? {
            id: 'campus-return-last-question',
            role: 'clara',
            text: latestUser.text,
          }
        : null);
    clearCardStages();
    setSurface('chat');
    comparisonLayoutSnapRef.current = null;
    setIsCampusNavigationStage(true);
    setSelectedCampusIndex(0);
    setHasCampusRoomSelection(false);
    setCampusRouteMode('default');
    setCampusRouteResult(null);
    setCampusDirectionOverride(null);
    setLayoutMode('SPLIT_CARDS');
  }, [
    clearCardStages,
    clearSuggestionLayer,
    displayMessages,
    onChatUserActivity,
    setLayoutMode,
    stopListening,
    visuallyFocusedMessage,
  ]);

  const returnToChatFromCampus = useCallback(() => {
    stopCampusSpeech();
    clearSuggestionLayer();
    setIsCampusNavigationStage(false);
    currentUiLockRef.current = 'IDLE';
    setCampusRouteMode('default');
    setCampusRouteResult(null);
    setCampusDirectionOverride(null);
    setLayoutMode('FULL_TEXT');
    setVisuallyFocusedMessage(savedChatFocusRef.current);
  }, [clearSuggestionLayer, setLayoutMode, stopCampusSpeech]);

  // Sync Card Progression with Backend Audio Duration
  const handleAudioPlayback = useCallback(
    (
      audioBase64: string,
      segmentKey: string,
      isOverview: boolean,
      cardsToSync: any[] | null,
      _turnId?: string,
      audioChainFollowUp?: boolean,
      totalDurationEstimateMs?: number | null,
      clipMeta?: {
        channel?: 'ack' | 'response';
        sequence?: number;
        watchdogMs?: number;
        chunkIndex?: number | null;
        sectionId?: string | null;
        segmentId?: string | null;
        unitId?: string | null;
      },
    ) => {
    const playbackChannel =
      clipMeta?.channel === 'ack' ? 'ack' : clipMeta?.channel === 'response' ? 'response' : 'legacy';
    const responseTid = String(_turnId || '');
    if (
      playbackChannel !== 'ack' &&
      (shouldBlockResponsePlayback(thinkingGateRef.current) ||
        thinkingPlayerRef.current?.playing() === true)
    ) {
      if (
        !responseTid ||
        thinkingGateRef.current.turnId === responseTid ||
        thinkingGateRef.current.turnId?.startsWith('pending:')
      ) {
        return;
      }
    }
    // Dedupe by a per-segment key (not just per-turn), because the backend can stream
    // multiple TTS segments for the same `turn_id` (ack + first sentence + remainder).
    if (playedSegmentKeysRef.current.has(segmentKey)) return;
    if (!audioBase64) return;

    if (playbackChannel === 'ack') {
      const thinkingBusy =
        thinkingPlayerRef.current?.playing() === true ||
        (thinkingGateRef.current.ttsPlaying &&
          !thinkingGateRef.current.ttsFinished &&
          !thinkingGateRef.current.ttsFailed);
      if (thinkingBusy) return;
      ackPlayerRef.current.play(audioBase64);
      return;
    }

    if (playbackChannel === 'response') {
      // Stop ACK only — never interrupt thinking TTS; gate already ensures thinking finished.
      ackPlayerRef.current.stop();
    }

    if (responseTid && canStartResponsePlayback(thinkingGateRef.current, responseTid)) {
      const started = markResponseStarted(thinkingGateRef.current, responseTid);
      thinkingGateRef.current = started;
      setThinkingGate(started);
    }

    const tid = typeof _turnId === 'string' ? _turnId : '';
    if (assistantAudioTurnOwnerRef.current === TURN_FENCE_PENDING) {
      if (shouldIgnorePayloadTurn(TURN_FENCE_PENDING, tid, previousAudioTurnOwnerRef.current)) {
        return;
      }
      if (tid) {
        assistantAudioTurnOwnerRef.current = tid;
      }
    }
    const skipTurnOwnerGuard =
      !tid ||
      tid.startsWith('campus-') ||
      tid.startsWith('greeting') ||
      tid.includes('language_gate') ||
      tid.includes('name_after') ||
      tid.includes('ready_after');
    if (
      !skipTurnOwnerGuard &&
      assistantAudioTurnOwnerRef.current &&
      tid !== assistantAudioTurnOwnerRef.current
    ) {
      return;
    }
    if (audioLockRef.current && currentAudioRef.current && !currentAudioRef.current.paused) {
      if (playbackChannel === 'response') {
        try {
          currentAudioRef.current.pause();
        } catch {
          // ignore
        }
        currentAudioRef.current = null;
        audioLockRef.current = false;
      } else if (audioChainFollowUp) {
        const exists = ttsStreamQueueRef.current.some((c) => c.segmentKey === segmentKey);
        if (!exists) {
          ttsStreamQueueRef.current.splice(ttsPlayheadRef.current + 1, 0, {
            audioBase64,
            segmentKey,
            isOverview,
            cardsToSync,
            turnId: tid,
            totalDurationEstimateMs,
            chunkIndex: clipMeta?.chunkIndex ?? null,
            sectionId: clipMeta?.sectionId ?? null,
            segmentId: clipMeta?.segmentId ?? null,
            unitId: clipMeta?.unitId ?? null,
          });
        }
        return;
      } else {
        return;
      }
    }

    playedSegmentKeysRef.current.add(segmentKey);

    if (!audioChainFollowUp) {
      presentationRef.current.audioManager.current?.invalidate();
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
        currentAudioRef.current = null;
      }
    } else if (currentAudioRef.current) {
      presentationRef.current.audioManager.current?.invalidate();
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }

    const audio = new Audio(`data:audio/wav;base64,${audioBase64}`);
    audio.dataset.claraChannel = playbackChannel;
    if (tid) audio.dataset.turnId = tid;
    currentAudioRef.current = audio;
    audioLockRef.current = true;
    setIsPlayingBackendAudio(true);

    // Narration-plan sync: prefer unitId on the clip (never live payload index as content identity).
    const plan = narrationPlanRef.current;
    if (plan && plan.turnId === tid) {
      presentationRef.current.setSceneAdvanceMode('per_clip');
      const incomingUnitIds = unitIdsFromSegments(plan.segments);
      const loadedIds = (presentationRef.current.snapshot.scenes || [])
        .map((s) => (typeof s.unitId === 'string' ? s.unitId.trim() : ''))
        .filter(Boolean);
      if (
        shouldLoadUnitPlan({
          incomingTurnId: tid,
          lastLoadedTurnId: lastLoadedPresentationTurnRef.current,
          incomingUnitIds,
          loadedSceneUnitIds: loadedIds,
        })
      ) {
        const ctrl = presentationRef.current;
        ctrl.loadPresentation({
          kind: 'plan',
          plan: {
            turnId: tid,
            mode: 'card_narration',
            segments: plan.segments,
          },
          estimatedTotalDurationMs: finitePositiveMs(totalDurationEstimateMs),
        });
        ctrl.play();
        lastLoadedPresentationTurnRef.current = tid;
      }
      const chunkIdx =
        typeof clipMeta?.chunkIndex === 'number' && Number.isFinite(clipMeta.chunkIndex)
          ? Math.max(0, Math.floor(clipMeta.chunkIndex))
          : null;
      let unitId =
        typeof clipMeta?.unitId === 'string' && clipMeta.unitId.trim()
          ? clipMeta.unitId.trim()
          : null;
      let sectionId =
        typeof clipMeta?.sectionId === 'string' && clipMeta.sectionId.trim()
          ? clipMeta.sectionId.trim()
          : null;
      let seg =
        typeof chunkIdx === 'number' && plan.segments[chunkIdx]
          ? plan.segments[chunkIdx]
          : null;
      if (!unitId && seg && typeof seg.unitId === 'string' && seg.unitId.trim()) {
        unitId = seg.unitId.trim();
      }
      if (!sectionId && seg) {
        sectionId =
          typeof seg.sectionId === 'string' && seg.sectionId.trim()
            ? seg.sectionId.trim()
            : null;
      }
      if (!seg && unitId) {
        const foundIdx = plan.segments.findIndex(
          (s) => typeof s.unitId === 'string' && s.unitId.trim() === unitId,
        );
        if (foundIdx >= 0) {
          seg = plan.segments[foundIdx]!;
        }
      }
      if (!seg && sectionId) {
        const foundIdx = plan.segments.findIndex(
          (s) => typeof s.sectionId === 'string' && s.sectionId.trim() === sectionId,
        );
        if (foundIdx >= 0) {
          seg = plan.segments[foundIdx]!;
        }
      }
      if (seg && typeof chunkIdx === 'number') {
        applyComparisonNarrationSegment(seg, chunkIdx);
      } else if (unitId) {
        const pid = presentationRef.current.snapshot.presentationId;
        if (
          !pid ||
          assertLivePresentationOwnership({
            snapshotPresentationId: pid,
            loadedTurnId: lastLoadedPresentationTurnRef.current,
          })
        ) {
          presentationRef.current.activateByUnitId(unitId);
        }
      } else if (sectionId) {
        const pid = presentationRef.current.snapshot.presentationId;
        if (
          !pid ||
          assertLivePresentationOwnership({
            snapshotPresentationId: pid,
            loadedTurnId: lastLoadedPresentationTurnRef.current,
          })
        ) {
          presentationRef.current.activateBySectionId(sectionId);
        }
      } else if (typeof chunkIdx === 'number' && plan.segments[chunkIdx]) {
        applyComparisonNarrationSegment(plan.segments[chunkIdx]!, chunkIdx);
      }
    } else if (
      // A unit-backed plan owns the whole turn, even when a late/stale audio
      // clip has a different turn id. Never let that clip install a legacy
      // card scene without unit identity over the canonical plan.
      unitIdsFromSegments(plan?.segments).length === 0 &&
      isOverview &&
      cardsToSync &&
      cardsToSync.length > 0
    ) {
      // Fallback multi-card path only when this turn has no unit-backed plan.
      const planUnits = unitIdsFromSegments(narrationPlanRef.current?.segments);
      const ctrl = presentationRef.current;
      if (
        shouldAllowLegacySingle(planUnits) &&
        (ctrl.engineState === 'IDLE' ||
          ctrl.engineState === 'CANCELLED' ||
          ctrl.engineState === 'PRESENTATION_COMPLETE' ||
          !ctrl.isPresenting)
      ) {
        const streaming =
          latestPayloadRef.current?.tts_streaming === true;
        ctrl.setSceneAdvanceMode(
          audioChainFollowUp || streaming ? 'per_clip' : 'shared_clip',
        );
        ctrl.loadPresentation({
          kind: 'cards',
          cards: cardsToSync,
          turnId: tid || `turn-${Date.now()}`,
          estimatedTotalDurationMs: finitePositiveMs(totalDurationEstimateMs),
        });
        ctrl.play();
        lastLoadedPresentationTurnRef.current = tid || lastLoadedPresentationTurnRef.current;
      }
    } else if (
      unitIdsFromSegments(plan?.segments).length === 0 &&
      currentUiLockRef.current === 'CARD' &&
      (presentationRef.current.engineState === 'IDLE' ||
        presentationRef.current.engineState === 'CANCELLED' ||
        presentationRef.current.engineState === 'PRESENTATION_COMPLETE')
    ) {
      const planUnits = unitIdsFromSegments(narrationPlanRef.current?.segments);
      if (shouldAllowLegacySingle(planUnits)) {
        const ctrl = presentationRef.current;
        ctrl.setSceneAdvanceMode('per_clip');
        const singleTurn = tid || `card-${Date.now()}`;
        ctrl.loadPresentation({
          kind: 'single',
          turnId: singleTurn,
          cardId: 'stage',
          caption: '',
          spokenSummary: '',
        });
        ctrl.play();
        lastLoadedPresentationTurnRef.current = singleTurn;
      }
    }

    // Bind tokenized listeners — engine owns scene completion; ChatScreen still chains the queue.
    presentationRef.current.bindPlaybackAudio(audio);

    const liveFaceChannel = faceChannelRef.current;
    if (!audioChainFollowUp && liveFaceChannel?.enabled && tid) {
      const facePayload = latestPayloadRef.current;
      let text = payloadAssistantSpeechText(facePayload);
      const explicitTotalMs =
        finitePositiveMs(totalDurationEstimateMs) ??
        finitePositiveMs(facePayload?.tts_total_duration_estimate_ms);
      let sentences = processResponseSentences(text);
      let durationsMs = allocateSentenceDurations(sentences, explicitTotalMs);
      if (!sentences.length) {
        const fallbackMs =
          finitePositiveMs(explicitTotalMs) ??
          finitePositiveMs(facePayload?.tts_total_duration_estimate_ms);
        if (fallbackMs !== null && fallbackMs > 0) {
          sentences = ['Audio'];
          durationsMs = [fallbackMs];
        }
      }
      if (sentences.length && durationsMs.length === sentences.length) {
        liveFaceChannel.postSpeech({
          turnId: tid,
          sentences,
          durationsMs,
          emotion: inferEmotionFromPayload(facePayload),
          emotionHint: 'calm',
        });
      }
    }

    const preferredSyncDurationSeconds = () =>
      !audioChainFollowUp &&
      typeof totalDurationEstimateMs === 'number' &&
      Number.isFinite(totalDurationEstimateMs) &&
      totalDurationEstimateMs > 0
        ? totalDurationEstimateMs / 1000
        : audio.duration;

    audio.onloadedmetadata = () => {
      const syncDurationSeconds = preferredSyncDurationSeconds();
      setCurrentAudioDuration(syncDurationSeconds);
    };

    const startedGen = playbackGenRef.current;
    const responseSequence =
      playbackChannel === 'response' && typeof clipMeta?.sequence === 'number'
        ? clipMeta.sequence
        : null;
    if (responseSequence !== null) {
      responseTtsSchedulerRef.current.markPlaying(responseSequence);
    }
    const clearResponseWatchdog = () => {
      if (responseWatchdogTimerRef.current) {
        window.clearTimeout(responseWatchdogTimerRef.current);
        responseWatchdogTimerRef.current = null;
      }
    };
    const finishResponseClip = (source: 'response-ended' | 'response-error' | 'watchdog') => {
      clearResponseWatchdog();
      if (responseSequence !== null) {
        responseTtsSchedulerRef.current.completeClip(responseSequence, source);
      }
      setIsPlayingBackendAudio(false);
      audioLockRef.current = false;
      setIsCampusSpeaking(false);
      setHasGreeted(true);
      if (responseSequence !== null) {
        playQueuedClipRef.current(true);
      }
    };
    if (responseSequence !== null) {
      const watchdogMs = clipMeta?.watchdogMs ?? 8000;
      responseWatchdogTimerRef.current = window.setTimeout(() => {
        if (startedGen !== playbackGenRef.current) return;
        if (currentAudioRef.current !== audio) return;
        console.error('[CLARA_TTS] response playback watchdog', {
          turnId: tid,
          sequence: responseSequence,
          watchdogMs,
        });
        try {
          audio.pause();
        } catch {
          // ignore
        }
        finishResponseClip('watchdog');
      }, watchdogMs);
    }

    audio.onended = () => {
      if (startedGen !== playbackGenRef.current) return;
      if (currentAudioRef.current !== audio) return;
      if (responseSequence !== null) {
        finishResponseClip('response-ended');
        const next = responseTtsSchedulerRef.current.nextPlayable();
        if (!next) {
          pendingFinalBackupRef.current = null;
          faceChannelRef.current?.postIdle(tid);
        }
        if (!next && presentationRef.current.engineState === 'PRESENTATION_COMPLETE') {
          setNarrationCaption('');
        }
        return;
      }
      setIsPlayingBackendAudio(false);
      audioLockRef.current = false;
      setIsCampusSpeaking(false);
      setHasGreeted(true);
    };

    audio.play().catch(err => {
      if (startedGen !== playbackGenRef.current) return;
      audioLockRef.current = false;
      console.error('[CLARA_TTS] audio.play() failed', {
        turnId: tid,
        segmentKey,
        playbackGen: startedGen,
        owner: assistantAudioTurnOwnerRef.current,
        channel: playbackChannel,
        sequence: responseSequence,
        error: err instanceof Error ? err.message : String(err),
      });
      const eng = presentationRef.current.engine.current;
      const tok = presentationRef.current.audioManager.current?.token;
      const snap = eng?.snapshot();
      if (eng && tok && snap?.presentationId && snap.activeScene) {
        eng.onAudioEvent({
          type: 'blocked',
          presentationId: snap.presentationId,
          audioToken: tok,
          sceneId: snap.activeScene.sceneId,
        });
      }
      setIsPlayingBackendAudio(false);
      setIsCampusSpeaking(false);
      setHasGreeted(true);
      setShowUnmuteHint(true);
      if (responseSequence !== null) {
        finishResponseClip('response-error');
      }
    });
  }, [applyComparisonNarrationSegment]);

  useEffect(() => {
    handleAudioPlaybackRef.current = handleAudioPlayback;
  }, [handleAudioPlayback]);

  useEffect(() => {
    const completeFailedClip = (clip: (typeof ttsStreamQueueRef.current)[number]) => {
      const tid = clip.turnId;
      const unitId =
        typeof clip.unitId === 'string' && clip.unitId.trim() ? clip.unitId.trim() : null;
      const plan = narrationPlanRef.current;
      if (plan && plan.turnId === tid && unitId) {
        const ctrl = presentationRef.current;
        ctrl.setSceneAdvanceMode('per_clip');
        const pid = ctrl.snapshot.presentationId;
        if (
          !pid ||
          assertLivePresentationOwnership({
            snapshotPresentationId: pid,
            loadedTurnId: lastLoadedPresentationTurnRef.current,
          })
        ) {
          ctrl.activateByUnitId(unitId);
        }
        const engine = ctrl.engine.current;
        const snap = engine?.snapshot();
        const scene = snap?.activeScene;
        const presentationId = snap?.presentationId;
        if (engine && scene && presentationId) {
          const token = engine.beginAudioBind(presentationId, scene.sceneId);
          if (token) {
            engine.onAudioEvent({
              type: 'ended',
              presentationId,
              audioToken: token,
              sceneId: scene.sceneId,
            });
          }
        }
      }
      clip.status = 'COMPLETED';
      ttsPlayheadRef.current += 1;
      playQueuedClipRef.current(true);
    };

    const playQueuedClip = (followUp: boolean) => {
      if (
        shouldBlockResponsePlayback(thinkingGateRef.current) ||
        thinkingPlayerRef.current?.playing() === true
      ) {
        return;
      }
      const scheduler = responseTtsSchedulerRef.current;
      const next = scheduler.nextPlayable();
      if (!next) {
        pendingFinalBackupRef.current = null;
        return;
      }
      if (next.status === 'PLAYING') return;
      if (next.status === 'FAILED' || !next.audioBase64) {
        scheduler.completeClip(next.sequence, 'response-error');
        const tid = next.turnId;
        const unitId = next.unitId;
        const plan = narrationPlanRef.current;
        if (plan && plan.turnId === tid && unitId) {
          completeFailedClip({
            audioBase64: '',
            segmentKey: next.segmentKey,
            isOverview: next.isOverview,
            cardsToSync: next.cardsToSync,
            turnId: tid,
            chunkIndex: next.sequence,
            unitId,
            status: 'FAILED',
          });
          return;
        }
        playQueuedClip(true);
        return;
      }
      handleAudioPlaybackRef.current?.(
        next.audioBase64,
        next.segmentKey,
        next.isOverview,
        next.cardsToSync as any[] | null,
        next.turnId,
        followUp,
        next.totalDurationEstimateMs,
        {
          channel: 'response',
          sequence: next.sequence,
          watchdogMs: next.watchdogMs,
          chunkIndex: next.sequence,
          sectionId: next.sectionId,
          segmentId: next.segmentId,
          unitId: next.unitId,
        },
      );
    };
    playQueuedClipRef.current = playQueuedClip;
  });

  // The opening wake greeting includes a short English instruction to choose
  // a language; the picker remains available after that audio completes.

  // Sync from payload
  useEffect(() => {
    if (!payload) return;
    if (isPayloadStale?.(payload)) return;

    if (typeof payload?.guest_name === 'string' && payload.guest_name.trim()) {
      guestNameRef.current = payload.guest_name.trim();
    } else if (payload?.guest_name === null) {
      guestNameRef.current = null;
    }

    if (payload.isProcessing === true && typeof payload.turn_id === 'string' && payload.turn_id.length > 0) {
      const nextOwner = String(payload.turn_id);
      if (assistantAudioTurnOwnerRef.current !== nextOwner) {
        // Backend-mic path never runs interceptAndSendMessage; mirror turn reset here.
        resetTurnPresentationState({ resetLayout: true });
        assistantAudioTurnOwnerRef.current = nextOwner;
      }
      if (responseTtsSchedulerRef.current.turnId !== nextOwner) {
        responseTtsSchedulerRef.current.beginTurn(nextOwner);
      }
      if (payload.thinking_skip === true) {
        const tp = thinkingPlayerRef.current;
        if (tp && typeof tp.reset === 'function') tp.reset();
        else tp?.stop();
        const failed = markThinkingTtsFailed(thinkingGateRef.current, nextOwner);
        thinkingGateRef.current = failed;
        setThinkingGate(failed);
        bumpThinkingEpoch();
      } else if (thinkingGateRef.current.turnId?.startsWith('pending:')) {
        const rebound = rebindThinkingTurn(thinkingGateRef.current, nextOwner);
        thinkingGateRef.current = rebound;
        setThinkingGate(rebound);
        armThinkingWatchdog(nextOwner);
      } else if (thinkingGateRef.current.turnId !== nextOwner) {
        const lastUser = Array.isArray(payload?.messages)
          ? [...(payload.messages as any[])].reverse().find((m: any) => String(m?.role ?? '').toLowerCase() === 'user')
          : null;
        const query = typeof lastUser?.text === 'string' ? lastUser.text : '';
        const sentence = composeThinkingBridge({
          query,
          language,
          guestName: guestNameRef.current,
        }) || thinkingBridgeFallback(language);
        const started = beginThinkingTurn(thinkingGateRef.current, { turnId: nextOwner, sentence });
        thinkingGateRef.current = started;
        setThinkingGate(started);
        armThinkingWatchdog(nextOwner);
      }
    } else if (assistantAudioTurnOwnerRef.current === TURN_FENCE_PENDING) {
      const incomingTid = typeof payload.turn_id === 'string' ? payload.turn_id : '';
      const adopted = adoptTurnOwner(
        assistantAudioTurnOwnerRef.current,
        incomingTid,
        previousAudioTurnOwnerRef.current,
      );
      if (adopted && adopted !== TURN_FENCE_PENDING) {
        assistantAudioTurnOwnerRef.current = adopted;
        if (responseTtsSchedulerRef.current.turnId !== adopted) {
          responseTtsSchedulerRef.current.beginTurn(adopted);
        }
      }
    }

    const payloadTurnId = typeof payload.turn_id === 'string' ? payload.turn_id : '';
    if (shouldIgnorePayloadTurn(
      assistantAudioTurnOwnerRef.current,
      payloadTurnId,
      previousAudioTurnOwnerRef.current,
    )) {
      return;
    }

    // Helper to detect if the backend is sending us a fallback message ("Go to admissions block")
    const isFallbackMessage = (text: string) => {
      const t = text.toLowerCase();
      return t.includes('admission block') || 
             t.includes('admissions block') || 
             t.includes('एडमिशन ब्लॉक') || 
             t.includes('अडमिशन ब्लॉक') ||
             t.includes('सबसे सटीक जानकारी');
    };
    
    // M5.4: the backend response decision is the only card authority. The frontend
    // consumes showCard and narration_plan unitIds; it never infers a card from text.
    const nativeTrigger = payload?.showCard;
    const payloadMessageList = Array.isArray(payload?.messages) ? payload.messages : [];
    const isResponseReady =
      payload?.isProcessing !== true &&
      payload?.audioPending !== true &&
      payloadMessageList.length > 0;

    const lastUserForInference = [...payloadMessageList].reverse().find((m: any) => {
      const role = String(m?.role ?? '').toLowerCase();
      return role === 'user' && getPayloadMessageText(m).trim().length > 0;
    });
    const lastUserTextForInference = lastUserForInference
      ? getPayloadMessageText(lastUserForInference).trim()
      : '';
    const cardTrigger = normalizeCardTrigger(nativeTrigger);
    const unitModelsFromPayload = presentationCardsFromNarrationSegments(
      Array.isArray(payload?.narration_plan?.segments) ? payload.narration_plan.segments : [],
    );
    const useCollegeWidePlacements = shouldUseCollegeWidePlacementDeck(
      cardTrigger,
      unitModelsFromPayload,
    );

    const departmentIdFromPayload = typeof payload?.departmentId === 'string' ? payload.departmentId : null;
    const targetDepartment =
      payload?.targetDepartment ?? payload?.target_department ?? departmentIdFromPayload ?? null;

    
    // STICKY STATE: Only update if we have a fresh target, otherwise preserve existing for this turn
    if (targetDepartment && targetDepartment !== '') {
      setActiveTargetDepartment(targetDepartment);
      // Also sync back to activeDepartmentId if we are in an overview stage
      if (isDepartmentOverviewStage) {
        setActiveDepartmentId(targetDepartment);
      }
    }

    const menuOptionsFromPayload = Array.isArray(payload?.options)
      ? payload.options.filter((x: unknown) => typeof x === 'string')
      : [];
    const audioBase64 = payload?.audioBase64;
    const turnId = payload?.turn_id ?? 'greeting';
    lastPayloadTurnIdRef.current = String(turnId);
    const type = payload?.type ?? '';
    const utteranceKind = payload?.utterance_kind ?? '';
    if (type === 'assistant_ack_audio' || utteranceKind === 'ack_earcon') {
      // Never let ACK start after thinking audio has begun — it clips the bridge on some WebViews.
      const thinkingBusy =
        thinkingPlayerRef.current?.playing() === true ||
        (thinkingGateRef.current.ttsPlaying &&
          !thinkingGateRef.current.ttsFinished &&
          !thinkingGateRef.current.ttsFailed);
      if (thinkingBusy) {
        return;
      }
      if (typeof audioBase64 === 'string' && audioBase64.length > 0) {
        ackPlayerRef.current.play(audioBase64);
      }
      return;
    }

    if (typeof payload?.thinking_text === 'string' && payload.thinking_text.trim()) {
      const rebound = rebindThinkingTurn(thinkingGateRef.current, String(turnId));
      const withSentence = attachThinkingSentence(rebound, payload.thinking_text);
      thinkingGateRef.current = withSentence;
      setThinkingGate(withSentence);
    }

    const thinkingB64 =
      (typeof payload?.thinkingAudioBase64 === 'string' && payload.thinkingAudioBase64) ||
      (type === 'thinking_audio' && typeof audioBase64 === 'string' ? audioBase64 : '');
    if (thinkingB64 && String(turnId)) {
      const playKey = `${turnId}:once`;
      if (thinkingAudioPlayedRef.current !== playKey) {
        thinkingAudioPlayedRef.current = playKey;
        const spoken =
          (typeof payload?.thinking_text === 'string' && payload.thinking_text.trim()) ||
          thinkingGateRef.current.sentence ||
          '';
        scheduleThinkingAudio(thinkingB64, String(turnId), spoken);
      }
    }
    if (type === 'thinking_audio_failed' || payload?.thinking_audio_failed === true) {
      thinkingPlayerRef.current?.stop();
      const failed = markThinkingTtsFailed(thinkingGateRef.current, String(turnId));
      thinkingGateRef.current = failed;
      setThinkingGate(failed);
      bumpThinkingEpoch();
      playQueuedClipRef.current(false);
      if (type === 'thinking_audio_failed') return;
    }
    if (
      type === 'thinking_interlude' ||
      type === 'thinking_audio' ||
      utteranceKind === 'thinking_bridge'
    ) {
      if (shouldBlockResponsePlayback(thinkingGateRef.current)) {
        return;
      }
    }

    const blocking = shouldBlockResponsePlayback(thinkingGateRef.current);
    if (blocking) {
      const looksLikeAnswer =
        (Array.isArray(payload?.messages) && payload.messages.length > 0) ||
        Boolean(payload?.showCard) ||
        Boolean(payload?.narration_plan) ||
        Array.isArray(payload?.tts_clip_slots) ||
        payload?.audioPending === true ||
        (payload?.isProcessing === false && typeof audioBase64 === 'string' && audioBase64.length > 0);
      if (looksLikeAnswer) {
        heldResponsePayloadRef.current = payload;
      }
      return;
    }
    heldResponsePayloadRef.current = null;
    const segmentIndex = payload?.segment_index ?? 0;
    const isFinalSegment = payload?.is_final_segment ?? true;
    // Small signature so missing metadata cannot cause false collisions.
    const audioSig = `${audioBase64?.length ?? 0}:${audioBase64?.slice(0, 24) ?? ''}`;
    // Dedupe key intentionally ignores optional streaming metadata that can drift between retries.
    // Keeping this keyed to turn + actual audio bytes avoids duplicate playback for repeated frames.
    const segmentKey = [turnId, audioSig].join('|');
    if (typeof audioBase64 === 'string' && audioBase64.length > 0) {
      const estimatedDuration = estimateWavDurationSeconds(audioBase64);
      if (estimatedDuration) {
        setCurrentAudioDuration(estimatedDuration);
      }
    }

    const deferAssistantTtsToStream = shouldDeferAssistantTtsToStream(payload);
    const offerAssistantAudio = (opts: {
      audioBase64: string | undefined;
      segmentKey: string;
      turnId: string;
      isOverview: boolean;
      cardsToSync: any[] | null;
      targetLayout: 'FULL_TEXT' | 'SPLIT_CARDS';
    }) => {
      streamAudioLayoutRef.current = {
        isOverview: opts.isOverview,
        cardsToSync: opts.cardsToSync,
        targetLayout: opts.targetLayout,
        turnId: opts.turnId,
      };
      if (typeof opts.audioBase64 !== 'string' || opts.audioBase64.length === 0) {
        return;
      }
      if (!deferAssistantTtsToStream) {
        setPendingAudio({
          audioBase64: opts.audioBase64,
          segmentKey: opts.segmentKey,
          turnId: opts.turnId,
          isOverview: opts.isOverview,
          cardsToSync: opts.cardsToSync,
          targetLayout: opts.targetLayout,
        });
      }
    };

    if (type === 'campus_navigation_tts') {
      if (audioBase64) {
        offerAssistantAudio({
          audioBase64,
          segmentKey,
          turnId: turnId,
          isOverview: false,
          cardsToSync: null,
          targetLayout: isCampusNavigationStage ? 'SPLIT_CARDS' : 'FULL_TEXT',
        });
      } else {
        setIsCampusSpeaking(false);
        setIsPlayingBackendAudio(false);
      }
      return;
    }

    // If backend explicitly says it is not speaking and gives no audio, force-release local speaking flags.
    if (!audioBase64 && payload?.isSpeaking === false) {
      setIsCampusSpeaking(false);
      setIsPlayingBackendAudio(false);
    }
    if (payload?.audioUnavailable === true) {
      audioLockRef.current = false;
      setIsPlayingBackendAudio(false);
      setIsCampusSpeaking(false);
      setAudioPendingTimedOut(false);
    }

    const planTurnId =
      typeof payload?.narration_plan?.turnId === 'string' ? payload.narration_plan.turnId : String(turnId);
    const unitBackedPlanReady = shouldApplyUnitBackedPlan({
      activeTurnId: assistantAudioTurnOwnerRef.current,
      planTurnId,
      audioPending: payload?.audioPending === true,
      previousTurnId: previousAudioTurnOwnerRef.current,
    }) && isUnitBackedNarrationPlan(payload);

    // Defer split-card transitions until the turn has finalized messages,
    // except unit-backed HOD/overview identity which must apply even while audioPending.
    if (cardTrigger && cardTrigger !== 'documents' && !isResponseReady && !unitBackedPlanReady) {
      if (audioBase64) {
        offerAssistantAudio({
          audioBase64,
          segmentKey,
          turnId: turnId,
          isOverview: false,
          cardsToSync: null,
          targetLayout: 'FULL_TEXT',
        });
      }
      return;
    }

    if (cardTrigger === 'department_comparison' && isResponseReady) {
      engageCardUiLock(lastPayloadTurnIdRef.current ?? 'ui-local');
      if (comparisonLayoutSnapRef.current === null) {
        comparisonLayoutSnapRef.current = layoutMode;
      }
      const rawList = payload?.comparisonDepartments;
      const cmpIds = Array.isArray(rawList)
        ? (rawList as unknown[]).filter((x): x is string => typeof x === 'string')
        : [];
      // Backend is the only source of comparison identity. No local re-inference.
      setComparisonDeptIds(cmpIds);
      setComparisonHighlightId(
        typeof payload?.comparisonHighlightId === 'string' ? payload.comparisonHighlightId : null,
      );
      setComparisonRecommendFocus(
        typeof payload?.comparisonRecommendFocus === 'string'
          ? payload.comparisonRecommendFocus
          : null,
      );
      // Section + point are driven by PresentationEngine from narration_plan segments.
      setComparisonNarrationSection(0);
      setSurface('department_comparison');
      setBusRoutesHighlightQuery(null);
      setLayoutMode('FULL_TEXT');
      if (audioBase64) {
        offerAssistantAudio({
          audioBase64,
          segmentKey,
          turnId: turnId,
          isOverview: false,
          cardsToSync: null,
          targetLayout: 'FULL_TEXT',
        });
      }
      return;
    }

    if (cardTrigger === 'bus_routes' && isResponseReady) {
      const turnIdStr = String(turnId);
      if (busRoutesDismissedTurnIdRef.current !== turnIdStr) {
        engageCardUiLock(lastPayloadTurnIdRef.current ?? 'ui-local');
        comparisonLayoutSnapRef.current = null;
        setBusRoutesHighlightQuery(lastUserTextForInference);
        setBusRoutesMountKey((k) => k + 1);
        setSurface('bus_routes');
        setLayoutMode('FULL_TEXT');
        if (audioBase64) {
          setPendingAudio({
            audioBase64,
            segmentKey,
            turnId,
            isOverview: false,
            cardsToSync: null,
            targetLayout: 'FULL_TEXT',
          });
        }
        return;
      }
    }

    // Keep Bus routes fullscreen sticky while TTS trailing frames omit `showCard`.
    if (isBusRoutesSurface && currentUiLockRef.current === 'CARD' && cardTrigger !== 'bus_routes') {
      setLayoutMode('FULL_TEXT');
      if (audioBase64) {
        setPendingAudio({
          audioBase64,
          segmentKey,
          turnId,
          isOverview: false,
          cardsToSync: null,
          targetLayout: 'FULL_TEXT',
        });
      }
      return;
    }

    // Keep Fees card sticky for the active response stream (same turn only).
    // M5.2 fees often arrive as showCard=department_overview; sticky must not block a new turn.
    if (
      isFeesStage &&
      currentUiLockRef.current === 'CARD' &&
      cardTrigger !== 'department_fees' &&
      feesStickyTurnIdRef.current &&
      feesStickyTurnIdRef.current === String(turnId)
    ) {
      setLayoutMode('SPLIT_CARDS');
      if (audioBase64) {
        offerAssistantAudio({
          audioBase64,
          segmentKey,
          turnId: turnId,
          isOverview: false,
          cardsToSync: null,
          targetLayout: 'SPLIT_CARDS',
        });
      }
      return;
    }

    // Keep Principal / Vice Principal premium cards sticky across TTS chunks that omit `showCard`.
    if (
      executiveLeadershipKind &&
      currentUiLockRef.current === 'CARD' &&
      cardTrigger !== 'principal_profile' &&
      cardTrigger !== 'vice_principal_profile'
    ) {
      setLayoutMode('SPLIT_CARDS');
      if (audioBase64) {
        offerAssistantAudio({
          audioBase64,
          segmentKey,
          turnId: turnId,
          isOverview: false,
          cardsToSync: null,
          targetLayout: 'SPLIT_CARDS',
        });
      }
      return;
    }

    // Keep Trustees stage sticky — suppress any backend audio that arrives
    // during the slideshow.
    if (isTrusteesStage && currentUiLockRef.current === 'CARD') {
      setLayoutMode('SPLIT_CARDS');
      const isTrusteeNarrationTurn = String(turnId).startsWith('trustee-card-');
      // Block unrelated backend audio while trustees are active, but allow trustee summaries.
      if (!isTrusteeNarrationTurn) return;
    }

    // Trustees Premium Slideshow Integration.
    // Trigger comes from the backend surface or an explicit UI event only.
    if (cardTrigger === 'trustees' || type === 'TRUSTEES_UI') {
      engageCardUiLock(lastPayloadTurnIdRef.current ?? 'ui-local');
      setCourseMenuOptions([]);
      setIsDepartmentOverviewStage(false);
      setActiveDepartmentId(null);
      setIsInfoSlideStage(false);
      setInfoSlides([]);
      setInfoSlideChip('');
      setIsHodStage(false);
      setIsFeesStage(false);
      setActiveFeesDepartmentId(null);
      setIsDocumentsStage(false);
      setIsTrusteesStage(true);
      setLayoutMode('SPLIT_CARDS');
      lastTrusteeNarrationKeyRef.current = null;
      
      // Avoid stale non-trustee audio continuing when trustees UI takes over.
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
        currentAudioRef.current = null;
        setIsPlayingBackendAudio(false);
      }
      return;
    }

    if (cardTrigger === 'course_menu') {
      engageCardUiLock(lastPayloadTurnIdRef.current ?? 'ui-local');
      setLayoutMode('SPLIT_CARDS');
      setActiveCards(null);
      setCurrentCardIdx(0);
      setSuppressedTurnId(null);
      setActiveDepartmentId(null);
      setIsDepartmentOverviewStage(false);
      setIsInfoSlideStage(false);
      setInfoSlides([]);
      setInfoSlideChip('');
      setIsHodStage(false);
      setExecutiveLeadershipKind(null);
      setIsFeesStage(false);
      setActiveFeesDepartmentId(null);
      setIsDocumentsStage(false);
      setCourseMenuOptions(menuOptionsFromPayload.length ? menuOptionsFromPayload : DEFAULT_COURSE_MENU_OPTIONS);
      if (audioBase64) {
        offerAssistantAudio({
          audioBase64,
          segmentKey,
          turnId: turnId,
          isOverview: false,
          cardsToSync: null,
          targetLayout: 'SPLIT_CARDS',
        });
      }
      return;
    }

    if (
      (cardTrigger === 'admissions' || cardTrigger === 'college_overview') &&
      unitModelsFromPayload.length === 0
    ) {
      // Legacy payloads without canonical ContentUnits remain text-only. A
      // registered admissions/location unit must continue to the shared card queue.
      setCourseMenuOptions([]);
      setIsDepartmentOverviewStage(false);
      setActiveDepartmentId(null);
      setIsInfoSlideStage(false);
      setInfoSlides([]);
      setInfoSlideChip('');
      setIsHodStage(false);
      setExecutiveLeadershipKind(null);
      setIsFeesStage(false);
      setActiveFeesDepartmentId(null);
      setIsDocumentsStage(false);
      currentUiLockRef.current = 'TEXT';
      setLayoutMode('FULL_TEXT');
      if (audioBase64) {
        offerAssistantAudio({
          audioBase64,
          segmentKey,
          turnId: turnId,
          isOverview: false,
          cardsToSync: null,
          targetLayout: 'FULL_TEXT',
        });
      }
      return;
    }

    if (useCollegeWidePlacements) {
      engageCardUiLock(lastPayloadTurnIdRef.current ?? 'ui-local');
      setIsHodStage(false);
      setExecutiveLeadershipKind(null);
      setIsDepartmentOverviewStage(false);
      setActiveDepartmentId(null);
      setCourseMenuOptions([]);
      setIsFeesStage(false);
      setActiveFeesDepartmentId(null);
      setIsDocumentsStage(false);
      setIsInfoSlideStage(true);
      const chips = INFO_STAGE_CHIPS[language] ?? INFO_STAGE_CHIPS.English;
      setInfoSlideChip(chips.placements);
      const slides = buildPlacementCardsFromLocale(collegeData, language);
      setInfoSlides(slides);
      
      setLayoutMode('SPLIT_CARDS');
      setActiveCards(null);
      if (audioBase64) {
        offerAssistantAudio({
          audioBase64,
          segmentKey,
          turnId: turnId,
          isOverview: true,
          cardsToSync: slides.map(s => ({ title: s.title, content: s.content, type: 'dept' })),
          targetLayout: 'SPLIT_CARDS',
        });
      }
      return;
    }

    // Canonical ContentUnit plans must reach the shared unit-card branch below.
    // This legacy surface-only branch is only for payloads with no representable
    // department unit; consuming a real HOD plan here would discard repeated and
    // mixed card identities before queue/navigation setup.
    if (cardTrigger === 'hod' && unitModelsFromPayload.length === 0) {
      setIsFeesStage(false);
      setActiveFeesDepartmentId(null);
      setIsDocumentsStage(false);
      const targetDept = String(targetDepartment || '').trim();
      if (targetDept) {
        // Any department with a valid label — lock onto the HOD card stage.
        // LeadershipOverview will pick the correct component from its COMPONENT_MAP.
        setIsInfoSlideStage(false);
        setInfoSlides([]);
        setInfoSlideChip('');
        setIsDepartmentOverviewStage(false);
        setActiveDepartmentId(null);
        setCourseMenuOptions([]);

        engageCardUiLock(lastPayloadTurnIdRef.current ?? 'ui-local');
        setExecutiveLeadershipKind(null);
        setIsHodStage(true);
        // Unit-backed HOD may contain multiple departments (e.g. CSE + AIML).
        const planUnits: string[] =
          Array.isArray(payload?.narration_plan?.segments)
            ? payload!.narration_plan!.segments
                .map((s: any) => (typeof s?.unitId === 'string' ? s.unitId : null))
                .filter((x: any) => typeof x === 'string' && x.trim())
            : [];
        const hodUnits = planUnits.filter((u) => u.endsWith('.hod'));
        const hodDepts = hodUnits.map((u) => departmentIdFromUnitId(u)).filter(Boolean);
        setActiveHodDepartments(hodDepts.length ? hodDepts : [targetDept]);
        setActiveTargetDepartment(hodDepts.length ? hodDepts[0]! : targetDept);
        setLayoutMode('SPLIT_CARDS');
      } else if (currentUiLockRef.current !== 'CARD') {
        // No department resolved — only go to text if we haven't already locked a card
        setLayoutMode('FULL_TEXT');
      }
      return;
    }

    if (cardTrigger === 'principal_profile') {
      engageCardUiLock(lastPayloadTurnIdRef.current ?? 'ui-local');
      setIsFeesStage(false);
      setActiveFeesDepartmentId(null);
      setIsDocumentsStage(false);
      setIsInfoSlideStage(false);
      setInfoSlides([]);
      setInfoSlideChip('');
      setIsDepartmentOverviewStage(false);
      setActiveDepartmentId(null);
      setCourseMenuOptions([]);
      setIsHodStage(false);
      setExecutiveLeadershipKind('principal');
      setLayoutMode('SPLIT_CARDS');
      setActiveCards(null);
      if (audioBase64) {
        offerAssistantAudio({
          audioBase64,
          segmentKey,
          turnId: turnId,
          isOverview: false,
          cardsToSync: null,
          targetLayout: 'SPLIT_CARDS',
        });
      }
      return;
    }

    if (cardTrigger === 'vice_principal_profile') {
      engageCardUiLock(lastPayloadTurnIdRef.current ?? 'ui-local');
      setIsFeesStage(false);
      setActiveFeesDepartmentId(null);
      setIsDocumentsStage(false);
      setIsInfoSlideStage(false);
      setInfoSlides([]);
      setInfoSlideChip('');
      setIsDepartmentOverviewStage(false);
      setActiveDepartmentId(null);
      setCourseMenuOptions([]);
      setIsHodStage(false);
      setExecutiveLeadershipKind('vice_principal');
      setLayoutMode('SPLIT_CARDS');
      setActiveCards(null);
      if (audioBase64) {
        offerAssistantAudio({
          audioBase64,
          segmentKey,
          turnId: turnId,
          isOverview: false,
          cardsToSync: null,
          targetLayout: 'SPLIT_CARDS',
        });
      }
      return;
    }

    if (useCollegeWidePlacements) {
      setIsHodStage(false);
      setIsFeesStage(false);
      setExecutiveLeadershipKind(null);
      setActiveFeesDepartmentId(null);
      setIsDocumentsStage(false);
      setCourseMenuOptions([]);
      setIsDepartmentOverviewStage(false);
      setActiveDepartmentId(null);
      setIsInfoSlideStage(true);
      const chips = INFO_STAGE_CHIPS[language] ?? INFO_STAGE_CHIPS.English;
      setInfoSlideChip(chips.placements);
      const slides = buildPlacementCardsFromLocale(collegeData, language);
      setInfoSlides(slides);
      const lastAssistantInPayload = [...payloadMessageList]
        .reverse()
        .find((m: any) => m?.role === 'clara' && typeof m?.id === 'string');
      const assistantMessageId = lastAssistantInPayload?.id ?? null;
      setLayoutMode('SPLIT_CARDS');
      setActiveCards(null);
      setSuppressedTurnId(assistantMessageId ?? turnId);
      if (audioBase64) {
        const syncCards: CardDataItem[] = slides.map((s) => ({
          title: s.title,
          content: s.content,
          type: 'dept',
        }));
        offerAssistantAudio({
          audioBase64,
          segmentKey,
          turnId: turnId,
          isOverview: true,
          cardsToSync: syncCards,
          targetLayout: 'SPLIT_CARDS',
        });
      }
      return;
    }

    if (cardTrigger === 'department_overview' || unitModelsFromPayload.length > 0) {
      // UnitSelector is the sole composition authority. The unitIds on narration_plan
      // decide how many cards exist, in which order, and for which department.
      engageCardUiLock(lastPayloadTurnIdRef.current ?? 'ui-local');
      setIsInfoSlideStage(false);
      setInfoSlides([]);
      setInfoSlideChip('');
      setIsHodStage(false);
      setExecutiveLeadershipKind(null);
      setIsFeesStage(false);
      setIsTrusteesStage(false);
      setActiveFeesDepartmentId(null);
      setIsDocumentsStage(false);
      setDepartmentOverviewDeckUnitIds(null);
      setActiveHodDepartments([]);
      feesStickyTurnIdRef.current = null;

      const targetRaw = String(targetDepartment || '');
      const targetAll = targetRaw.toLowerCase() === 'all';

      const lastAssistantInPayload = [...payloadMessageList]
        .reverse()
        .find((m: any) => m?.role === 'clara' && typeof m?.id === 'string');
      const assistantMessageId = lastAssistantInPayload?.id ?? null;
      setCourseMenuOptions([]);

      const models = presentationCardsFromNarrationSegments(
        Array.isArray(payload?.narration_plan?.segments)
          ? payload!.narration_plan!.segments
          : [],
      );
      setUnitBackedCards(models.length > 0 ? models : null);

      if (models.length > 0) {
        const allHod = models.every((m) => m.cardType === 'hod');
        const allFees = models.length === 1 && models[0]!.cardType === 'department_fees';
        const allPrincipal = models.every((m) => m.cardType === 'principal');
        const allVicePrincipal = models.every((m) => m.cardType === 'vice_principal');
        const allTrustees = models.every((m) => m.cardType === 'trustees');

        if (allFees) {
          const deptKey = models[0]!.departmentId;
          setIsFeesStage(true);
          setActiveFeesDepartmentId(deptKey);
          feesStickyTurnIdRef.current = String(turnId);
          setIsDepartmentOverviewStage(false);
          setActiveDepartmentId(null);
          setLayoutMode('SPLIT_CARDS');
          setSuppressedTurnId(turnId);
          offerAssistantAudio({
            audioBase64,
            segmentKey,
            turnId: turnId,
            isOverview: false,
            cardsToSync: null,
            targetLayout: 'SPLIT_CARDS',
          });
          return;
        }

        if (allHod) {
          const depts = models.map((m) => m.departmentId);
          setIsHodStage(true);
          setActiveHodDepartments(depts);
          setActiveTargetDepartment(depts[0] ?? null);
          setIsDepartmentOverviewStage(false);
          setActiveDepartmentId(null);
          setLayoutMode('SPLIT_CARDS');
          setSuppressedTurnId(turnId);
          offerAssistantAudio({
            audioBase64,
            segmentKey,
            turnId: turnId,
            isOverview: false,
            cardsToSync: null,
            targetLayout: 'SPLIT_CARDS',
          });
          return;
        }

        if (allPrincipal) {
          setExecutiveLeadershipKind('principal');
          setIsDepartmentOverviewStage(false);
          setActiveDepartmentId(null);
          setLayoutMode('SPLIT_CARDS');
          setActiveCards(null);
          setSuppressedTurnId(turnId);
          offerAssistantAudio({
            audioBase64,
            segmentKey,
            turnId: turnId,
            isOverview: false,
            cardsToSync: null,
            targetLayout: 'SPLIT_CARDS',
          });
          return;
        }

        if (allVicePrincipal) {
          setExecutiveLeadershipKind('vice_principal');
          setIsDepartmentOverviewStage(false);
          setActiveDepartmentId(null);
          setLayoutMode('SPLIT_CARDS');
          setActiveCards(null);
          setSuppressedTurnId(turnId);
          offerAssistantAudio({
            audioBase64,
            segmentKey,
            turnId: turnId,
            isOverview: false,
            cardsToSync: null,
            targetLayout: 'SPLIT_CARDS',
          });
          return;
        }

        if (allTrustees) {
          setIsTrusteesStage(true);
          setIsDepartmentOverviewStage(false);
          setActiveDepartmentId(null);
          setLayoutMode('SPLIT_CARDS');
          setActiveCards(null);
          setSuppressedTurnId(turnId);
          offerAssistantAudio({
            audioBase64,
            segmentKey,
            turnId: turnId,
            isOverview: false,
            cardsToSync: null,
            targetLayout: 'SPLIT_CARDS',
          });
          return;
        }

        const campusOnly = models.every((m) => CAMPUS_UNIT_CARD_TYPES.has(m.cardType));
        if (campusOnly) {
          setIsDepartmentOverviewStage(false);
          setActiveDepartmentId(null);
          setLayoutMode('SPLIT_CARDS');
          setActiveCards(null);
          setSuppressedTurnId(turnId);
          offerAssistantAudio({
            audioBase64,
            segmentKey,
            turnId: turnId,
            isOverview: false,
            cardsToSync: null,
            targetLayout: 'SPLIT_CARDS',
          });
          return;
        }

        // Overview / achievements / placements / mixed multi-unit: exactly models.length slides.
        // Each unit resolves against its OWN department, so cse_ds.overview +
        // cse_aiml.hod + cse.fees each render their real content.
        // A singleton `{dept}.placements` uses that department's placement unit, not
        // the college-wide placements_and_training deck.
        const slides = models.map((m) => {
          const slot = typeof m.slotIndex === 'number' ? m.slotIndex : 0;
          const fromLocale = buildDepartmentSlideForUnit(collegeData, m.unitId, presentationLanguage);
          return {
            title: fromLocale?.title || m.title,
            content: fromLocale?.content || m.content,
            slotIndex: slot,
          };
        });
        const isSingleDepartmentDeck = new Set(
          models.filter((m) => DEPARTMENT_UNIT_CARD_TYPES.has(m.cardType)).map((m) => m.departmentId),
        ).size === 1;
        const firstDept = models.find((m) => DEPARTMENT_UNIT_CARD_TYPES.has(m.cardType));
        setDepartmentOverviewDeckUnitIds(models.map((m) => m.unitId));
        setIsDepartmentOverviewStage(true);
        setActiveDepartmentId(
          isSingleDepartmentDeck && firstDept
            ? factoryDepartmentLabelFromJsonKey(firstDept.departmentId)
            : firstDept
              ? factoryDepartmentLabelFromJsonKey(firstDept.departmentId)
              : null,
        );
        setLayoutMode('SPLIT_CARDS');
        setActiveCards(null);
        setSuppressedTurnId(assistantMessageId ?? turnId);
        offerAssistantAudio({
          audioBase64,
          segmentKey,
          turnId: turnId,
          isOverview: true,
          cardsToSync: slides.map((s, i) => ({
            title: s.title,
            content: s.content,
            type: 'dept',
            unitId: models[i]?.unitId,
          })),
          targetLayout: 'SPLIT_CARDS',
        });
        return;
      }

      // No unitIds on the narration plan. Only an explicit all-departments deck or a
      // menu click may still render; a CARD turn without units renders no card.
      if (targetAll) {
        setIsDepartmentOverviewStage(false);
        setActiveDepartmentId(null);
        const allDeptCards = buildAllDepartmentSummaryCardsFromLocale(collegeData, language);
        setLayoutMode('SPLIT_CARDS');
        setActiveCards(allDeptCards);
        setSuppressedTurnId(assistantMessageId ?? turnId);
        if (audioBase64) {
          offerAssistantAudio({
            audioBase64,
            segmentKey,
            turnId: turnId,
            isOverview: true,
            cardsToSync: allDeptCards,
            targetLayout: 'SPLIT_CARDS',
          });
        }
        return;
      }

      // Fail closed: without unitIds, only an explicit menu click may open a deck.
      const clickedDept = uiClickDeckDepartmentRef.current;
      uiClickDeckDepartmentRef.current = null;
      if (!clickedDept) {
        return;
      }
      const resolvedDept = normalizeDepartmentMenuKey(clickedDept);
      if (!resolvedDept) {
        return;
      }
      const jsonKey = menuLabelToJsonKey(resolvedDept);
      if (!jsonKey) {
        return;
      }
      const deptRecord = getDepartmentRecord(collegeData, jsonKey);
      const slides = buildDepartmentSlidesFromRecord(deptRecord, jsonKey, language);
      const syncCards: CardDataItem[] = slides.map((s) => ({
        title: s.title,
        content: s.content,
        type: 'dept',
      }));

      setIsDepartmentOverviewStage(true);
      setActiveDepartmentId(resolvedDept);
      setLayoutMode('SPLIT_CARDS');
      setActiveCards(null);
      setSuppressedTurnId(assistantMessageId ?? turnId);
      if (audioBase64) {
        offerAssistantAudio({
          audioBase64,
          segmentKey,
          turnId: turnId,
          isOverview: true,
          cardsToSync: syncCards,
          targetLayout: 'SPLIT_CARDS',
        });
      }
      return;
    }

    if (cardTrigger === 'department_fees') {
      engageCardUiLock(lastPayloadTurnIdRef.current ?? 'ui-local');
      setCourseMenuOptions([]);
      setIsDepartmentOverviewStage(false);
      setActiveDepartmentId(null);
      setIsInfoSlideStage(false);
      setInfoSlides([]);
      setInfoSlideChip('');
      setIsHodStage(false);
      setExecutiveLeadershipKind(null);
      setIsDocumentsStage(false);
      setActiveCards(null);
      setSuppressedTurnId(null);
      const resolvedDept = normalizeDepartmentMenuKey(
        String(departmentIdFromPayload || targetDepartment || ''),
      );
      const feeDeptKey =
        menuLabelToJsonKey(resolvedDept ?? '') ??
        menuLabelToJsonKey(String(targetDepartment || '')) ??
        menuLabelToJsonKey(String(departmentIdFromPayload || '')) ??
        null;
      setIsFeesStage(true);
      setActiveFeesDepartmentId(feeDeptKey);
      feesStickyTurnIdRef.current = String(turnId);
      setLayoutMode('SPLIT_CARDS');

      if (audioBase64) {
        offerAssistantAudio({
          audioBase64,
          segmentKey,
          turnId: turnId,
          isOverview: false,
          cardsToSync: null,
          targetLayout: 'SPLIT_CARDS',
        });
      }
      return;
    }

    if (cardTrigger === 'documents') {
      engageCardUiLock(lastPayloadTurnIdRef.current ?? 'ui-local');
      setCourseMenuOptions([]);
      setIsDepartmentOverviewStage(false);
      setActiveDepartmentId(null);
      setIsInfoSlideStage(false);
      setInfoSlides([]);
      setInfoSlideChip('');
      setIsHodStage(false);
      setExecutiveLeadershipKind(null);
      setIsFeesStage(false);
      setActiveFeesDepartmentId(null);
      setIsDocumentsStage(true);
      setLayoutMode('SPLIT_CARDS');
      setActiveCards(null);
      setSuppressedTurnId(null);
      if (audioBase64) {
        offerAssistantAudio({
          audioBase64,
          segmentKey,
          turnId: turnId,
          isOverview: false,
          cardsToSync: null,
          targetLayout: 'SPLIT_CARDS',
        });
      }
      return;
    }

    const cardsForTrigger = resolveCardsFromTrigger(cardTrigger);

    if (cardsForTrigger) {
        engageCardUiLock(lastPayloadTurnIdRef.current ?? 'ui-local');
        setCourseMenuOptions([]);
        setActiveDepartmentId(null);
        setIsDepartmentOverviewStage(false);
        setIsInfoSlideStage(false);
        setInfoSlides([]);
        setInfoSlideChip('');
        setIsHodStage(false);
        setExecutiveLeadershipKind(null);
        setIsFeesStage(false);
        setActiveFeesDepartmentId(null);
        setIsDocumentsStage(false);
        const lastAssistantInPayload = [...payloadMessageList]
          .reverse()
          .find((m: any) => m?.role === 'clara' && typeof m?.id === 'string');
        const assistantMessageId = lastAssistantInPayload?.id ?? null;
        setLayoutMode('SPLIT_CARDS');
        setActiveCards(cardsForTrigger);
        setSuppressedTurnId(assistantMessageId ?? turnId);
        if (audioBase64) {
          offerAssistantAudio({
            audioBase64,
            segmentKey,
            turnId: turnId,
            isOverview: true,
            cardsToSync: cardsForTrigger,
            targetLayout: 'SPLIT_CARDS',
          });
        }
        return;
    }

    // FALLBACK / TEXT-ONLY RESPONSE
    // If a higher priority UI layout (CARD) is already locked, DO NOT override it with text.
    // TEXT-ONLY FALLBACK (NO CARD METADATA)
    // Check if we should block the 'FULL_TEXT' transition because this is a backend failure message
    const combinedContent = payloadMessageList.map((m: any) => m.content).join(' ');
    const isFallback = isFallbackMessage(combinedContent);

    const sameTurnCardLock =
      currentUiLockRef.current === 'CARD' &&
      cardLockTurnIdRef.current != null &&
      cardLockTurnIdRef.current === turnId;
    const sameTurnFeesSticky =
      isFallback &&
      activeTargetDepartment &&
      feesStickyTurnIdRef.current === turnId;

    if (sameTurnCardLock || sameTurnFeesSticky) {
        if (sameTurnFeesSticky) {
            // Backend failed, but we have a department. Stay in SPLIT_CARDS.
            setLayoutMode('SPLIT_CARDS'); 
        }
        if (audioBase64) {
          offerAssistantAudio({
            audioBase64,
            segmentKey,
            turnId: turnId,
            isOverview: false,
            cardsToSync: null,
            targetLayout: 'SPLIT_CARDS', // Play audio gracefully in background alongside locked card
          });
        }
        return; 
    }

    // Valid text progression since no higher priority rules are locked
    currentUiLockRef.current = 'TEXT';
    
    // Resetting behavior completely removed from backend completion chunk parsing (Rule 5)
    // We strictly use `interceptAndSendMessage` to reset on explicitly new inquiries!
    if (audioBase64) {
          offerAssistantAudio({
        audioBase64,
        segmentKey,
        turnId: turnId,
        isOverview: false,
        cardsToSync: null,
        targetLayout: 'FULL_TEXT',
      });
    }

  }, [
    payload,
    resolveCardsFromTrigger,
    collegeData,
    language,
    interceptAndSendMessage,
    isPayloadStale,
    isCampusNavigationStage,
    executiveLeadershipKind,
    isFeesStage,
    isDepartmentOverviewStage,
    isBusRoutesSurface,
    layoutMode,
    resetTurnPresentationState,
    activeTargetDepartment,
    thinkingEpoch,
    language,
    armThinkingWatchdog,
    bumpThinkingEpoch,
  ]);

  useEffect(() => {
    if (payload && isPayloadStale?.(payload)) return;

    let categories: FaqSuggestionCategory[] = GENERAL_FAQ_CATEGORIES;
    let turnId = 'general';

    if (payload?.type !== 'campus_navigation_tts' && payload?.type !== 'assistant_ack_audio' && payload?.type !== 'assistant_partial') {
      if (Array.isArray(payload?.messages)) {
        const latestAssistant = [...payload.messages]
          .reverse()
          .find(
            (message: any) =>
              message?.role === 'clara' &&
              typeof message?.text === 'string' &&
              !message?.isHidden &&
              !message?.isCardData,
          );
        const assistantText =
          latestAssistant?.text ??
          (typeof payload?.assistantText === 'string' ? payload.assistantText : '') ??
          '';
        turnId = String(payload?.turn_id || latestAssistant?.id || 'general');
        categories = inferFaqCategories(payload, assistantText);
      }
    }

    const nextSuggestions = selectFaqSuggestions(language, categories, lastSuggestionIdsRef.current);
    ensureSuggestions(nextSuggestions);
    if (turnId !== 'general') {
      lastSuggestionTurnIdRef.current = turnId;
      const ids = nextSuggestions.map((suggestion) => suggestion.id);
      lastSuggestionIdsRef.current = [...ids, ...lastSuggestionIdsRef.current]
        .filter((id, index, list) => list.indexOf(id) === index)
        .slice(0, 15);
    }
  }, [payload, language, isPayloadStale, ensureSuggestions]);

  useEffect(() => {
    if (
      departmentComparisonOpen ||
      isBusRoutesSurface ||
      faqSuggestions.length <= 1 ||
      isFaqCarouselPaused ||
      isBrochureOpen
    )
      return;
    const maxIndex = Math.max(0, faqSuggestions.length - 1);
    const timer = setInterval(() => {
      setFaqCarouselIndex((index) => (index >= maxIndex ? 0 : index + 1));
    }, FAQ_CAROUSEL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [
    departmentComparisonOpen,
    isBusRoutesSurface,
    faqSuggestions.length,
    isFaqCarouselPaused,
    isBrochureOpen,
  ]);

  useAnimationFrame((_time, delta) => {
    if (
      departmentComparisonOpen ||
      isBusRoutesSurface ||
      !faqSuggestions.length ||
      isFaqCarouselPaused ||
      isBrochureOpen ||
      isResponsePending ||
      isPlayingBackendAudio ||
      isCampusSpeaking ||
      (showLanguageOverlay && inlineLanguageGate && !languageGateSatisfied)
    ) {
      return;
    }
    const totalWidth = faqTickerLayout.totalTrackWidth;
    if (!totalWidth) return;
    const next = tickerX.get() - delta * FAQ_TICKER_SPEED_PX_PER_MS;
    tickerX.set(next <= -totalWidth ? next + totalWidth : next);
  });

  // Start queued audio only after its target layout is visible.
  useEffect(() => {
    if (!pendingAudio) return;
    if (shouldBlockResponsePlayback(thinkingGateRef.current)) return;
    if (layoutMode !== pendingAudio.targetLayout) return;
    const delayMs =
      pendingAudio.targetLayout === 'SPLIT_CARDS'
        ? CARD_AUDIO_START_DELAY_MS
        : FULL_TEXT_AUDIO_START_DELAY_MS;
    const timer = setTimeout(() => {
      if (
        deferredMessagesRef.current &&
        (!deferredTurnIdRef.current || deferredTurnIdRef.current === pendingAudio.turnId)
      ) {
        const committedMessages = deferredMessagesRef.current;
        setDisplayMessages(committedMessages);
        const latestAssistant = [...committedMessages]
          .reverse()
          .find((m: any) => m?.role === 'clara' && typeof m?.text === 'string' && !(m as any)?.isHidden && !(m as any)?.isCardData);
        setVisuallyFocusedMessage((latestAssistant as ChatMessage) ?? null);
        deferredMessagesRef.current = null;
        deferredTurnIdRef.current = null;
      }
      handleAudioPlayback(
        pendingAudio.audioBase64,
        pendingAudio.segmentKey,
        pendingAudio.isOverview,
        pendingAudio.cardsToSync,
        pendingAudio.turnId
      );
      setPendingAudio(current =>
        current?.segmentKey === pendingAudio.segmentKey ? null : current
      );
    }, delayMs);
    return () => clearTimeout(timer);
  }, [pendingAudio, layoutMode, handleAudioPlayback, thinkingEpoch]);

  // Progressive backend TTS: `tts_audio_queue` is merged in useWebSocket; drain clips sequentially.
  useEffect(() => {
    if (!payload || isPayloadStale?.(payload)) return;
    const tid = String(payload.turn_id ?? '');
    if (shouldIgnorePayloadTurn(
      assistantAudioTurnOwnerRef.current,
      tid,
      previousAudioTurnOwnerRef.current,
    )) {
      return;
    }
    let streamTurnReset = false;
    if (tid !== lastBackendTtsStreamTurnRef.current) {
      lastBackendTtsStreamTurnRef.current = tid;
      appliedBackendTtsQueueLenRef.current = 0;
      ttsStreamQueueRef.current = [];
      ttsPlayheadRef.current = 0;
      playbackGenRef.current += 1;
      presentationRef.current.audioManager.current?.invalidate();
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
        currentAudioRef.current = null;
      }
      audioLockRef.current = false;
      setIsPlayingBackendAudio(false);
      streamTurnReset = true;
      receivedTtsChunkIndicesRef.current.clear();
      firstTtsChunkSeenAtRef.current = null;
      if (ttsBufferTimerRef.current) {
        window.clearTimeout(ttsBufferTimerRef.current);
        ttsBufferTimerRef.current = null;
      }
      pendingFinalBackupRef.current = null;
    }
    const sched = responseTtsSchedulerRef.current;
    if (tid && sched.turnId !== tid) {
      sched.beginTurn(tid);
    }
    const streamChunkIndex =
      typeof payload.tts_chunk_index === 'number' && Number.isInteger(payload.tts_chunk_index)
        ? payload.tts_chunk_index
        : null;
    if (payload.tts_streaming === true && streamChunkIndex !== null) {
      const expected =
        typeof payload.tts_expected_clip_count === 'number' &&
        Number.isInteger(payload.tts_expected_clip_count)
          ? payload.tts_expected_clip_count
          : null;
      if (expected && expected > 0) {
        sched.setExpectedCount(expected);
      }
      const planSeg =
        narrationPlanRef.current?.turnId === tid
          ? narrationPlanRef.current.segments[streamChunkIndex]
          : payload?.narration_plan?.segments?.[streamChunkIndex];
      sched.ingestClip({
        turnId: tid,
        sequence: streamChunkIndex,
        audioBase64: typeof payload.audioBase64 === 'string' ? payload.audioBase64 : null,
        audioUnavailable: payload.audioUnavailable === true || !payload.audioBase64,
        unitId: (typeof planSeg?.unitId === 'string' && planSeg.unitId.trim()) || null,
        sectionId: planSeg?.sectionId ?? null,
        segmentId: planSeg?.segmentId ?? null,
        isOverview: Boolean(streamAudioLayoutRef.current?.isOverview) && streamChunkIndex === 0,
        cardsToSync: streamAudioLayoutRef.current?.cardsToSync ?? null,
      });
    }
    const unitBackedSlotsEarly =
      isUnitBackedNarrationPlan(payload) && Array.isArray(payload.tts_clip_slots);
    if (unitBackedSlotsEarly) {
      const slots = payload.tts_clip_slots as Array<{
        turnId?: string;
        unitId?: string | null;
        segmentIndex?: number;
        status?: TtsClipStatus;
        audioBase64?: string;
      }>;
      sched.setExpectedCount(slots.length);
      for (let idx = 0; idx < slots.length; idx += 1) {
        const slot = slots[idx];
        if (!slot || slot.status === 'PENDING') continue;
        const planSeg =
          narrationPlanRef.current?.turnId === tid
            ? narrationPlanRef.current.segments[idx]
            : undefined;
        sched.ingestClip({
          turnId: tid,
          sequence: typeof slot.segmentIndex === 'number' ? slot.segmentIndex : idx,
          audioBase64: slot.audioBase64,
          audioUnavailable: slot.status === 'FAILED' || !slot.audioBase64,
          unitId: slot.unitId || planSeg?.unitId || null,
          sectionId: planSeg?.sectionId ?? null,
          segmentId: planSeg?.segmentId ?? null,
          isOverview: Boolean(streamAudioLayoutRef.current?.isOverview) && idx === 0,
          cardsToSync: streamAudioLayoutRef.current?.cardsToSync ?? null,
        });
      }
    } else if (Array.isArray(payload.tts_audio_queue) && payload.tts_audio_queue.length > 0) {
      const q = payload.tts_audio_queue as string[];
      sched.setExpectedCount(q.length);
      q.forEach((b64, idx) => {
        if (typeof b64 !== 'string' || !b64.length) return;
        const planSeg =
          narrationPlanRef.current?.turnId === tid
            ? narrationPlanRef.current.segments[idx]
            : payload?.narration_plan?.segments?.[idx];
        sched.ingestClip({
          turnId: tid,
          sequence: idx,
          audioBase64: b64,
          unitId: (typeof planSeg?.unitId === 'string' && planSeg.unitId.trim()) || null,
          sectionId: planSeg?.sectionId ?? null,
          segmentId: planSeg?.segmentId ?? null,
        });
      });
    } else if (
      payload.type === 'assistant_audio_update' &&
      payload.tts_streaming !== true &&
      payload.audioPending !== true &&
      typeof payload.audioBase64 === 'string' &&
      payload.audioBase64.length > 0
    ) {
      sched.setExpectedCount(Math.max(1, sched.snapshot().clips.length));
      sched.ingestClip({
        turnId: tid,
        sequence: 0,
        audioBase64: payload.audioBase64,
      });
    }
    const schedSnap = sched.snapshot();
    if (schedSnap.clips.length > 0) {
      ttsStreamQueueRef.current = schedSnap.clips.map((c) => ({
        audioBase64: c.audioBase64,
        segmentKey: c.segmentKey,
        isOverview: c.isOverview,
        cardsToSync: c.cardsToSync,
        turnId: c.turnId,
        totalDurationEstimateMs: c.totalDurationEstimateMs,
        chunkIndex: c.sequence,
        sectionId: c.sectionId,
        segmentId: c.segmentId,
        unitId: c.unitId,
        status:
          c.status === 'FAILED'
            ? 'FAILED'
            : c.status === 'COMPLETED' || c.status === 'CANCELLED'
              ? 'COMPLETED'
              : c.status === 'PENDING'
                ? 'PENDING'
                : 'PLAYABLE',
      }));
      ttsPlayheadRef.current = schedSnap.playhead;
    }
    if (sched.snapshot().clips.length > 0) {
      const layout =
        streamAudioLayoutRef.current?.targetLayout ??
        (isUnitBackedNarrationPlan(payload) || payload.showCard ? 'SPLIT_CARDS' : 'FULL_TEXT');
      if (layoutMode !== layout) return;
      if (sched.phase === 'PLAYING') return;
      if (!sched.isPresentationReady()) return;
      const delayMs =
        layout === 'SPLIT_CARDS' ? CARD_AUDIO_START_DELAY_MS : FULL_TEXT_AUDIO_START_DELAY_MS;
      const timer = window.setTimeout(() => {
        playQueuedClipRef.current(false);
      }, delayMs);
      return () => window.clearTimeout(timer);
    }
    const chunkIndex =
      typeof payload.tts_chunk_index === 'number' && Number.isInteger(payload.tts_chunk_index)
        ? payload.tts_chunk_index
        : null;
    if (payload.tts_streaming === true && chunkIndex !== null) {
      receivedTtsChunkIndicesRef.current.add(chunkIndex);
    }
    const hasContiguousChunks = () => {
      const indices = [...receivedTtsChunkIndicesRef.current].sort((a, b) => a - b);
      if (indices.length === 0) return false;
      return indices.every((value, idx) => value === idx);
    };
    const unitBackedSlots = isUnitBackedNarrationPlan(payload) && Array.isArray(payload.tts_clip_slots);
    const finalBackupAudio =
      !unitBackedSlots &&
      payload.tts_streaming === false &&
      typeof payload.audioBase64 === 'string' &&
      payload.audioBase64.length > 0
        ? payload.audioBase64
        : null;
    if (finalBackupAudio) {
      const finalSig = `${finalBackupAudio.length}:${finalBackupAudio.slice(0, 24)}`;
      pendingFinalBackupRef.current = {
        audioBase64: finalBackupAudio,
        segmentKey: `${tid}|tts_final_backup|${finalSig}`,
        turnId: tid,
      };
      const queued = payload.tts_audio_queue;
      const unitBackedClipQueue =
        narrationPlanRef.current?.turnId === tid &&
        Array.isArray(narrationPlanRef.current.segments) &&
        narrationPlanRef.current.segments.some(
          (s) => typeof s.unitId === 'string' && s.unitId.trim(),
        ) &&
        Array.isArray(queued) &&
        queued.length > 0;
      // Unit-backed per_clip: keep the existing clip list. Do not replace it with a
      // single concatenated backup — that desyncs visual unitId from TTS identity.
      if (!hasContiguousChunks() && !unitBackedClipQueue) {
        const unitBackedPlan = isUnitBackedNarrationPlan(payload);
        if (unitBackedPlan && Array.isArray(queued) && queued.length === 0) {
          // Slot-backed final frames may arrive with an empty legacy queue.
          // Do not wipe a live clip list; wait for tts_clip_slots / a later queue.
        } else {
        ttsStreamQueueRef.current = [];
        ttsPlayheadRef.current = 0;
        appliedBackendTtsQueueLenRef.current = Array.isArray(payload.tts_audio_queue)
          ? payload.tts_audio_queue.length
          : appliedBackendTtsQueueLenRef.current;
        if (currentAudioRef.current) {
          currentAudioRef.current.pause();
          currentAudioRef.current = null;
        }
        audioLockRef.current = false;
        handleAudioPlaybackRef.current?.(
          finalBackupAudio,
          pendingFinalBackupRef.current.segmentKey,
          false,
          null,
          tid,
          false,
        );
        pendingFinalBackupRef.current = null;
        return;
        }
      }
    }
    if (unitBackedSlots) {
      const slots = payload.tts_clip_slots as Array<{
        turnId?: string;
        unitId?: string | null;
        segmentIndex?: number;
        status?: TtsClipStatus;
        audioBase64?: string;
      }>;
      const layout = streamAudioLayoutRef.current?.targetLayout ?? 'SPLIT_CARDS';
      if (layoutMode !== layout) return;
      let added = false;
      for (let idx = 0; idx < slots.length; idx += 1) {
        const slot = slots[idx];
        if (!slot || slot.status === 'PENDING') continue;
        const existing = ttsStreamQueueRef.current[idx];
        if (
          existing &&
          (existing.status === 'PLAYABLE' ||
            existing.status === 'FAILED' ||
            existing.status === 'COMPLETED' ||
            existing.status === 'CANCELLED')
        ) {
          continue;
        }
        const st = streamAudioLayoutRef.current;
        const isOv = Boolean(st?.isOverview) && idx === 0;
        const planSeg =
          narrationPlanRef.current?.turnId === tid
            ? narrationPlanRef.current.segments[idx]
            : undefined;
        const sectionId =
          typeof planSeg?.sectionId === 'string' && planSeg.sectionId.trim()
            ? planSeg.sectionId.trim()
            : typeof planSeg?.cardId === 'string' && planSeg.cardId.trim()
              ? planSeg.cardId.trim()
              : planSeg
                ? `seg_${idx}`
                : null;
        const segmentId =
          typeof planSeg?.segmentId === 'string' && planSeg.segmentId.trim()
            ? planSeg.segmentId.trim()
            : null;
        const unitId =
          (typeof slot.unitId === 'string' && slot.unitId.trim()
            ? slot.unitId.trim()
            : null) ||
          (typeof planSeg?.unitId === 'string' && planSeg.unitId.trim()
            ? planSeg.unitId.trim()
            : null);
        const b64 = typeof slot.audioBase64 === 'string' ? slot.audioBase64 : '';
        const segKey = `${tid}|tts_stream|${idx}|${slot.status}|${b64.length}:${b64.slice(0, 24)}`;
        while (ttsStreamQueueRef.current.length < idx) {
          const hole = ttsStreamQueueRef.current.length;
          ttsStreamQueueRef.current.push({
            audioBase64: '',
            segmentKey: `${tid}|tts_slot|${hole}`,
            isOverview: false,
            cardsToSync: null,
            turnId: tid,
            chunkIndex: hole,
            status: 'PENDING',
            unitId: null,
          });
        }
        const clip = {
          audioBase64: b64,
          segmentKey: segKey,
          isOverview: isOv,
          cardsToSync: isOv ? st?.cardsToSync ?? null : null,
          turnId: tid,
          chunkIndex: idx,
          sectionId,
          segmentId,
          unitId,
          status: slot.status === 'FAILED' ? 'FAILED' : 'PLAYABLE',
        } as (typeof ttsStreamQueueRef.current)[number];
        if (idx === ttsStreamQueueRef.current.length) {
          ttsStreamQueueRef.current.push(clip);
        } else {
          ttsStreamQueueRef.current[idx] = clip;
        }
        appliedBackendTtsQueueLenRef.current = Math.max(appliedBackendTtsQueueLenRef.current, idx + 1);
        added = true;
      }
      const head = ttsStreamQueueRef.current[ttsPlayheadRef.current];
      const needsStart =
        !isPlayingBackendAudio &&
        !currentAudioRef.current &&
        Boolean(head) &&
        head.status !== 'PENDING' &&
        head.status !== 'COMPLETED' &&
        head.status !== 'CANCELLED';
      if (!added && !needsStart) return;
      if (isPlayingBackendAudio && !streamTurnReset) return;
      if (firstTtsChunkSeenAtRef.current === null) {
        firstTtsChunkSeenAtRef.current = Date.now();
      }
      const bufferedEnough =
        ttsStreamQueueRef.current.filter((c) => c.status && c.status !== 'PENDING').length >= 1;
      if (!bufferedEnough) return;
      const delayMs =
        layout === 'SPLIT_CARDS' ? CARD_AUDIO_START_DELAY_MS : FULL_TEXT_AUDIO_START_DELAY_MS;
      const timer = window.setTimeout(() => {
        playQueuedClipRef.current(false);
      }, delayMs);
      return () => clearTimeout(timer);
    }
    const q = payload.tts_audio_queue;
    if (!Array.isArray(q) || q.length === 0) return;
    const layout = streamAudioLayoutRef.current?.targetLayout ?? 'FULL_TEXT';
    if (layoutMode !== layout) return;

    let added = false;
    while (appliedBackendTtsQueueLenRef.current < q.length) {
      const idx = appliedBackendTtsQueueLenRef.current;
      const b64 = q[idx];
      appliedBackendTtsQueueLenRef.current += 1;
      if (typeof b64 !== 'string' || !b64.length) continue;
      added = true;
      const st = streamAudioLayoutRef.current;
      const isOv = Boolean(st?.isOverview) && idx === 0;
      const totalDurationEstimateMs =
        idx === 0 &&
        typeof payload.tts_total_duration_estimate_ms === 'number' &&
        Number.isFinite(payload.tts_total_duration_estimate_ms)
          ? payload.tts_total_duration_estimate_ms
          : null;
      const segKey = `${tid}|tts_stream|${idx}|${b64.length}:${b64.slice(0, 24)}`;
      const planSeg = narrationPlanRef.current?.turnId === tid
        ? narrationPlanRef.current.segments[idx]
        : undefined;
      const sectionId =
        typeof planSeg?.sectionId === 'string' && planSeg.sectionId.trim()
          ? planSeg.sectionId.trim()
          : typeof planSeg?.cardId === 'string' && planSeg.cardId.trim()
            ? planSeg.cardId.trim()
            : planSeg
              ? `seg_${idx}`
              : null;
      const segmentId =
        typeof planSeg?.segmentId === 'string' && planSeg.segmentId.trim()
          ? planSeg.segmentId.trim()
          : null;
      const unitId =
        typeof planSeg?.unitId === 'string' && planSeg.unitId.trim()
          ? planSeg.unitId.trim()
          : null;
      ttsStreamQueueRef.current.push({
        audioBase64: b64,
        segmentKey: segKey,
        isOverview: isOv,
        cardsToSync: isOv ? st?.cardsToSync ?? null : null,
        turnId: tid,
        totalDurationEstimateMs,
        chunkIndex: idx,
        sectionId,
        segmentId,
        unitId,
        status: 'PLAYABLE',
      });
    }
    if (!added) return;
    if (isPlayingBackendAudio && !streamTurnReset) return;
    if (firstTtsChunkSeenAtRef.current === null) {
      firstTtsChunkSeenAtRef.current = Date.now();
    }
    const bufferedEnough =
      ttsStreamQueueRef.current.length >= 2 ||
      Date.now() - firstTtsChunkSeenAtRef.current >= 300 ||
      payload.tts_streaming === false;
    if (!bufferedEnough) {
      if (ttsBufferTimerRef.current) return;
      ttsBufferTimerRef.current = window.setTimeout(() => {
        ttsBufferTimerRef.current = null;
        const next = ttsStreamQueueRef.current[ttsPlayheadRef.current];
        if (!next || isPlayingBackendAudio) return;
        handleAudioPlaybackRef.current?.(
          next.audioBase64,
          next.segmentKey,
          next.isOverview,
          next.cardsToSync,
          next.turnId,
          false,
          next.totalDurationEstimateMs,
          {
            chunkIndex: next.chunkIndex,
            sectionId: next.sectionId,
            segmentId: next.segmentId,
            unitId: next.unitId,
          },
        );
      }, 300);
      return;
    }
    const delayMs =
      layout === 'SPLIT_CARDS' ? CARD_AUDIO_START_DELAY_MS : FULL_TEXT_AUDIO_START_DELAY_MS;
    const timer = window.setTimeout(() => {
      const next = ttsStreamQueueRef.current[ttsPlayheadRef.current];
      if (!next) return;
      handleAudioPlaybackRef.current?.(
        next.audioBase64,
        next.segmentKey,
        next.isOverview,
        next.cardsToSync,
        next.turnId,
        false,
        next.totalDurationEstimateMs,
        {
          chunkIndex: next.chunkIndex,
          sectionId: next.sectionId,
          segmentId: next.segmentId,
          unitId: next.unitId,
        },
      );
    }, delayMs);
    return () => clearTimeout(timer);
  }, [
    payload,
    isPayloadStale,
    layoutMode,
    isPlayingBackendAudio,
    handleAudioPlayback,
    thinkingEpoch,
  ]);

  useEffect(() => {
    if (!isCampusNavigationStage) {
      stopCampusSpeech();
      return;
    }
    const timer = window.setTimeout(() => {
      if (!hasCampusRoomSelection) {
        promptCampusRoomSelection();
      }
    }, 350);
    return () => window.clearTimeout(timer);
  }, [
    hasCampusRoomSelection,
    isCampusNavigationStage,
    selectedCampusIndex,
    language,
    promptCampusRoomSelection,
    stopCampusSpeech,
  ]);

  useEffect(() => {
    return () => stopCampusSpeech();
  }, [stopCampusSpeech]);

  useEffect(() => {
    return () => {
      stopTextReveal(false);
    };
  }, [stopTextReveal]);

  // Time-based reset UI behavior removed to enforce persistent screen state.

  // Orb State — with persistent 'completed' state for post-response guidance
  // "Tap to Speak" stays visible FOREVER until user taps orb or listening starts.
  useEffect(() => {
    // Detect speaking → finished transition
    const wasSpeaking = wasPlayingAudioRef.current;
    const audioPending = Boolean(payload?.audioPending);
    const backendSaysSpeaking = Boolean(propIsSpeaking) && !audioPending;
    wasPlayingAudioRef.current = isPlayingBackendAudio || backendSaysSpeaking;

    if (isPlayingBackendAudio || isCampusSpeaking || backendSaysSpeaking) {
      setOrbState('speaking');
    } else if (audioPending && !audioPendingTimedOut) {
      setOrbState('processing');
    } else if (isProcessing) {
      setOrbState('processing');
    } else if (speechListening || propIsListening || isPendingListeningRef.current) {
      // User started speaking, browser mic active, or explicitly tapped the orb
      setOrbState('listening');
    } else if (wasSpeaking && !isPlayingBackendAudio && !backendSaysSpeaking) {
      // CLARA just finished speaking → show 'completed' with "Tap to Speak"
      // This state persists indefinitely — NO auto-timeout.
      // Only cleared when: user taps orb OR listening begins.
      setOrbState('completed');
    } else if (orbState !== 'completed') {
      // Normal idle/ready — never override a persistent completed state
      if (hasGreeted && !showUnmuteHint) setOrbState('ready');
      else setOrbState('idle');
    }
  }, [
    speechListening,
    propIsListening,
    propIsSpeaking,
    payload?.audioPending,
    audioPendingTimedOut,
    isProcessing,
    isPlayingBackendAudio,
    isCampusSpeaking,
    hasGreeted,
    showUnmuteHint,
    orbState,
  ]);

  useEffect(() => {
    if (!payload?.audioPending) {
      setAudioPendingTimedOut(false);
      return;
    }
    const tid = typeof payload.turn_id === 'string' ? payload.turn_id : '';
    const gen = playbackGenRef.current;
    const started = Date.now();
    const timer = window.setTimeout(() => {
      if (playbackGenRef.current !== gen) return;
      audioLockRef.current = false;
      setIsPlayingBackendAudio(false);
      setIsCampusSpeaking(false);
      setAudioPendingTimedOut(true);
      console.error('[CLARA_TTS] audioPending watchdog recovered', {
        turnId: tid,
        elapsedMs: Date.now() - started,
        owner: assistantAudioTurnOwnerRef.current,
      });
    }, ANSWER_TTS_WATCHDOG_MS);
    return () => window.clearTimeout(timer);
  }, [payload?.audioPending, payload?.turn_id]);

  useEffect(() => {
    if (!hasStartedRef.current) {
      hasStartedRef.current = true;
      // K1: a visitor whose welcome already completed (e.g. accidental refresh
      // within the same visitor session) resumes instead of replaying the
      // welcome. A genuinely new visitor gets the full welcome flow.
      const resumed =
        Boolean(getVisitorLanguage()) &&
        isWelcomeCompleted() &&
        Boolean(getVisitorSessionId());
      const visitorId = getVisitorSessionId();
      sendMessage({
        action: 'conversation_started',
        ...(resumed ? { resumed: true } : {}),
        ...(visitorId ? { visitor_session_id: visitorId } : {}),
      });
    }
  }, [sendMessage]);

  // Clear optimistic listening state once real listening engages
  useEffect(() => {
    if (propIsListening) {
      isPendingListeningRef.current = false;
    }
  }, [propIsListening]);

  const handleOrbTap = () => {
    // #region agent log
    _agentDbg('A', 'ChatScreen.tsx:handleOrbTap', 'handleOrbTap_enter', {
      speechListening,
      pendingListen: isPendingListeningRef.current,
      propIsListening,
      voiceInputMode,
      audioPending: Boolean(payload?.audioPending),
      isProcessing,
    });
    // #endregion
    const browserListening = speechListening || isPendingListeningRef.current;
    const backendListening = voiceInputMode === 'backend' && propIsListening;
    const shouldStopMic = browserListening || backendListening;

    const interruptedTurnId = assistantAudioTurnOwnerRef.current;
    sendMessage({ action: 'cancel_turn' });
    faceChannel?.postInterrupt(interruptedTurnId);
    assistantAudioTurnOwnerRef.current = null;
    playedSegmentKeysRef.current.clear();
    playbackGenRef.current += 1;
    ttsStreamQueueRef.current = [];
    ttsPlayheadRef.current = 0;
    presentationRef.current.audioManager.current?.invalidate();

    clearSuggestionLayer();
    setIsFaqCarouselPaused(true);
    stopTextReveal(true);
    setPendingAudio(null);
    presentationRef.current.cancel();
    lastLoadedPresentationTurnRef.current = null;
    setNarrationCaption('');
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    stopListening();
    setIsPlayingBackendAudio(false);
    setIsCampusSpeaking(false);
    setShowUnmuteHint(false);
    setHasGreeted(true);
    isPendingListeningRef.current = false;

    if (shouldStopMic) {
      if (voiceInputMode === 'backend') {
        sendMessage({ action: 'mic_stop' });
      }
      setOrbState('idle');
      return;
    }
    
    // IMMEDIATE VISUAL FEEDBACK: Optimistically set listening state
    // so the UI feels instantly responsive. The effect above will clear
    // this when real listening engages or we timeout.
    isPendingListeningRef.current = true;
    setOrbState('listening');
    
    // Safety fallback: if mic fails to engage, drop optimistic state
    setTimeout(() => {
      isPendingListeningRef.current = false;
      // Force a re-render evaluating state; keep listening if browser speech recognition is active
      setOrbState(prev => prev === 'listening' && !propIsListening && !speechListening ? 'idle' : prev);
    }, 3000);

    if (voiceInputMode === 'backend') onOrbTap();
    else startSpeechRecognition();
  };

  const handleCardSelect = useCallback((idx: number) => {
    const ctrl = presentationRef.current;
    const plan = narrationPlanRef.current;
    const targetIdx = Math.max(0, Math.floor(idx));
    const targetUnitId = unitIdForCardIndex(plan?.segments, targetIdx);

    if (ctrl.isPresenting || ctrl.engineState === 'READY' || ctrl.engineState === 'SCENE_COMPLETE') {
      // MANUAL SEEK: visual unitId == playback unitId. Do not wipe the clip list.
      playbackGenRef.current += 1;
      presentationRef.current.audioManager.current?.invalidate();
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
        currentAudioRef.current = null;
      }
      audioLockRef.current = false;
      setIsPlayingBackendAudio(false);

      const clipIdx = findClipIndexForTarget(ttsStreamQueueRef.current, {
        unitId: targetUnitId,
        cardIndex: targetIdx,
      });
      if (clipIdx >= 0) {
        ttsPlayheadRef.current = clipIdx;
      } else {
        ttsPlayheadRef.current = targetIdx;
      }

      for (const key of segmentKeysFromPlayhead(ttsStreamQueueRef.current, ttsPlayheadRef.current)) {
        playedSegmentKeysRef.current.delete(key);
      }

      ctrl.jumpToCardIndex(targetIdx);
      if (targetUnitId) {
        ctrl.activateByUnitId(targetUnitId);
      }

      const next = ttsStreamQueueRef.current[ttsPlayheadRef.current];
      if (next) {
        handleAudioPlaybackRef.current?.(
          next.audioBase64,
          next.segmentKey,
          next.isOverview,
          next.cardsToSync,
          next.turnId,
          false,
          next.totalDurationEstimateMs,
          {
            channel: 'response',
            sequence: typeof next.chunkIndex === 'number' ? next.chunkIndex : ttsPlayheadRef.current,
            chunkIndex: next.chunkIndex,
            sectionId: next.sectionId,
            segmentId: next.segmentId,
            unitId: next.unitId ?? targetUnitId,
          },
        );
      }
      return;
    }

    setCurrentCardIdx(targetIdx);
  }, []);
  cardNavigationRef.current = handleCardSelect;

  const handleCourseMenuSelect = useCallback(
    (departmentName: string) => {
      clearSuggestionLayer();
      setCourseMenuOptions([]);

      // Keep the click as a canonical department request. The response payload
      // must own the presentation state so a menu click follows the same
      // ContentUnit → narration_plan → PresentationEngine path as voice/text.
      uiClickDeckDepartmentRef.current = departmentName;

      // The local intent preserves deterministic menu semantics while the
      // backend resolves the department into its canonical overview unit.
      interceptAndSendMessage({
        action: 'user_message',
        text: departmentName,
        localIntent: {
          type: 'department_click',
          departmentLabel: departmentName,
          requested_card: 'department_overview',
        },
      }, 'UI');
    },
    [clearSuggestionLayer, interceptAndSendMessage]
  );

  const filteredMessages = useMemo(() => {
    return displayMessages.filter(m => {
       const isHidden = (m as any).isHidden || (m as any).isCardData;
       return !isHidden && (m.id !== suppressedTurnId);
    });
  }, [displayMessages, suppressedTurnId]);
  const recentPanelMessages = useMemo(() => filteredMessages.slice(-4), [filteredMessages]);

  const latestTextAssistantMsg = useMemo((): TextMessage | null => {
    const found = [...filteredMessages]
      .reverse()
      .find((message): message is TextMessage => isTextMessage(message) && message.role === 'clara');
    return found ?? null;
  }, [filteredMessages]);
  const lastAssistantMsg: TextMessage | null =
    visuallyFocusedMessage &&
    isTextMessage(visuallyFocusedMessage) &&
    visuallyFocusedMessage.role === 'clara'
      ? visuallyFocusedMessage
      : latestTextAssistantMsg;
  const isLanguageGateOpen = inlineLanguageGate && !languageGateSatisfied;
  const shouldHideFaqSuggestions =
    isLanguageGateOpen || isResponsePending || departmentComparisonOpen || isBusRoutesSurface;
  const submitFaqSuggestion = useCallback(
    (_id: string, question: string) => {
      // #region agent log
      _agentDbg('B', 'ChatScreen.tsx:submitFaqSuggestion', 'faq_submit', {
        qLen: question.length,
        audioPending: Boolean(payload?.audioPending),
        isProcessing,
        propIsListening,
      });
      // #endregion
      stopListening();
      isPendingListeningRef.current = false;
      if (voiceInputMode === 'backend' && propIsListening) {
        sendMessage({ action: 'mic_stop' });
      }
      // Force orb out of any optimistic listening state before the new turn
      // begins so a stuck `processing` visual cannot be misread as the mic
      // being live. The orb effect will switch to `processing`/`speaking`
      // shortly after based on backend state.
      setOrbState('idle');
      clearSuggestionLayer();
      interceptAndSendMessage({ action: 'user_message', text: question }, 'VOICE');
    },
    [clearSuggestionLayer, interceptAndSendMessage, propIsListening, sendMessage, stopListening, voiceInputMode],
  );
  /** English greeting uses Didone-style stack from backend (`greetings.py` → `greetingFontFamily`). */
  const greetingFontStyle = useMemo((): React.CSSProperties | undefined => {
    if (payload && isPayloadStale?.(payload)) return undefined;
    const ff = payload?.greetingFontFamily;
    if (typeof ff !== 'string' || !ff.trim()) return undefined;
    return { fontFamily: ff };
  }, [payload, payload?.greetingFontFamily, isPayloadStale]);
  const fullTextGreetingStyle =
    lastAssistantMsg?.id === 'greeting' ? greetingFontStyle : undefined;
  const fullTextDisplayText =
    lastAssistantMsg && sentenceRevealTurnId === lastAssistantMsg.id
      ? sentenceRevealText
      : lastAssistantMsg?.text ?? '';
  const fullTextAnimate = true;

  const responseLayoutEnabled =
    layoutMode === 'FULL_TEXT' &&
    Boolean(fullTextDisplayText) &&
    !isResponsePending &&
    !isAwaitingReadyPrompt &&
    !(showLanguageOverlay && inlineLanguageGate && !languageGateSatisfied);

  const playbackClock = useAudioPlaybackClock(currentAudioRef, responseLayoutEnabled);

  const responseLayout = useResponseLayout({
    text: fullTextDisplayText,
    language,
    containerRef: fullTextScrollRef,
    enabled: responseLayoutEnabled,
    audioDurationSeconds: currentAudioDuration,
    externalPlaybackSync: true,
  });

  const pageGraphemeCounts = useMemo(
    () => responseLayout.pages.map((p) => Math.max(1, countGraphemes(p.replace(/\s+/g, '')))),
    [responseLayout.pages],
  );

  const pagedPlayback = useMemo(() => {
    const duration =
      playbackClock.duration > 0
        ? playbackClock.duration
        : currentAudioDuration > 0
          ? currentAudioDuration
          : 0;
    const t = playbackClock.currentTime;
    if (responseLayout.overflowMode !== 'paginated' || responseLayout.pages.length <= 1) {
      const progress =
        duration > 0 ? Math.min(1, Math.max(0, t / duration)) : playbackClock.progress;
      return { pageIndex: 0, localProgress: progress };
    }
    return resolvePagedPlayback(t, duration || 1, pageGraphemeCounts);
  }, [
    playbackClock.currentTime,
    playbackClock.duration,
    playbackClock.progress,
    currentAudioDuration,
    responseLayout.overflowMode,
    responseLayout.pages.length,
    pageGraphemeCounts,
  ]);

  useEffect(() => {
    if (!responseLayoutEnabled) return;
    if (responseLayout.overflowMode !== 'paginated' || responseLayout.pages.length <= 1) return;
    if (pagedPlayback.pageIndex !== responseLayout.activePageIndex) {
      responseLayout.setActivePageIndex(pagedPlayback.pageIndex);
    }
  }, [
    responseLayoutEnabled,
    responseLayout.overflowMode,
    responseLayout.pages.length,
    responseLayout.activePageIndex,
    responseLayout.setActivePageIndex,
    pagedPlayback.pageIndex,
  ]);

  const fullTextPageText =
    responseLayout.pages[responseLayout.activePageIndex] ?? fullTextDisplayText;

  const fullTextPageAudioDuration = useMemo(() => {
    if (responseLayout.overflowMode !== 'paginated' || responseLayout.pages.length <= 1) {
      return currentAudioDuration;
    }
    const totalGraphemes = Math.max(
      1,
      countGraphemes(fullTextDisplayText.replace(/\s+/g, '')),
    );
    const pageGraphemes = Math.max(
      1,
      countGraphemes(fullTextPageText.replace(/\s+/g, '')),
    );
    return currentAudioDuration * (pageGraphemes / totalGraphemes);
  }, [
    responseLayout.overflowMode,
    responseLayout.pages.length,
    fullTextDisplayText,
    fullTextPageText,
    currentAudioDuration,
  ]);

  const fullTextRevealProgress = useMemo(() => {
    // Prefer live playback; fall back to 1 when audio finished / unavailable so text remains readable.
    if (playbackClock.playing || playbackClock.progress > 0) {
      return pagedPlayback.localProgress;
    }
    if (currentAudioDuration <= 0 && fullTextDisplayText) {
      return 1;
    }
    return pagedPlayback.localProgress;
  }, [
    playbackClock.playing,
    playbackClock.progress,
    pagedPlayback.localProgress,
    currentAudioDuration,
    fullTextDisplayText,
  ]);

  const fullTextAnswerStyle = useMemo((): React.CSSProperties => {
    return {
      ...responseLayout.answerStyle,
      ...(fullTextGreetingStyle ?? {}),
    };
  }, [responseLayout.answerStyle, fullTextGreetingStyle]);

  const fullTextMessageClassName = `word-by-word-text full-text-readable ${scriptPreset.cssClass}`;

  useEffect(() => {
    if (!lastAssistantMsg || isAwaitingReadyPrompt || isResponsePending) return;
    if (payload && isPayloadStale?.(payload)) return;
    if (
      payload &&
      (payload.showCard ||
        payload.event === 'error' ||
        payload.errorCode ||
        (payload.type === 'assistant_audio_update' && payload.tts_streaming))
    ) {
      return;
    }

    const sourceText = payloadResponseText(payload, lastAssistantMsg.text);
    const processedSentences = processResponseSentences(sourceText);
    if (!processedSentences.length) return;

    const visibleText = processedSentences.join(' ');
    const revealKey = `${lastAssistantMsg.id}:${language}:${visibleText}`;
    if (sentenceRevealKeyRef.current === revealKey) return;

    sentenceRevealKeyRef.current = revealKey;
    sentenceRevealAbortRef.current += 1;
    setSentenceRevealTurnId(lastAssistantMsg.id);
    setSentenceRevealText(visibleText);
  }, [
    lastAssistantMsg?.id,
    lastAssistantMsg?.text,
    language,
    isAwaitingReadyPrompt,
    isResponsePending,
    payload,
    isPayloadStale,
  ]);

  const campusCopy = campusLabels(language);
  const selectedCampusDirection = useMemo(
    () => campusDirectionOverride ?? (CAMPUS_DIRECTIONS[selectedCampusIndex] ?? CAMPUS_DIRECTIONS[0])!,
    [campusDirectionOverride, selectedCampusIndex],
  );
  const campusDisplaySteps = useMemo(() => {
    if (campusRouteResult?.status === 'ok') {
      const flat = campusRouteResult.floor_segments.flatMap((s) => s.steps ?? []);
      if (flat.length) return flat;
    }
    return localizedCampusSteps(selectedCampusDirection, language);
  }, [campusRouteResult, selectedCampusDirection, language]);

  useEffect(() => {
    if (!isCampusNavigationStage || !hasCampusRoomSelection) {
      setCampusRouteResult(null);
      return;
    }
    const code = parseRoomCodeFromDestinationLabel(selectedCampusDirection.to);
    if (!code) {
      setCampusRouteResult(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      const res = await getCampusRouteApi({
        destination_room_code: code,
        mode: campusNavigationRouteModeToApi(campusRouteMode),
        // K1: propagate the canonical selected code instead of a hardcoded 'en'.
        language: languageToCode(language),
      });
      if (!cancelled) setCampusRouteResult(res);
    })();
    return () => {
      cancelled = true;
    };
  }, [
    campusRouteMode,
    hasCampusRoomSelection,
    isCampusNavigationStage,
    language,
    selectedCampusDirection.to,
  ]);

  const departmentSlides = useMemo(() => {
    if (!isDepartmentOverviewStage) return [];

    // Unit-backed selection wins: exact length, per-unit department identity.
    if (Array.isArray(unitBackedCards) && unitBackedCards.length > 0) {
      return unitBackedCards.map((m) => {
        const slot = typeof m.slotIndex === 'number' ? m.slotIndex : 0;
        const fromLocale = buildDepartmentSlideForUnit(collegeData, m.unitId, presentationLanguage);
        return {
          title: fromLocale?.title || m.title,
          content: fromLocale?.content || m.content,
          slotIndex: slot,
        };
      });
    }

    if (Array.isArray(departmentOverviewDeckUnitIds) && departmentOverviewDeckUnitIds.length > 0) {
      return departmentOverviewDeckUnitIds
        .map((unitId) => buildDepartmentSlideForUnit(collegeData, unitId, presentationLanguage))
        .filter((x): x is DepartmentStageSlide => Boolean(x));
    }

    // Menu-click deck: one department, full five slides.
    if (!activeDepartmentId) return [];
    const jk = menuLabelToJsonKey(activeDepartmentId);
    if (!jk) return [];
    return buildDepartmentSlidesFromRecord(getDepartmentRecord(collegeData, jk), jk, presentationLanguage);
  }, [
    isDepartmentOverviewStage,
    activeDepartmentId,
    departmentOverviewDeckUnitIds,
    unitBackedCards,
    collegeData,
    presentationLanguage,
  ]);

  const currentUnitCard = useMemo(() => {
    if (!Array.isArray(unitBackedCards) || unitBackedCards.length === 0) return null;
    const idx = Math.min(Math.max(0, currentCardIdx), unitBackedCards.length - 1);
    return unitBackedCards[idx] ?? null;
  }, [unitBackedCards, currentCardIdx]);

  const factoryDepartmentId = useMemo(() => {
    if (currentUnitCard && DEPARTMENT_UNIT_CARD_TYPES.has(currentUnitCard.cardType)) {
      return factoryDepartmentLabelFromJsonKey(currentUnitCard.departmentId);
    }
    return activeDepartmentId;
  }, [currentUnitCard, activeDepartmentId]);

  useEffect(() => {
    if (!isE2EFlow) return;
    window.__CLARA_M52_DEBUG = () => {
      const sched = responseTtsSchedulerRef.current.snapshot();
      const queue = ttsStreamQueueRef.current;
      const playhead = sched.clips.length > 0 ? sched.playhead : ttsPlayheadRef.current;
      const queuedUnit =
        typeof sched.clips[playhead]?.unitId === 'string' && sched.clips[playhead]!.unitId!.trim()
          ? sched.clips[playhead]!.unitId!.trim()
          : typeof queue[playhead]?.unitId === 'string' && queue[playhead]!.unitId!.trim()
            ? queue[playhead]!.unitId!.trim()
            : null;
      const engineUnit = presentation.snapshot.activeScene?.unitId ?? null;
      return {
        cardIndex: currentCardIdx,
        slideCount: departmentSlides.length,
        hodCount: activeHodDepartments.length,
        hodDepartments: [...activeHodDepartments],
        feesDepartmentId: activeFeesDepartmentId,
        isFeesStage,
        isHodStage,
        isDepartmentOverviewStage,
        isInfoSlideStage,
        unitIds: Array.isArray(unitBackedCards)
          ? unitBackedCards.map((m) => m.unitId)
          : departmentOverviewDeckUnitIds,
        cardIds: Array.isArray(unitBackedCards)
          ? unitBackedCards.map((m) => m.cardId)
          : null,
        unitCardContents: Array.isArray(unitBackedCards)
          ? unitBackedCards.map((m) => ({
              unitId: m.unitId,
              title: m.title,
              content: m.content,
            }))
          : [],
        visibleUnitId:
          Array.isArray(unitBackedCards) && unitBackedCards[currentCardIdx]
            ? unitBackedCards[currentCardIdx]!.unitId
            : queuedUnit ?? engineUnit,
        playhead,
        queueLength: sched.clips.length > 0 ? sched.clips.length : queue.length,
        queueUnitIds: (sched.clips.length > 0 ? sched.clips : queue).map((c) =>
          typeof c.unitId === 'string' && c.unitId.trim() ? c.unitId.trim() : null,
        ),
        clipStatuses: (sched.clips.length > 0 ? sched.clips : queue).map((c) =>
          'status' in c ? c.status ?? null : null,
        ),
      playbackUnitId: queuedUnit ?? engineUnit,
      engineUnitId: engineUnit,
      engineState: presentation.snapshot.engineState,
      playbackGen: playbackGenRef.current,
      hasCurrentAudio: Boolean(currentAudioRef.current),
    };
    };
    window.__CLARA_M52_END_CLIP = () => {
      const audio = currentAudioRef.current;
      if (!audio) return;
      audio.dispatchEvent(new Event('ended'));
    };
    return () => {
      delete window.__CLARA_M52_DEBUG;
      delete window.__CLARA_M52_END_CLIP;
    };
  });

  const renderFaqCarousel = (placement: 'full' | 'panel') => {
    if (placement === 'full' && (departmentComparisonOpen || isBusRoutesSurface)) return null;
    if (placement === 'panel') {
      const activeSuggestion = faqSuggestions[faqCarouselIndex % faqSuggestions.length];
      if (!activeSuggestion) return null;
      return (
        <div
          className={`faq-panel-suggestion-row ${shouldHideFaqSuggestions ? 'faq-suggestions-hidden' : ''}`}
          onMouseEnter={() => setIsFaqCarouselPaused(true)}
          onMouseLeave={() => setIsFaqCarouselPaused(false)}
        >
          <motion.button
            type="button"
            className={`faq-suggestion-pill faq-suggestion-pill-panel ${scriptPreset.cssClass}`}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.98 }}
            onClick={(event) => {
              event.stopPropagation();
              submitFaqSuggestion(activeSuggestion.id, activeSuggestion.text);
            }}
          >
            {activeSuggestion.text}
          </motion.button>
        </div>
      );
    }

    const tickerItems = [...faqSuggestions, ...faqSuggestions, ...faqSuggestions];
    const visibleGroupWidth = Math.max(1, faqTickerLayout.viewportWidth);
    return (
      <div
        className={`faq-carousel-shell faq-carousel-shell-full ${shouldHideFaqSuggestions ? 'faq-suggestions-hidden' : ''}`}
        onMouseEnter={() => setIsFaqCarouselPaused(true)}
        onMouseLeave={() => setIsFaqCarouselPaused(false)}
      >
        <div
          className="faq-carousel-viewport"
          style={{ width: visibleGroupWidth }}
        >
          <motion.div
            className="faq-carousel-track"
            style={{ x: tickerX, gap: faqTickerLayout.gap }}
          >
            {tickerItems.map((suggestion, index) => (
              <React.Fragment key={`${suggestion.id}-${index}`}>
                <FaqTickerCard
                  suggestion={suggestion}
                  index={index}
                  layout={faqTickerLayout}
                  cycleLength={faqSuggestions.length}
                  x={tickerX}
                  onSelect={submitFaqSuggestion}
                  scriptClass={scriptPreset.cssClass}
                />
              </React.Fragment>
            ))}
          </motion.div>
        </div>
      </div>
    );
  };

  useEffect(() => {
    const prev = prevLayoutModeRef.current;
    if (prev === 'SPLIT_CARDS' && layoutMode === 'FULL_TEXT') {
      setVisuallyFocusedMessage(null);
    }
    prevLayoutModeRef.current = layoutMode;
  }, [layoutMode]);

  useEffect(() => {
    if (layoutMode !== 'SPLIT_CARDS') return;
    const panel = scrollRef.current;
    if (!panel) return;
    const raf = requestAnimationFrame(() => {
      panel.scrollTo({ top: panel.scrollHeight, behavior: 'smooth' });
    });
    return () => cancelAnimationFrame(raf);
  }, [layoutMode, recentPanelMessages, isResponsePending]);

  return (
    <div className={`light-chat-container ${scriptPreset.cssClass}`} data-testid="chat-screen" lang={languageToCode(language)}>
      <AnimatePresence mode="wait" initial={false}>
        {surface === 'bus_routes' ? (
          React.createElement(BusRoutesFullscreen, {
            key: `bus-routes-${busRoutesMountKey}`,
            highlightQuery: busRoutesHighlightQuery,
            onClose: handleCloseBusRoutes,
          })
        ) : (
          <motion.div
            key="main-chat-shell"
            role="presentation"
            className="relative flex h-full min-h-0 w-full flex-1 flex-col"
            initial={false}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15, ease: [0.22, 1, 0.36, 1] }}
          >
      <div className="cinematic-overlay" />

      {/* Global Home Button */}
      <motion.button
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        onClick={handleHomeClick}
        data-testid="home-button"
        className="premium-home-button"
        title={uiText(language, 'session.home')}
        aria-label={uiText(language, 'session.home')}
      >
        <Home className="w-6 h-6" />
      </motion.button>

      {/* Global Quick Actions */}
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="absolute right-[30px] top-[30px] z-50 flex flex-wrap justify-end gap-2"
      >
        <motion.button
          type="button"
          whileHover={{ scale: 1.04, y: -2, boxShadow: 'none' }}
          whileTap={{ scale: 0.97 }}
          onClick={isCampusNavigationStage ? returnToChatFromCampus : openCampusNavigation}
          className="group flex items-center gap-2 rounded-full border-2 border-[#2a115c]/80 bg-[linear-gradient(135deg,rgba(255,255,255,0.74),rgba(252,231,243,0.58),rgba(167,139,250,0.36))] px-4 py-2.5 text-sm font-semibold text-slate-900 backdrop-blur-xl transition-colors hover:border-[#17072f]/90 hover:bg-white/82"
        >
          {isCampusNavigationStage ? (
            <MessageSquareText className="h-4 w-4 text-[#2a115c]" />
          ) : (
            <MapPinned className="h-4 w-4 text-[#2a115c]" />
          )}
          {isCampusNavigationStage ? campusCopy.chat : campusCopy.campusNavigation}
        </motion.button>
        <motion.button
          type="button"
          whileHover={{ scale: 1.04, y: -2, boxShadow: 'none' }}
          whileTap={{ scale: 0.97 }}
          onClick={() => {
            if (isCampusNavigationStage) returnToChatFromCampus();
            onChatUserActivity?.();
            setSurface('brochure');
          }}
          className="group flex items-center gap-2 rounded-full border-2 border-[#2a115c]/80 bg-[linear-gradient(135deg,rgba(255,255,255,0.74),rgba(252,231,243,0.58),rgba(167,139,250,0.36))] px-4 py-2.5 text-sm font-semibold text-slate-900 backdrop-blur-xl transition-colors hover:border-[#17072f]/90 hover:bg-white/82"
        >
          <FileText className="h-4 w-4 text-[#2a115c]" />
          {uiText(language, 'cards.college_brochure')}
        </motion.button>
      </motion.div>

      {/* ─── GLOBAL CINEMATIC BACKGROUND ─── */}
      <div 
        className="absolute inset-0 w-full h-full z-0 pointer-events-none"
        style={{ 
          backgroundImage: `url(${fullTextBgImage})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
        }}
      />

      {/* True full-viewport thinking state — outside .text-container / orb zone */}
      <AnimatePresence>
        {showThinkingStage ? (
          <motion.div
            key="clara-thinking-overlay"
            className="clara-thinking-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, filter: 'blur(8px)' }}
            transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
          >
            <ThinkingInterlude
              sentence={thinkingGate.sentence || thinkingBridgeFallback(presentationLanguage)}
              language={presentationLanguage}
            />
          </motion.div>
        ) : null}
      </AnimatePresence>

      <AnimatePresence mode="wait">
          {/* ─── FULL TEXT MODE ─── */}
          {layoutMode === 'FULL_TEXT' ? (
            <motion.div
              key="full-text"
              layoutId="main"
              className={`full-text-layout min-h-0${departmentComparisonOpen ? ' full-text-layout--comparison-active' : ''}`}
            >
              <div
                className={`full-text-message-stage relative z-10 flex min-h-0 flex-col${departmentComparisonOpen ? ' full-text-message-stage--with-comparison' : ''}`}
              >
                <div
                  ref={fullTextScrollRef}
                  className={`text-container${
                    !departmentComparisonOpen &&
                    lastAssistantMsg &&
                    isTextMessage(lastAssistantMsg) &&
                    !isAwaitingReadyPrompt &&
                    !isResponsePending &&
                    !(
                      showLanguageOverlay &&
                      inlineLanguageGate &&
                      !languageGateSatisfied
                    )
                      ? ' text-container--optical'
                      : ''
                  }`}
                  style={
                    responseLayoutEnabled
                      ? {
                          width: responseLayout.containerStyle.width,
                          overflowY: responseLayout.containerStyle.overflowY,
                          // Optical spacers own vertical placement when --optical is active.
                          ...(departmentComparisonOpen
                            ? { justifyContent: responseLayout.containerStyle.justifyContent }
                            : {}),
                        }
                      : undefined
                  }
                >
                  <AnimatePresence mode="wait">
                    {showLanguageOverlay &&
                    inlineLanguageGate &&
                    !languageGateSatisfied &&
                    layoutMode === 'FULL_TEXT' &&
                    !isResponsePending ? (
                      <motion.div
                        key="inline-lang-panel"
                        role="region"
                        aria-labelledby="inline-lang-title"
                        initial={{ opacity: 0, y: 44, scale: 0.88, filter: 'blur(18px)', rotateX: -18 }}
                        animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)', rotateX: 0 }}
                        exit={{ opacity: 0, y: -24, scale: 0.96, filter: 'blur(12px)' }}
                        transition={{ duration: 0.85, ease: [0.16, 1, 0.3, 1] }}
                        className="mx-auto w-full max-w-5xl px-4"
                        style={{ perspective: 1200 }}
                      >
                        <motion.h2
                          id="inline-lang-title"
                          initial={{ opacity: 0, letterSpacing: '0.38em' }}
                          animate={{ opacity: 1, letterSpacing: '0.12em' }}
                          transition={{ duration: 0.9, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
                          className="mb-8 text-center text-2xl sm:text-3xl font-semibold uppercase text-slate-900/85"
                          style={{ fontFamily: '"Bodoni Moda", "Libre Bodoni", Didot, "Playfair Display", serif' }}
                        >
                          {t('selectLanguage')}
                        </motion.h2>
                        <div className="grid grid-cols-3 gap-5 sm:gap-6">
                          {LANGUAGE_OPTIONS.map((lang, index) => {
                            const testId = `inline-language-${lang.name.toLowerCase()}`;
                            return (
                              <motion.button
                                key={lang.name}
                                type="button"
                                data-testid={testId}
                                initial={{ opacity: 0, y: 28, scale: 0.86, filter: 'blur(10px)' }}
                                animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
                                transition={{
                                  delay: 0.18 + index * 0.06,
                                  duration: 0.62,
                                  ease: [0.16, 1, 0.3, 1],
                                }}
                                whileHover={{
                                  scale: 1.06,
                                  y: -4,
                                  boxShadow: '0 18px 48px rgba(55, 24, 112, 0.24)',
                                }}
                                whileTap={{ scale: 0.97 }}
                                onClick={() => handleInlineLanguagePick(lang.name)}
                                className="group relative min-h-[7rem] overflow-hidden rounded-[1.65rem] border-2 border-[#3b176f]/55 bg-white/55 px-6 py-5 text-center shadow-[0_14px_40px_rgba(55,24,112,0.12)] backdrop-blur-xl transition-colors hover:border-[#2a0f58]/80 hover:bg-white/75"
                              >
                                <span className="pointer-events-none absolute inset-x-5 top-0 h-px bg-gradient-to-r from-transparent via-white to-transparent" />
                                <span className="block text-2xl sm:text-3xl font-bold text-slate-950">
                                  {lang.label}
                                </span>
                                <span className="mt-2 block text-[11px] sm:text-xs uppercase tracking-[0.22em] text-slate-500 group-hover:text-indigo-500">
                                  {lang.name}
                                </span>
                              </motion.button>
                            );
                          })}
                        </div>
                      </motion.div>
                    ) : lastAssistantMsg && isTextMessage(lastAssistantMsg) && !isAwaitingReadyPrompt ? (
                      <motion.div
                        key={lastAssistantMsg.id ?? lastAssistantMsg.text}
                        initial={{ opacity: 0, y: 18, filter: 'blur(10px)' }}
                        animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                        exit={{ opacity: 0, y: -34, scale: 0.96, filter: 'blur(16px)' }}
                        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
                        className="full-text-message-wrapper full-text-safe-zone"
                      >
                        <AnimatedAiMessage
                          key={`${lastAssistantMsg.id ?? 'msg'}-page-${responseLayout.activePageIndex}`}
                          text={fullTextPageText}
                          animate={fullTextAnimate}
                          audioDuration={fullTextPageAudioDuration}
                          playbackProgress={fullTextRevealProgress}
                          className={fullTextMessageClassName}
                          style={fullTextAnswerStyle}
                        />
                      </motion.div>
                    ) : null}
                  </AnimatePresence>
                </div>

                {!departmentComparisonOpen && !showThinkingStage ? (
                  <div
                    className="full-text-orb-zone"
                    onPointerDownCapture={(ev) => {
                      // #region agent log
                      const el = ev.target as HTMLElement;
                      _agentDbg('A', 'ChatScreen.tsx:full-text-orb-zone', 'pointer_capture', {
                        placement: 'full',
                        tag: el?.tagName,
                        cls: typeof el?.className === 'string' ? el.className.slice(0, 120) : '',
                      });
                      // #endregion
                    }}
                  >
                    {renderFaqCarousel('full')}
                    <div className="chat-orb-stack-below-faq">
                      <ChatOrbControl
                        orbState={orbState}
                        isProcessing={false}
                        amplitude={orbState === 'listening' ? voiceAnalyser.amplitude : 0.05}
                        frequencyDataRef={voiceAnalyser.frequencyDataRef}
                        onTap={handleOrbTap}
                        bottomClassName="mt-2 mb-5 w-full text-center"
                      />
                    </div>
                  </div>
                ) : null}
              </div>

              <DepartmentComparisonCinema
                language={language}
                open={departmentComparisonOpen}
                initialDepartmentIds={comparisonDeptIds}
                highlightId={comparisonHighlightId}
                recommendFocus={comparisonRecommendFocus}
                narrationSectionIndex={comparisonNarrationSection}
                onClose={handleCloseDepartmentComparison}
              />
            </motion.div>

          /* ─── SPLIT CARDS MODE (college/dept/hod/trustees) ─── */
          ) : (
            <motion.div
              key="split"
              className={`split-cards-layout ${isCampusNavigationStage ? 'split-cards-layout--campus-map-and-panel' : ''}`}
            >
              <div className={`visual-stage-70 flex flex-col items-center ${isCampusNavigationStage ? 'visual-stage-70--campus-map-only' : ''}`}>
                {/* Content Layer */}
                <div
                  className="relative z-10 w-full h-full flex flex-col items-center justify-center"
                  data-card-language={presentationLanguage}
                  data-current-unit-id={currentUnitCard?.unitId || ''}
                >

                {isCampusNavigationStage && selectedCampusDirection ? (
                  <CampusNavigationMapOnly
                    direction={selectedCampusDirection}
                    language={presentationLanguage}
                    routeMode={campusRouteMode}
                    routeResult={campusRouteResult}
                    onMappedRoomSelect={handleMappedCampusRoomSelect}
                  />
                ) : currentUnitCard && CAMPUS_UNIT_CARD_TYPES.has(currentUnitCard.cardType) ? (
                  <CampusUnitCard card={currentUnitCard} language={presentationLanguage} />
                ) : currentUnitCard?.cardType === 'principal' || (executiveLeadershipKind === 'principal' && !currentUnitCard) ? (
                  <PremiumPrincipalCard language={presentationLanguage} />
                ) : currentUnitCard?.cardType === 'vice_principal' || (executiveLeadershipKind === 'vice_principal' && !currentUnitCard) ? (
                  <PremiumVicePrincipalCard language={presentationLanguage} />
                ) : currentUnitCard?.cardType === 'trustees' || (isTrusteesStage && !currentUnitCard) ? (
                  <Trustees onNarrateTrustee={handleTrusteeNarration} language={presentationLanguage} />
                ) : isHodStage ? (
                  <LeadershipOverview
                    cards={[]}
                    currentCardIdx={currentCardIdx}
                    targetDepartment={activeTargetDepartment}
                    targetDepartments={activeHodDepartments}
                    unitCards={
                      Array.isArray(unitBackedCards)
                        ? unitBackedCards.filter((m) => m.cardType === 'hod')
                        : null
                    }
                  />
                ) : currentUnitCard?.cardType === 'hod' ? (
                  <LeadershipOverview
                    cards={[]}
                    currentCardIdx={0}
                    targetDepartment={currentUnitCard.departmentId}
                    targetDepartments={[currentUnitCard.departmentId]}
                    unitCards={[currentUnitCard]}
                  />
                ) : currentUnitCard?.cardType === 'department_fees' || isFeesStage ? (
                  <DepartmentFeesCard
                    departmentId={currentUnitCard?.departmentId || activeFeesDepartmentId}
                    language={presentationLanguage}
                  />
                ) : isDepartmentOverviewStage && factoryDepartmentId ? (
                  <DepartmentCardFactory 
                    departmentId={factoryDepartmentId}
                    slides={departmentSlides}
                    currentIdx={currentCardIdx}
                    onNext={() => handleCardSelect(Math.min(departmentSlides.length - 1, currentCardIdx + 1))}
                    onPrev={() => handleCardSelect(Math.max(0, currentCardIdx - 1))}
                    onSelectSlide={handleCardSelect}
                    language={presentationLanguage}
                    onClose={() => {
                      setIsDepartmentOverviewStage(false);
                      setActiveDepartmentId(null);
                      currentUiLockRef.current = 'IDLE';
                    }}
                  />
                ) : courseMenuOptions.length > 0 ? (
                  <CourseMenuComponent options={courseMenuOptions} onSelect={handleCourseMenuSelect} />
                ) : isDocumentsStage ? (
                  <DocumentsBlock />
                ) : isInfoSlideStage && infoSlides.length > 0 ? (
                  <DepartmentCardStage
                    departmentLabel=""
                    chipText={infoSlideChip}
                    slides={infoSlides}
                    currentCardIdx={currentCardIdx}
                    onCardClick={handleCardSelect}
                  />
                ) : isTrusteesStage ? (
                  <Trustees onNarrateTrustee={handleTrusteeNarration} language={presentationLanguage} />
                ) : activeCards && activeCards.length > 0 ? (
                  <LeadershipOverview 
                    cards={activeCards} 
                    currentCardIdx={currentCardIdx} 
                    targetDepartment={activeTargetDepartment}
                    onCardClick={handleCardSelect}
                  />
                ) : null}
                </div>
              </div>
              <motion.aside
                className={`interaction-panel-30 ${isCampusNavigationStage ? 'interaction-panel-30--campus-directions' : ''}`}
                onPointerDownCapture={(ev) => {
                  // #region agent log
                  const el = ev.target as HTMLElement;
                  _agentDbg('A', 'ChatScreen.tsx:interaction-panel-30', 'pointer_capture', {
                    placement: 'panel30',
                    tag: el?.tagName,
                    cls: typeof el?.className === 'string' ? el.className.slice(0, 120) : '',
                  });
                  // #endregion
                }}
              >

                <header className="panel-header">
                  <div className="panel-title flex items-center gap-2">
                    <Sparkles size={18} /> {isCampusNavigationStage ? campusCopy.campusNavigation : 'CLARA'}
                  </div>
                </header>
                {narrationCaption ? (
                  <div className="px-4 pb-2 pt-1">
                    <div className="rounded-2xl bg-white/5 px-4 py-3 text-[13px] leading-snug text-white/90 backdrop-blur-sm">
                      {narrationCaption}
                    </div>
                  </div>
                ) : null}
                <div ref={scrollRef} className="panel-messages no-scrollbar">
                  {isCampusNavigationStage && selectedCampusDirection ? (
                    <div className="campus-direction-panel">
                      <label className="campus-select-label" htmlFor="campus-destination-select">
                        {campusCopy.chooseDestination}
                      </label>
                      <select
                        id="campus-destination-select"
                        value={selectedCampusIndex}
                        onChange={(event) => {
                          const nextIndex = Number(event.target.value);
                          setCampusDirectionOverride(null);
                          setCampusRouteResult(null);
                          setSelectedCampusIndex(nextIndex);
                          setHasCampusRoomSelection(true);
                          speakCampusDirection(nextIndex);
                        }}
                        className="campus-destination-select"
                      >
                        {CAMPUS_DIRECTIONS.map((direction, index) => (
                          <option key={direction.to} value={index}>
                            {direction.to}
                          </option>
                        ))}
                      </select>

                      <div className="campus-direction-card">
                        <span className="campus-direction-kicker">{campusCopy.destination}</span>
                        <h3>{selectedCampusDirection.to}</h3>
                        <div className="campus-direction-meta">
                          <span>{campusCopy.block} {selectedCampusDirection.block}</span>
                          <span>{campusCopy.groundFloor}</span>
                          <span>{selectedCampusDirection.estimated_steps} {campusCopy.steps}</span>
                          <span>{selectedCampusDirection.estimated_time_seconds} {campusCopy.seconds}</span>
                        </div>
                        <ol className="campus-direction-steps">
                          {campusDisplaySteps.map((step, index) => (
                            <li key={`${selectedCampusDirection.to}-${index}`}>{step}</li>
                          ))}
                        </ol>
                      </div>

                      <button
                        type="button"
                        onClick={() => (isCampusSpeaking ? stopCampusSpeech() : speakCampusDirection())}
                        className="campus-speak-button"
                      >
                        {isCampusSpeaking ? <Square size={16} /> : <Volume2 size={17} />}
                        {isCampusSpeaking ? campusCopy.stop : campusCopy.speak}
                      </button>
                    </div>
                  ) : (
                    <>
                      {recentPanelMessages.map((m, i) => isTextMessage(m) && (
                        m.role === 'user' 
                          ? <div key={m.id || i} className="bubble-user">{m.text}</div>
                          : <AnimatedAiMessage 
                              key={m.id || i} 
                              text={sentenceRevealTurnId === m.id ? sentenceRevealText : m.text} 
                              animate={i === recentPanelMessages.length - 1}
                              audioDuration={i === recentPanelMessages.length - 1 ? currentAudioDuration : 0}
                              className="bubble-clara"
                              style={m.id === 'greeting' ? greetingFontStyle : undefined}
                            />
                      ))}
                    </>
                  )}
                </div>
                {!showThinkingStage && renderFaqCarousel('panel')}
                
                {!isCampusNavigationStage && !showThinkingStage && (
                  <motion.div className="chat-orb-stack-below-faq w-full flex justify-center pb-12">
                    <ChatOrbControl
                      orbState={orbState}
                      isProcessing={false}
                      amplitude={orbState === 'listening' ? voiceAnalyser.amplitude : 0.05}
                      frequencyDataRef={voiceAnalyser.frequencyDataRef}
                      onTap={handleOrbTap}
                      bottomClassName="absolute -bottom-10 left-1/2 -translate-x-1/2 w-full text-center"
                    />
                  </motion.div>
                )}
              </motion.aside>
            </motion.div>
          )}
      </AnimatePresence>

      {/* Comparison mode: orb lives outside the FULL_TEXT motion wrapper so position:fixed is viewport-anchored
          (transform on layoutId/main would otherwise trap fixed positioning and overlap the panel). */}
      {layoutMode === 'FULL_TEXT' && departmentComparisonOpen && !showThinkingStage ? (
        <>
          <div className="full-text-comparison-faq-layer">
            {renderFaqCarousel('full')}
          </div>
          <div className="full-text-comparison-orb-layer">
            <ChatOrbControl
              orbState={orbState}
              isProcessing={isResponsePending}
              amplitude={orbState === 'listening' ? voiceAnalyser.amplitude : (isResponsePending ? 0.3 : 0.05)}
              frequencyDataRef={voiceAnalyser.frequencyDataRef}
              onTap={handleOrbTap}
              comparisonMode
              bottomClassName="pointer-events-none mt-1 w-full text-center"
            />
          </div>
        </>
      ) : null}

      <AnimatePresence>
        {isBrochureOpen && (
          <motion.div
            key="college-brochure-modal"
            className="brochure-modal-backdrop"
            role="presentation"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
            onClick={() => {
              onChatUserActivity?.();
              setSurface('chat');
            }}
          >
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-labelledby="brochure-title"
              className="brochure-modal-card"
              initial={{ opacity: 0, y: 28, scale: 0.94, filter: 'blur(12px)' }}
              animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
              exit={{ opacity: 0, y: 14, scale: 0.97, filter: 'blur(8px)' }}
              transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
              onClick={(event) => event.stopPropagation()}
            >
              <button
                type="button"
                className="brochure-modal-close"
                onClick={() => {
                  onChatUserActivity?.();
                  setSurface('chat');
                }}
                aria-label={`${uiText(language, 'session.close')} ${uiText(language, 'cards.college_brochure')}`}
              >
                <X className="h-5 w-5" />
              </button>
              <header className="brochure-modal-head">
                <div className="brochure-modal-head-row">
                  <FileText className="brochure-modal-head-icon" aria-hidden />
                  <div className="brochure-modal-head-text">
                    <h2 id="brochure-title">{uiText(language, 'cards.college_brochure')}</h2>
                    <p className="brochure-modal-sub">Latest SVIT brochure — use viewer controls to zoom.</p>
                  </div>
                </div>
              </header>
              <object
                aria-label={uiText(language, 'cards.college_brochure')}
                data={`${collegeBrochurePdfUrl}#view=FitH`}
                type="application/pdf"
                className="brochure-modal-frame"
              >
                <div className="brochure-modal-fallback">
                  <FileText className="h-10 w-10" />
                  <strong>Brochure preview</strong>
                  <span>
                    Open{' '}
                    <a href={collegeBrochurePdfUrl} download className="text-[#2a115c] underline">
                      svit_brochure.pdf
                    </a>
                    .
                  </span>
                </div>
              </object>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
