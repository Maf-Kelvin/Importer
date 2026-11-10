import { describe, expect, it } from 'vitest';
import {
  addDecimals,
  compareDecimals,
  formatMoney,
  formatPercent,
  fromScaled,
  compactMoney,
  decimalForInput,
  isPositiveDecimal,
  normalizeDecimalInput,
  numberToDecimalString,
  requireDecimal,
  toScaled,
} from './money';

describe('normalizeDecimalInput', () => {
  it('cleans what people type', () => {
    expect(normalizeDecimalInput(' 1,234.50 ', 4)).toBe('1234.50');
    expect(normalizeDecimalInput('.5', 4)).toBe('0.5');
    expect(normalizeDecimalInput('007.25', 4)).toBe('7.25');
    expect(normalizeDecimalInput('0', 4)).toBe('0');
  });
  it('rejects invalid input and too many decimals', () => {
    expect(normalizeDecimalInput('abc', 4)).toBeNull();
    expect(normalizeDecimalInput('1.2.3', 4)).toBeNull();
    expect(normalizeDecimalInput('', 4)).toBeNull();
    expect(normalizeDecimalInput('1e5', 4)).toBeNull();
    expect(normalizeDecimalInput('1.23456', 4)).toBeNull();
  });
});

describe('isPositiveDecimal', () => {
  it('accepts only values above zero', () => {
    expect(isPositiveDecimal('0.0001', 4)).toBe(true);
    expect(isPositiveDecimal('0', 4)).toBe(false);
    expect(isPositiveDecimal('-1', 4)).toBe(false);
    expect(isPositiveDecimal('x', 4)).toBe(false);
  });
});

describe('scaled arithmetic', () => {
  it('round-trips decimals exactly', () => {
    expect(fromScaled(toScaled('12.5', 4), 4)).toBe('12.5000');
    expect(fromScaled(toScaled('-0.0001', 4), 4)).toBe('-0.0001');
    expect(fromScaled(0n, 2)).toBe('0.00');
  });
  it('adds without floating point error', () => {
    expect(addDecimals(['0.1', '0.2'], 4)).toBe('0.3000');
    expect(addDecimals([0.1, 0.2], 4)).toBe('0.3000');
    expect(addDecimals(['33.3333', '33.3333', '33.3334'], 4)).toBe('100.0000');
  });
  it('treats missing values as zero', () => {
    expect(addDecimals([null, undefined, '', '5'], 2)).toBe('5.00');
  });
  it('compares', () => {
    expect(compareDecimals('1.10', '1.1')).toBe(0);
    expect(compareDecimals(2, '1.99')).toBe(1);
    expect(compareDecimals('0.1', 0.3)).toBe(-1);
  });
  it('never uses exponent notation', () => {
    expect(numberToDecimalString(0.0000001, 8)).toBe('0.00000010');
  });
});

describe('formatting (display only)', () => {
  it('formats money, percent and empty values', () => {
    expect(formatMoney(1234.5, 'USD')).toBe('$1,234.50');
    expect(formatMoney(null)).toBe('-');
    expect(formatMoney('abc')).toBe('-');
    expect(formatPercent(0.1864, 1)).toBe('18.6%');
  });
  it('survives an unknown currency code', () => {
    expect(formatMoney(5, 'XX')).toContain('5.00');
  });
});

describe('compactMoney', () => {
  it('shortens big numbers for chart axes', () => {
    expect(compactMoney(1250000)).toBe('$1.3M');
    expect(compactMoney(950)).toBe('$950');
    expect(compactMoney(1500)).toBe('$1.5K');
    expect(compactMoney(NaN)).toBe('-');
  });
});

describe('form helpers', () => {
  it('turns API numbers into clean input text', () => {
    expect(decimalForInput(12.5)).toBe('12.5');
    expect(decimalForInput(100)).toBe('100');
    expect(decimalForInput(0.0001)).toBe('0.0001');
    expect(decimalForInput(null)).toBe('');
    expect(decimalForInput(10.1)).toBe('10.1');
  });
  it('requireDecimal returns a clean value or throws', () => {
    expect(requireDecimal(' 1,000.50 ', 4)).toBe('1000.50');
    let threw = false;
    try { requireDecimal('abc', 4); } catch { threw = true; }
    expect(threw).toBe(true);
  });
});

