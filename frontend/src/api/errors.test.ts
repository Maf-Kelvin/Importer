import { describe, expect, it } from 'vitest';
import { ApiError, errorFromResponse, userMessage } from './errors';

const json = (status: number, body: unknown, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } });

describe('errorFromResponse', () => {
  it('reads a plain detail message', async () => {
    const err = await errorFromResponse(json(404, { detail: 'Container not found' }));
    expect(err.status).toBe(404);
    expect(err.message).toBe('Container not found');
  });
  it('maps FastAPI validation errors to field messages', async () => {
    const err = await errorFromResponse(
      json(422, { detail: [{ loc: ['body', 'name'], msg: 'Field required', type: 'missing' }, { loc: ['body', 'weight'], msg: 'Input should be greater than 0' }] }),
    );
    expect(err.fieldErrors.name).toBe('Field required');
    expect(err.fieldErrors.weight).toBe('Input should be greater than 0');
    expect(err.message).toBe('Field required');
  });
  it('reads Retry-After', async () => {
    const err = await errorFromResponse(json(503, { detail: 'down' }, { 'Retry-After': '30' }));
    expect(err.retryAfter).toBe(30);
  });
  it('copes with a non-JSON body', async () => {
    const err = await errorFromResponse(new Response('<html>', { status: 502 }));
    expect(err.status).toBe(502);
  });
});

describe('userMessage', () => {
  it('explains each important status in plain language', () => {
    expect(userMessage(new ApiError(0, 'x'))).toContain('Cannot reach the server');
    expect(userMessage(new ApiError(403, 'x'))).toContain("don't have permission");
    expect(userMessage(new ApiError(429, 'x', { retryAfter: 12 }))).toContain('12 seconds');
    expect(userMessage(new ApiError(503, 'x', { retryAfter: 5 }))).toContain('5 seconds');
    expect(userMessage(new ApiError(500, 'boom'))).toContain('server had a problem');
    expect(userMessage(new Error('weird'))).toContain('Something went wrong');
  });
  it('never leaks a raw server error for 5xx', () => {
    expect(userMessage(new ApiError(500, 'Traceback (most recent call last)'))).not.toContain('Traceback');
  });
});
