export interface WebSocketTokenResponse {
  token: string;
  expires_at: number;
  expires_in: number;
}

export function websocketTokenEndpoint(wsUrl: string): string {
  const base = globalThis.location?.href ?? 'http://localhost/';
  const parsed = new URL(wsUrl, base);
  parsed.protocol = parsed.protocol === 'wss:' ? 'https:' : 'http:';
  parsed.pathname = '/api/ws-token';
  parsed.search = '';
  parsed.hash = '';
  return parsed.toString();
}

export function appendWebSocketToken(wsUrl: string, token: string): string {
  const base = globalThis.location?.href ?? 'http://localhost/';
  const parsed = new URL(wsUrl, base);
  parsed.searchParams.set('token', token);
  return parsed.toString();
}

/** Fetches a fresh handshake credential. The token is returned in memory only. */
export async function authenticatedWebSocketUrl(
  wsUrl: string,
  fetchImpl: typeof fetch = fetch,
  allowUnsignedDevelopment = false,
): Promise<string> {
  let response: Response;
  try {
    response = await fetchImpl(websocketTokenEndpoint(wsUrl), {
      method: 'POST',
      mode: 'cors',
      cache: 'no-store',
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    });
  } catch (error) {
    if (allowUnsignedDevelopment) return wsUrl;
    throw error;
  }
  if (!response.ok) {
    if (allowUnsignedDevelopment) return wsUrl;
    throw new Error(`WebSocket bootstrap failed (${response.status})`);
  }
  const body = (await response.json()) as Partial<WebSocketTokenResponse>;
  if (typeof body.token !== 'string' || body.token.length < 16) {
    throw new Error('WebSocket bootstrap returned an invalid credential');
  }
  return appendWebSocketToken(wsUrl, body.token);
}
