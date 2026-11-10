import { BarChartCard } from '@/components/shared/BarChartCard';
import { Table, TBody, Td, Th, THead, Tr } from '@/components/ui/table';
import { formatMoney, formatPercent } from '@/lib/money';
import { formatDateTime, titleCase } from '@/lib/utils';
import { useDemandReport } from '../api';
import { ReportState } from './ReportState';

function ScoreBar({ score }: { score: number | null }) {
  if (score === null) return <span className="text-muted-foreground">-</span>;
  const pct = Math.max(0, Math.min(100, Math.round(score)));
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-24 overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} aria-label="Demand score">
        <div className="h-full bg-primary" style={{ width: `${pct}%` }} />
      </div>
      <span className="tabular-nums">{pct}</span>
    </div>
  );
}

export function DemandReportSection() {
  const q = useDemandReport();
  const rows = q.data ?? [];
  const updated = rows.map((r) => r.updated_at).filter((x): x is string => x !== null).sort().at(-1) ?? null;
  return (
    <ReportState query={q} isEmpty={rows.length === 0} emptyTitle="No demand data yet" emptyText="These figures are calculated every few hours from your sales. Sell some items and check back later.">
      <div className="space-y-4">
        <BarChartCard
          title="Units sold by category"
          description={`Bar chart of units sold in the last 30 and 90 days for ${rows.length} categories. The table below has the same numbers.`}
          money={false}
          data={rows.map((r) => ({ name: titleCase(r.item_category), d30: r.units_sold_30d, d90: r.units_sold_90d }))}
          series={[{ key: 'd30', label: 'Last 30 days', color: 'var(--primary)' }, { key: 'd90', label: 'Last 90 days', color: 'var(--muted-foreground)' }]}
        />
        <Table>
          <THead><Tr><Th>Category</Th><Th className="text-right">Sold (30 d)</Th><Th className="text-right">Sold (90 d)</Th><Th>Demand</Th><Th className="text-right">Avg sale price</Th><Th className="text-right">Avg margin</Th></Tr></THead>
          <TBody>
            {rows.map((r) => (
              <Tr key={r.item_category}>
                <Td className="font-medium">{titleCase(r.item_category)}</Td>
                <Td className="text-right tabular-nums">{r.units_sold_30d}</Td>
                <Td className="text-right tabular-nums">{r.units_sold_90d}</Td>
                <Td><ScoreBar score={r.demand_score} /></Td>
                <Td className="text-right tabular-nums">{r.avg_sale_price === null ? '-' : formatMoney(r.avg_sale_price)}</Td>
                <Td className="text-right tabular-nums">{r.avg_margin === null ? '-' : formatPercent(r.avg_margin)}</Td>
              </Tr>
            ))}
          </TBody>
        </Table>
        <p className="text-xs text-muted-foreground">Organisation-wide. {updated ? `Last calculated ${formatDateTime(updated)}.` : ''}</p>
      </div>
    </ReportState>
  );
}
