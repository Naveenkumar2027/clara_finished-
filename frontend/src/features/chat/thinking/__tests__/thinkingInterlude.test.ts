import { describe, expect, it } from 'vitest';
import {
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
} from '../thinkingGate';
import { composeThinkingBridge, inferThinkingTopic, thinkingBridgeFallback } from '../thinkingBridge';

describe('thinking bridge language and name', () => {
  it('uses the current language fallback, not English, for Kannada', () => {
    const s = composeThinkingBridge({ query: 'ಶುಲ್ಕ ಎಷ್ಟು', language: 'Kannada' });
    expect(s).toMatch(/[\u0C80-\u0CFF]/);
    expect(s.toLowerCase()).not.toContain('processing');
    expect(s.toLowerCase()).not.toContain('let me');
  });

  it('keeps optimistic FE bridge neutral until backend semantic text arrives', () => {
    const named = composeThinkingBridge({
      query: 'How good is the college?',
      language: 'English',
      guestName: 'Rahul',
    });
    // Frontend no longer invents topic templates; backend owns contextual text.
    expect(named.toLowerCase()).not.toContain('department head');
    expect(named.toLowerCase()).not.toContain('processing');
  });

  it('omits fabricated entity claims in the optimistic fallback', () => {
    const s = composeThinkingBridge({ query: 'Who is the principal?', language: 'English' });
    expect(s.toLowerCase()).not.toContain('department head');
  });

  it('keeps fallback sentences short and non-factual', () => {
    const s = composeThinkingBridge({ query: 'Tell me about placements.', language: 'English' });
    const words = s.split(/\s+/).filter(Boolean);
    expect(words.length).toBeGreaterThanOrEqual(4);
    expect(words.length).toBeLessThanOrEqual(16);
    expect(s.toLowerCase()).not.toContain('excellent placements');
  });

  it('does not classify topics on the frontend anymore', () => {
    expect(inferThinkingTopic('Who is the HOD?')).toBe('general');
    expect(inferThinkingTopic('What about the buses?')).toBe('general');
  });

  it('fallback is language-aware', () => {
    expect(thinkingBridgeFallback('Hindi')).toMatch(/[\u0900-\u097F]/);
  });
});

describe('thinking TTS / response race', () => {
  it('blocks the final response until thinking TTS finishes even if RAG is ready', () => {
    let g = beginThinkingTurn(EMPTY_THINKING_GATE, {
      turnId: 't1',
      sentence: 'Let me bring that together for you.',
    });
    expect(shouldShowThinkingInterlude(g)).toBe(true);
    // t=0.3 RAG ready
    expect(shouldBlockResponsePlayback(g)).toBe(true);
    expect(canStartResponsePlayback(g, 't1')).toBe(false);
    // t=0.4 thinking TTS begins
    g = markThinkingTtsPlaying(g);
    expect(g.ttsPlaying).toBe(true);
    expect(canStartResponsePlayback(g, 't1')).toBe(false);
    // t=1.5 still waiting
    expect(shouldBlockResponsePlayback(g)).toBe(true);
    // t=2.4 thinking TTS finishes
    g = markThinkingTtsFinished(g, 't1');
    expect(canStartResponsePlayback(g, 't1')).toBe(true);
    g = markResponseStarted(g, 't1');
    expect(g.responseStarted).toBe(true);
    expect(canStartResponsePlayback(g, 't1')).toBe(false);
    expect(shouldShowThinkingInterlude(g)).toBe(false);
  });

  it('does not start the final response twice', () => {
    let g = beginThinkingTurn(EMPTY_THINKING_GATE, { turnId: 't1', sentence: 'bridge' });
    g = markThinkingTtsFinished(g, 't1');
    g = markResponseStarted(g, 't1');
    const again = markResponseStarted(g, 't1');
    expect(again).toEqual(g);
  });

  it('fails open if thinking TTS errors so the answer is not deadlocked', () => {
    let g = beginThinkingTurn(EMPTY_THINKING_GATE, { turnId: 't1', sentence: 'bridge' });
    g = markThinkingTtsPlaying(g);
    g = markThinkingTtsFailed(g, 't1');
    expect(shouldBlockResponsePlayback(g)).toBe(false);
    expect(canStartResponsePlayback(g, 't1')).toBe(true);
    expect(shouldShowThinkingInterlude(g)).toBe(false);
  });

  it('ignores stale thinking-finished events from a previous turn', () => {
    let g = beginThinkingTurn(EMPTY_THINKING_GATE, { turnId: 't2', sentence: 'new' });
    g = markThinkingTtsFinished(g, 't1');
    expect(g.ttsFinished).toBe(false);
    expect(shouldBlockResponsePlayback(g)).toBe(true);
  });

  it('session reset clears thinking so it cannot leak', () => {
    let g = beginThinkingTurn(EMPTY_THINKING_GATE, { turnId: 't1', sentence: 'bridge' });
    g = markThinkingTtsPlaying(g);
    g = resetThinkingGate();
    expect(g.turnId).toBeNull();
    expect(shouldBlockResponsePlayback(g)).toBe(false);
    expect(shouldShowThinkingInterlude(g)).toBe(false);
  });

  it('allows a later RAG arrival after thinking TTS already finished', () => {
    let g = beginThinkingTurn(EMPTY_THINKING_GATE, { turnId: 't9', sentence: 'bridge' });
    g = markThinkingTtsFinished(g, 't9');
    expect(canStartResponsePlayback(g, 't9')).toBe(true);
  });

  it('blocks backend-turn audio while the gate is still on a pending local id', () => {
    let g = beginThinkingTurn(EMPTY_THINKING_GATE, { turnId: 'pending:1', sentence: 'bridge' });
    expect(canStartResponsePlayback(g, 'backend-turn')).toBe(false);
    g = rebindThinkingTurn(g, 'backend-turn');
    expect(g.turnId).toBe('backend-turn');
    expect(canStartResponsePlayback(g, 'backend-turn')).toBe(false);
    g = markThinkingTtsFinished(g, 'backend-turn');
    expect(canStartResponsePlayback(g, 'backend-turn')).toBe(true);
  });

  it('thinking UI must not include the old CLARA IS THINKING status copy', () => {
    const s = composeThinkingBridge({
      query: 'How good is the college?',
      language: 'English',
      guestName: 'Ashutosh',
    });
    expect(s.toLowerCase()).not.toContain('clara is thinking');
    expect(s.toLowerCase()).not.toContain('processing');
    expect(s.toLowerCase()).not.toContain('loading');
  });
});
