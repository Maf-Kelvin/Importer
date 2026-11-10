import { useAuth, useCurrentUser } from '@/auth';
import { ThemeToggle } from '@/components/layout/ThemeToggle';
import { PageHeader } from '@/components/shared/PageHeader';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { ROLE_LABEL } from '@/lib/permissions';
import { formatDateTime } from '@/lib/utils';
import { useMyOrganization } from '../api';

export function SettingsPage() {
  const user = useCurrentUser();
  const { logout } = useAuth();
  const org = useMyOrganization();
  const rows: [string, string][] = [
    ['Name', `${user.first_name} ${user.last_name}`],
    ['Username', user.username],
    ['Email', user.email],
    ['Last sign-in', formatDateTime(user.last_login)],
  ];
  return (
    <>
      <PageHeader title="Settings" />
      <div className="max-w-xl space-y-4">
        <Card>
          <CardContent className="space-y-3 p-4">
            <h2 className="font-medium">Your account</h2>
            <dl className="grid grid-cols-[8rem_1fr] gap-y-2 text-sm">
              {rows.map(([k, v]) => (
                <div key={k} className="contents">
                  <dt className="text-muted-foreground">{k}</dt>
                  <dd>{v}</dd>
                </div>
              ))}
              <dt className="text-muted-foreground">Role</dt>
              <dd><Badge tone="info">{user.is_superuser ? 'Platform admin' : ROLE_LABEL[user.role]}</Badge></dd>
            </dl>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="space-y-3 p-4">
            <h2 className="font-medium">Your organisation</h2>
            {org.isPending ? (
              <p className="text-sm text-muted-foreground">Loading...</p>
            ) : org.isError ? (
              <p className="text-sm text-muted-foreground">Organisation details are not available right now.</p>
            ) : (
              <dl className="grid grid-cols-[8rem_1fr] gap-y-2 text-sm">
                <dt className="text-muted-foreground">Name</dt><dd>{org.data.name}</dd>
                <dt className="text-muted-foreground">Plan</dt><dd className="capitalize">{org.data.plan}</dd>
                <dt className="text-muted-foreground">Limits</dt><dd>{org.data.max_users} users, {org.data.max_containers} containers</dd>
              </dl>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <div><h2 className="font-medium">Appearance</h2><p className="text-sm text-muted-foreground">Light or dark mode</p></div>
            <ThemeToggle />
          </CardContent>
        </Card>
        <Button variant="outline" onClick={() => void logout()}>Sign out</Button>
      </div>
    </>
  );
}
