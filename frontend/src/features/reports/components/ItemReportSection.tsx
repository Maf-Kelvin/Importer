import { useState } from 'react';
import type { ProfitItemFilters } from '@/api/endpoints';
import { ITEM_CATEGORIES } from '@/api/types';
import { FormField } from '@/components/shared/FormField';
import { Badge } from '@/components/ui/badge';
import { Input, Select } from '@/components/ui/input';
import { Table, TBody, Td, Th, THead, Tr } from '@/components/ui/table';
import { formatMoney, formatPercent } from '@/lib/money';
import { formatDate, titleCase } from '@/lib/utils';
import { useItemReport } from '../api';
import { ReportState, profitTone } from './ReportState';

const MAX_ROWS = 200; // the API returns every matching item; show the first 200 and say so

export function ItemReportSection() {
  const [category, setCategory] = useState('');
  const [soldOnly, setSoldOnly] = useState(false);
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const filters: ProfitItemFilters = { category: category || undefined, sold_only: soldOnly || undefined, start_date: start || undefined, end_date: end || undefined };
  const q = useItemReport(filters);
  const rows = q.data ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-4">
        <div className="w-48"><FormField label="Category"><Select value={category} onChange={(e) => setCategory(e.target.value)}><option value="">All categories</option>{ITEM_CATEGORIES.map((c) => <option key={c} value={c}>{titleCase(c)}</option>)}</Select></FormField></div>
        <div className="w-40"><FormField label="Sold from"><Input type="date" value={start} onChange={(e) => setStart(e.target.value)} /></FormField></div>
        <div className="w-40"><FormField label="Sold until"><Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} /></FormField></div>
        <label className="flex items-center gap-2 pb-2 text-sm"><input type="checkbox" checked={soldOnly} onChange={(e) => setSoldOnly(e.target.checked)} /> Sold items only</label>
      </div>
      <ReportState query={q} isEmpty={rows.length === 0} emptyTitle="No items match" emptyText="Try clearing the filters.">
        <Table>
          <THead>
            <Tr><Th>Item</Th><Th>Category</Th><Th className="text-right">Landed cost</Th><Th className="text-right">Sold for</Th><Th className="text-right">Profit</Th><Th className="text-right">Margin</Th><Th>Sold</Th></Tr>
          </THead>
          <TBody>
            {rows.slice(0, MAX_ROWS).map((r) => (
              <Tr key={r.item_id}>
                <Td className="font-medium">{r.item_name}</Td>
                <Td className="text-muted-foreground">{titleCase(r.category)}</Td>
                <Td className="text-right tabular-nums">{formatMoney(r.landed_cost)}</Td>
                <Td className="text-right tabular-nums">{r.sold ? formatMoney(r.selling_price) : <Badge>In stock</Badge>}</Td>
                <Td className={`text-right tabular-nums ${profitTone(r.profit_amount)}`}>{r.profit_amount === null ? '-' : formatMoney(r.profit_amount)}</Td>
                <Td className="text-right tabular-nums">{r.profit_margin === null ? '-' : formatPercent(r.profit_margin)}</Td>
                <Td className="text-muted-foreground">{formatDate(r.sold_date)}</Td>
              </Tr>
            ))}
          </TBody>
        </Table>
        {rows.length > MAX_ROWS && <p className="text-xs text-muted-foreground">Showing the first {MAX_ROWS} of {rows.length} items. Narrow the filters to see the rest.</p>}
      </ReportState>
    </div>
  );
}
