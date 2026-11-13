import { DollarSign, Pencil, Plus, Tag, Trash2 } from 'lucide-react';
import { useState } from 'react';
import type { Item } from '@/api/types';
import { useCurrentUser } from '@/auth';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { EmptyState } from '@/components/shared/states';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TBody, Td, Th, THead, Tr } from '@/components/ui/table';
import { useToast } from '@/components/ui/toast';
import { PricingDialog } from '@/features/pricing';
import { formatMoney, formatNumber } from '@/lib/money';
import { can } from '@/lib/permissions';
import { titleCase } from '@/lib/utils';
import { useDeleteItem } from '../api';
import { ItemFormDialog } from './ItemFormDialog';
import { MarkSoldDialog } from './MarkSoldDialog';

/** The items of one container: table, add/edit/sell/delete, with the same permission rules as the server. */
export function ItemsSection({ containerId, items }: { containerId: number; items: Item[] }) {
  const user = useCurrentUser();
  const toast = useToast();
  const canWrite = can(user, 'item.write');
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<Item | null>(null);
  const [selling, setSelling] = useState<Item | null>(null);
  const [deleting, setDeleting] = useState<Item | null>(null);
  const [pricing, setPricing] = useState<Item | null>(null);
  const canPrice = can(user, 'pricing.generate');
  const del = useDeleteItem();

  return (
    <section aria-labelledby="items-heading" className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 id="items-heading" className="font-medium">Items ({items.length})</h2>
        {canWrite && <Button size="sm" onClick={() => setAdding(true)}><Plus className="h-4 w-4" aria-hidden /> Add item</Button>}
      </div>

      {items.length === 0 ? (
        <EmptyState title="No items yet" description="Add the goods in this container so costs can be shared across them." action={canWrite ? <Button onClick={() => setAdding(true)}>Add the first item</Button> : undefined} />
      ) : (
        <Table>
          <THead>
            <Tr>
              <Th>Item</Th><Th className="text-right">Weight</Th><Th className="text-right">Purchase price</Th>
              <Th className="text-right">Allocated</Th><Th className="text-right">Landed cost</Th><Th>Status</Th>
              {canWrite && <Th><span className="sr-only">Actions</span></Th>}
            </Tr>
          </THead>
          <TBody>
            {items.map((i) => (
              <Tr key={i.id}>
                <Td>
                  <p className="font-medium">{i.name}</p>
                  <p className="text-xs text-muted-foreground">{titleCase(i.category)} - {titleCase(i.condition)}</p>
                </Td>
                <Td className="text-right tabular-nums">{i.weight == null ? '-' : `${formatNumber(i.weight, 3)} kg`}</Td>
                <Td className="text-right tabular-nums">{formatMoney(i.purchase_price, i.purchase_currency)}</Td>
                <Td className="text-right tabular-nums">{formatMoney(i.allocated_cost)}</Td>
                <Td className="text-right tabular-nums">{formatMoney(i.landed_cost)}</Td>
                <Td>{i.sold ? <Badge tone="success">Sold {formatMoney(i.selling_price)}</Badge> : <Badge>In stock</Badge>}</Td>
                {canWrite && (
                  <Td>
                    <div className="flex justify-end gap-1">
                      {!i.sold && canPrice && <Button variant="ghost" size="icon" aria-label={`Price ${i.name}`} onClick={() => setPricing(i)}><Tag className="h-4 w-4" /></Button>}
                      {!i.sold && <Button variant="ghost" size="icon" aria-label={`Sell ${i.name}`} onClick={() => setSelling(i)}><DollarSign className="h-4 w-4" /></Button>}
                      <Button variant="ghost" size="icon" aria-label={`Edit ${i.name}`} onClick={() => setEditing(i)}><Pencil className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" aria-label={`Delete ${i.name}`} onClick={() => setDeleting(i)}><Trash2 className="h-4 w-4 text-destructive" /></Button>
                    </div>
                  </Td>
                )}
              </Tr>
            ))}
          </TBody>
        </Table>
      )}

      {adding && <ItemFormDialog open onOpenChange={setAdding} containerId={containerId} />}
      {editing && <ItemFormDialog open onOpenChange={(o) => !o && setEditing(null)} containerId={containerId} item={editing} />}
      {pricing && <PricingDialog open onOpenChange={(o) => !o && setPricing(null)} item={pricing} />}
      {selling && <MarkSoldDialog open onOpenChange={(o) => !o && setSelling(null)} item={selling} />}
      {deleting && (
        <ConfirmDialog
          open
          onOpenChange={(o) => !o && setDeleting(null)}
          title="Delete this item?"
          description={`"${deleting.name}" will be removed from the container. Run cost allocation again afterwards.`}
          confirmLabel="Delete item"
          destructive
          onConfirm={async () => {
            await del.mutateAsync(deleting.id);
            toast({ title: 'Item deleted', variant: 'success' });
          }}
        />
      )}
    </section>
  );
}