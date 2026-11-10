import { Plus } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import type { ContainerFilters } from '@/api/endpoints';
import { CONTAINER_TYPES } from '@/api/types';
import { useCurrentUser } from '@/auth';
import { PageHeader } from '@/components/shared/PageHeader';
import { Pagination } from '@/components/shared/Pagination';
import { EmptyState, ErrorState } from '@/components/shared/states';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TBody, Td, Th, THead, Tr } from '@/components/ui/table';
import { can } from '@/lib/permissions';
import { formatDate, titleCase } from '@/lib/utils';
import { useContainers } from '../api';
import { ContainerFormDialog } from '../components/ContainerFormDialog';

export function ContainerListPage() {
  const user = useCurrentUser();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [creating, setCreating] = useState(false);
  const page = Math.max(1, Number(params.get('page')) || 1);
  const type = params.get('type') ?? '';
  const shipped = params.get('shipped') ?? '';

  const filters: ContainerFilters = {
    page,
    limit: 20,
    container_type: type || undefined,
    is_shipped: shipped === '' ? undefined : shipped === 'true',
  };
  const q = useContainers(filters);
  const canCreate = can(user, 'container.create');

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    next.delete('page');
    setParams(next);
  }

  let body;
  if (q.isPending) {
    body = <div className="space-y-2">{Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-12" />)}</div>;
  } else if (q.isError) {
    body = <ErrorState error={q.error} onRetry={() => void q.refetch()} />;
  } else if (q.data.items.length === 0) {
    body = (
      <EmptyState
        title="No containers yet"
        description={type || shipped ? 'No container matches these filters.' : 'Create a container, add its items and expenses, then allocate the costs.'}
        action={canCreate && !type && !shipped ? <Button onClick={() => setCreating(true)}>Create your first container</Button> : undefined}
      />
    );
  } else {
    body = (
      <>
        <Table>
          <THead>
            <Tr><Th>Name</Th><Th>Type</Th><Th>Carrier no.</Th><Th>Cost split</Th><Th>Status</Th><Th>Created</Th></Tr>
          </THead>
          <TBody>
            {q.data.items.map((c) => (
              <Tr key={c.id}>
                <Td><Link to={`/containers/${c.id}`} className="font-medium text-primary underline-offset-2 hover:underline">{c.name}</Link></Td>
                <Td>{c.container_type}</Td>
                <Td className="text-muted-foreground">{c.msc_container_number ?? '-'}</Td>
                <Td>{titleCase(c.allocation_method)}</Td>
                <Td>
                  <div className="flex gap-1">
                    {c.is_sealed && <Badge tone="warning">Sealed</Badge>}
                    {c.is_shipped && <Badge tone="info">Shipped</Badge>}
                    {!c.is_sealed && !c.is_shipped && <Badge>Open</Badge>}
                  </div>
                </Td>
                <Td className="text-muted-foreground">{formatDate(c.created_at)}</Td>
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
      <PageHeader
        title="Containers"
        description={user.role === 'clerk' && !user.is_superuser ? 'The containers you own.' : 'All containers in your organisation.'}
        actions={canCreate ? <Button onClick={() => setCreating(true)}><Plus className="h-4 w-4" aria-hidden /> New container</Button> : undefined}
      />
      <div className="mb-4 flex flex-wrap gap-3">
        <Select aria-label="Container type" className="w-40" value={type} onChange={(e) => setFilter('type', e.target.value)}>
          <option value="">All types</option>
          {CONTAINER_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </Select>
        <Select aria-label="Shipping status" className="w-44" value={shipped} onChange={(e) => setFilter('shipped', e.target.value)}>
          <option value="">Shipped or not</option>
          <option value="true">Shipped</option>
          <option value="false">Not shipped</option>
        </Select>
      </div>
      {body}
      {creating && <ContainerFormDialog open onOpenChange={setCreating} onCreated={(c) => navigate(`/containers/${c.id}`)} />}
    </>
  );
}
