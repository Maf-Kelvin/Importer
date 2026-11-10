import type { ReactNode } from 'react';
import { useCurrentUser } from '@/auth';
import { PricingAccuracyCard } from '@/features/pricing';
import { can } from '@/lib/permissions';
import { PageHeader } from '@/components/shared/PageHeader';
import { ErrorState } from '@/components/shared/states';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { formatDateTime } from '@/lib/utils';
import { formatMoney, formatPercent } from '@/lib/money';
import { useDashboard } from '../api';

function Stat({ title, value, hint, tone }: { title: string; value: ReactNode; hint?: string; tone?: 'good' | 'bad' }) {
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent>
        <p className={`text-2xl font-semibold tabular-nums ${tone === 'good' ? 'text-success' : tone === 'bad' ? 'text-destructive' : ''}`}>{value}</p>
        {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  );
}

export function DashboardPage() {
  const user = useCurrentUser();
  const q = useDashboard();
  const isClerk = user.role === 'clerk' && !user.is_superuser;

  let content: ReactNode;
  if (q.isPending) {
    content = (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 8 }, (_, i) => <Skeleton key={i} className="h-28" />)}
      </div>
    );
  } else if (q.isError) {
    content = <ErrorState error={q.error} onRetry={() => void q.refetch()} />;
  } else {
    const data = q.data;
    content = (
      <>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat title="Revenue" value={formatMoney(data.total_revenue)} hint="Sold items" />
          <Stat title="Cost of goods sold" value={formatMoney(data.cost_of_goods_sold)} hint="Landed cost of sold items" />
          <Stat
            title="Profit"
            value={formatMoney(data.total_profit)}
            hint={`${formatPercent(data.avg_profit_margin)} margin`}
            tone={data.total_profit > 0 ? 'good' : data.total_profit < 0 ? 'bad' : undefined}
          />
          <Stat title="Inventory value" value={formatMoney(data.inventory_value)} hint="Unsold stock at landed cost" />
          <Stat title="Containers" value={data.active_containers} />
          <Stat title="Items sold" value={`${data.items_sold} / ${data.total_items}`} />
          <Stat title="Shipped containers" value={data.pending_shipments} />
          {!isClerk && <Stat title="Low-stock alerts" value={data.low_stock_alerts} tone={data.low_stock_alerts > 0 ? 'bad' : undefined} />}
        </div>
        {can(user, 'pricing.accuracy') && <div className="mt-4 max-w-xl"><PricingAccuracyCard /></div>}
        <p className="mt-4 text-xs text-muted-foreground">Updated {formatDateTime(data.generated_at)} (cached for up to 5 minutes)</p>
      </>
    );
  }

  return (
    <>
      <PageHeader title="Dashboard" description={isClerk ? 'Totals for the containers you own.' : 'Totals for your whole organisation.'} />
      {content}
    </>
  );
}
