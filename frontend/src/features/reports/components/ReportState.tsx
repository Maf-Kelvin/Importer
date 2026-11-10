import type { ReactNode } from 'react';
import { EmptyState, ErrorState } from '@/components/shared/states';
import { Skeleton } from '@/components/ui/skeleton';

interface Query {
  isPending: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => unknown;
}

/** The loading / error / empty states every report shares; children render only when there is data. */
export function ReportState({ query, isEmpty, emptyTitle, emptyText, children }: { query: Query; isEmpty: boolean; emptyTitle: string; emptyText: string; children: ReactNode }) {
  if (query.isPending) return <div className="space-y-3"><Skeleton className="h-80" /><Skeleton className="h-40" /></div>;
  if (query.isError) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  if (isEmpty) return <EmptyState title={emptyTitle} description={emptyText} />;
  return <>{children}</>;
}

export const profitTone = (n: number | null): string => (n === null || n === 0 ? '' : n > 0 ? 'text-success' : 'text-destructive');
