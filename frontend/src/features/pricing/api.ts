import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { pricingApi } from '@/api/endpoints';
import { qk } from '@/api/queryKeys';
import type { PricingRequest } from '@/api/types';

/** Generating a recommendation also saves it on the item, so item lists must refetch afterwards. */
export function useGeneratePricing(itemId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: PricingRequest) => pricingApi.generate(itemId, body),
    onSuccess: () => Promise.all([qc.invalidateQueries({ queryKey: qk.items.all }), qc.invalidateQueries({ queryKey: qk.containers.all })]),
  });
}

export function useRefreshMarket(itemId: number) {
  return useMutation({ mutationFn: () => pricingApi.refreshMarket(itemId) });
}

export function usePricingAccuracy() {
  return useQuery({ queryKey: qk.pricingAccuracy, queryFn: pricingApi.accuracy, staleTime: 5 * 60_000 });
}
