import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { formatPercent } from '@/lib/money';
import { usePricingAccuracy } from '../api';

/** How close past recommendations were to what the items actually sold for (managers and admins). */
export function PricingAccuracyCard() {
  const q = usePricingAccuracy();

  let body;
  if (q.isPending) body = <Skeleton className="h-16" />;
  else if (q.isError) body = <p className="text-sm text-muted-foreground">Accuracy is not available right now.</p>;
  else if (q.data.n === 0) {
    body = <p className="text-sm text-muted-foreground">Not enough data yet. Once items you priced are sold, this shows how close the recommendations were.</p>;
  } else {
    const { n, mape, bias, within_10pct } = q.data;
    body = (
      <>
        <dl className="grid grid-cols-3 gap-4 text-sm">
          <div><dt className="text-muted-foreground">Average error</dt><dd className="text-xl font-semibold tabular-nums">{formatPercent(mape)}</dd></div>
          <div><dt className="text-muted-foreground">Within 10%</dt><dd className="text-xl font-semibold tabular-nums">{formatPercent(within_10pct, 0)}</dd></div>
          <div><dt className="text-muted-foreground">Bias</dt><dd className="text-xl font-semibold tabular-nums">{formatPercent(bias)}</dd></div>
        </dl>
        <p className="mt-3 text-xs text-muted-foreground">
          Based on {n} sold {n === 1 ? 'item' : 'items'}. A positive bias means recommendations ran too high, a negative one too low.
        </p>
      </>
    );
  }

  return (
    <Card>
      <CardHeader><CardTitle>Pricing accuracy</CardTitle></CardHeader>
      <CardContent>{body}</CardContent>
    </Card>
  );
}
