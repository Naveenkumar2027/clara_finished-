/**
 * Thinking-interlude playback gate.
 * Final response audio/cards may become ready early; they must wait until
 * thinking TTS finishes, fails, or times out. Never cancel thinking TTS
 * because the answer arrived.
 */

export const THINKING_TTS_WATCHDOG_MS = 10_000;

export type ThinkingGateSnapshot = {
  turnId: string | null;
  sentence: string;
  ttsPlaying: boolean;
  ttsFinished: boolean;
  ttsFailed: boolean;
  responseStarted: boolean;
};

export const EMPTY_THINKING_GATE: ThinkingGateSnapshot = {
  turnId: null,
  sentence: '',
  ttsPlaying: false,
  ttsFinished: false,
  ttsFailed: false,
  responseStarted: false,
};

export function beginThinkingTurn(
  prev: ThinkingGateSnapshot,
  opts: { turnId: string; sentence: string },
): ThinkingGateSnapshot {
  const turnId = opts.turnId.trim();
  const sentence = opts.sentence.trim();
  if (!turnId) return prev;
  return {
    turnId,
    sentence: sentence || prev.sentence,
    ttsPlaying: false,
    ttsFinished: false,
    ttsFailed: false,
    responseStarted: false,
  };
}

/** Bind a local pending turn to the backend turn_id without resetting TTS flags. */
export function rebindThinkingTurn(
  prev: ThinkingGateSnapshot,
  turnId: string,
): ThinkingGateSnapshot {
  const next = turnId.trim();
  if (!next || !prev.turnId) return prev;
  if (prev.turnId === next) return prev;
  if (!prev.turnId.startsWith('pending:')) return prev;
  return { ...prev, turnId: next };
}

export function attachThinkingSentence(
  prev: ThinkingGateSnapshot,
  sentence: string,
): ThinkingGateSnapshot {
  const text = sentence.trim();
  if (!text || !prev.turnId) return prev;
  return { ...prev, sentence: text };
}

export function markThinkingTtsPlaying(prev: ThinkingGateSnapshot): ThinkingGateSnapshot {
  if (!prev.turnId || prev.ttsFinished || prev.ttsFailed) return prev;
  return { ...prev, ttsPlaying: true };
}

export function markThinkingTtsFinished(
  prev: ThinkingGateSnapshot,
  turnId: string,
): ThinkingGateSnapshot {
  if (!prev.turnId || prev.turnId !== turnId) return prev;
  return { ...prev, ttsPlaying: false, ttsFinished: true };
}

export function markThinkingTtsFailed(
  prev: ThinkingGateSnapshot,
  turnId?: string | null,
): ThinkingGateSnapshot {
  if (!prev.turnId) return prev;
  if (turnId && prev.turnId !== turnId) return prev;
  return { ...prev, ttsPlaying: false, ttsFailed: true };
}

export function markResponseStarted(
  prev: ThinkingGateSnapshot,
  turnId: string,
): ThinkingGateSnapshot {
  if (!prev.turnId || prev.turnId !== turnId) return prev;
  if (!canStartResponsePlayback(prev, turnId)) return prev;
  return { ...prev, responseStarted: true };
}

export function resetThinkingGate(): ThinkingGateSnapshot {
  return { ...EMPTY_THINKING_GATE };
}

/** Visible thinking stage: active turn that has not finished or failed. */
export function shouldShowThinkingInterlude(gate: ThinkingGateSnapshot): boolean {
  if (!gate.turnId) return false;
  if (gate.ttsFailed) return false;
  if (gate.ttsFinished || gate.responseStarted) return false;
  return true;
}

/**
 * Block final response TTS and card presentation until thinking TTS
 * completes. Fail-open on TTS failure so the answer is never deadlocked.
 */
export function shouldBlockResponsePlayback(gate: ThinkingGateSnapshot): boolean {
  if (!gate.turnId) return false;
  if (gate.ttsFailed) return false;
  if (gate.ttsFinished) return false;
  return true;
}

export function canStartResponsePlayback(
  gate: ThinkingGateSnapshot,
  responseTurnId: string,
): boolean {
  const tid = (responseTurnId || '').trim();
  if (!tid) return false;
  if (gate.responseStarted && (gate.turnId === tid || gate.turnId?.startsWith('pending:'))) {
    return false;
  }
  if (!gate.turnId) return true;
  if (gate.turnId !== tid) {
    // Local pending id must still block backend-turn audio until rebound + TTS done.
    if (gate.turnId.startsWith('pending:')) {
      if (gate.ttsFailed || gate.ttsFinished) return true;
      return false;
    }
    return true;
  }
  if (gate.ttsFailed) return true;
  return gate.ttsFinished;
}
