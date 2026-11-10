import { useQuery } from '@tanstack/react-query';
import { reportsApi, type ProfitItemFilters } from '@/api/endpoints';
import { qk } from '@/api/queryKeys';

export const useCategoryReport = () => useQuery({ queryKey: qk.reports.categories, queryFn: reportsApi.profitCategories });
export const useContainerReport = () => useQuery({ queryKey: qk.reports.containers, queryFn: reportsApi.profitContainers });
export const useItemReport = (f: ProfitItemFilters) => useQuery({ queryKey: qk.reports.items(f), queryFn: () => reportsApi.profitItems(f) });
export const useDemandReport = () => useQuery({ queryKey: qk.reports.demand, queryFn: reportsApi.demand });
