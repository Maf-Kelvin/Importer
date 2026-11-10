import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { ROLES } from '@/api/types';
import { applyApiError } from '@/components/shared/forms';
import { FormField } from '@/components/shared/FormField';
import { Button } from '@/components/ui/button';
import { Dialog } from '@/components/ui/dialog';
import { Input, Select } from '@/components/ui/input';
import { useToast } from '@/components/ui/toast';
import { newIdempotencyKey } from '@/lib/idempotency';
import { ROLE_LABEL } from '@/lib/permissions';
import { useCreateUser } from '../api';
import { newUserDefaults, newUserSchema, toUserCreate, type NewUserValues } from '../schemas';

const FIELDS = ['first_name', 'last_name', 'email', 'username', 'password', 'role'] as const;

export function NewUserDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange} title="Add a team member" description="They sign in with the username and password you set here. Share the password through a secure channel.">
      <NewUserForm onDone={() => onOpenChange(false)} />
    </Dialog>
  );
}

function NewUserForm({ onDone }: { onDone: () => void }) {
  const toast = useToast();
  const create = useCreateUser();
  const [idempotencyKey] = useState(newIdempotencyKey);
  const [formError, setFormError] = useState<string | null>(null);
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<NewUserValues>({ resolver: zodResolver(newUserSchema), defaultValues: newUserDefaults });

  async function onSubmit(v: NewUserValues) {
    setFormError(null);
    try {
      await create.mutateAsync({ body: toUserCreate(v), key: idempotencyKey });
      toast({ title: 'Team member added', variant: 'success' });
      onDone();
    } catch (e) {
      setFormError(applyApiError(e, setError, FIELDS));
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      {formError && <p role="alert" className="rounded-md bg-destructive/10 p-2 text-sm text-destructive">{formError}</p>}
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="First name" error={errors.first_name?.message} required><Input autoFocus autoComplete="off" {...register('first_name')} /></FormField>
        <FormField label="Last name" error={errors.last_name?.message} required><Input autoComplete="off" {...register('last_name')} /></FormField>
      </div>
      <FormField label="Email" error={errors.email?.message} required><Input type="email" autoComplete="off" {...register('email')} /></FormField>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Username" error={errors.username?.message} required><Input autoComplete="off" {...register('username')} /></FormField>
        <FormField label="Role" error={errors.role?.message} hint="Viewers can only read; clerks work on their own containers">
          <Select {...register('role')}>{ROLES.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}</Select>
        </FormField>
      </div>
      <FormField label="Initial password" error={errors.password?.message} hint="At least 12 characters" required>
        <Input type="password" autoComplete="new-password" {...register('password')} />
      </FormField>
      <div className="flex justify-end"><Button type="submit" loading={isSubmitting}>Add member</Button></div>
    </form>
  );
}
