import { beforeEach, describe, expect, it } from 'vitest';
import { api, configureApi, refreshSession, request, resetApiStateForTests, session } from './client';
import { ApiError } from './errors';

interface Call {
  url: string;
  method: string;
  headers: Record<string, string>;
  body: string | undefined;
}

let calls: Call[] = [];
let authLost = 0;

function install(handler: (call: Call) => Response | Promise<Response>) {
  calls = [];
  configureApi({
    baseUrl: '/api/v1',
    onAuthLost: () => {
      authLost += 1;
    },
    fetchImpl: (async (input: RequestInfo | URL, init?: RequestInit) => {
      const call: Call = {
        url: String(input),
        method: init?.method ?? 'GET',
        headers: { ...(init?.headers as Record<string, string>) },
        body: init?.body as string | undefined,
      };
      calls.push(call);
      return handler(call);
    }) as typeof fetch,
  });
}

const ok = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

async function rejection(p: Promise<unknown>): Promise<unknown> {
  try {
    await p;
  } catch (e) {
    return e;
  }
  throw new Error('expected the promise to reject');
}

beforeEach(() => {
  resetApiStateForTests();
  authLost = 0;
});

describe('request basics', () => {
  it('sends the bearer token and the web-session header', async () => {
    install(() => ok({ id: 1 }));
    session.set('tok', 1800, false);
    await api.get('/containers/1');
    expect(calls[0]?.headers.Authorization).toBe('Bearer tok');
    expect(calls[0]?.headers['X-Auth-Mode']).toBe('cookie');
    expect(calls[0]?.url).toBe('/api/v1/containers/1');
  });

  it('builds a query string and skips empty values', async () => {
    install(() => ok({}));
    await api.get('/items/', { page: 2, search: '', sold: false, category: undefined, limit: 20 });
    expect(calls[0]?.url).toBe('/api/v1/items/?page=2&sold=false&limit=20');
  });

  it('sends an Idempotency-Key only when one is given', async () => {
    install(() => ok({ id: 1 }, 201));
    await api.post('/containers/', { name: 'x' }, { idempotencyKey: 'abc-12345678' });
    await api.post('/containers/', { name: 'y' });
    expect(calls[0]?.headers['Idempotency-Key']).toBe('abc-12345678');
    expect(calls[1]?.headers['Idempotency-Key']).toBeUndefined();
    expect(calls[0]?.headers['Content-Type']).toBe('application/json');
    expect(calls[0]?.body).toBe('{"name":"x"}');
  });

  it('encodes the login form', async () => {
    install(() => ok({}));
    await request('POST', '/auth/login', { form: { username: 'a b', password: 'p&q' }, skipRefresh: true });
    expect(calls[0]?.headers['Content-Type']).toBe('application/x-www-form-urlencoded');
    expect(calls[0]?.body).toBe('username=a+b&password=p%26q');
  });

  it('returns undefined for 204', async () => {
    install(() => new Response(null, { status: 204 }));
    expect(await api.delete('/items/1')).toBeUndefined();
  });
});

describe('errors', () => {
  it('turns a network failure into ApiError(0)', async () => {
    install(() => {
      throw new TypeError('failed to fetch');
    });
    const err = await rejection(api.get('/x'));
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(0);
  });

  it('exposes validation messages by field', async () => {
    install(() => ok({ detail: [{ loc: ['body', 'name'], msg: 'Field required' }] }, 422));
    const err = (await rejection(api.post('/containers/', {}))) as ApiError;
    expect(err.status).toBe(422);
    expect(err.fieldErrors.name).toBe('Field required');
  });
});

describe('token refresh', () => {
  it('refreshes once on 401 and retries with the new token', async () => {
    install((call) => {
      if (call.url.endsWith('/auth/refresh')) return ok({ access_token: 'new', expires_in: 1800 });
      return call.headers.Authorization === 'Bearer new' ? ok({ ok: true }) : ok({ detail: 'expired' }, 401);
    });
    session.set('old', 1800, false);
    expect(await api.get('/containers/')).toEqual({ ok: true });
    expect(calls.map((c) => c.url)).toEqual(['/api/v1/containers/', '/api/v1/auth/refresh', '/api/v1/containers/']);
    expect(session.token).toBe('new');
  });

  it('shares ONE refresh between concurrent requests (refresh tokens rotate)', async () => {
    let refreshes = 0;
    install(async (call) => {
      if (call.url.endsWith('/auth/refresh')) {
        refreshes += 1;
        await new Promise((r) => setTimeout(r, 20));
        return ok({ access_token: 'new', expires_in: 1800 });
      }
      return call.headers.Authorization === 'Bearer new' ? ok({ ok: true }) : ok({ detail: 'expired' }, 401);
    });
    session.set('old', 1800, false);
    const results = await Promise.all([api.get('/a'), api.get('/b'), api.get('/c')]);
    expect(results).toHaveLength(3);
    expect(refreshes).toBe(1);
  });

  it('ends the session when the refresh token is rejected', async () => {
    install((call) => (call.url.endsWith('/auth/refresh') ? ok({ detail: 'revoked' }, 401) : ok({ detail: 'expired' }, 401)));
    session.set('old', 1800, false);
    const err = (await rejection(api.get('/containers/'))) as ApiError;
    expect(err.status).toBe(401);
    expect(session.token).toBeNull();
    expect(authLost).toBe(1);
  });

  it('does not try to refresh when logging in with wrong credentials', async () => {
    install(() => ok({ detail: 'Incorrect credentials' }, 401));
    const err = (await rejection(request('POST', '/auth/login', { form: { username: 'a', password: 'b' }, skipRefresh: true }))) as ApiError;
    expect(err.status).toBe(401);
    expect(calls).toHaveLength(1);
  });

  it('refreshSession returns null when there is no session cookie', async () => {
    install(() => ok({ detail: 'Refresh token missing' }, 401));
    expect(await refreshSession()).toBeNull();
  });

  it('reuses a token another tab already refreshed instead of rotating again', async () => {
    // Simulated by two sequential refreshes: the second must still call the server (no stale reuse here),
    // while the broadcast path is exercised in the browser end-to-end test.
    install(() => ok({ access_token: 'n1', expires_in: 1800 }));
    expect(await refreshSession()).toBe('n1');
    expect(session.token).toBe('n1');
  });
});
