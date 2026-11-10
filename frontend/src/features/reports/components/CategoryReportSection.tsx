import { BarChartCard } from '@/components/shared/BarChartCard';
import { Table, TBody, Td, Th, THead, Tr } from '@/components/ui/table';
import { formatMoney, formatPercent } from '@/lib/money';
import { titleCase } from '@/lib/utils';
import { useCategoryReport } from '../api';
import { ReportState, profitTone } from './ReportState';

export function CategoryReportSection() {
  const q = useCategoryReport();
  const rows = q.data ?? [];
  return (
    <ReportState query={q} isEmpty={rows.length === 0} emptyTitle="No data yet" emptyText="Add items to a container to see how each category performs.">
      <div className="space-y-4">
        <BarChartCard
          title="Revenue, cost and profit by category"
          description={`Bar chart comparing revenue, cost of goods sold and profit for ${rows.length} categories. The table below has the same numbers.`}
          data={rows.map((r) => ({ name: titleCase(r.category), revenue: r.total_revenue, cogs: r.cost_of_goods_sold, profit: r.total_profit }))}
          series={[
            { key: 'revenue', label: 'Revenue', color: 'var(--primary)' },
            { key: 'cogs', label: 'Cost of goods sold', color: 'var(--warning)' },
            { key: 'profit', label: 'Profit', color: 'var(--success)' },
          ]}
        />
        <Table>
          <THead>
            <Tr><Th>Category</Th><Th className="text-right">Items sold</Th><Th className="text-right">Revenue</Th><Th className="text-right">Cost of goods sold</Th><Th className="text-right">Profit</Th><Th className="text-right">Margin</Th><Th className="text-right">Unsold stock</Th></Tr>
          </THead>
          <TBody>
            {rows.map((r) => (
              <Tr key={r.category}>
                <Td className="font-medium">{titleCase(r.category)}</Td>
                <Td className="text-right tabular-nums">{r.items_sold} / {r.total_items}</Td>
                <Td className="text-right tabular-nums">{formatMoney(r.total_revenue)}</Td>
                <Td className="text-right tabular-nums">{formatMoney(r.cost_of_goods_sold)}</Td>
                <Td className={`text-right tabular-nums ${profitTone(r.total_profit)}`}>{formatMoney(r.total_profit)}</Td>
                <Td className="text-right tabular-nums">{formatPercent(r.average_margin)}</Td>
                <Td className="text-right tabular-nums text-muted-foreground">{formatMoney(r.inventory_value)}</Td>
              </Tr>
            ))}
          </TBody>
        </Table>
        <p className="text-xs text-muted-foreground">Profit counts sold items only (revenue minus their landed cost). Unsold stock is money tied up, not a loss.</p>
      </div>
    </ReportState>
  );
}
