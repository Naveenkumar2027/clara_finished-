/**
 * Isolated thinking-TTS player. Must not touch ACK or the response scheduler.
 * Play-once per turn: never restart/interrupt an in-flight thinking utterance
 * for the same turnId (prevents partial speech from re-entrant play).
 */

export type ThinkingTtsPlayer = {
  play: (audioBase64: string, turnId: string, meta?: { text?: string }) => void;
  stop: () => void;
  reset: () => void;
  playing: () => boolean;
  activeTurnId: () => string | null;
};

export function createThinkingTtsPlayer(opts?: {
  AudioCtor?: typeof Audio;
  onEnded?: (turnId: string) => void;
  onError?: (turnId: string) => void;
  onStarted?: (turnId: string, meta?: { text?: string; audioBytes: number }) => void;
}): ThinkingTtsPlayer {
  const AudioCtor = opts?.AudioCtor ?? (typeof Audio !== 'undefined' ? Audio : undefined);
  let current: HTMLAudioElement | null = null;
  let currentTurn = '';
  /** Turns that already started thinking audio — ignore re-play for that turn. */
  const startedTurns = new Set<string>();

  const hardStop = () => {
    if (!current) {
      currentTurn = '';
      return;
    }
    try {
      current.onended = null;
      current.onerror = null;
      current.pause();
      current.removeAttribute('src');
      current.load();
    } catch {
      // ignore
    }
    current = null;
    currentTurn = '';
  };

  return {
    play(audioBase64: string, turnId: string, meta?: { text?: string }) {
      if (!AudioCtor || !audioBase64 || !turnId) return;
      // Idempotent: never clip an in-flight or completed thinking utterance for this turn.
      if (startedTurns.has(turnId)) return;
      if (currentTurn && currentTurn !== turnId) {
        hardStop();
      }
      startedTurns.add(turnId);
      hardStop();
      const audio = new AudioCtor(`data:audio/wav;base64,${audioBase64}`);
      audio.dataset.claraChannel = 'thinking';
      audio.dataset.turnId = turnId;
      current = audio;
      currentTurn = turnId;
      audio.onended = () => {
        if (current === audio) {
          current = null;
          const tid = currentTurn;
          currentTurn = '';
          opts?.onEnded?.(tid);
        }
      };
      audio.onerror = () => {
        if (current === audio) {
          current = null;
          const tid = currentTurn;
          currentTurn = '';
          startedTurns.delete(tid);
          opts?.onError?.(tid);
        }
      };
      void audio.play()
        .then(() => {
          opts?.onStarted?.(turnId, {
            text: meta?.text,
            audioBytes: audioBase64.length,
          });
        })
        .catch(() => {
          if (current === audio) {
            current = null;
            const tid = currentTurn;
            currentTurn = '';
            startedTurns.delete(tid);
            opts?.onError?.(tid);
          }
        });
    },
    stop: hardStop,
    reset: () => {
      hardStop();
      startedTurns.clear();
    },
    playing: () => current !== null && !current.paused,
    activeTurnId: () => currentTurn || null,
  };
}
