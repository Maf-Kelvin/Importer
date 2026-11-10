import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import type { Item } from '@/api/types';
import { applyApiError } from '@/components/shared/forms';
import { FormField } from '@/components/shared/FormField';
import { Button } from '@/components/ui/button';
import { Dialog } from '@/components/ui/dialog';
import { Input, Select } from '@/components/ui/input';
import { useToast } from '@/components/ui/toast';
import { useCustomerOptions } from '@/features/customers';
import { newIdempotencyKey } from '@/lib/idempotency';
import { MONEY_DECIMALS, formatMoney, requireDecimal } from '@/lib/money';
import { useMarkSold } from '../api';
import { soldSchema, type SoldFormValues } from '../schemas';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  item: Item;
}

export function MarkSoldDialog({ open, onOpenChange, item }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange} title={`Sell "${item.name}"`} description={`Landed cost: ${formatMoney(item.landed_cost)}`}>
      <SoldForm item={item} onDone={() => onOpenChange(false)} />
    </Dialog>
  );
}

function SoldForm({ item, onDone }: { item: Item; onDone: () => void }) {
  const toast = useToast();
  const sell = useMarkSold();
  const customers = useCustomerOptions();
  const [idempotencyKey] = useState(newIdempotencyKey);
  const [formError, setFormError] = useState<string | null>(null);
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<SoldFormValues>({
    resolver: zodResolver(soldSchema),
    defaultValues: { selling_price: '', sold_date: new Date().toLocaleDateString('en-CA'), customer_id: '' }, // en-CA = YYYY-MM-DD in local time
  });

  async function onSubmit(v: SoldFormValues) {
    setFormError(null);
    try {
      await sell.mutateAsync({
        id: item.id,
        body: { selling_price: requireDecimal(v.selling_price, MONEY_DECIMALS), sold_date: v.sold_date, customer_id: v.customer_id ? Number(v.customer_id) : null },
        key: idempotencyKey,
      });
      toast({ title: 'Sale recorded', variant: 'success' });
      onDone();
    } catch (e) {
      setFormError(applyApiError(e, setError, ['selling_price', 'sold_date', 'customer_id']));
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      {formError && <p role="alert" className="rounded-md bg-destructive/10 p-2 text-sm text-destructive">{formError}</p>}
      <FormField label="Selling price (USD)" error={errors.selling_price?.message} required>
        <Input inputMode="decimal" autoFocus placeholder="0.00" {...register('selling_price')} />
      </FormField>
      <FormField label="Sale date" error={errors.sold_date?.message} required>
        <Input type="date" {...register('sold_date')} />
      </FormField>
      <FormField label="Customer" error={errors.customer_id?.message} hint={customers.isError ? 'Customers could not be loaded: you can still record the sale without one' : 'Optional'}>
        <Select disabled={customers.isPending} {...register('customer_id')}>
          <option value="">No customer</option>
          {(customers.data?.items ?? []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </Select>
      </FormField>
      <div className="flex justify-end"><Button type="submit" loading={isSubmitting}>Record sale</Button></div>
    </form>
  );
}
