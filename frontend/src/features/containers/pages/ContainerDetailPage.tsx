import { ArrowLeft, Calculator, Lock, Pencil, Trash2 } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ApiError } from '@/api/errors';
import { useCurrentUser } from '@/auth';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState, ErrorState } from '@/components/shared/states';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/components/ui/toast';
import { ExpensesSection } from '@/features/expenses';
import { ItemsSection } from '@/features/items';
import { addDecimals, compareDecimals, formatMoney } from '@/lib/money';
import { can } from '@/lib/permissions';
import { titleCase } from '@/lib/utils';
import { useContainer, useDeleteContainer, useSealContainer } from '../api';
import { AllocateDialog } from '../components/AllocateDialog';
import { ContainerFormDialog } from '../components/ContainerFormDialog';

function Stat({ title, value, hint }: { title: string; value: ReactNode; hint?: string }) {
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent>
        <p className="text-xl font-semibold tabular-nums">{value}</p>
        {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  );
}

function BackLink() {
  return <Link to="/containers" className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" aria-hidden /> All containers</Link>;
}

export function ContainerDetailPage() {
  const { id } = useParams();
  const containerId = Number(id);
  const user = useCurrentUser();
  const navigate = useNavigate();
  const toast = useToast();
  const q = useContainer(containerId);
  const seal = useSealContainer(containerId);
  const del = useDeleteContainer(containerId);
  const [editing, setEditing] = useState(false);
  const [allocating, setAllocating] = useState(false);
  const [sealing, setSealing] = useState(false);
  const [deleting, setDeleting] = useState(false);

  if (!Number.isInteger(containerId) || containerId <= 0) {
    return <><BackLink /><EmptyState title="Container not found" /></>;
  }
  if (q.isPending) {
    return <><BackLink /><Skeleton className="mb-4 h-10 w-72" /><div className="grid gap-4 sm:grid-cols-4">{Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-24" />)}</div></>;
  }
  if (q.isError) {
    return (
      <>
        <BackLink />
        {q.error instanceof ApiError && q.error.isNotFound ? <EmptyState title="Container not found" description="It may have been deleted, or it belongs to someone else." /> : <ErrorState error={q.error} onRetry={() => void q.refetch()} />}
      </>
    );
  }

  const d = q.data;
  const expensesTotal = addDecimals(d.expenses.map((e) => e.amount_usd));
  const purchaseTotal = addDecimals(d.items.map((i) => i.purchase_price_usd));
  const landedTotal = addDecimals(d.items.map((i) => i.landed_cost));
  const allocatedTotal = addDecimals(d.items.map((i) => i.allocated_cost));
  const sold = d.items.filter((i) => i.sold).length;
  const needsAllocation = d.items.length > 0 && compareDecimals(expensesTotal, allocatedTotal, 4) !== 0;

  return (
    <>
      <BackLink />
      <PageHeader
        title={d.name}
        description={`${d.container_type} container - cost split by ${titleCase(d.allocation_method)}${d.msc_container_number ? ` - ${d.msc_container_number}` : ''}`}
        actions={
          <>
            {d.is_sealed && <Badge tone="warning">Sealed</Badge>}
            {d.is_shipped && <Badge tone="info">Shipped</Badge>}
            {can(user, 'container.update') && <Button variant="outline" onClick={() => setEditing(true)}><Pencil className="h-4 w-4" aria-hidden /> Edit</Button>}
            {can(user, 'container.allocate') && <Button onClick={() => setAllocating(true)}><Calculator className="h-4 w-4" aria-hidden /> Allocate costs</Button>}
            {can(user, 'container.seal') && !d.is_sealed && <Button variant="outline" onClick={() => setSealing(true)}><Lock className="h-4 w-4" aria-hidden /> Seal</Button>}
            {can(user, 'container.delete') && <Button variant="outline" onClick={() => setDeleting(true)}><Trash2 className="h-4 w-4 text-destructive" aria-hidden /> Delete</Button>}
          </>
        }
      />

      {needsAllocation && (
        <p role="status" className="mb-4 rounded-md border border-warning/40 bg-warning/10 p-3 text-sm">
          Costs are not fully spread over the items: {formatMoney(allocatedTotal)} of {formatMoney(expensesTotal)} allocated.
          {can(user, 'container.allocate') ? ' Run "Allocate costs" to update every item\'s landed cost.' : ' Ask someone with access to allocate the costs.'}
        </p>
      )}

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat title="Items" value={`${sold} sold / ${d.items.length}`} />
        <Stat title="Expenses" value={formatMoney(expensesTotal)} hint="In US dollars" />
        <Stat title="Purchase value" value={formatMoney(purchaseTotal)} hint="Items before shared costs" />
        <Stat title="Landed cost" value={formatMoney(landedTotal)} hint="Purchase value + allocated costs" />
      </div>

      <Tabs defaultValue="items">
        <TabsList>
          <TabsTrigger value="items">Items</TabsTrigger>
          <TabsTrigger value="expenses">Expenses</TabsTrigger>
        </TabsList>
        <TabsContent value="items"><ItemsSection containerId={d.id} items={d.items} /></TabsContent>
        <TabsContent value="expenses"><ExpensesSection containerId={d.id} expenses={d.expenses} /></TabsContent>
      </Tabs>

      {editing && <ContainerFormDialog open onOpenChange={setEditing} container={d} />}
      {allocating && <AllocateDialog open onOpenChange={setAllocating} containerId={d.id} defaultMethod={d.allocation_method} />}
      <ConfirmDialog
        open={sealing}
        onOpenChange={setSealing}
        title="Seal this container?"
        description="Sealing marks the container as closed for loading. Do this when it is ready to ship."
        confirmLabel="Seal container"
        onConfirm={async () => { await seal.mutateAsync(); toast({ title: 'Container sealed', variant: 'success' }); }}
      />
      <ConfirmDialog
        open={deleting}
        onOpenChange={setDeleting}
        title="Delete this container?"
        description="It disappears from your lists. Its items and expenses are kept in the audit history."
        confirmLabel="Delete container"
        destructive
        onConfirm={async () => { await del.mutateAsync(); toast({ title: 'Container deleted', variant: 'success' }); navigate('/containers', { replace: true }); }}
      />
    </>
  );
}
