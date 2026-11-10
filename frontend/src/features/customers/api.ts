import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { customersApi, type CustomerFilters } from '@/api/endpoints';
import { qk } from '@/api/queryKeys';
import type { CustomerCreate, CustomerUpdate } from '@/api/types';

export function useCustomers(filters: CustomerFilters) {
  return useQuery({ queryKey: qk.customers.list(filters), queryFn: () => customersApi.list(filters), placeholderData: keepPreviousData });
}

/**
 * The customers for a "pick a customer" dropdown (first 100, alphabetical).
 * If an organisation outgrows 100 customers, replace this with a search-as-you-type picker.
 */
export function useCustomerOptions() {
  return useQuery({ queryKey: qk.customers.options, queryFn: () => customersApi.list({ limit: 100 }), staleTime: 60_000 });
}

export function useCreateCustomer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { body: CustomerCreate; key: string }) => customersApi.create(v.body, v.key),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.customers.all }),
  });
}

export function useUpdateCustomer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: number; body: CustomerUpdate }) => customersApi.update(v.id, v.body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.customers.all }),
  });
}

export function useDeleteCustomer() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: number) => customersApi.remove(id), onSuccess: () => qc.invalidateQueries({ queryKey: qk.customers.all }) });
}
