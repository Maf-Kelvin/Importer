import { useQuery } from '@tanstack/react-query';
import { organizationsApi } from '@/api/endpoints';
import { qk } from '@/api/queryKeys';

export function useMyOrganization() {
  return useQuery({ queryKey: qk.organization, queryFn: organizationsApi.me, staleTime: 5 * 60_000 });
}
