import { describe, expect, it, vi } from 'vitest';
import { createThinkingTtsPlayer } from '../thinkingTtsPlayer';

describe('thinking TTS player', () => {
  it('uses a dedicated thinking channel and notifies on natural end', () => {
    const instances: FakeAudio[] = [];
    class FakeAudio {
      src: string;
      paused = false;
      dataset: Record<string, string> = {};
      onended: (() => void) | null = null;
      onerror: (() => void) | null = null;
      constructor(src: string) {
        this.src = src;
        instances.push(this);
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

    const onEnded = vi.fn();
    const player = createThinkingTtsPlayer({
      AudioCtor: FakeAudio as unknown as typeof Audio,
      onEnded,
    });
    player.play('d2F2', 'turn-a');
    expect(instances).toHaveLength(1);
    expect(instances[0]?.dataset.claraChannel).toBe('thinking');
    expect(instances[0]?.dataset.turnId).toBe('turn-a');
    instances[0]?.onended?.();
    expect(onEnded).toHaveBeenCalledWith('turn-a');
  });

  it('ignores a second play for the same turnId (prevents partial restart)', () => {
    const instances: FakeAudio[] = [];
    class FakeAudio {
      src: string;
      paused = false;
      dataset: Record<string, string> = {};
      onended: (() => void) | null = null;
      onerror: (() => void) | null = null;
      constructor(src: string) {
        this.src = src;
        instances.push(this);
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

    const player = createThinkingTtsPlayer({
      AudioCtor: FakeAudio as unknown as typeof Audio,
    });
    player.play('first', 't1');
    player.play('second', 't1');
    expect(instances).toHaveLength(1);
    expect(instances[0]?.src).toContain('first');
  });
});
