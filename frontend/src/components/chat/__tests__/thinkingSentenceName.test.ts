import { describe, expect, it } from 'vitest';
import { splitTrailingName } from '../ThinkingInterlude';

describe('thinking sentence name emphasis', () => {
  it('highlights a trailing English guest name', () => {
    const parts = splitTrailingName(
      'Let me bring together some of the best things about the college for you, Naveen.',
    );
    expect(parts.name).toBe('Naveen');
    expect(parts.after).toBe('.');
  });

  it('leaves sentences without a trailing name untouched', () => {
    const parts = splitTrailingName('Let me check the fee details for the program you are asking about.');
    expect(parts.name).toBeNull();
    expect(parts.before).toContain('fee details');
  });
});
