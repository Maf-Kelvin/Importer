import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import type { Expense } from '@/api/types';
import { CURRENCIES, EXPENSE_TYPES } from '@/api/types';
import { applyApiError } from '@/components/shared/forms';
import { FormField } from '@/components/shared/FormField';
import { Button } from '@/components/ui/button';
import { Dialog } from '@/components/ui/dialog';
import { Input, Select, Textarea } from '@/components/ui/input';
import { useToast } from '@/components/ui/toast';
import { newIdempotencyKey } from '@/lib/idempotency';
import { titleCase } from '@/lib/utils';
import { useCreateExpense, useUpdateExpense } from '../api';
import { expenseDefaults, expenseSchema, toExpenseBody, valuesFromExpense, type ExpenseFormValues } from '../schemas';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  containerId: number;
  expense?: Expense;
}

const FIELDS = ['expense_type', 'amount', 'currency', 'description'] as const;

export function ExpenseFormDialog({ open, onOpenChange, containerId, expense }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange} title={expense ? 'Edit expense' : 'Add expense'} description="Converted to US dollars at today's exchange rate.">
      <ExpenseForm containerId={containerId} expense={expense} onDone={() => onOpenChange(false)} />
    </Dialog>
  );
}

function ExpenseForm({ containerId, expense, onDone }: { containerId: number; expense?: Expense; onDone: () => void }) {
  const toast = useToast();
  const create = useCreateExpense();
  const update = useUpdateExpense();
  const [idempotencyKey] = useState(newIdempotencyKey);
  const [formError, setFormError] = useState<string | null>(null);
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<ExpenseFormValues>({
    resolver: zodResolver(expenseSchema),
    defaultValues: expense ? valuesFromExpense(expense) : expenseDefaults,
  });

  async function onSubmit(v: ExpenseFormValues) {
    setFormError(null);
    const body = toExpenseBody(v);
    try {
      if (expense) {
        await update.mutateAsync({ id: expense.id, body });
        toast({ title: 'Expense updated', description: 'Run cost allocation again to refresh landed costs.', variant: 'success' });
      } else {
        await create.mutateAsync({ body: { ...body, container_id: containerId }, key: idempotencyKey });
        toast({ title: 'Expense added', description: 'Run cost allocation to spread it over the items.', variant: 'success' });
      }
      onDone();
    } catch (e) {
      setFormError(applyApiError(e, setError, FIELDS));
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      {formError && <p role="alert" className="rounded-md bg-destructive/10 p-2 text-sm text-destructive">{formError}</p>}
      <FormField label="Type" error={errors.expense_type?.message}>
        <Select autoFocus {...register('expense_type')}>{EXPENSE_TYPES.map((t) => <option key={t} value={t}>{titleCase(t)}</option>)}</Select>
      </FormField>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Amount" error={errors.amount?.message} required>
          <Input inputMode="decimal" placeholder="0.00" {...register('amount')} />
        </FormField>
        <FormField label="Currency" error={errors.currency?.message}>
          <Select {...register('currency')}>{CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}</Select>
        </FormField>
      </div>
      <FormField label="Description" error={errors.description?.message}>
        <Textarea {...register('description')} />
      </FormField>
      <div className="flex justify-end"><Button type="submit" loading={isSubmitting}>{expense ? 'Save changes' : 'Add expense'}</Button></div>
    </form>
  );
}
