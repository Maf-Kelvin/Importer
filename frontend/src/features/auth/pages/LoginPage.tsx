import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { ApiError, userMessage } from '@/api/errors';
import { useAuth } from '@/auth';
import { FormField } from '@/components/shared/FormField';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

const schema = z.object({
  username: z.string().trim().min(1, 'Enter your username'),
  password: z.string().min(1, 'Enter your password'),
});
type Values = z.infer<typeof schema>;

function loginMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 401) return 'Incorrect username or password.';
    if (err.status === 400 || err.status === 403 || err.status === 423) return err.message; // e.g. account locked or disabled
  }
  return userMessage(err);
}

export function LoginPage() {
  const { status, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [formError, setFormError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Values>({ resolver: zodResolver(schema) });

  const from = (location.state as { from?: string } | null)?.from ?? '/';
  if (status === 'authenticated') return <Navigate to={from} replace />;

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      await login(values.username, values.password);
      navigate(from, { replace: true });
    } catch (e) {
      setFormError(loginMessage(e));
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardContent className="space-y-5 p-6">
          <div>
            <h1 className="text-xl font-semibold">Sign in to Importer</h1>
            <p className="mt-1 text-sm text-muted-foreground">Use the account your administrator created for you.</p>
          </div>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            {formError && <p role="alert" className="rounded-md bg-destructive/10 p-2 text-sm text-destructive">{formError}</p>}
            <FormField label="Username" error={errors.username?.message} required>
              <Input autoComplete="username" autoFocus {...register('username')} />
            </FormField>
            <FormField label="Password" error={errors.password?.message} required>
              <Input type="password" autoComplete="current-password" {...register('password')} />
            </FormField>
            <Button type="submit" className="w-full" loading={isSubmitting}>Sign in</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
