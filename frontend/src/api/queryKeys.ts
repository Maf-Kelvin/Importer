/** One place for every query key, so a mutation can invalidate exactly what it changed. */
import type { QueryClient } from '@tanstack/react-query';
import type { AuditFilters, ContainerFilters, CustomerFilters, ItemFilters, ProfitItemFilters } from './endpoints';

export const qk = {
  dashboard: ['dashboard'] as const,
  reports: {
    all: ['reports'] as const,
    categories: ['reports', 'categories'] as const,
    containers: ['reports', 'containers'] as const,
    items: (f: ProfitItemFilters) => ['reports', 'items', f] as const,
    demand: ['reports', 'demand'] as const,
  },
  containers: {
    all: ['containers'] as const,
    list: (f: ContainerFilters) => ['containers', 'list', f] as const,
    detail: (id: number) => ['containers', 'detail', id] as const,
  },
  customers: {
    all: ['customers'] as const,
    list: (f: CustomerFilters) => ['customers', 'list', f] as const,
    options: ['customers', 'options'] as const,
  },
  pricingAccuracy: ['pricing', 'accuracy'] as const,
  users: {
    all: ['users'] as const,
    list: (page: number) => ['users', 'list', page] as const,
    options: ['users', 'options'] as const,
  },
  audit: { list: (f: AuditFilters) => ['audit', f] as const },
  organization: ['organization', 'me'] as const,
  items: {
    all: ['items'] as const,
    list: (f: ItemFilters) => ['items', 'list', f] as const,
  },
};

/** After any change to containers, items or expenses: every screen that shows money or counts must refetch. */
export function invalidateInventory(qc: QueryClient): Promise<unknown> {
  return Promise.all([
    qc.invalidateQueries({ queryKey: qk.containers.all }),
    qc.invalidateQueries({ queryKey: qk.items.all }),
    qc.invalidateQueries({ queryKey: qk.dashboard }),
    qc.invalidateQueries({ queryKey: qk.reports.all }),
  ]);
}
