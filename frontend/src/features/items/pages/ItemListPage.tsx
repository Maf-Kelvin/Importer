import { Search } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import type { ItemFilters } from '@/api/endpoints';
import { ITEM_CATEGORIES, ITEM_CONDITIONS } from '@/api/types';
import { PageHeader } from '@/components/shared/PageHeader';
import { Pagination } from '@/components/shared/Pagination';
import { EmptyState, ErrorState } from '@/components/shared/states';
import { Badge } from '@/components/ui/badge';
import { Input, Select } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TBody, Td, Th, THead, Tr } from '@/components/ui/table';
import { formatMoney, formatNumber } from '@/lib/money';
import { titleCase } from '@/lib/utils';
import { useItems } from '../api';

export function ItemListPage() {
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get('page')) || 1);
  const search = params.get('search') ?? '';
  const category = params.get('category') ?? '';
  const condition = params.get('condition') ?? '';
  const sold = params.get('sold') ?? '';

  const filters: ItemFilters = {
    page,
    limit: 20,
    search: search || undefined,
    category: category || undefined,
    condition: condition || undefined,
    sold: sold === '' ? undefined : sold === 'true',
  };
  const q = useItems(filters);

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    next.delete('page');
    setParams(next);
  }

  let body;
  if (q.isPending) {
    body = <div className="space-y-2">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-12" />)}</div>;
  } else if (q.isError) {
    body = <ErrorState error={q.error} onRetry={() => void q.refetch()} />;
  } else if (q.data.items.length === 0) {
    body = <EmptyState title="No items match" description="Try clearing the filters. Items are added from inside a container." />;
  } else {
    body = (
      <>
        <Table>
          <THead>
            <Tr><Th>Item</Th><Th>Container</Th><Th className="text-right">Weight</Th><Th className="text-right">Landed cost</Th><Th>Status</Th></Tr>
          </THead>
          <TBody>
            {q.data.items.map((i) => (
              <Tr key={i.id}>
                <Td><p className="font-medium">{i.name}</p><p className="text-xs text-muted-foreground">{titleCase(i.category)} - {titleCase(i.condition)}</p></Td>
                <Td><Link className="text-primary underline" to={`/containers/${i.container_id}`}>Container #{i.container_id}</Link></Td>
                <Td className="text-right tabular-nums">{formatNumber(i.weight, 3)} kg</Td>
                <Td className="text-right tabular-nums">{formatMoney(i.landed_cost)}</Td>
                <Td>{i.sold ? <Badge tone="success">Sold {formatMoney(i.selling_price)}</Badge> : <Badge>In stock</Badge>}</Td>
              </Tr>
            ))}
          </TBody>
        </Table>
        <Pagination page={q.data.page} pages={q.data.pages} total={q.data.total} onPage={(p) => { const next = new URLSearchParams(params); next.set('page', String(p)); setParams(next); }} />
      </>
    );
  }

  return (
    <>
      <PageHeader title="Items" description="Every item across your containers." />
      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" aria-hidden />
          <Input className="pl-9" placeholder="Search by name" aria-label="Search items" defaultValue={search} onKeyDown={(e) => { if (e.key === 'Enter') setFilter('search', e.currentTarget.value.trim()); }} onBlur={(e) => { if (e.currentTarget.value.trim() !== search) setFilter('search', e.currentTarget.value.trim()); }} />
        </div>
        <Select aria-label="Category" value={category} onChange={(e) => setFilter('category', e.target.value)}>
          <option value="">All categories</option>
          {ITEM_CATEGORIES.map((c) => <option key={c} value={c}>{titleCase(c)}</option>)}
        </Select>
        <Select aria-label="Condition" value={condition} onChange={(e) => setFilter('condition', e.target.value)}>
          <option value="">Any condition</option>
          {ITEM_CONDITIONS.map((c) => <option key={c} value={c}>{titleCase(c)}</option>)}
        </Select>
        <Select aria-label="Sale status" value={sold} onChange={(e) => setFilter('sold', e.target.value)}>
          <option value="">Sold and in stock</option>
          <option value="false">In stock</option>
          <option value="true">Sold</option>
        </Select>
      </div>
      {body}
    </>
  );
}
