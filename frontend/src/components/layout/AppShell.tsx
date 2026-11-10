import { BarChart3, Boxes, Building2, LayoutDashboard, LogOut, Menu, Package, ScrollText, Settings, UserCog, Users, X, type LucideIcon } from 'lucide-react';
import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import type { User } from '@/api/types';
import { useAuth, useCurrentUser } from '@/auth';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ROLE_LABEL, can, canCreateOrganizations } from '@/lib/permissions';
import { cn } from '@/lib/utils';
import { ThemeToggle } from './ThemeToggle';

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
  show?: (user: User) => boolean;
}

const MAIN: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/containers', label: 'Containers', icon: Boxes },
  { to: '/items', label: 'Items', icon: Package },
  { to: '/customers', label: 'Customers', icon: Users },
  { to: '/reports', label: 'Reports', icon: BarChart3 },
  { to: '/settings', label: 'Settings', icon: Settings },
];

/** Shown only to people who may use them (the server enforces the same rules). */
const ADMIN: NavItem[] = [
  { to: '/admin/users', label: 'Team', icon: UserCog, show: (u) => can(u, 'users.manage') },
  { to: '/admin/audit', label: 'Audit log', icon: ScrollText, show: (u) => can(u, 'audit.read') },
  { to: '/admin/organizations', label: 'Organisations', icon: Building2, show: (u) => canCreateOrganizations(u) },
];

function NavItemLink({ item }: { item: NavItem }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.end}
      className={({ isActive }) => cn('flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium', isActive ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-muted hover:text-foreground')}
    >
      <Icon className="h-4 w-4" aria-hidden />
      {item.label}
    </NavLink>
  );
}

export function AppShell() {
  const user = useCurrentUser();
  const { logout } = useAuth();
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const adminItems = ADMIN.filter((i) => !i.show || i.show(user));

  // close the mobile menu after navigating
  useEffect(() => setOpen(false), [location.pathname]);

  const sidebar = (
    <div className="flex h-full flex-col gap-4 p-4">
      <div className="px-2 text-lg font-semibold tracking-tight">Importer</div>
      <nav aria-label="Main" className="flex flex-1 flex-col gap-1 overflow-y-auto">
        {MAIN.filter((i) => !i.show || i.show(user)).map((item) => <NavItemLink key={item.to} item={item} />)}
        {adminItems.length > 0 && (
          <>
            <p className="mt-4 px-3 pb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Administration</p>
            {adminItems.map((item) => <NavItemLink key={item.to} item={item} />)}
          </>
        )}
      </nav>
      <div className="space-y-2 border-t border-border pt-3">
        <div className="px-2 text-sm">
          <p className="truncate font-medium">{user.first_name} {user.last_name}</p>
          <p className="truncate text-xs text-muted-foreground">{user.email}</p>
          <Badge tone="info" className="mt-1">{user.is_superuser ? 'Platform admin' : ROLE_LABEL[user.role]}</Badge>
        </div>
        <Button variant="ghost" size="sm" className="w-full justify-start" onClick={() => void logout()}>
          <LogOut className="h-4 w-4" aria-hidden /> Sign out
        </Button>
      </div>
    </div>
  );

  return (
    <div className="flex h-full">
      <aside className="hidden w-60 shrink-0 border-r border-border bg-card lg:block">{sidebar}</aside>

      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setOpen(false)} aria-hidden />
          <aside className="absolute left-0 top-0 h-full w-64 bg-card shadow-xl">{sidebar}</aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-border bg-card px-4">
          <Button variant="ghost" size="icon" className="lg:hidden" aria-label={open ? 'Close menu' : 'Open menu'} onClick={() => setOpen((o) => !o)}>
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
          <div className="ml-auto"><ThemeToggle /></div>
        </header>
        <main id="main" className="flex-1 overflow-y-auto p-4 sm:p-6">
          <div className="mx-auto w-full max-w-6xl"><Outlet /></div>
        </main>
      </div>
    </div>
  );
}
