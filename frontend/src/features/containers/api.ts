import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { containersApi, type ContainerFilters } from '@/api/endpoints';
import { invalidateInventory, qk } from '@/api/queryKeys';
import type { AllocationMethod, ContainerCreate, ContainerUpdate } from '@/api/types';

export function useContainers(filters: ContainerFilters) {
  return useQuery({
    queryKey: qk.containers.list(filters),
    queryFn: () => containersApi.list(filters),
    placeholderData: keepPreviousData, // keep the old page on screen while the next loads
  });
}

export function useContainer(id: number) {
  return useQuery({ queryKey: qk.containers.detail(id), queryFn: () => containersApi.get(id), enabled: Number.isInteger(id) && id > 0 });
}

export function useCreateContainer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { body: ContainerCreate; key: string }) => containersApi.create(v.body, v.key),
    onSuccess: () => invalidateInventory(qc),
  });
}

export function useUpdateContainer(id: number) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (body: ContainerUpdate) => containersApi.update(id, body), onSuccess: () => invalidateInventory(qc) });
}

export function useSealContainer(id: number) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: () => containersApi.seal(id), onSuccess: () => invalidateInventory(qc) });
}

export function useDeleteContainer(id: number) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: () => containersApi.remove(id), onSuccess: () => invalidateInventory(qc) });
}

export function useAllocateCosts(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (method: AllocationMethod) => containersApi.allocate(id, method),
    onSuccess: () => invalidateInventory(qc),
  });
}
