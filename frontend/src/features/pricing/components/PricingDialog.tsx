import { AlertTriangle, Info, RefreshCw } from 'lucide-react';
import { useState } from 'react';
import type { PricingResponse } from '@/api/types';
import { userMessage } from '@/api/errors';
import { FormField } from '@/components/shared/FormField';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Table, TBody, Td, Th, THead, Tr } from '@/components/ui/table';
import { useToast } from '@/components/ui/toast';
import { formatMoney, formatNumber, formatPercent } from '@/lib/money';
import { titleCase } from '@/lib/utils';
import { useGeneratePricing, useRefreshMarket } from '../api';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  item: { id: number; name: string };
}

/** Turn "25" (percent, as typed) into the ratio the API wants, or an error message. */
function parseMargin(raw: string): { ratio: number | null; error?: string } {
  const s = raw.trim();
  if (s === '') return { ratio: null }; // the server default (20%)
  const n = Number(s);
  if (!Number.isFinite(n) || n < 5 || n > 100) return { ratio: null, error: 'Enter a percentage between 5 and 100' };
  return { ratio: n / 100 };
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const tone = value >= 0.7 ? 'bg-success' : value >= 0.4 ? 'bg-warning' : 'bg-destructive';
  return (
    <div>
      <div className="flex justify-between text-xs text-muted-foreground"><span>Confidence in the market signal</span><span>{pct}%</span></div>
      <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} aria-label="Confidence">
        <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function PricingDialog({ open, onOpenChange, item }: Props) {
  const toast = useToast();
  const generate = useGeneratePricing(item.id);
  const refresh = useRefreshMarket(item.id);
  const [margin, setMargin] = useState('');
  const [market, setMarket] = useState(true);
  const [ownSales, setOwnSales] = useState(true);
  const [result, setResult] = useState<PricingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const parsed = parseMargin(margin);

  async function run() {
    if (parsed.error) return;
    setError(null);
    try {
      setResult(await generate.mutateAsync({ include_cost_based: true, include_market_pricing: market, include_last_sold: ownSales, profit_margin: parsed.ratio }));
    } catch (e) {
      setResult(null);
      setError(userMessage(e));
    }
  }

  async function refreshMarket() {
    try {
      await refresh.mutateAsync();
      toast({ title: 'Market prices are being refreshed', description: 'This runs in the background. Generate again in a minute.', variant: 'info' });
    } catch (e) {
      toast({ title: 'Could not start the refresh', description: userMessage(e), variant: 'error' });
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => { onOpenChange(o); if (!o) { setResult(null); setError(null); } }}
      title={`Price "${item.name}"`}
      description="A recommended selling price built from your cost, current market listings and your own past sales."
      size="lg"
    >
      <div className="flex flex-wrap items-end gap-4">
        <div className="w-44">
          <FormField label="Target margin (%)" error={parsed.error} hint="Blank = 20%">
            <Input inputMode="decimal" placeholder="20" value={margin} onChange={(e) => setMargin(e.target.value)} />
          </FormField>
        </div>
        <label className="flex items-center gap-2 pb-2 text-sm"><input type="checkbox" checked={market} onChange={(e) => setMarket(e.target.checked)} /> Market prices</label>
        <label className="flex items-center gap-2 pb-2 text-sm"><input type="checkbox" checked={ownSales} onChange={(e) => setOwnSales(e.target.checked)} /> My past sales</label>
        <Button onClick={() => void run()} loading={generate.isPending} disabled={Boolean(parsed.error)}>Get recommendation</Button>
      </div>

      {error && <p role="alert" className="mt-3 rounded-md bg-destructive/10 p-2 text-sm text-destructive">{error}</p>}

      {result && (
        <div className="mt-5 space-y-5">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-border p-4 sm:col-span-2">
              <p className="text-sm text-muted-foreground">Recommended price</p>
              <p className="text-3xl font-semibold tabular-nums">{formatMoney(result.recommended_price)}</p>
              {result.price_low !== null && result.price_high !== null && (
                <p className="mt-1 text-sm text-muted-foreground">Suggested range {formatMoney(result.price_low)} to {formatMoney(result.price_high)}</p>
              )}
              {result.confidence !== null && <div className="mt-4"><ConfidenceBar value={result.confidence} /></div>}
            </div>
            <div className="space-y-2 rounded-lg border border-border p-4 text-sm">
              <div className="flex justify-between"><span className="text-muted-foreground">Landed cost</span><span className="tabular-nums">{formatMoney(result.landed_cost)}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Cost-plus price</span><span className="tabular-nums">{formatMoney(result.cost_based_price)}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Expected margin</span><span className="tabular-nums">{formatPercent(result.expected_margin)}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Comparables used</span><span className="tabular-nums">{result.comparables_used}</span></div>
              {result.last_sold_price !== null && <div className="flex justify-between"><span className="text-muted-foreground">Last similar sale</span><span className="tabular-nums">{formatMoney(result.last_sold_price)}</span></div>}
            </div>
          </div>

          {result.warnings.length > 0 && (
            <ul className="space-y-2" aria-label="Warnings">
              {result.warnings.map((w) => (
                <li key={w} className="flex gap-2 rounded-md border border-warning/40 bg-warning/10 p-3 text-sm"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden />{w}</li>
              ))}
            </ul>
          )}

          {result.explanation.length > 0 && (
            <div>
              <h3 className="mb-2 flex items-center gap-2 text-sm font-medium"><Info className="h-4 w-4" aria-hidden /> Why this price</h3>
              <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">{result.explanation.map((x) => <li key={x}>{x}</li>)}</ul>
            </div>
          )}

          <div>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-sm font-medium">Market listings ({result.market_prices.length})</h3>
              <Button variant="outline" size="sm" onClick={() => void refreshMarket()} loading={refresh.isPending}><RefreshCw className="h-4 w-4" aria-hidden /> Refresh market prices</Button>
            </div>
            {result.market_prices.length === 0 ? (
              <p className="rounded-md border border-dashed border-border p-4 text-sm text-muted-foreground">No market listings yet. Refresh market prices, wait a minute, then get a new recommendation.</p>
            ) : (
              <Table>
                <THead><Tr><Th>Source</Th><Th className="text-right">Listed price</Th><Th className="text-right">In USD</Th><Th className="text-right">Age</Th><Th className="text-right">Confidence</Th></Tr></THead>
                <TBody>
                  {result.market_prices.map((m) => (
                    <Tr key={`${m.source}-${m.found_at}-${m.price}`}>
                      <Td>{m.url ? <a className="text-primary underline" href={m.url} target="_blank" rel="noreferrer noopener">{titleCase(m.source)}</a> : <Badge>{titleCase(m.source)}</Badge>}</Td>
                      <Td className="text-right tabular-nums">{formatMoney(m.price, m.currency)}</Td>
                      <Td className="text-right tabular-nums">{formatMoney(m.price_usd)}</Td>
                      <Td className="text-right tabular-nums">{m.age_days === null ? '-' : `${formatNumber(m.age_days, 0)} d`}</Td>
                      <Td className="text-right tabular-nums">{formatPercent(m.confidence, 0)}</Td>
                    </Tr>
                  ))}
                </TBody>
              </Table>
            )}
          </div>
          <p className="text-xs text-muted-foreground">This recommendation was saved on the item. It is advice: the final price is your decision.</p>
        </div>
      )}
    </Dialog>
  );
}
