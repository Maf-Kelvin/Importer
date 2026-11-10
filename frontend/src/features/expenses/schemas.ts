import { z } from 'zod';
import type { Expense, ExpenseCreate } from '@/api/types';
import { CURRENCIES, EXPENSE_TYPES } from '@/api/types';
import { MONEY_DECIMALS, decimalForInput, requireDecimal } from '@/lib/money';
import { positiveDecimal } from '@/lib/validation';

export const expenseSchema = z.object({
  expense_type: z.enum(EXPENSE_TYPES),
  amount: positiveDecimal(MONEY_DECIMALS, 'Amount'),
  currency: z.enum(CURRENCIES),
  description: z.string().trim(),
});
export type ExpenseFormValues = z.infer<typeof expenseSchema>;

export const expenseDefaults: ExpenseFormValues = { expense_type: 'shipping_fee', amount: '', currency: 'USD', description: '' };

export function valuesFromExpense(e: Expense): ExpenseFormValues {
  return {
    expense_type: e.expense_type,
    amount: decimalForInput(e.amount),
    currency: (CURRENCIES as readonly string[]).includes(e.currency) ? (e.currency as ExpenseFormValues['currency']) : 'USD',
    description: e.description ?? '',
  };
}

export function toExpenseBody(v: ExpenseFormValues): Omit<ExpenseCreate, 'container_id'> {
  return {
    expense_type: v.expense_type,
    amount: requireDecimal(v.amount, MONEY_DECIMALS),
    currency: v.currency,
    description: v.description || null,
  };
}
