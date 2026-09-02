import { describe, expect, it, vi } from 'vitest';

import {
  appendWebSocketToken,
  authenticatedWebSocketUrl,
  websocketTokenEndpoint,
} from './wsTokenBootstrap';

describe('short-lived WebSocket bootstrap', () => {
  it('derives the HTTPS bootstrap endpoint', () => {
    expect(websocketTokenEndpoint('wss://clara.example/ws/clara')).toBe(
      'https://clara.example/api/ws-token',
    );
  });

  it('fetches a token without touching browser storage', async () => {
    const localStorageSpy = vi.fn();
    const sessionStorageSpy = vi.fn();
    vi.stubGlobal('localStorage', { setItem: localStorageSpy });
    vi.stubGlobal('sessionStorage', { setItem: sessionStorageSpy });
    const fetchImpl = vi.fn(async () =>
      new Response(
        JSON.stringify({ token: 'short-lived-signed-token', expires_at: 123, expires_in: 90 }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    ) as unknown as typeof fetch;

    const result = await authenticatedWebSocketUrl(
      'wss://clara.example/ws/clara',
      fetchImpl,
    );
    expect(result).toBe('wss://clara.example/ws/clara?token=short-lived-signed-token');
    expect(fetchImpl).toHaveBeenCalledOnce();
    expect(localStorageSpy).not.toHaveBeenCalled();
    expect(sessionStorageSpy).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });

  it('preserves existing query parameters', () => {
    expect(appendWebSocketToken('ws://localhost:6969/ws/clara?mode=kiosk', 'signed')).toContain(
      'mode=kiosk&token=signed',
    );
  });

  it('allows an unsigned fallback only when explicitly in development', async () => {
    const unavailable = vi.fn(async () => {
      throw new TypeError('network unavailable');
    }) as unknown as typeof fetch;
    await expect(
      authenticatedWebSocketUrl('ws://localhost:6969/ws/clara', unavailable, true),
    ).resolves.toBe('ws://localhost:6969/ws/clara');
    await expect(
      authenticatedWebSocketUrl('ws://localhost:6969/ws/clara', unavailable, false),
    ).rejects.toThrow('network unavailable');
  });

  it('keeps non-success response fallback development-only', async () => {
    const notFound = vi.fn(async () => new Response(null, { status: 404 })) as unknown as typeof fetch;
    await expect(
      authenticatedWebSocketUrl('ws://localhost:6969/ws/clara', notFound, true),
    ).resolves.toBe('ws://localhost:6969/ws/clara');
    await expect(
      authenticatedWebSocketUrl('ws://localhost:6969/ws/clara', notFound, false),
    ).rejects.toThrow('WebSocket bootstrap failed (404)');
  });
});
