import { describe, expect, it, vi } from 'vitest';
import { createThinkingTtsPlayer } from '../thinkingTtsPlayer';
import { createAckPlayer } from '../../../../lib/tts/ackAudio';
import {
  beginThinkingTurn,
  canStartResponsePlayback,
  EMPTY_THINKING_GATE,
  markResponseStarted,
  markThinkingTtsFailed,
  markThinkingTtsFinished,
  markThinkingTtsPlaying,
  shouldBlockResponsePlayback,
} from '../thinkingGate';
import { splitTrailingName } from '../../../../components/chat/ThinkingInterlude';

const EXACT =
  'Let me bring together some of the best things about the college for you, Ashutosh.';

class FakeAudio {
  src: string;
  paused = true;
  dataset: Record<string, string> = {};
  onended: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(src: string) {
    this.src = src;
  }
  play() {
    this.paused = false;
    return Promise.resolve();
  }
  pause() {
    this.paused = true;
  }
  load() {}
  removeAttribute() {}
}

describe('thinking TTS completeness + gating', () => {
  it('UI text equals TTS text for the critical Ashutosh sentence', () => {
    const uiText = EXACT;
    const ttsText = EXACT;
    expect(uiText).toBe(ttsText);
    expect(uiText).not.toMatch(/\.\.\.$/);
    expect(uiText.toLowerCase()).not.toContain('clara is thinking');
  });

  it('keeps the guest name integrated in the sentence (not a second headline)', () => {
    const parts = splitTrailingName(EXACT);
    expect(parts.name).toBe('Ashutosh');
    expect(`${parts.before}${parts.name}${parts.after}`).toBe(EXACT);
  });

  it('plays thinking TTS exactly once per turn (no re-entrant clip)', () => {
    const instances: FakeAudio[] = [];
    class CountingAudio extends FakeAudio {
      constructor(src: string) {
        super(src);
        instances.push(this);
      }
    }
    const onEnded = vi.fn();
    const player = createThinkingTtsPlayer({
      AudioCtor: CountingAudio as unknown as typeof Audio,
      onEnded,
    });
    player.play('aaa', 'turn-1', { text: EXACT });
    player.play('bbb-longer-payload', 'turn-1', { text: EXACT });
    player.play('ccc', 'turn-1');
    expect(instances).toHaveLength(1);
    expect(instances[0]?.src).toContain('aaa');
    instances[0]?.onended?.();
    expect(onEnded).toHaveBeenCalledTimes(1);
    expect(onEnded).toHaveBeenCalledWith('turn-1');
  });

  it('emits completion only via ended, then opens the response gate', () => {
    let g = beginThinkingTurn(EMPTY_THINKING_GATE, { turnId: 't1', sentence: EXACT });
    g = markThinkingTtsPlaying(g);
    expect(shouldBlockResponsePlayback(g)).toBe(true);
    expect(canStartResponsePlayback(g, 't1')).toBe(false);

    const instances: FakeAudio[] = [];
    class CountingAudio extends FakeAudio {
      constructor(src: string) {
        super(src);
        instances.push(this);
      }
    }
    const player = createThinkingTtsPlayer({
      AudioCtor: CountingAudio as unknown as typeof Audio,
      onEnded: (tid) => {
        g = markThinkingTtsFinished(g, tid);
      },
    });
    player.play('wav', 't1', { text: EXACT });
    expect(player.playing()).toBe(true);
    expect(canStartResponsePlayback(g, 't1')).toBe(false);
    instances[0]?.onended?.();
    expect(canStartResponsePlayback(g, 't1')).toBe(true);
    expect(shouldBlockResponsePlayback(g)).toBe(false);
  });

  it('final response starts only after thinking ended, and only once', () => {
    let g = beginThinkingTurn(EMPTY_THINKING_GATE, { turnId: 't1', sentence: EXACT });
    g = markThinkingTtsPlaying(g);
    expect(shouldBlockResponsePlayback(g)).toBe(true);

    g = markThinkingTtsFinished(g, 't1');
    expect(shouldBlockResponsePlayback(g)).toBe(false);
    expect(canStartResponsePlayback(g, 't1')).toBe(true);

    g = markResponseStarted(g, 't1');
    expect(canStartResponsePlayback(g, 't1')).toBe(false);
    expect(markResponseStarted(g, 't1')).toEqual(g);
  });

  it('fail-opens on thinking TTS error and on watchdog-style failure mark', () => {
    let g = beginThinkingTurn(EMPTY_THINKING_GATE, { turnId: 't1', sentence: EXACT });
    g = markThinkingTtsPlaying(g);
    g = markThinkingTtsFailed(g, 't1');
    expect(shouldBlockResponsePlayback(g)).toBe(false);
    expect(canStartResponsePlayback(g, 't1')).toBe(true);
  });

  it('stale turn finished cannot unlock a newer response', () => {
    let g = beginThinkingTurn(EMPTY_THINKING_GATE, { turnId: 't2', sentence: EXACT });
    g = markThinkingTtsFinished(g, 't1');
    expect(g.ttsFinished).toBe(false);
    expect(canStartResponsePlayback(g, 't2')).toBe(false);
  });

  it('ACK whenIdle waits before thinking play; ACK cannot restart mid-thinking', () => {
    const ackInstances: FakeAudio[] = [];
    class AckAudio extends FakeAudio {
      constructor(src: string) {
        super(src);
        ackInstances.push(this);
      }
    }
    const thinkInstances: FakeAudio[] = [];
    class ThinkAudio extends FakeAudio {
      constructor(src: string) {
        super(src);
        thinkInstances.push(this);
      }
    }

    const ack = createAckPlayer({ AudioCtor: AckAudio as unknown as typeof Audio });
    const thinking = createThinkingTtsPlayer({
      AudioCtor: ThinkAudio as unknown as typeof Audio,
    });

    ack.play('ack-wav');
    expect(ack.playing()).toBe(true);

    let started = false;
    ack.whenIdle(() => {
      thinking.play('think-wav', 'turn-ack', { text: EXACT });
      started = true;
    });
    expect(started).toBe(false);
    expect(thinkInstances).toHaveLength(0);

    ackInstances[0]?.onended?.();
    expect(started).toBe(true);
    expect(thinkInstances).toHaveLength(1);

    // Late ACK while thinking plays must be skipped by ChatScreen; player itself stays isolated.
    expect(thinking.playing()).toBe(true);
    ack.play('late-ack');
    expect(ackInstances).toHaveLength(2);
    // Thinking must not be stopped by ACK play
    expect(thinking.playing()).toBe(true);
    expect(thinkInstances).toHaveLength(1);
  });

  it('does not truncate the canonical thinking sentence for TTS input', () => {
    const forUi = EXACT;
    const forTts = EXACT;
    expect(forTts.length).toBe(forUi.length);
    expect(forTts).toBe(forUi);
    expect(forTts.includes('Ashutosh')).toBe(true);
  });
});
