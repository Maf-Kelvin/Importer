import { Outlet } from 'react-router-dom';
import { can, canCreateOrganizations, type Action } from '@/lib/permissions';
import { useCurrentUser } from './auth-context';

/**
 * Wrap routes that only some people may open. This is a convenience (a clear message instead of a page full of
 * 403 errors): the SERVER still enforces every one of these rules.
 */
export function RequireAccess({ action, platformAdmin }: { action?: Action; platformAdmin?: boolean }) {
  const user = useCurrentUser();
  const allowed = platformAdmin ? canCreateOrganizations(user) : action ? can(user, action) : true;
  if (allowed) return <Outlet />;
  return (
    <div role="alert" className="mx-auto mt-16 max-w-md rounded-lg border border-border bg-card p-8 text-center">
      <h1 className="text-lg font-semibold">You don&apos;t have access to this page</h1>
      <p className="mt-2 text-sm text-muted-foreground">Ask an administrator if you think you should.</p>
    </div>
  );
}
