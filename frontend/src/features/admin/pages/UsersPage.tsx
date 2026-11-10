import { Pencil, Plus, UserX } from 'lucide-react';
import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { User } from '@/api/types';
import { useCurrentUser } from '@/auth';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { PageHeader } from '@/components/shared/PageHeader';
import { Pagination } from '@/components/shared/Pagination';
import { ErrorState } from '@/components/shared/states';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TBody, Td, Th, THead, Tr } from '@/components/ui/table';
import { useToast } from '@/components/ui/toast';
import { ROLE_LABEL } from '@/lib/permissions';
import { formatDateTime } from '@/lib/utils';
import { useDeactivateUser, useUsers } from '../api';
import { EditUserDialog } from '../components/EditUserDialog';
import { NewUserDialog } from '../components/NewUserDialog';

export function UsersPage() {
  const me = useCurrentUser();
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get('page')) || 1);
  const q = useUsers(page);
  const deactivate = useDeactivateUser();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [deactivating, setDeactivating] = useState<User | null>(null);

  let body;
  if (q.isPending) {
    body = <div className="space-y-2">{Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-12" />)}</div>;
  } else if (q.isError) {
    body = <ErrorState error={q.error} onRetry={() => void q.refetch()} />;
  } else {
    body = (
      <>
        <Table>
          <THead><Tr><Th>Name</Th><Th>Username</Th><Th>Role</Th><Th>Status</Th><Th>Last sign-in</Th><Th><span className="sr-only">Actions</span></Th></Tr></THead>
          <TBody>
            {q.data.items.map((u) => {
              const isSelf = u.id === me.id;
              return (
                <Tr key={u.id}>
                  <Td>
                    <p className="font-medium">{u.first_name} {u.last_name}{isSelf && <span className="ml-2 text-xs text-muted-foreground">(you)</span>}</p>
                    <p className="text-xs text-muted-foreground">{u.email}</p>
                  </Td>
                  <Td className="text-muted-foreground">{u.username}</Td>
                  <Td><Badge tone={u.role === 'admin' ? 'info' : 'neutral'}>{ROLE_LABEL[u.role]}</Badge></Td>
                  <Td>{u.is_active ? <Badge tone="success">Active</Badge> : <Badge tone="danger">Deactivated</Badge>}</Td>
                  <Td className="text-muted-foreground">{formatDateTime(u.last_login)}</Td>
                  <Td>
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" aria-label={`Edit ${u.first_name} ${u.last_name}`} onClick={() => setEditing(u)}><Pencil className="h-4 w-4" /></Button>
                      {!isSelf && u.is_active && (
                        <Button variant="ghost" size="icon" aria-label={`Deactivate ${u.first_name} ${u.last_name}`} onClick={() => setDeactivating(u)}><UserX className="h-4 w-4 text-destructive" /></Button>
                      )}
                    </div>
                  </Td>
                </Tr>
              );
            })}
          </TBody>
        </Table>
        <Pagination page={q.data.page} pages={q.data.pages} total={q.data.total} onPage={(p) => { const next = new URLSearchParams(params); next.set('page', String(p)); setParams(next); }} />
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Team"
        description="The people who can sign in to your organisation."
        actions={<Button onClick={() => setCreating(true)}><Plus className="h-4 w-4" aria-hidden /> Add member</Button>}
      />
      {body}
      {creating && <NewUserDialog open onOpenChange={setCreating} />}
      {editing && <EditUserDialog user={editing} isSelf={editing.id === me.id} onOpenChange={(o) => !o && setEditing(null)} />}
      {deactivating && (
        <ConfirmDialog
          open
          onOpenChange={(o) => !o && setDeactivating(null)}
          title="Deactivate this account?"
          description={`${deactivating.first_name} ${deactivating.last_name} will no longer be able to sign in. Their history is kept, and you can re-activate the account later by editing it.`}
          confirmLabel="Deactivate"
          destructive
          onConfirm={async () => {
            await deactivate.mutateAsync(deactivating.id);
            toast({ title: 'Account deactivated', variant: 'success' });
          }}
        />
      )}
    </>
  );
}
