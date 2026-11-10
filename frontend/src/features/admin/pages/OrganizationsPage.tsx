import { zodResolver } from '@hookform/resolvers/zod';
import { CheckCircle2 } from 'lucide-react';
import { useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import type { OrganizationCreated } from '@/api/types';
import { applyApiError } from '@/components/shared/forms';
import { FormField } from '@/components/shared/FormField';
import { PageHeader } from '@/components/shared/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { newIdempotencyKey } from '@/lib/idempotency';
import { useCreateOrganization } from '../api';
import { organizationDefaults, organizationSchema, slugify, toOrganizationCreate, type OrganizationValues } from '../schemas';

const FIELDS = ['name', 'slug', 'admin_first_name', 'admin_last_name', 'admin_email', 'admin_username', 'admin_password'] as const;

/** Platform administrators only: create a customer organisation together with its first admin. */
export function OrganizationsPage() {
  const create = useCreateOrganization();
  const [idempotencyKey, setKey] = useState(newIdempotencyKey);
  const [created, setCreated] = useState<OrganizationCreated | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const slugTouched = useRef(false);
  const { register, handleSubmit, setValue, reset, setError, formState: { errors, isSubmitting } } = useForm<OrganizationValues>({
    resolver: zodResolver(organizationSchema),
    defaultValues: organizationDefaults,
  });

  async function onSubmit(v: OrganizationValues) {
    setFormError(null);
    try {
      setCreated(await create.mutateAsync({ body: toOrganizationCreate(v), key: idempotencyKey }));
    } catch (e) {
      setFormError(applyApiError(e, setError, FIELDS));
    }
  }

  function another() {
    reset(organizationDefaults);
    slugTouched.current = false;
    setKey(newIdempotencyKey());
    setCreated(null);
  }

  if (created) {
    return (
      <>
        <PageHeader title="Organisations" />
        <Card className="max-w-xl">
          <CardContent className="space-y-3 p-6">
            <p className="flex items-center gap-2 text-lg font-semibold"><CheckCircle2 className="h-5 w-5 text-success" aria-hidden /> Organisation created</p>
            <dl className="grid grid-cols-[9rem_1fr] gap-y-1 text-sm">
              <dt className="text-muted-foreground">Name</dt><dd>{created.name}</dd>
              <dt className="text-muted-foreground">Identifier</dt><dd>{created.slug}</dd>
              <dt className="text-muted-foreground">Plan</dt><dd>{created.plan} ({created.max_users} users, {created.max_containers} containers)</dd>
              <dt className="text-muted-foreground">First admin (id)</dt><dd>{created.admin_user_id}</dd>
            </dl>
            <p className="text-sm text-muted-foreground">Give the admin their username and password through a secure channel. They can change the password after signing in.</p>
            <Button onClick={another}>Create another</Button>
          </CardContent>
        </Card>
      </>
    );
  }

  const nameField = register('name', {
    onChange: (e: { target: { value: string } }) => {
      if (!slugTouched.current) setValue('slug', slugify(e.target.value));
    },
  });
  const slugField = register('slug', { onChange: () => { slugTouched.current = true; } });

  return (
    <>
      <PageHeader title="Organisations" description="Create a customer organisation and its first administrator." />
      <form onSubmit={handleSubmit(onSubmit)} className="max-w-xl space-y-5" noValidate>
        {formError && <p role="alert" className="rounded-md bg-destructive/10 p-2 text-sm text-destructive">{formError}</p>}
        <Card>
          <CardContent className="space-y-4 p-4">
            <h2 className="font-medium">Organisation</h2>
            <FormField label="Name" error={errors.name?.message} required><Input autoFocus {...nameField} /></FormField>
            <FormField label="Identifier" error={errors.slug?.message} hint="Lowercase letters, digits and hyphens. Must be unique." required><Input {...slugField} /></FormField>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="space-y-4 p-4">
            <h2 className="font-medium">First administrator</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label="First name" error={errors.admin_first_name?.message} required><Input autoComplete="off" {...register('admin_first_name')} /></FormField>
              <FormField label="Last name" error={errors.admin_last_name?.message} required><Input autoComplete="off" {...register('admin_last_name')} /></FormField>
            </div>
            <FormField label="Email" error={errors.admin_email?.message} required><Input type="email" autoComplete="off" {...register('admin_email')} /></FormField>
            <FormField label="Username" error={errors.admin_username?.message} required><Input autoComplete="off" {...register('admin_username')} /></FormField>
            <FormField label="Initial password" error={errors.admin_password?.message} hint="At least 12 characters" required><Input type="password" autoComplete="new-password" {...register('admin_password')} /></FormField>
          </CardContent>
        </Card>
        <Button type="submit" loading={isSubmitting}>Create organisation</Button>
      </form>
    </>
  );
}
