import { Pencil, Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';
import type { Expense } from '@/api/types';
import { useCurrentUser } from '@/auth';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { EmptyState } from '@/components/shared/states';
import { Button } from '@/components/ui/button';
import { Table, TBody, Td, Th, THead, Tr } from '@/components/ui/table';
import { useToast } from '@/components/ui/toast';
import { addDecimals, formatMoney } from '@/lib/money';
import { can } from '@/lib/permissions';
import { titleCase } from '@/lib/utils';
import { useDeleteExpense } from '../api';
import { ExpenseFormDialog } from './ExpenseFormDialog';

export function ExpensesSection({ containerId, expenses }: { containerId: number; expenses: Expense[] }) {
  const user = useCurrentUser();
  const toast = useToast();
  const canWrite = can(user, 'expense.write');
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<Expense | null>(null);
  const [deleting, setDeleting] = useState<Expense | null>(null);
  const del = useDeleteExpense();
  const total = addDecimals(expenses.map((e) => e.amount_usd));

  return (
    <section aria-labelledby="expenses-heading" className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 id="expenses-heading" className="font-medium">Expenses ({expenses.length})</h2>
        {canWrite && <Button size="sm" onClick={() => setAdding(true)}><Plus className="h-4 w-4" aria-hidden /> Add expense</Button>}
      </div>

      {expenses.length === 0 ? (
        <EmptyState title="No expenses yet" description="Shipping, clearing and other shared costs go here." action={canWrite ? <Button onClick={() => setAdding(true)}>Add an expense</Button> : undefined} />
      ) : (
        <Table>
          <THead>
            <Tr><Th>Type</Th><Th>Description</Th><Th className="text-right">Amount</Th><Th className="text-right">In USD</Th>{canWrite && <Th><span className="sr-only">Actions</span></Th>}</Tr>
          </THead>
          <TBody>
            {expenses.map((e) => (
              <Tr key={e.id}>
                <Td className="font-medium">{titleCase(e.expense_type)}</Td>
                <Td className="text-muted-foreground">{e.description ?? '-'}</Td>
                <Td className="text-right tabular-nums">{formatMoney(e.amount, e.currency)}</Td>
                <Td className="text-right tabular-nums">{formatMoney(e.amount_usd)}</Td>
                {canWrite && (
                  <Td>
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" aria-label={`Edit ${titleCase(e.expense_type)}`} onClick={() => setEditing(e)}><Pencil className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" aria-label={`Delete ${titleCase(e.expense_type)}`} onClick={() => setDeleting(e)}><Trash2 className="h-4 w-4 text-destructive" /></Button>
                    </div>
                  </Td>
                )}
              </Tr>
            ))}
            <Tr className="font-medium">
              <Td colSpan={3} className="text-right">Total</Td>
              <Td className="text-right tabular-nums">{formatMoney(total)}</Td>
              {canWrite && <Td />}
            </Tr>
          </TBody>
        </Table>
      )}

      {adding && <ExpenseFormDialog open onOpenChange={setAdding} containerId={containerId} />}
      {editing && <ExpenseFormDialog open onOpenChange={(o) => !o && setEditing(null)} containerId={containerId} expense={editing} />}
      {deleting && (
        <ConfirmDialog
          open
          onOpenChange={(o) => !o && setDeleting(null)}
          title="Delete this expense?"
          description="This cannot be undone. Run cost allocation again afterwards."
          confirmLabel="Delete expense"
          destructive
          onConfirm={async () => {
            await del.mutateAsync(deleting.id);
            toast({ title: 'Expense deleted', variant: 'success' });
          }}
        />
      )}
    </section>
  );
}
