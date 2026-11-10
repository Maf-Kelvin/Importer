/** A failed API call, normalised so the UI never has to inspect raw responses. */
export class ApiError extends Error {
  readonly status: number; // 0 = the request never reached the server
  readonly retryAfter: number | null; // seconds, from the Retry-After header
  readonly fieldErrors: Record<string, string>; // 422 validation messages keyed by field name

  constructor(
    status: number,
    message: string,
    opts: { retryAfter?: number | null; fieldErrors?: Record<string, string> } = {},
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.retryAfter = opts.retryAfter ?? null;
    this.fieldErrors = opts.fieldErrors ?? {};
  }

  get isNetwork(): boolean {
    return this.status === 0;
  }
  get isUnauthorized(): boolean {
    return this.status === 401;
  }
  get isForbidden(): boolean {
    return this.status === 403;
  }
  get isNotFound(): boolean {
    return this.status === 404;
  }
}

interface FastApiValidationItem {
  loc?: unknown[];
  msg?: string;
}

export async function errorFromResponse(res: Response): Promise<ApiError> {
  let detail: unknown;
  try {
    detail = ((await res.json()) as { detail?: unknown }).detail;
  } catch {
    detail = undefined;
  }
  const retryHeader = res.headers.get('Retry-After');
  const retryAfter = retryHeader && /^\d+$/.test(retryHeader) ? Number(retryHeader) : null;

  const fieldErrors: Record<string, string> = {};
  let message = res.statusText || `Request failed (${res.status})`;
  if (typeof detail === 'string') {
    message = detail;
  } else if (Array.isArray(detail)) {
    for (const item of detail as FastApiValidationItem[]) {
      const field = String(item.loc?.[item.loc.length - 1] ?? 'form');
      fieldErrors[field] ??= item.msg ?? 'Invalid value';
    }
    message = Object.values(fieldErrors)[0] ?? message;
  }
  return new ApiError(res.status, message, { retryAfter, fieldErrors });
}

/** The sentence shown to a person. Technical detail stays in the console. */
export function userMessage(err: unknown): string {
  if (!(err instanceof ApiError)) return 'Something went wrong. Please try again.';
  switch (err.status) {
    case 0:
      return 'Cannot reach the server. Check your connection and try again.';
    case 401:
      return 'Your session has expired. Please sign in again.';
    case 403:
      return "You don't have permission to do that.";
    case 404:
      return 'That record was not found.';
    case 409:
      return err.message || 'That conflicts with an existing record, or is still being processed. Try again in a moment.';
    case 422:
      return err.message || 'Some of the values are not valid.';
    case 429:
      return err.retryAfter ? `Too many requests. Try again in ${err.retryAfter} seconds.` : 'Too many requests. Please wait a moment.';
    case 503:
      return err.retryAfter
        ? `The service is temporarily unavailable. Try again in ${err.retryAfter} seconds.`
        : 'The service is temporarily unavailable. Please try again shortly.';
    default:
      return err.status >= 500 ? 'The server had a problem. Please try again.' : err.message || 'Request failed.';
  }
}
