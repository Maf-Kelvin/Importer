import { ApiError, errorFromResponse } from './errors';

/**
 * HTTP client.
 *  - Access token lives in MEMORY only. The refresh token is an httpOnly cookie that JavaScript cannot read.
 *  - On 401 it refreshes once and retries. Concurrent 401s share a single refresh call, and
 *    several browser tabs coordinate (Web Locks + BroadcastChannel) because refresh tokens rotate:
 *    a second refresh with the old token would sign the user out.
 *  - Create/update calls carry an Idempotency-Key when the caller provides one.
 */
type Query = Record<string, string | number | boolean | null | undefined>;

interface RequestOptions {
  query?: Query;
  json?: unknown;
  form?: Record<string, string>;
  idempotencyKey?: string;
  signal?: AbortSignal;
  skipRefresh?: boolean; // do not try to refresh on 401 (login, refresh itself)
}

interface Config {
  baseUrl: string;
  fetchImpl: typeof fetch;
  onAuthLost: () => void;
}

const config: Config = {
  baseUrl: '/api/v1',
  fetchImpl: (...args) => fetch(...args),
  onAuthLost: () => undefined,
};

let accessToken: string | null = null;
let expiresAt = 0; // epoch ms
let tokenVersion = 0; // bumped whenever ANOTHER tab hands us a newer token
let refreshInFlight: Promise<string | null> | null = null;
let channel: BroadcastChannel | null = null;

type BroadcastMessage = { type: 'token'; token: string; expiresAt: number } | { type: 'logout' };

function getChannel(): BroadcastChannel | null {
  if (channel || typeof BroadcastChannel === 'undefined') return channel;
  channel = new BroadcastChannel('importer-auth');
  channel.onmessage = (event: MessageEvent<BroadcastMessage>) => {
    const msg = event.data;
    if (msg.type === 'token') {
      accessToken = msg.token;
      expiresAt = msg.expiresAt;
      tokenVersion += 1;
    } else if (msg.type === 'logout') {
      accessToken = null;
      expiresAt = 0;
      config.onAuthLost();
    }
  };
  return channel;
}

export function configureApi(partial: Partial<Config>): void {
  Object.assign(config, partial);
}

export const session = {
  get token(): string | null {
    return accessToken;
  },
  get expiresAt(): number {
    return expiresAt;
  },
  set(token: string, expiresInSeconds: number, broadcast = true): void {
    accessToken = token;
    expiresAt = Date.now() + expiresInSeconds * 1000;
    if (broadcast) getChannel()?.postMessage({ type: 'token', token, expiresAt } satisfies BroadcastMessage);
  },
  clear(broadcast = true): void {
    accessToken = null;
    expiresAt = 0;
    if (broadcast) getChannel()?.postMessage({ type: 'logout' } satisfies BroadcastMessage);
  },
};

/** Test helper. */
export function resetApiStateForTests(): void {
  accessToken = null;
  expiresAt = 0;
  tokenVersion = 0;
  refreshInFlight = null;
}

function buildUrl(path: string, query?: Query): string {
  const url = `${config.baseUrl}${path}`;
  if (!query) return url;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

async function send(method: string, path: string, opts: RequestOptions, token: string | null): Promise<Response> {
  const headers: Record<string, string> = { Accept: 'application/json', 'X-Auth-Mode': 'cookie' };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (opts.idempotencyKey) headers['Idempotency-Key'] = opts.idempotencyKey;

  let body: BodyInit | undefined;
  if (opts.form) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded';
    body = new URLSearchParams(opts.form).toString();
  } else if (opts.json !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.json);
  }

  try {
    return await config.fetchImpl(buildUrl(path, opts.query), {
      method,
      headers,
      body,
      signal: opts.signal,
      credentials: 'same-origin',
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err;
    throw new ApiError(0, 'Network error');
  }
}

interface TokenResponse {
  access_token: string;
  expires_in: number;
}

async function withCrossTabLock<T>(fn: () => Promise<T>): Promise<T> {
  const locks = typeof navigator !== 'undefined' ? navigator.locks : undefined;
  return locks ? locks.request('importer-refresh', fn) : fn();
}

/** Get a new access token using the refresh cookie. Returns null if the session is over. */
export function refreshSession(): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight;
  getChannel();
  const versionBefore = tokenVersion;
  refreshInFlight = withCrossTabLock(async () => {
    // Another tab refreshed while we waited for the lock: use its token, do not rotate again.
    if (tokenVersion !== versionBefore && accessToken && Date.now() < expiresAt) return accessToken;
    const res = await send('POST', '/auth/refresh', {}, null);
    if (res.status === 401 || res.status === 403) {
      session.clear();
      return null;
    }
    if (!res.ok) throw await errorFromResponse(res);
    const data = (await res.json()) as TokenResponse;
    session.set(data.access_token, data.expires_in);
    return data.access_token;
  }).finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

export async function request<T>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
  let res = await send(method, path, opts, accessToken);

  if (res.status === 401 && !opts.skipRefresh) {
    const token = await refreshSession();
    if (token) {
      res = await send(method, path, opts, token);
    } else {
      config.onAuthLost();
    }
  }

  if (!res.ok) throw await errorFromResponse(res);
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export const api = {
  get: <T>(path: string, query?: Query, signal?: AbortSignal) => request<T>('GET', path, { query, signal }),
  post: <T>(path: string, json?: unknown, opts: Omit<RequestOptions, 'json'> = {}) => request<T>('POST', path, { ...opts, json }),
  put: <T>(path: string, json?: unknown, opts: Omit<RequestOptions, 'json'> = {}) => request<T>('PUT', path, { ...opts, json }),
  delete: <T = void>(path: string, opts: RequestOptions = {}) => request<T>('DELETE', path, opts),
};
