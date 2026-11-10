import { useState } from 'react';
import type { AllocationMethod, AllocationResult } from '@/api/types';
import { ALLOCATION_METHODS } from '@/api/types';
import { userMessage } from '@/api/errors';
import { FormField } from '@/components/shared/FormField';
import { Button } from '@/components/ui/button';
import { Dialog } from '@/components/ui/dialog';
import { Select } from '@/components/ui/input';
import { Table, TBody, Td, Th, THead, Tr } from '@/components/ui/table';
import { formatMoney, formatPercent } from '@/lib/money';
import { titleCase } from '@/lib/utils';
import { useAllocateCosts } from '../api';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  containerId: number;
  defaultMethod: AllocationMethod;
}

export function AllocateDialog({ open, onOpenChange, containerId, defaultMethod }: Props) {
  const allocate = useAllocateCosts(containerId);
  const [method, setMethod] = useState<AllocationMethod>(defaultMethod);
  const [result, setResult] = useState<AllocationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setError(null);
    try {
      setResult(await allocate.mutateAsync(method));
    } catch (e) {
      setResult(null);
      setError(userMessage(e));
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => { onOpenChange(o); if (!o) { setResult(null); setError(null); } }}
      title="Allocate shared costs"
      description="Spreads the container's expenses over its items. Run it again after changing an item's price or weight, or an expense."
      size="lg"
    >
      <div className="flex flex-wrap items-end gap-3">
        <div className="w-56">
          <FormField label="Split by">
            <Select value={method} onChange={(e) => setMethod(e.target.value as AllocationMethod)}>
              {ALLOCATION_METHODS.map((m) => <option key={m} value={m}>{titleCase(m)}</option>)}
            </Select>
          </FormField>
        </div>
        <Button onClick={() => void run()} loading={allocate.isPending}>Allocate costs</Button>
      </div>
      {error && <p role="alert" className="mt-3 rounded-md bg-destructive/10 p-2 text-sm text-destructive">{error}</p>}
      {result && (
        <div className="mt-4 space-y-3">
          <p className="text-sm">
            Spread <strong className="tabular-nums">{formatMoney(result.allocated_total)}</strong> of <strong className="tabular-nums">{formatMoney(result.total_expenses)}</strong> across {result.items.length} items by {titleCase(result.method)}.
            The shares add up exactly.
          </p>
          <Table>
            <THead><Tr><Th>Item</Th><Th className="text-right">Share of basis</Th><Th className="text-right">Allocated</Th><Th className="text-right">Landed cost</Th></Tr></THead>
            <TBody>
              {result.items.map((i) => (
                <Tr key={i.item_id}>
                  <Td>{i.item_name}</Td>
                  <Td className="text-right tabular-nums">{formatPercent(i.ratio, 2)}</Td>
                  <Td className="text-right tabular-nums">{formatMoney(i.allocated_cost)}</Td>
                  <Td className="text-right tabular-nums">{formatMoney(i.landed_cost)}</Td>
                </Tr>
              ))}
            </TBody>
          </Table>
        </div>
      )}
    </Dialog>
  );
}
