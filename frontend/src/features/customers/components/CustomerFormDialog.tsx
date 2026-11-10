import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import type { Customer } from '@/api/types';
import { applyApiError } from '@/components/shared/forms';
import { FormField } from '@/components/shared/FormField';
import { Button } from '@/components/ui/button';
import { Dialog } from '@/components/ui/dialog';
import { Input, Textarea } from '@/components/ui/input';
import { useToast } from '@/components/ui/toast';
import { newIdempotencyKey } from '@/lib/idempotency';
import { useCreateCustomer, useUpdateCustomer } from '../api';
import { customerDefaults, customerSchema, toCustomerBody, valuesFromCustomer, type CustomerFormValues } from '../schemas';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  customer?: Customer;
}

const FIELDS = ['name', 'email', 'phone', 'address', 'notes'] as const;

export function CustomerFormDialog({ open, onOpenChange, customer }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange} title={customer ? 'Edit customer' : 'New customer'} description="Customers can be chosen when you record a sale.">
      <CustomerForm customer={customer} onDone={() => onOpenChange(false)} />
    </Dialog>
  );
}

function CustomerForm({ customer, onDone }: { customer?: Customer; onDone: () => void }) {
  const toast = useToast();
  const create = useCreateCustomer();
  const update = useUpdateCustomer();
  const [idempotencyKey] = useState(newIdempotencyKey);
  const [formError, setFormError] = useState<string | null>(null);
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<CustomerFormValues>({
    resolver: zodResolver(customerSchema),
    defaultValues: customer ? valuesFromCustomer(customer) : customerDefaults,
  });

  async function onSubmit(v: CustomerFormValues) {
    setFormError(null);
    const body = toCustomerBody(v);
    try {
      if (customer) {
        await update.mutateAsync({ id: customer.id, body });
        toast({ title: 'Customer updated', variant: 'success' });
      } else {
        await create.mutateAsync({ body, key: idempotencyKey });
        toast({ title: 'Customer added', variant: 'success' });
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
        <FormField label="Email" error={errors.email?.message}>
          <Input type="email" autoComplete="off" {...register('email')} />
        </FormField>
        <FormField label="Phone" error={errors.phone?.message}>
          <Input type="tel" autoComplete="off" {...register('phone')} />
        </FormField>
      </div>
      <FormField label="Address" error={errors.address?.message}>
        <Textarea {...register('address')} />
      </FormField>
      <FormField label="Notes" error={errors.notes?.message}>
        <Textarea {...register('notes')} />
      </FormField>
      <div className="flex justify-end"><Button type="submit" loading={isSubmitting}>{customer ? 'Save changes' : 'Add customer'}</Button></div>
    </form>
  );
}
