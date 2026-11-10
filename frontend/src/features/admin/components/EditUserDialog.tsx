import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import type { User } from '@/api/types';
import { ROLES } from '@/api/types';
import { applyApiError } from '@/components/shared/forms';
import { FormField } from '@/components/shared/FormField';
import { Button } from '@/components/ui/button';
import { Dialog } from '@/components/ui/dialog';
import { Input, Select } from '@/components/ui/input';
import { useToast } from '@/components/ui/toast';
import { ROLE_LABEL } from '@/lib/permissions';
import { useUpdateUser } from '../api';
import { editUserSchema, toUserUpdate, valuesFromUser, type EditUserValues } from '../schemas';

const FIELDS = ['first_name', 'last_name', 'email', 'username', 'role', 'is_active', 'password'] as const;

interface Props {
  user: User;
  isSelf: boolean;
  onOpenChange: (open: boolean) => void;
}

export function EditUserDialog({ user, isSelf, onOpenChange }: Props) {
  return (
    <Dialog open onOpenChange={onOpenChange} title={`Edit ${user.first_name} ${user.last_name}`} description={isSelf ? 'This is your own account.' : undefined}>
      <EditUserForm user={user} isSelf={isSelf} onDone={() => onOpenChange(false)} />
    </Dialog>
  );
}

function EditUserForm({ user, isSelf, onDone }: { user: User; isSelf: boolean; onDone: () => void }) {
  const toast = useToast();
  const update = useUpdateUser();
  const [formError, setFormError] = useState<string | null>(null);
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<EditUserValues>({ resolver: zodResolver(editUserSchema), defaultValues: valuesFromUser(user) });

  async function onSubmit(v: EditUserValues) {
    setFormError(null);
    try {
      await update.mutateAsync({ id: user.id, body: toUserUpdate(v, user, isSelf) });
      toast({ title: 'Changes saved', variant: 'success' });
      onDone();
    } catch (e) {
      setFormError(applyApiError(e, setError, FIELDS));
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      {formError && <p role="alert" className="rounded-md bg-destructive/10 p-2 text-sm text-destructive">{formError}</p>}
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="First name" error={errors.first_name?.message} required><Input {...register('first_name')} /></FormField>
        <FormField label="Last name" error={errors.last_name?.message} required><Input {...register('last_name')} /></FormField>
      </div>
      <FormField label="Email" error={errors.email?.message} required><Input type="email" {...register('email')} /></FormField>
      <FormField label="Username" error={errors.username?.message} required><Input {...register('username')} /></FormField>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Role" error={errors.role?.message} hint={isSelf ? 'You cannot change your own role' : undefined}>
          <Select disabled={isSelf} {...register('role')}>{ROLES.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}</Select>
        </FormField>
        <label className="flex items-center gap-2 self-end pb-2 text-sm">
          <input type="checkbox" disabled={isSelf} {...register('is_active')} /> Account is active
        </label>
      </div>
      <FormField label="New password" error={errors.password?.message} hint="Leave empty to keep the current password">
        <Input type="password" autoComplete="new-password" {...register('password')} />
      </FormField>
      <div className="flex justify-end"><Button type="submit" loading={isSubmitting}>Save changes</Button></div>
    </form>
  );
}
