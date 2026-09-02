import React, {
  Fragment,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { AnimatePresence, motion } from 'motion/react';
import {
  forceSingletonWsRouteSleep,
  peekClaraWsDiagnostics,
  useWebSocket,
} from './hooks/useWebSocket';
import { useLanguage } from './context/LanguageContext';
import { uiText } from './localization/uiCopy';
import { getScriptTypography } from './features/chat/typography/scriptTypography';
import { agentLog, registerClaraDebugInteractionAudit } from './debug/interactionDebug';
import { runHardResetTransaction } from './session/hardResetTransaction';
import {
  beginVisitorSession,
  getVisitorLanguage,
  getVisitorSessionId,
} from './session/visitorSession';
import { kioskStore } from './store/kiosk/kioskStore';
import { KioskState } from './store/kiosk/types';
import { useFaceChannel } from './hooks/useFaceChannel';
import {
  getConversationRuntime,
  getRuntimeTimeline,
  patchConversationRuntime,
  resetConversationRuntime,
  runtimeSettings,
} from './runtime';
import { RuntimeDashboard } from './runtime/RuntimeDashboard';

// Screens
import SleepScreen from './screens/SleepScreen';
import ChatScreen from './screens/ChatScreen';
import AboutMeScreen from './features/about/AboutMeScreen';

const WS_BASE_URL =
  import.meta.env.VITE_WS_URL ||
  `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.hostname}:6969/ws/clara`;
const WS_URL = WS_BASE_URL;
const VOICE_INPUT_MODE = (import.meta.env.VITE_VOICE_INPUT_MODE || 'browser').toLowerCase() === 'backend' ? 'backend' : 'browser';

const _parsedInactivityMs = Number(import.meta.env.VITE_KIOSK_INACTIVITY_MS);
const CHAT_USER_INACTIVITY_MS =
  Number.isFinite(_parsedInactivityMs) && _parsedInactivityMs > 0 ? _parsedInactivityMs : 240_000;

function isChatRouteState(state: number): boolean {
  return state === 3 || state === 4 || state === 5;
}

/**
 * Shell: increments `runtimeSessionKey` so Home destroys the FULL kiosk subtree (React remount —
 * analogous to reload for all component state, overlays, and session-scoped contexts below).
 */
export default function App() {
  const [runtimeSessionKey, setRuntimeSessionKey] = useState(0);
  const scheduleFullRuntimeRemount = useCallback(() => {
    setRuntimeSessionKey((k) => k + 1);
  }, []);

  return (
    <Fragment key={runtimeSessionKey}>
      <ClaraKioskRuntime
        runtimeSessionKey={runtimeSessionKey}
        scheduleFullRuntimeRemount={scheduleFullRuntimeRemount}
      />
    </Fragment>
  );
}

type ClaraKioskRuntimeProps = {
  runtimeSessionKey: number;
  /** Invoked LAST on Home — increments root session key → full kiosk remount */
  scheduleFullRuntimeRemount: () => void;
};

function ClaraKioskRuntime({
  runtimeSessionKey,
  scheduleFullRuntimeRemount,
}: ClaraKioskRuntimeProps) {
  const { language, resetToDefaultLanguage } = useLanguage();
  const scriptClass = getScriptTypography(language).cssClass;
  const faceChannel = useFaceChannel();
  const {
    state,
    payload,
    isConnected,
    setManualState,
    sendMessage,
    retryConnect,
    showOfflineBanner,
    bumpSessionGenForReset,
    appliedSessionGen,
    stalePayloadDropCount,
    wireStaleDropCount,
    isStalePayloadGen,
  } = useWebSocket(WS_URL);
  const [urlOverrideState, setUrlOverrideState] = React.useState<number | null>(null);
  const [showChatLanguageGate, setShowChatLanguageGate] = useState(false);
  const [showAboutMe, setShowAboutMe] = useState(false);
  const [lastHardResetAt, setLastHardResetAt] = useState<number | null>(null);

  const effectiveState = urlOverrideState !== null ? urlOverrideState : state;
  const effectiveStateRef = useRef(effectiveState);
  effectiveStateRef.current = effectiveState;
  const attemptedFaceWindowForChatRef = useRef(false);
  const latestPayloadRef = useRef<any>(null);
  latestPayloadRef.current = payload;

  const chatIdleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const chatInactivityGenerationRef = useRef(0);
  /** Brochure (and similar overlays) suppress kiosk sleep — PDF viewing is intentional activity. */
  const [suppressChatIdleForOverlay, setSuppressChatIdleForOverlay] = useState(false);

  const clearChatUserInactivityTimer = useCallback(() => {
    if (chatIdleTimerRef.current !== null) {
      clearTimeout(chatIdleTimerRef.current);
      chatIdleTimerRef.current = null;
    }
  }, []);

  // Before passive effects re-subscribe singleton WS snapshot, force canonical sleep route.
  // Runs every runtime mount (cold load + Home remount); prevents stale entry.state===5 resurrecting Chat.
  useLayoutEffect(() => {
    forceSingletonWsRouteSleep(WS_URL);
    setManualState(0, null);
    setShowChatLanguageGate(false);
  }, [runtimeSessionKey, setManualState]);

  const resetClaraSession = useCallback(() => {
    runHardResetTransaction({
      bumpWsSessionFloor: bumpSessionGenForReset,
      resetLanguageToDefault: resetToDefaultLanguage,
      resetKioskSnapshot: () => kioskStore.resetSession(),
      forceKioskSemanticSleep: () => kioskStore.dispatchTransition(KioskState.SLEEP, true),
      clearAppOwnedGates: () => setShowChatLanguageGate(false),
      sendBackendResetPayload: () =>
        sendMessage({ action: 'reset_session', type: 'RESET_SESSION' }),
      applyClientSleepUi: () => setManualState(0, null),
      scheduleFullRuntimeRemount,
    });
  }, [
    scheduleFullRuntimeRemount,
    bumpSessionGenForReset,
    resetToDefaultLanguage,
    sendMessage,
    setManualState,
  ]);

  const resetClaraSessionWithTimestamp = useCallback(() => {
    setLastHardResetAt(Date.now());
    resetClaraSession();
  }, [resetClaraSession]);

  // K1: on every (re)connect, re-register the active visitor session and its
  // canonical selected language so a new backend socket rebinds to `kn` etc.
  // without replaying any welcome. Runs only when a selection is stored; after
  // a visitor reset the storage is cleared so nothing stale is restored.
  const lastConnectedRef = useRef(false);
  useEffect(() => {
    if (!isConnected) {
      lastConnectedRef.current = false;
      return;
    }
    if (lastConnectedRef.current) return;
    lastConnectedRef.current = true;
    const storedCode = getVisitorLanguage();
    const visitorId = getVisitorSessionId();
    if (storedCode && visitorId) {
      sendMessage({
        action: 'restore_language',
        language_code_key: storedCode,
        visitor_session_id: visitorId,
        ui_state: effectiveStateRef.current,
      });
    }
  }, [isConnected, sendMessage]);

  const scheduleChatUserInactivityTimer = useCallback(() => {
    clearChatUserInactivityTimer();
    chatInactivityGenerationRef.current += 1;
    const gen = chatInactivityGenerationRef.current;
    chatIdleTimerRef.current = setTimeout(() => {
      chatIdleTimerRef.current = null;
      if (gen !== chatInactivityGenerationRef.current) return;
      if (!isChatRouteState(effectiveStateRef.current)) return;
      const p = latestPayloadRef.current;
      const shouldSuppressReset =
        p &&
        typeof p === 'object' &&
        (p.isProcessing === true ||
          p.audioPending === true ||
          p.isSpeaking === true ||
          (p.type === 'assistant_audio_update' && (p.tts_streaming === true || (Array.isArray(p.tts_audio_queue) && p.tts_audio_queue.length > 0))));
      if (shouldSuppressReset) {
        scheduleChatUserInactivityTimer();
        return;
      }
      resetClaraSession();
    }, CHAT_USER_INACTIVITY_MS);
  }, [clearChatUserInactivityTimer, resetClaraSession]);

  const reportChatUserActivity = useCallback(() => {
    scheduleChatUserInactivityTimer();
  }, [scheduleChatUserInactivityTimer]);

  useEffect(() => {
    if (!isChatRouteState(effectiveState)) {
      clearChatUserInactivityTimer();
      return;
    }
    if (suppressChatIdleForOverlay) {
      clearChatUserInactivityTimer();
      return clearChatUserInactivityTimer;
    }
    scheduleChatUserInactivityTimer();
    return clearChatUserInactivityTimer;
  }, [
    effectiveState,
    suppressChatIdleForOverlay,
    scheduleChatUserInactivityTimer,
    clearChatUserInactivityTimer,
  ]);

  useEffect(() => {
    if (effectiveState === 0) {
      setShowChatLanguageGate(false);
      attemptedFaceWindowForChatRef.current = false;
    }
  }, [effectiveState]);

  useEffect(() => {
    if (!isChatRouteState(effectiveState) || attemptedFaceWindowForChatRef.current) return;
    attemptedFaceWindowForChatRef.current = true;
    // Browsers may block this without a user gesture; the banner control remains the reliable path.
    faceChannel.openFaceWindow();
  }, [effectiveState, faceChannel]);

  useEffect(() => {
    // Re-read ?state= on every ClaraKioskRuntime remount used to FORCE ChatScreen after Home whenever
    // developers left ?state=5 in the URL — survives session key bump and defeats Sleep boot.
    if (runtimeSessionKey > 0) return;
    const params = new URLSearchParams(window.location.search);
    const s = params.get('state');
    if (s !== null) {
      const n = parseInt(s, 10);
      if (n >= 0 && n <= 8) setUrlOverrideState(n);
    }
  }, [runtimeSessionKey]);

  useEffect(() => {
    if (!import.meta.env.DEV) return;
    registerClaraDebugInteractionAudit();
  }, []);

  useEffect(() => {
    const w = window as unknown as { claraDebug?: Record<string, unknown> };
    w.claraDebug = {
      ...(w.claraDebug ?? {}),
      getSessionDiagnostics: () => ({
        runtimeSessionKey,
        resetGenerationFence: appliedSessionGen,
        backendWs: peekClaraWsDiagnostics(WS_URL),
        stalePayloadDropCount,
        wireStaleDropCount,
        lastHardResetAt,
        kioskSnapshot: kioskStore.getSnapshot(),
      }),
      getRuntimeIntegrity: () => ({
        snapshot: getConversationRuntime(),
        timeline: getRuntimeTimeline(),
      }),
      peekClaraWsDiagnostics: () => peekClaraWsDiagnostics(WS_URL),
      retryConnect,
      requestHardResetRecovery: () => resetClaraSessionWithTimestamp(),
      recoverSemanticLocksOnly: () => kioskStore.clearSemanticLocks(),
      isStalePayloadGen,
      /** Full kiosk subtree React remounts each increment (controlled runtime rebuild). */
      scheduleFullRuntimeRemount,
    };
  }, [
    runtimeSessionKey,
    appliedSessionGen,
    stalePayloadDropCount,
    wireStaleDropCount,
    lastHardResetAt,
    isStalePayloadGen,
    resetClaraSessionWithTimestamp,
    scheduleFullRuntimeRemount,
    retryConnect,
  ]);

  useEffect(() => {
    resetConversationRuntime();
    patchConversationRuntime({
      generation: appliedSessionGen,
      sessionId: `runtime-${runtimeSessionKey}`,
      conversationId: `runtime-${runtimeSessionKey}`,
    });
  }, [runtimeSessionKey, appliedSessionGen]);

  useEffect(() => {
    if (!import.meta.env.DEV) return;
    agentLog('H2', 'App.tsx:effectiveState', 'route snapshot', {
      runtimeSessionKey,
      effectiveState,
      wsUiStateHook: state,
      urlOverrideState,
      inferredUi:
        effectiveState === 0
          ? 'sleep'
          : [3, 4, 5].includes(effectiveState)
            ? 'chat'
            : 'fallback',
    });
  }, [effectiveState, state, urlOverrideState, runtimeSessionKey]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const key = parseInt(e.key, 10);
      if (Number.isNaN(key) || key < 0 || key > 8) return;
      setUrlOverrideState(null);
      if (key === 3) {
        setManualState(5);
        setShowChatLanguageGate(true);
        return;
      }
      setShowChatLanguageGate(false);
      setManualState(key);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setManualState]);

  const chatScreenIdentity = useMemo(
    () => `chat-${runtimeSessionKey}`,
    [runtimeSessionKey]
  );

  const renderState = () => {
    if (showAboutMe) {
      return (
        <motion.div key="about-me" className="w-full h-full">
          <AboutMeScreen onExit={() => setShowAboutMe(false)} />
        </motion.div>
      );
    }

    switch (effectiveState) {
      case 0:
        return (
          <motion.div key={`sleep-${runtimeSessionKey}`} className="w-full h-full">
            <SleepScreen
              onAboutMe={() => setShowAboutMe(true)}
              onWake={() => {
                // K1: waking begins a visitor session; the id is bound to the
                // backend session so language restoration can be validated.
                const visitorId = beginVisitorSession();
                sendMessage({ action: 'wake', visitor_session_id: visitorId });
                setManualState(5);
                setShowChatLanguageGate(true);
              }}
            />
          </motion.div>
        );
      case 3:
      case 4:
      case 5:
        return (
          <motion.div key={`chat-branch-${runtimeSessionKey}`} className="w-full h-full">
            <Fragment key={chatScreenIdentity}>
              <ChatScreen
                isPayloadStale={isStalePayloadGen}
                messages={payload?.messages ?? []}
                isListening={payload?.isListening ?? false}
                isSpeaking={payload?.isSpeaking ?? false}
                isProcessing={payload?.isProcessing ?? false}
                payload={payload}
                isConnected={isConnected}
                voiceInputMode={VOICE_INPUT_MODE}
                inlineLanguageGate={showChatLanguageGate}
                onInlineLanguageResolved={() => setShowChatLanguageGate(false)}
                // K1: returning to sleep is a new-visitor boundary — run the
                // full deterministic reset so no language persists across visitors.
                onBack={resetClaraSessionWithTimestamp}
                onHome={resetClaraSessionWithTimestamp}
                onOrbTap={() => {
                  reportChatUserActivity();
                  sendMessage({ action: 'mic_start' });
                }}
                onChatUserActivity={reportChatUserActivity}
                onChatIdleOverlayChange={setSuppressChatIdleForOverlay}
                sendMessage={sendMessage}
                faceChannel={faceChannel}
              />
            </Fragment>
          </motion.div>
        );
      default:
        return (
          <motion.div
            key="fallback"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="w-full h-full flex items-center justify-center"
          >
            <div className="glass p-12 rounded-3xl text-center">
              <h2 className="text-3xl font-display italic mb-4 text-white">State {effectiveState}</h2>
              <p className="text-stone-400 tracking-widest uppercase text-sm">
                This interface is currently under development.
              </p>
              <button
                type="button"
                onClick={() => setManualState(0)}
                className="mt-8 px-8 py-4 border border-white/10 rounded-full hover:bg-white/5 transition-colors text-white"
              >
                Return to Sleep
              </button>
            </div>
          </motion.div>
        );
    }
  };

  return (
    <div className="relative w-screen h-screen bg-black overflow-hidden font-sans">
      {showOfflineBanner && (
        <div className={`${scriptClass} absolute top-0 left-0 right-0 z-[100] p-4 bg-amber-500/20 border-b border-amber-500/40 text-amber-200 text-xs text-center backdrop-blur-md`}>
          {uiText(language, 'status.connectivity_issue')}{' '}
          <button type="button" onClick={retryConnect} className="underline font-bold">
            {uiText(language, 'session.retry_connection')}
          </button>
          {faceChannel.enabled && (
            <>
              {' '}
              |{' '}
              <button
                type="button"
                onClick={() => faceChannel.openFaceWindow()}
                className="underline font-bold"
              >
                {uiText(language, 'session.enable_face_display')}
              </button>
            </>
          )}
        </div>
      )}

      <main className="relative z-10 w-full h-full">
        <AnimatePresence mode="wait">{renderState()}</AnimatePresence>
      </main>
      {runtimeSettings.dashboardEnabled ? <RuntimeDashboard /> : null}
    </div>
  );
}
