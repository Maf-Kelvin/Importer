/**
 * Money helpers. Rules (same as the backend):
 *  - amounts are decimal STRINGS while editing and when sent to the API; never floats
 *  - sums are done on scaled BigInts, so 0.1 + 0.2 is exactly 0.3
 *  - the API returns JSON numbers; they are only ever formatted for display here
 */
export const MONEY_DECIMALS = 4;
export const RATE_DECIMALS = 8;
export const WEIGHT_DECIMALS = 3;

const DECIMAL_RE = /^-?\d+(\.\d+)?$/;

/** Clean what a user typed ("1,234.50", " 7 ", ".5") into a plain decimal string, or null if invalid. */
export function normalizeDecimalInput(raw: string, maxDecimals: number): string | null {
  let s = raw.trim().replace(/,/g, '');
  if (s.startsWith('.')) s = `0${s}`;
  if (!DECIMAL_RE.test(s)) return null;
  const [intPart = '', frac = ''] = s.replace('-', '').split('.');
  if (frac.length > maxDecimals) return null;
  const negative = s.startsWith('-');
  const cleanInt = intPart.replace(/^0+(?=\d)/, '');
  return `${negative ? '-' : ''}${cleanInt}${frac ? `.${frac}` : ''}`;
}

/** A validated decimal string, or an error: use after a form has already been validated. */
export function requireDecimal(raw: string, maxDecimals: number): string {
  const n = normalizeDecimalInput(raw, maxDecimals);
  if (n === null) throw new Error(`Not a valid decimal: ${raw}`);
  return n;
}

/** A number from the API as text for an edit form: 12.5 -> "12.5", 100 -> "100", never exponent notation. */
export function decimalForInput(n: number | null | undefined): string {
  if (n === null || n === undefined || !Number.isFinite(n)) return '';
  const s = n.toFixed(8);
  return s.includes('.') ? s.replace(/0+$/, '').replace(/\.$/, '') : s;
}

export function isPositiveDecimal(s: string, maxDecimals: number): boolean {
  const n = normalizeDecimalInput(s, maxDecimals);
  return n !== null && !n.startsWith('-') && toScaled(n, maxDecimals) > 0n;
}

/** "12.5" with scale 4 -> 125000n. Throws if the value has more decimals than the scale. */
export function toScaled(value: string, scale: number): bigint {
  const n = normalizeDecimalInput(value, scale);
  if (n === null) throw new Error(`Not a valid decimal with at most ${scale} places: ${value}`);
  const negative = n.startsWith('-');
  const [i = '0', f = ''] = n.replace('-', '').split('.');
  const scaled = BigInt(i + f.padEnd(scale, '0'));
  return negative ? -scaled : scaled;
}

export function fromScaled(value: bigint, scale: number): string {
  const negative = value < 0n;
  const digits = (negative ? -value : value).toString().padStart(scale + 1, '0');
  const int = digits.slice(0, digits.length - scale);
  const frac = digits.slice(digits.length - scale);
  return `${negative ? '-' : ''}${int}${scale > 0 ? `.${frac}` : ''}`;
}

/** Plain decimal string for a JSON number (never exponent notation). */
export function numberToDecimalString(n: number, scale = RATE_DECIMALS): string {
  if (!Number.isFinite(n)) throw new Error('Not a finite number');
  return n.toFixed(scale);
}

type Amount = string | number | null | undefined;

function toScaledLoose(v: Amount, scale: number): bigint {
  if (v === null || v === undefined || v === '') return 0n;
  const s = typeof v === 'number' ? numberToDecimalString(v, scale + 2) : v;
  // numbers from the API can carry more decimals than the scale: round half up at the scale
  const [i = '0', f = ''] = s.replace('-', '').split('.');
  const neg = s.startsWith('-');
  const kept = f.slice(0, scale).padEnd(scale, '0');
  let scaled = BigInt(i + kept);
  if ((f[scale] ?? '0') >= '5') scaled += 1n;
  return neg ? -scaled : scaled;
}

export function addDecimals(values: Amount[], scale = MONEY_DECIMALS): string {
  return fromScaled(values.reduce<bigint>((sum, v) => sum + toScaledLoose(v, scale), 0n), scale);
}

export function compareDecimals(a: Amount, b: Amount, scale = RATE_DECIMALS): -1 | 0 | 1 {
  const x = toScaledLoose(a, scale);
  const y = toScaledLoose(b, scale);
  return x === y ? 0 : x < y ? -1 : 1;
}

/** Display only. */
export function formatMoney(value: Amount, currency = 'USD', locale = 'en-US'): string {
  if (value === null || value === undefined || value === '') return '-';
  const n = Number(value);
  if (!Number.isFinite(n)) return '-';
  try {
    return new Intl.NumberFormat(locale, { style: 'currency', currency }).format(n);
  } catch {
    return `${n.toFixed(2)} ${currency}`;
  }
}

/** Short money for chart axes: 1250000 -> "$1.3M". Display only. */
export function compactMoney(value: number, currency = 'USD', locale = 'en-US'): string {
  if (!Number.isFinite(value)) return '-';
  try {
    return new Intl.NumberFormat(locale, { style: 'currency', currency, notation: 'compact', minimumFractionDigits: 0, maximumFractionDigits: 1 }).format(value);
  } catch {
    return String(value);
  }
}

export function formatNumber(value: Amount, decimals = 2, locale = 'en-US'): string {
  if (value === null || value === undefined || value === '') return '-';
  const n = Number(value);
  if (!Number.isFinite(n)) return '-';
  return new Intl.NumberFormat(locale, { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(n);
}

export function formatPercent(ratio: Amount, decimals = 1, locale = 'en-US'): string {
  if (ratio === null || ratio === undefined || ratio === '') return '-';
  const n = Number(ratio);
  if (!Number.isFinite(n)) return '-';
  return new Intl.NumberFormat(locale, { style: 'percent', minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(n);
}
