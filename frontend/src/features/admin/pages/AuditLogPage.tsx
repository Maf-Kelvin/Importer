import { ChevronDown, ChevronRight } from 'lucide-react';
import { Fragment, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { AuditFilters } from '@/api/endpoints';
import { PageHeader } from '@/components/shared/PageHeader';
import { Pagination } from '@/components/shared/Pagination';
import { EmptyState, ErrorState } from '@/components/shared/states';
import { Badge } from '@/components/ui/badge';
import { Select } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TBody, Td, Th, THead, Tr } from '@/components/ui/table';
import { formatDateTime } from '@/lib/utils';
import { useAuditLogs, useUserNames } from '../api';
import { ChangesView } from '../components/ChangesView';

const ACTION_GROUPS: [string, string][] = [
  ['', 'All actions'],
  ['container.', 'Containers'],
  ['item.', 'Items and sales'],
  ['expense.', 'Expenses'],
  ['costs.', 'Cost allocation'],
  ['customer.', 'Customers'],
  ['user.', 'Team'],
  ['file.', 'Files'],
  ['organization.', 'Organisation'],
];
const ENTITY_TYPES = ['Container', 'Item', 'ContainerExpense', 'Customer', 'User', 'Organization', 'File'];

function actionTone(action: string): 'success' | 'info' | 'danger' | 'neutral' {
  if (action.endsWith('.deleted') || action.endsWith('.deactivated')) return 'danger';
  if (action.endsWith('.created')) return 'success';
  if (action.endsWith('.updated') || action.endsWith('.allocated') || action.endsWith('.sold') || action.endsWith('.sealed')) return 'info';
  return 'neutral';
}

export function AuditLogPage() {
  const [params, setParams] = useSearchParams();
  const [open, setOpen] = useState<number | null>(null);
  const page = Math.max(1, Number(params.get('page')) || 1);
  const action = params.get('action') ?? '';
  const entity = params.get('entity') ?? '';
  const filters: AuditFilters = { page, limit: 25, action: action || undefined, entity_type: entity || undefined };
  const q = useAuditLogs(filters);
  const names = useUserNames();

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    next.delete('page');
    setParams(next);
    setOpen(null);
  }

  let body;
  if (q.isPending) {
    body = <div className="space-y-2">{Array.from({ length: 8 }, (_, i) => <Skeleton key={i} className="h-11" />)}</div>;
  } else if (q.isError) {
    body = <ErrorState error={q.error} onRetry={() => void q.refetch()} />;
  } else if (q.data.items.length === 0) {
    body = <EmptyState title="Nothing recorded" description="No activity matches these filters." />;
  } else {
    body = (
      <>
        <Table>
          <THead><Tr><Th><span className="sr-only">Details</span></Th><Th>When</Th><Th>Who</Th><Th>Action</Th><Th>Record</Th><Th>From</Th></Tr></THead>
          <TBody>
            {q.data.items.map((e) => {
              const isOpen = open === e.id;
              const who = e.user_id === null ? 'System' : (names.data?.get(e.user_id) ?? `User #${e.user_id}`);
              return (
                <Fragment key={e.id}>
                  <Tr>
                    <Td className="w-8">
                      <button type="button" className="rounded p-1 hover:bg-muted" aria-expanded={isOpen} aria-label={isOpen ? 'Hide details' : 'Show details'} onClick={() => setOpen(isOpen ? null : e.id)}>
                        {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                      </button>
                    </Td>
                    <Td className="whitespace-nowrap text-muted-foreground">{formatDateTime(e.created_at)}</Td>
                    <Td>{who}</Td>
                    <Td><Badge tone={actionTone(e.action)}>{e.action}</Badge></Td>
                    <Td>{e.entity_type ?? '-'}{e.entity_id !== null && ` #${e.entity_id}`}</Td>
                    <Td className="text-muted-foreground">{e.ip_address ?? '-'}</Td>
                  </Tr>
                  {isOpen && (
                    <Tr>
                      <Td colSpan={6} className="bg-muted/30 p-4"><ChangesView data={e.extra_data} /></Td>
                    </Tr>
                  )}
                </Fragment>
              );
            })}
          </TBody>
        </Table>
        <Pagination page={q.data.page} pages={q.data.pages} total={q.data.total} onPage={(p) => { const next = new URLSearchParams(params); next.set('page', String(p)); setParams(next); setOpen(null); }} />
      </>
    );
  }

  return (
    <>
      <PageHeader title="Audit log" description="Who changed what, newest first. Entries cannot be edited or removed." />
      <div className="mb-4 flex flex-wrap gap-3">
        <Select aria-label="Action" className="w-52" value={action} onChange={(e) => setFilter('action', e.target.value)}>
          {ACTION_GROUPS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </Select>
        <Select aria-label="Record type" className="w-52" value={entity} onChange={(e) => setFilter('entity', e.target.value)}>
          <option value="">All record types</option>
          {ENTITY_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </Select>
      </div>
      {body}
    </>
  );
}
