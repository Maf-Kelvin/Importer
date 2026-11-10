import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { itemsApi, type ItemFilters } from '@/api/endpoints';
import { invalidateInventory, qk } from '@/api/queryKeys';
import type { ItemCreate, ItemUpdate, MarkSoldRequest } from '@/api/types';

export function useItems(filters: ItemFilters) {
  return useQuery({ queryKey: qk.items.list(filters), queryFn: () => itemsApi.list(filters), placeholderData: keepPreviousData });
}

export function useCreateItem() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (v: { body: ItemCreate; key: string }) => itemsApi.create(v.body, v.key), onSuccess: () => invalidateInventory(qc) });
}

export function useUpdateItem() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (v: { id: number; body: ItemUpdate }) => itemsApi.update(v.id, v.body), onSuccess: () => invalidateInventory(qc) });
}

export function useDeleteItem() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: number) => itemsApi.remove(id), onSuccess: () => invalidateInventory(qc) });
}

export function useMarkSold() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: number; body: MarkSoldRequest; key: string }) => itemsApi.markSold(v.id, v.body, v.key),
    onSuccess: () => invalidateInventory(qc),
  });
}
