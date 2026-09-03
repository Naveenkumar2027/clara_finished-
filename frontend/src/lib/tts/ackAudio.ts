/**
 * Independent ACK/earcon player. Must never touch response-TTS scheduler state.
 */

export type AckPlayer = {
  play: (audioBase64: string) => void;
  stop: () => void;
  playing: () => boolean;
  /** Register a one-shot listener for when the current ACK finishes or fails. */
  whenIdle: (cb: () => void) => void;
};

export function createAckPlayer(opts?: {
  AudioCtor?: typeof Audio;
}): AckPlayer {
  const AudioCtor = opts?.AudioCtor ?? (typeof Audio !== 'undefined' ? Audio : undefined);
  let current: HTMLAudioElement | null = null;
  let idleWaiters: Array<() => void> = [];

  const flushIdle = () => {
    const waiters = idleWaiters;
    idleWaiters = [];
    for (const cb of waiters) {
      try {
        cb();
      } catch {
        // ignore
      }
    }
  };

  const stop = () => {
    if (!current) {
      flushIdle();
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
    flushIdle();
  };

  return {
    play(audioBase64: string) {
      if (!AudioCtor || !audioBase64) return;
      stop();
      const audio = new AudioCtor(`data:audio/wav;base64,${audioBase64}`);
      audio.dataset.claraChannel = 'ack';
      current = audio;
      audio.onended = () => {
        if (current === audio) current = null;
        flushIdle();
      };
      audio.onerror = () => {
        if (current === audio) current = null;
        flushIdle();
      };
      void audio.play().catch(() => {
        if (current === audio) current = null;
        flushIdle();
      });
    },
    stop,
    playing: () => current !== null && !current.paused,
    whenIdle(cb: () => void) {
      if (!current || current.paused) {
        cb();
        return;
      }
      idleWaiters.push(cb);
    },
  };
}
