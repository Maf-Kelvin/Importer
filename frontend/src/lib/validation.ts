import { z } from 'zod';
import { isPositiveDecimal } from './money';

/** A required decimal above zero, kept as TEXT (money is never a float). */
export const positiveDecimal = (decimals: number, label: string) =>
  z.string().trim().refine((v) => isPositiveDecimal(v, decimals), { message: `${label} must be above 0, with at most ${decimals} decimal places` });

/** Same, but the field may be left empty. */
export const optionalPositiveDecimal = (decimals: number, label: string) =>
  z.string().trim().refine((v) => v === '' || isPositiveDecimal(v, decimals), { message: `${label} must be above 0, with at most ${decimals} decimal places` });
