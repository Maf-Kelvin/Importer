/**
 * Role rules, copied from the API reference (docs/API.md). The UI uses them to hide actions a user
 * cannot perform; the SERVER still enforces every one of them, so this is convenience, not security.
 */
export type Role = 'viewer' | 'clerk' | 'manager' | 'admin';

const RANK: Record<Role, number> = { viewer: 0, clerk: 1, manager: 2, admin: 3 };

export const ACTIONS = {
  'container.create': 'clerk',
  'container.update': 'clerk',
  'container.seal': 'clerk',
  'container.allocate': 'clerk',
  'container.delete': 'manager',
  'item.write': 'clerk', // create, update, delete, mark sold
  'expense.write': 'clerk',
  'customer.write': 'clerk',
  'customer.delete': 'manager',
  'pricing.generate': 'clerk', // saves the recommended price on the item and can start scraping
  'pricing.record': 'clerk',
  'pricing.accuracy': 'manager',
  'tracking.update': 'clerk',
  'report.containers': 'manager',
  'users.manage': 'admin',
  'audit.read': 'admin',
} as const satisfies Record<string, Role>;

export type Action = keyof typeof ACTIONS;

export interface Actor {
  role: Role;
  is_superuser?: boolean;
}

export function can(user: Actor | null | undefined, action: Action): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  return RANK[user.role] >= RANK[ACTIONS[action]];
}

export function canCreateOrganizations(user: Actor | null | undefined): boolean {
  return Boolean(user?.is_superuser);
}

/** Organisation-wide analytics (demand) are refused to clerks: they only ever see their own containers. */
export function canViewOrganisationAnalytics(user: Actor | null | undefined): boolean {
  if (!user) return false;
  return user.is_superuser === true || user.role !== 'clerk';
}

export const ROLE_LABEL: Record<Role, string> = {
  viewer: 'Viewer',
  clerk: 'Clerk',
  manager: 'Manager',
  admin: 'Admin',
};
