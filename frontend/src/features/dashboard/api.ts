import { useQuery } from '@tanstack/react-query';
import { reportsApi } from '@/api/endpoints';
import { qk } from '@/api/queryKeys';

export function useDashboard() {
  return useQuery({ queryKey: qk.dashboard, queryFn: reportsApi.dashboard });
}
