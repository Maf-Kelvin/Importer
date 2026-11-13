import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import type { Item } from '@/api/types';
import { CURRENCIES, ITEM_CATEGORIES, ITEM_CONDITIONS } from '@/api/types';
import { applyApiError } from '@/components/shared/forms';
import { FormField } from '@/components/shared/FormField';
import { Button } from '@/components/ui/button';
import { Dialog } from '@/components/ui/dialog';
import { Input, Select, Textarea } from '@/components/ui/input';
import { useToast } from '@/components/ui/toast';
import { newIdempotencyKey } from '@/lib/idempotency';
import { titleCase } from '@/lib/utils';
import { useCreateItem, useUpdateItem } from '../api';
import { itemDefaults, itemSchema, toItemBody, valuesFromItem, type ItemFormValues } from '../schemas';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  containerId: number;
  item?: Item;
}

const FIELDS = ['name', 'description', 'category', 'condition', 'purchase_price', 'purchase_currency', 'purchase_date', 'weight', 'volume'] as const;

export function ItemFormDialog({ open, onOpenChange, containerId, item }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange} size="lg" title={item ? 'Edit item' : 'Add item'} description="Amounts are converted to US dollars at today's exchange rate.">
      <ItemForm containerId={containerId} item={item} onDone={() => onOpenChange(false)} />
    </Dialog>
  );
}

function ItemForm({ containerId, item, onDone }: { containerId: number; item?: Item; onDone: () => void }) {
  const toast = useToast();
  const create = useCreateItem();
  const update = useUpdateItem();
  const [idempotencyKey] = useState(newIdempotencyKey);
  const [formError, setFormError] = useState<string | null>(null);
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<ItemFormValues>({
    resolver: zodResolver(itemSchema),
    defaultValues: item ? valuesFromItem(item) : itemDefaults,
  });

  async function onSubmit(v: ItemFormValues) {
    setFormError(null);
    const body = toItemBody(v);
    try {
      if (item) {
        await update.mutateAsync({ id: item.id, body });
        toast({ title: 'Item updated', description: 'Run cost allocation again to refresh landed costs.', variant: 'success' });
      } else {
        await create.mutateAsync({ body: { ...body, container_id: containerId }, key: idempotencyKey });
        toast({ title: 'Item added', variant: 'success' });
      }
      onDone();
    } catch (e) {
      setFormError(applyApiError(e, setError, FIELDS));
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      {formError && <p role="alert" className="rounded-md bg-destructive/10 p-2 text-sm text-destructive">{formError}</p>}
      <FormField label="Name" error={errors.name?.message} required>
        <Input autoFocus {...register('name')} />
      </FormField>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Category" error={errors.category?.message}>
          <Select {...register('category')}>{ITEM_CATEGORIES.map((c) => <option key={c} value={c}>{titleCase(c)}</option>)}</Select>
        </FormField>
        <FormField label="Condition" error={errors.condition?.message}>
          <Select {...register('condition')}>{ITEM_CONDITIONS.map((c) => <option key={c} value={c}>{titleCase(c)}</option>)}</Select>
        </FormField>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <FormField label="Purchase price" error={errors.purchase_price?.message} required>
          <Input inputMode="decimal" placeholder="0.00" {...register('purchase_price')} />
        </FormField>
        <FormField label="Currency" error={errors.purchase_currency?.message}>
          <Select {...register('purchase_currency')}>{CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}</Select>
        </FormField>
        <FormField label="Purchase date" error={errors.purchase_date?.message}>
          <Input type="date" {...register('purchase_date')} />
        </FormField>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Weight (kg)" error={errors.weight?.message} hint="Optional. Needed only to split costs by weight">
          <Input inputMode="decimal" placeholder="Optional" {...register('weight')} />
        </FormField>
        <FormField label="Volume (m3)" error={errors.volume?.message}>
          <Input inputMode="decimal" placeholder="Optional" {...register('volume')} />
        </FormField>
      </div>
      <FormField label="Description" error={errors.description?.message}>
        <Textarea {...register('description')} />
      </FormField>
      <div className="flex justify-end">
        <Button type="submit" loading={isSubmitting}>{item ? 'Save changes' : 'Add item'}</Button>
      </div>
    </form>
  );
}