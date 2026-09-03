import { useState, useEffect, useCallback, useRef } from 'react';
import {
  createOutboundCommandDispatcher,
  type OutboundCommandDispatcher,
} from '../lib/ws/outboundCommandDispatcher';
import {
  isUnitBackedNarrationPlan,
  mergeTtsClipSlot,
  unitIdFromPlanSegment,
  type TtsClipSlot,
} from '../lib/ws/ttsClipSlots';
import { authenticatedWebSocketUrl } from '../lib/ws/wsTokenBootstrap';

export type ConnectionPhase =
  | 'initial_connecting'
  | 'connected'
  | 'reconnecting'
  | 'offline';

export interface WSMessage {
  state: number;
  payload?: any;
}

const GRACE_MS = 5000;
const RECONNECT_DEBOUNCE_MS = 2000;
const INITIAL_BACKOFF_MS = 1000;
const MAX_BACKOFF_MS = 8000;

/** Prefer a complete incoming clip list; keep a longer previously accumulated stream queue. */
export function mergeTtsAudioQueue(incoming: unknown, previous: unknown): string[] {
  const incomingQueue = Array.isArray(incoming)
    ? incoming.filter((x): x is string => typeof x === 'string' && x.length > 0)
    : [];
  const prevQueue = Array.isArray(previous)
    ? previous.filter((x): x is string => typeof x === 'string' && x.length > 0)
    : [];
  if (incomingQueue.length >= prevQueue.length && incomingQueue.length > 0) return incomingQueue;
  if (prevQueue.length > 0) return prevQueue;
  return incomingQueue;
}

function readSessionGen(payload: unknown): number | undefined {
  if (!payload || typeof payload !== 'object') return undefined;
  const raw = (payload as { session_gen?: unknown }).session_gen;
  if (typeof raw === 'number' && !Number.isNaN(raw)) return raw;
  if (typeof raw === 'string') {
    const n = parseInt(raw, 10);
    return Number.isNaN(n) ? undefined : n;
  }
  return undefined;
}

function readWireSeq(payload: unknown): number | undefined {
  if (!payload || typeof payload !== 'object') return undefined;
  const raw = (payload as { wire_seq?: unknown }).wire_seq;
  if (typeof raw === 'number' && !Number.isNaN(raw)) return raw;
  if (typeof raw === 'string') {
    const n = parseInt(raw, 10);
    return Number.isNaN(n) ? undefined : n;
  }
  return undefined;
}

/** Survives disconnect: Home must advance even if WebSocket singleton is not mounted yet. */
const minAppliedBackendGenFloorByUrl = new Map<string, number>();

function bumpClientSessionFloor(url: string): number {
  const prev = minAppliedBackendGenFloorByUrl.get(url) ?? 0;
  const next = prev + 1;
  minAppliedBackendGenFloorByUrl.set(url, next);
  return next;
}

// Singleton per URL: cleanup never closes the socket so Strict Mode re-run always reuses it.
interface SharedEntry {
  socket: WebSocket;
  refCount: number;
  onConnected: (connected: boolean) => void;
  onMessage: (state: number, payload: any) => void;
  state: number;
  payload: any;
  /** Mirrors backend session_generation; stale WS payloads are dropped when older. */
  appliedBackendGen: number;
  stalePayloadDrops: number;
  wireStaleDrops: number;
  /** Monotonic per-connection server wire_seq; rejects duplicate / late ordering. */
  lastAppliedWireSeq: number;
  connectionPhase: ConnectionPhase;
  setPhase: (phase: ConnectionPhase) => void;
  /** Bumped on each new WebSocket so a stale onopen cannot flush. */
  socketGeneration: number;
}

const sharedByUrl = new Map<string, SharedEntry>();
const hasConnectedOnceByUrl = new Map<string, boolean>();
const connectionPhaseByUrl = new Map<string, ConnectionPhase>();
const phaseListenersByUrl = new Map<string, Set<() => void>>();
const outboundDispatchersByUrl = new Map<string, OutboundCommandDispatcher>();

function outboundDispatcherFor(url: string): OutboundCommandDispatcher {
  let d = outboundDispatchersByUrl.get(url);
  if (!d) {
    d = createOutboundCommandDispatcher();
    outboundDispatchersByUrl.set(url, d);
  }
  return d;
}

function notifyPhaseListeners(url: string) {
  phaseListenersByUrl.get(url)?.forEach((l) => l());
}

const NOOP = () => {};

export function useWebSocket(url: string) {
  const [state, setState] = useState<number>(0);
  const [payload, setPayload] = useState<any>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [hasAttemptedConnect, setHasAttemptedConnect] = useState(false);
  const [connectionPhase, setConnectionPhase] = useState<ConnectionPhase>(() =>
    connectionPhaseByUrl.get(url) ?? 'initial_connecting'
  );
  const [reconnectTrigger, setReconnectTrigger] = useState(0);
  const [appliedSessionGen, setAppliedSessionGen] = useState(0);
  const [stalePayloadDropCount, setStalePayloadDropCount] = useState(0);
  const [wireStaleDropCount, setWireStaleDropCount] = useState(0);
  const [authenticatedUrl, setAuthenticatedUrl] = useState<{
    generation: number;
    value: string;
  } | null>(null);
  const stateRef = useRef<number>(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const graceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectingDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const backoffAttemptRef = useRef(0);
  const entryRef = useRef<SharedEntry | null>(null);

  const showOfflineBanner = connectionPhase === 'offline';

  useEffect(() => {
    let cancelled = false;
    setAuthenticatedUrl(null);
    authenticatedWebSocketUrl(url, fetch, import.meta.env.DEV)
      .then((value) => {
        if (!cancelled) setAuthenticatedUrl({ generation: reconnectTrigger, value });
      })
      .catch(() => {
        if (cancelled) return;
        setIsConnecting(false);
        connectionPhaseByUrl.set(url, 'offline');
        notifyPhaseListeners(url);
        reconnectTimerRef.current = setTimeout(() => {
          reconnectTimerRef.current = null;
          setReconnectTrigger((trigger) => trigger + 1);
        }, MAX_BACKOFF_MS);
      });
    return () => {
      cancelled = true;
    };
  }, [url, reconnectTrigger]);

  const bumpSessionGenForReset = useCallback(() => {
    const floor = bumpClientSessionFloor(url);
    outboundDispatcherFor(url).invalidateBelow(floor);
    setAppliedSessionGen(floor);
    const entry = entryRef.current ?? sharedByUrl.get(url);
    if (entry) {
      entry.appliedBackendGen = Math.max(entry.appliedBackendGen, floor);
      // Logical new session while TCP stays open — allow next inbound ordering to start fresh so we
      // never deadlock on stale wire_seq vs missing-wire_seq edge cases across a hard reset.
      entry.lastAppliedWireSeq = 0;
    }
  }, [url]);

  const isStalePayloadGen = useCallback(
    (p: { session_gen?: number } | null | undefined): boolean => {
      const g = readSessionGen(p);
      if (g === undefined) return false;
      const entry = entryRef.current ?? sharedByUrl.get(url);
      if (!entry) return false;
      const floor = minAppliedBackendGenFloorByUrl.get(url) ?? 0;
      const effective = Math.max(entry.appliedBackendGen, floor);
      return g < effective;
    },
    [url]
  );

  useEffect(() => {
    if (!authenticatedUrl || authenticatedUrl.generation !== reconnectTrigger) return;
    setHasAttemptedConnect(true);

    let entry = sharedByUrl.get(url);
    const needNewSocket = !entry || entry.socket.readyState === WebSocket.CLOSED;

    const phaseListener = () =>
      setConnectionPhase(connectionPhaseByUrl.get(url) ?? 'initial_connecting');
    if (!phaseListenersByUrl.has(url)) phaseListenersByUrl.set(url, new Set());
    phaseListenersByUrl.get(url)!.add(phaseListener);

    const removePhaseListener = () => {
      phaseListenersByUrl.get(url)?.delete(phaseListener);
    };

    if (entry && !needNewSocket) {
      entry.refCount++;
      const floor = minAppliedBackendGenFloorByUrl.get(url) ?? 0;
      entry.appliedBackendGen = Math.max(entry.appliedBackendGen, floor);
      entry.onConnected = (connected) => setIsConnected(connected);
      entry.onMessage = (s, p) => {
        stateRef.current = s;
        setState(s);
        setPayload(p ?? null);
        setAppliedSessionGen(entry!.appliedBackendGen);
      };
      entryRef.current = entry;
      setConnectionPhase(entry.connectionPhase);
      setAppliedSessionGen(entry.appliedBackendGen);
      if (entry.socket.readyState === WebSocket.OPEN) {
        setIsConnecting(false);
        setIsConnected(true);
        setState(entry.state);
        setPayload(entry.payload);
        stateRef.current = entry.state;
      } else if (entry.socket.readyState === WebSocket.CONNECTING) {
        setIsConnecting(true);
        const syncWhenOpen = () => {
          if (entryRef.current?.socket.readyState === WebSocket.OPEN) {
            setIsConnecting(false);
            setIsConnected(true);
            setState(entryRef.current.state);
            setPayload(entryRef.current.payload);
            stateRef.current = entryRef.current.state;
            setAppliedSessionGen(entryRef.current.appliedBackendGen);
          }
        };
        const t = setTimeout(syncWhenOpen, 100);
        const t2 = setTimeout(syncWhenOpen, 300);
        return () => {
          clearTimeout(t);
          clearTimeout(t2);
          removePhaseListener();
          const e = entryRef.current ?? entry;
          if (!e) return;
          e.refCount--;
          e.onConnected = NOOP;
          e.onMessage = NOOP;
          entryRef.current = null;
        };
      }
      return () => {
        removePhaseListener();
        const e = entryRef.current ?? entry;
        if (!e) return;
        e.refCount--;
        e.onConnected = NOOP;
        e.onMessage = NOOP;
        entryRef.current = null;
      };
    }

    if (entry && needNewSocket) {
      entry.socket.close();
      sharedByUrl.delete(url);
      entry = null;
    }

    const hasConnectedOnce = hasConnectedOnceByUrl.get(url) ?? false;
    const initialPhase: ConnectionPhase = hasConnectedOnce ? 'reconnecting' : 'initial_connecting';
    connectionPhaseByUrl.set(url, initialPhase);
    notifyPhaseListeners(url);

    let socket: WebSocket;
    try {
      socket = new WebSocket(authenticatedUrl.value);
    } catch (err) {
      setIsConnecting(false);
      if ((import.meta as unknown as { env?: { DEV?: boolean } }).env?.DEV)
        console.debug('WebSocket connection error, retrying…', err);
      const delay = Math.min(
        INITIAL_BACKOFF_MS * 2 ** backoffAttemptRef.current,
        MAX_BACKOFF_MS
      );
      backoffAttemptRef.current = Math.min(backoffAttemptRef.current + 1, 10);
      reconnectTimerRef.current = setTimeout(() => {
        reconnectTimerRef.current = null;
        setReconnectTrigger((t) => t + 1);
      }, delay);
      return () => {
        removePhaseListener();
        if (reconnectTimerRef.current) {
          clearTimeout(reconnectTimerRef.current);
          reconnectTimerRef.current = null;
        }
      };
    }

    const floorAtCreate = minAppliedBackendGenFloorByUrl.get(url) ?? 0;
    const socketGeneration = outboundDispatcherFor(url).nextSocketGeneration();
    entry = {
      socket,
      refCount: 1,
      onConnected: (connected) => setIsConnected(connected),
      onMessage: (s, p) => {
        stateRef.current = s;
        setState(s);
        setPayload(p ?? null);
        setAppliedSessionGen(entry!.appliedBackendGen);
      },
      state: 0,
      payload: null,
      appliedBackendGen: floorAtCreate,
      stalePayloadDrops: 0,
      wireStaleDrops: 0,
      lastAppliedWireSeq: 0,
      connectionPhase: initialPhase,
      socketGeneration,
      setPhase: (phase: ConnectionPhase) => {
        connectionPhaseByUrl.set(url, phase);
        entry!.connectionPhase = phase;
        notifyPhaseListeners(url);
      },
    };
    sharedByUrl.set(url, entry);
    entryRef.current = entry;

    if (!hasConnectedOnce) {
      graceTimerRef.current = setTimeout(() => {
        const current = connectionPhaseByUrl.get(url);
        if (current === 'initial_connecting') {
          connectionPhaseByUrl.set(url, 'offline');
          notifyPhaseListeners(url);
        }
        graceTimerRef.current = null;
      }, GRACE_MS);
    } else {
      reconnectingDebounceRef.current = setTimeout(() => {
        const current = connectionPhaseByUrl.get(url);
        if (current === 'reconnecting') {
          connectionPhaseByUrl.set(url, 'offline');
          notifyPhaseListeners(url);
        }
        reconnectingDebounceRef.current = null;
      }, RECONNECT_DEBOUNCE_MS);
    }

    socket.onopen = () => {
      const dispatcher = outboundDispatcherFor(url);
      if (socketGeneration !== dispatcher.currentSocketGeneration()) {
        return;
      }
      hasConnectedOnceByUrl.set(url, true);
      // New TCP connection ⇒ new backend session dict (session_generation/wire_seq reset).
      // Clearing the floor avoids dropping every message as "stale" vs a pre-reconnect Home bump.
      minAppliedBackendGenFloorByUrl.set(url, 0);
      entry!.appliedBackendGen = 0;
      entry!.lastAppliedWireSeq = 0;
      if (graceTimerRef.current) {
        clearTimeout(graceTimerRef.current);
        graceTimerRef.current = null;
      }
      if (reconnectingDebounceRef.current) {
        clearTimeout(reconnectingDebounceRef.current);
        reconnectingDebounceRef.current = null;
      }
      backoffAttemptRef.current = 0;
      entry!.setPhase('connected');
      entry!.onConnected(true);
      setAppliedSessionGen(0);
      dispatcher.flush(socket, socketGeneration);
      if ((import.meta as unknown as { env?: { DEV?: boolean } }).env?.DEV)
        console.debug('CLARA WebSocket connected');
    };

    socket.onmessage = (event) => {
      try {
        const data: WSMessage = JSON.parse(event.data);
        if (typeof data.state !== 'number') return;
        const next = data.state;
        const rawPayload = data.payload ?? null;
        const g = readSessionGen(rawPayload);
        const wseq = readWireSeq(rawPayload);
        const floor = minAppliedBackendGenFloorByUrl.get(url) ?? 0;
        const effectiveGen = Math.max(entry!.appliedBackendGen, floor);

        if (g !== undefined && g < effectiveGen) {
          entry!.stalePayloadDrops += 1;
          setStalePayloadDropCount(entry!.stalePayloadDrops);
          return;
        }

        // wire_seq: only enforce ordering when the server includes it. Dropping *all* messages
        // without wire_seq after the first sequenced message deadlocks the kiosk if any path omits it.
        if (wseq !== undefined && wseq <= entry!.lastAppliedWireSeq) {
          entry!.wireStaleDrops += 1;
          setWireStaleDropCount(entry!.wireStaleDrops);
          return;
        }
        if (wseq !== undefined) {
          entry!.lastAppliedWireSeq = wseq;
        }

        if (g !== undefined && !Number.isNaN(g)) {
          entry!.appliedBackendGen = Math.max(entry!.appliedBackendGen, g);
        }

        const nextAfterGuard = next;
        const dispatcher = outboundDispatcherFor(url);
        if (nextAfterGuard === 0 && dispatcher.shouldHoldSleep()) {
          return;
        }
        dispatcher.acknowledgeInboundState(nextAfterGuard);
        entry!.state = nextAfterGuard;

        let outgoingPayload = rawPayload;
        const prevPayload = entry!.payload;
        const incomingType =
          rawPayload && typeof rawPayload === 'object'
            ? (rawPayload as { type?: unknown }).type
            : undefined;
        const incomingTurn =
          rawPayload && typeof rawPayload === 'object'
            ? (rawPayload as { turn_id?: unknown }).turn_id
            : undefined;
        const prevTurn =
          prevPayload && typeof prevPayload === 'object'
            ? (prevPayload as { turn_id?: unknown }).turn_id
            : undefined;
        const isThinkingFrame =
          incomingType === 'thinking_interlude' ||
          incomingType === 'thinking_audio' ||
          incomingType === 'thinking_audio_failed';
        if (
          isThinkingFrame &&
          prevPayload &&
          typeof prevPayload === 'object' &&
          typeof incomingTurn === 'string' &&
          incomingTurn === prevTurn
        ) {
          const rp = rawPayload as Record<string, unknown>;
          const pp = prevPayload as Record<string, unknown>;
          outgoingPayload = {
            ...pp,
            type: rp.type,
            thinking_text: rp.thinking_text ?? pp.thinking_text,
            guest_name: rp.guest_name !== undefined ? rp.guest_name : pp.guest_name,
            language_code_key: rp.language_code_key ?? pp.language_code_key,
            thinkingAudioBase64:
              incomingType === 'thinking_audio' && typeof rp.audioBase64 === 'string'
                ? rp.audioBase64
                : pp.thinkingAudioBase64,
            thinking_audio_failed:
              incomingType === 'thinking_audio_failed' ? true : pp.thinking_audio_failed,
            utterance_kind: rp.utterance_kind ?? pp.utterance_kind,
            turn_id: rp.turn_id ?? pp.turn_id,
          } as typeof rawPayload;
        } else if (
          rawPayload &&
          typeof rawPayload === 'object' &&
          incomingType === 'assistant_audio_update' &&
          typeof (rawPayload as { turn_id?: unknown }).turn_id === 'string' &&
          prevPayload &&
          typeof prevPayload === 'object' &&
          (prevPayload as { turn_id?: unknown }).turn_id === (rawPayload as { turn_id: string }).turn_id
        ) {
          const rp = rawPayload as Record<string, unknown>;
          const pp = prevPayload as Record<string, unknown>;
          const unitBacked = isUnitBackedNarrationPlan(rp) || isUnitBackedNarrationPlan(pp);
          const chunkIndex =
            typeof rp.tts_chunk_index === 'number' && Number.isInteger(rp.tts_chunk_index)
              ? rp.tts_chunk_index
              : null;
          if (rp.tts_streaming === true && chunkIndex !== null && unitBacked) {
            const prevSlots = Array.isArray(pp.tts_clip_slots)
              ? ([...(pp.tts_clip_slots as TtsClipSlot[])] as TtsClipSlot[])
              : [];
            const nextSlots = mergeTtsClipSlot(prevSlots, {
              turnId: rp.turn_id as string,
              segmentIndex: chunkIndex,
              audioBase64: typeof rp.audioBase64 === 'string' ? rp.audioBase64 : null,
              audioUnavailable: rp.audioUnavailable === true,
              unitId:
                unitIdFromPlanSegment(rp, chunkIndex) ?? unitIdFromPlanSegment(pp, chunkIndex),
            });
            outgoingPayload = { ...rp, tts_clip_slots: nextSlots } as typeof rawPayload;
          } else if (
            rp.tts_streaming === true &&
            typeof rp.audioBase64 === 'string' &&
            rp.audioBase64.length > 0
          ) {
            const prevQueue = Array.isArray(pp.tts_audio_queue)
              ? ([...(pp.tts_audio_queue as string[])] as string[])
              : [];
            prevQueue.push(rp.audioBase64 as string);
            outgoingPayload = { ...rp, tts_audio_queue: prevQueue } as typeof rawPayload;
          } else if (rp.tts_streaming === false) {
            const hasClipSlots =
              Array.isArray(rp.tts_clip_slots) || Array.isArray(pp.tts_clip_slots);
            outgoingPayload = {
              ...rp,
              tts_audio_queue:
                unitBacked && hasClipSlots
                  ? []
                  : mergeTtsAudioQueue(rp.tts_audio_queue, pp.tts_audio_queue),
              tts_clip_slots: Array.isArray(rp.tts_clip_slots) && (rp.tts_clip_slots as unknown[]).length > 0
                ? rp.tts_clip_slots
                : Array.isArray(pp.tts_clip_slots)
                  ? pp.tts_clip_slots
                  : rp.tts_clip_slots,
            } as typeof rawPayload;
          }
        }

        if (
          outgoingPayload &&
          typeof outgoingPayload === 'object' &&
          prevPayload &&
          typeof prevPayload === 'object' &&
          (outgoingPayload as { turn_id?: unknown }).turn_id ===
            (prevPayload as { turn_id?: unknown }).turn_id
        ) {
          const pp = prevPayload as Record<string, unknown>;
          const op = outgoingPayload as Record<string, unknown>;
          if (pp.thinkingAudioBase64 && !op.thinkingAudioBase64) {
            outgoingPayload = {
              ...op,
              thinkingAudioBase64: pp.thinkingAudioBase64,
              thinking_text: op.thinking_text ?? pp.thinking_text,
            } as typeof rawPayload;
          }
        }

        entry!.payload = outgoingPayload ?? null;
        entry!.onMessage(nextAfterGuard, entry!.payload);
      } catch (err) {
        console.error('Failed to parse WS message:', err);
      }
    };

    socket.onclose = () => {
      if (socketGeneration !== outboundDispatcherFor(url).currentSocketGeneration()) {
        return;
      }
      entry!.setPhase('reconnecting');
      hasConnectedOnceByUrl.set(url, true);
      sharedByUrl.delete(url);
      if (entry!.refCount > 0) {
        setIsConnecting(false);
        entry!.onConnected(false);
        setIsConnecting(true);
      }
      if (reconnectingDebounceRef.current) {
        clearTimeout(reconnectingDebounceRef.current);
        reconnectingDebounceRef.current = null;
      }
      reconnectingDebounceRef.current = setTimeout(() => {
        const current = connectionPhaseByUrl.get(url);
        if (current === 'reconnecting') {
          connectionPhaseByUrl.set(url, 'offline');
          notifyPhaseListeners(url);
        }
        reconnectingDebounceRef.current = null;
      }, RECONNECT_DEBOUNCE_MS);
      if (graceTimerRef.current) {
        clearTimeout(graceTimerRef.current);
        graceTimerRef.current = null;
      }
      const delay = Math.min(
        INITIAL_BACKOFF_MS * 2 ** backoffAttemptRef.current,
        MAX_BACKOFF_MS
      );
      backoffAttemptRef.current = Math.min(backoffAttemptRef.current + 1, 10);
      if ((import.meta as unknown as { env?: { DEV?: boolean } }).env?.DEV) {
        console.warn(
          'CLARA WebSocket disconnected at',
          url,
          '— Retrying in',
          delay,
          'ms. Ensure backend is running.'
        );
      }
      reconnectTimerRef.current = setTimeout(() => {
        reconnectTimerRef.current = null;
        setReconnectTrigger((t) => t + 1);
      }, delay);
    };

    socket.onerror = (event) => {
      if ((import.meta as unknown as { env?: { DEV?: boolean } }).env?.DEV) {
        console.error('CLARA WebSocket error event:', event);
      }
      // Keep UI responsive: mark disconnected/reconnecting until close/backoff path settles.
      entry!.onConnected(false);
      entry!.setPhase('reconnecting');
    };

    return () => {
      removePhaseListener();
      if (graceTimerRef.current) {
        clearTimeout(graceTimerRef.current);
        graceTimerRef.current = null;
      }
      if (reconnectingDebounceRef.current) {
        clearTimeout(reconnectingDebounceRef.current);
        reconnectingDebounceRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      const e = entry!;
      e.refCount--;
      e.onConnected = NOOP;
      e.onMessage = NOOP;
      entryRef.current = null;
    };
  }, [url, reconnectTrigger, authenticatedUrl]);

  const sendMessage = useCallback((msg: any): boolean => {
    const dispatcher = outboundDispatcherFor(url);
    const epoch = minAppliedBackendGenFloorByUrl.get(url) ?? 0;
    const accepted = dispatcher.enqueue(msg, epoch);
    const entry = entryRef.current ?? sharedByUrl.get(url);
    if (entry?.socket) {
      dispatcher.flush(entry.socket, entry.socketGeneration);
    }
    return accepted;
  }, [url]);

  const setManualState = useCallback((newState: number, newPayload?: any) => {
    stateRef.current = newState;
    const entry = entryRef.current ?? sharedByUrl.get(url);
    if (entry) {
      entry.state = newState;
      if (newPayload !== undefined) entry.payload = newPayload;
    }
    setState(newState);
    if (newPayload !== undefined) setPayload(newPayload);
  }, [url]);

  const retryConnect = useCallback(() => {
    const entry = sharedByUrl.get(url);
    if (entry?.socket) {
      entry.socket.close();
      sharedByUrl.delete(url);
    }
    backoffAttemptRef.current = 0;
    setReconnectTrigger((t) => t + 1);
  }, [url]);

  return {
    state,
    payload,
    isConnected,
    isConnecting,
    hasAttemptedConnect,
    connectionPhase,
    showOfflineBanner,
    sendMessage,
    setManualState,
    retryConnect,
    appliedSessionGen,
    stalePayloadDropCount,
    bumpSessionGenForReset,
    isStalePayloadGen,
    wireStaleDropCount,
  };
}

/** Diagnostics for window.claraDebug — read-only singleton snapshot per ws URL */
/** Imperative escape hatch: singleton route must be sleep before new runtime syncs WS UI. */
export function forceSingletonWsRouteSleep(url: string) {
  const e = sharedByUrl.get(url);
  if (!e) return;
  e.state = 0;
  e.payload = null;
}

export function peekClaraWsDiagnostics(url: string) {
  const e = sharedByUrl.get(url);
  if (!e) {
    return {
      connected: false as const,
      floorGen: minAppliedBackendGenFloorByUrl.get(url) ?? 0,
      pendingOutbound: outboundDispatcherFor(url).snapshot().pending.length,
    };
  }
  return {
    connected: true as const,
    socketReadyState: e.socket.readyState,
    socketGeneration: e.socketGeneration,
    pendingOutbound: outboundDispatcherFor(url).snapshot().pending.length,
    entryState: e.state,
    appliedBackendGen: e.appliedBackendGen,
    lastAppliedWireSeq: e.lastAppliedWireSeq,
    stalePayloadDrops: e.stalePayloadDrops,
    wireStaleDrops: e.wireStaleDrops,
    floorGen: minAppliedBackendGenFloorByUrl.get(url) ?? 0,
  };
}
