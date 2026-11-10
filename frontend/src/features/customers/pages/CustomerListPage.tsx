import { Pencil, Plus, Search, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { Customer } from '@/api/types';
import { useCurrentUser } from '@/auth';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { PageHeader } from '@/components/shared/PageHeader';
import { Pagination } from '@/components/shared/Pagination';
import { EmptyState, ErrorState } from '@/components/shared/states';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TBody, Td, Th, THead, Tr } from '@/components/ui/table';
import { useToast } from '@/components/ui/toast';
import { can } from '@/lib/permissions';
import { formatDate } from '@/lib/utils';
import { useCustomers, useDeleteCustomer } from '../api';
import { CustomerFormDialog } from '../components/CustomerFormDialog';

export function CustomerListPage() {
  const user = useCurrentUser();
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get('page')) || 1);
  const search = params.get('search') ?? '';
  const q = useCustomers({ page, limit: 20, search: search || undefined });
  const del = useDeleteCustomer();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Customer | null>(null);
  const [deleting, setDeleting] = useState<Customer | null>(null);
  const canWrite = can(user, 'customer.write');
  const canDelete = can(user, 'customer.delete');

  function setSearch(value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set('search', value);
    else next.delete('search');
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
        title={search ? 'No customers match' : 'No customers yet'}
        description={search ? 'Try a different name or email.' : 'Add the people you sell to, then pick them when you record a sale.'}
        action={canWrite && !search ? <Button onClick={() => setCreating(true)}>Add your first customer</Button> : undefined}
      />
    );
  } else {
    body = (
      <>
        <Table>
          <THead>
            <Tr><Th>Name</Th><Th>Email</Th><Th>Phone</Th><Th>Added</Th>{(canWrite || canDelete) && <Th><span className="sr-only">Actions</span></Th>}</Tr>
          </THead>
          <TBody>
            {q.data.items.map((c) => (
              <Tr key={c.id}>
                <Td className="font-medium">{c.name}</Td>
                <Td className="text-muted-foreground">{c.email ?? '-'}</Td>
                <Td className="text-muted-foreground">{c.phone ?? '-'}</Td>
                <Td className="text-muted-foreground">{formatDate(c.created_at)}</Td>
                {(canWrite || canDelete) && (
                  <Td>
                    <div className="flex justify-end gap-1">
                      {canWrite && <Button variant="ghost" size="icon" aria-label={`Edit ${c.name}`} onClick={() => setEditing(c)}><Pencil className="h-4 w-4" /></Button>}
                      {canDelete && <Button variant="ghost" size="icon" aria-label={`Delete ${c.name}`} onClick={() => setDeleting(c)}><Trash2 className="h-4 w-4 text-destructive" /></Button>}
                    </div>
                  </Td>
                )}
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
        title="Customers"
        description="The people and businesses you sell to."
        actions={canWrite ? <Button onClick={() => setCreating(true)}><Plus className="h-4 w-4" aria-hidden /> New customer</Button> : undefined}
      />
      <div className="relative mb-4 max-w-sm">
        <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" aria-hidden />
        <Input
          className="pl-9"
          placeholder="Search by name or email"
          aria-label="Search customers"
          defaultValue={search}
          onKeyDown={(e) => { if (e.key === 'Enter') setSearch(e.currentTarget.value.trim()); }}
          onBlur={(e) => { if (e.currentTarget.value.trim() !== search) setSearch(e.currentTarget.value.trim()); }}
        />
      </div>
      {body}
      {creating && <CustomerFormDialog open onOpenChange={setCreating} />}
      {editing && <CustomerFormDialog open onOpenChange={(o) => !o && setEditing(null)} customer={editing} />}
      {deleting && (
        <ConfirmDialog
          open
          onOpenChange={(o) => !o && setDeleting(null)}
          title="Delete this customer?"
          description={`"${deleting.name}" is removed from your list. Past sales to them are kept.`}
          confirmLabel="Delete customer"
          destructive
          onConfirm={async () => {
            await del.mutateAsync(deleting.id);
            toast({ title: 'Customer deleted', variant: 'success' });
          }}
        />
      )}
    </>
  );
}
