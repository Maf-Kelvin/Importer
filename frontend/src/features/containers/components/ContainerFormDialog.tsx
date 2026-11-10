import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import type { Container } from '@/api/types';
import { ALLOCATION_METHODS, CONTAINER_TYPES } from '@/api/types';
import { applyApiError } from '@/components/shared/forms';
import { FormField } from '@/components/shared/FormField';
import { Button } from '@/components/ui/button';
import { Dialog } from '@/components/ui/dialog';
import { Input, Select, Textarea } from '@/components/ui/input';
import { useToast } from '@/components/ui/toast';
import { newIdempotencyKey } from '@/lib/idempotency';
import { titleCase } from '@/lib/utils';
import { useCreateContainer, useUpdateContainer } from '../api';
import { containerDefaults, containerSchema, toCreateBody, valuesFromContainer, type ContainerFormValues } from '../schemas';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** present = edit this container; absent = create a new one */
  container?: Container;
  onCreated?: (c: Container) => void;
}

const FIELDS = ['name', 'container_type', 'msc_container_number', 'allocation_method', 'notes'] as const;

export function ContainerFormDialog({ open, onOpenChange, container, onCreated }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange} title={container ? 'Edit container' : 'New container'} description="A container groups the items you import together with its shared costs.">
      <ContainerForm container={container} onDone={(c) => { onOpenChange(false); if (!container) onCreated?.(c); }} />
    </Dialog>
  );
}

function ContainerForm({ container, onDone }: { container?: Container; onDone: (c: Container) => void }) {
  const toast = useToast();
  const create = useCreateContainer();
  const update = useUpdateContainer(container?.id ?? 0);
  // One key per form instance: a retry of the SAME submission can never create a second container.
  const [idempotencyKey] = useState(newIdempotencyKey);
  const [formError, setFormError] = useState<string | null>(null);
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<ContainerFormValues>({
    resolver: zodResolver(containerSchema),
    defaultValues: container ? valuesFromContainer(container) : containerDefaults,
  });

  async function onSubmit(v: ContainerFormValues) {
    setFormError(null);
    try {
      let saved: Container;
      if (container) {
        saved = await update.mutateAsync({ name: v.name, msc_container_number: v.msc_container_number || null, allocation_method: v.allocation_method, notes: v.notes || null });
        toast({ title: 'Container updated', variant: 'success' });
      } else {
        saved = await create.mutateAsync({ body: toCreateBody(v), key: idempotencyKey });
        toast({ title: 'Container created', variant: 'success' });
      }
      onDone(saved);
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
        <FormField label="Container type" error={errors.container_type?.message} hint={container ? 'Cannot be changed after creation' : undefined}>
          <Select disabled={Boolean(container)} {...register('container_type')}>
            {CONTAINER_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </Select>
        </FormField>
        <FormField label="Cost allocation" error={errors.allocation_method?.message} hint="How shared expenses are split across items">
          <Select {...register('allocation_method')}>
            {ALLOCATION_METHODS.map((m) => <option key={m} value={m}>{titleCase(m)}</option>)}
          </Select>
        </FormField>
      </div>
      <FormField label="Carrier container number" error={errors.msc_container_number?.message} hint="Optional. Needed for shipment tracking">
        <Input {...register('msc_container_number')} />
      </FormField>
      <FormField label="Notes" error={errors.notes?.message}>
        <Textarea {...register('notes')} />
      </FormField>
      <div className="flex justify-end gap-2">
        <Button type="submit" loading={isSubmitting}>{container ? 'Save changes' : 'Create container'}</Button>
      </div>
    </form>
  );
}
