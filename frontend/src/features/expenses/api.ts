import { useMutation, useQueryClient } from '@tanstack/react-query';
import { expensesApi } from '@/api/endpoints';
import { invalidateInventory } from '@/api/queryKeys';
import type { ExpenseCreate, ExpenseUpdate } from '@/api/types';

export function useCreateExpense() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (v: { body: ExpenseCreate; key: string }) => expensesApi.create(v.body, v.key), onSuccess: () => invalidateInventory(qc) });
}

export function useUpdateExpense() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (v: { id: number; body: ExpenseUpdate }) => expensesApi.update(v.id, v.body), onSuccess: () => invalidateInventory(qc) });
}

export function useDeleteExpense() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: number) => expensesApi.remove(id), onSuccess: () => invalidateInventory(qc) });
}
