import { Link } from 'react-router-dom';
import { BarChartCard } from '@/components/shared/BarChartCard';
import { Badge } from '@/components/ui/badge';
import { Table, TBody, Td, Th, THead, Tr } from '@/components/ui/table';
import { formatMoney, formatPercent } from '@/lib/money';
import { useContainerReport } from '../api';
import { ReportState, profitTone } from './ReportState';

export function ContainerReportSection() {
  const q = useContainerReport();
  const rows = q.data ?? [];
  const unallocated = rows.filter((r) => r.unallocated_expenses > 0).length;
  return (
    <ReportState query={q} isEmpty={rows.length === 0} emptyTitle="No containers yet" emptyText="Create a container, add items and expenses, then allocate the costs.">
      <div className="space-y-4">
        {unallocated > 0 && (
          <p role="status" className="rounded-md border border-warning/40 bg-warning/10 p-3 text-sm">
            {unallocated} {unallocated === 1 ? 'container has' : 'containers have'} expenses that are not spread over the items yet, so landed costs and profit can be off. Open the container and run &quot;Allocate costs&quot;.
          </p>
        )}
        <BarChartCard
          title="Profit by container"
          description={`Bar chart of profit and cost of goods sold for ${rows.length} containers. The table below has the same numbers.`}
          data={rows.map((r) => ({ name: r.container_name, profit: r.total_profit, cogs: r.cost_of_goods_sold }))}
          series={[{ key: 'profit', label: 'Profit', color: 'var(--success)' }, { key: 'cogs', label: 'Cost of goods sold', color: 'var(--warning)' }]}
        />
        <Table>
          <THead>
            <Tr><Th>Container</Th><Th className="text-right">Sold</Th><Th className="text-right">Revenue</Th><Th className="text-right">Cost of goods sold</Th><Th className="text-right">Profit</Th><Th className="text-right">Margin</Th><Th className="text-right">Unsold stock</Th><Th>Notes</Th></Tr>
          </THead>
          <TBody>
            {rows.map((r) => (
              <Tr key={r.container_id}>
                <Td><Link to={`/containers/${r.container_id}`} className="font-medium text-primary underline-offset-2 hover:underline">{r.container_name}</Link></Td>
                <Td className="text-right tabular-nums">{r.items_sold} / {r.total_items}</Td>
                <Td className="text-right tabular-nums">{formatMoney(r.total_revenue)}</Td>
                <Td className="text-right tabular-nums">{formatMoney(r.cost_of_goods_sold)}</Td>
                <Td className={`text-right tabular-nums ${profitTone(r.total_profit)}`}>{formatMoney(r.total_profit)}</Td>
                <Td className="text-right tabular-nums">{formatPercent(r.profit_margin)}</Td>
                <Td className="text-right tabular-nums text-muted-foreground">{formatMoney(r.inventory_value)}</Td>
                <Td>{r.unallocated_expenses > 0 ? <Badge tone="warning">{formatMoney(r.unallocated_expenses)} not allocated</Badge> : null}</Td>
              </Tr>
            ))}
          </TBody>
        </Table>
      </div>
    </ReportState>
  );
}
