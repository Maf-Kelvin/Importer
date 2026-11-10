import { describe, expect, it } from 'vitest';
import { ACTIONS, can, canCreateOrganizations, canViewOrganisationAnalytics, type Action, type Role } from './permissions';

const roles: Role[] = ['viewer', 'clerk', 'manager', 'admin'];

describe('organisation-wide analytics', () => {
  it('are hidden from clerks and anonymous users, visible to everyone else', () => {
    expect(canViewOrganisationAnalytics(null)).toBe(false);
    expect(canViewOrganisationAnalytics({ role: 'clerk' })).toBe(false);
    expect(canViewOrganisationAnalytics({ role: 'viewer' })).toBe(true);
    expect(canViewOrganisationAnalytics({ role: 'manager' })).toBe(true);
    expect(canViewOrganisationAnalytics({ role: 'clerk', is_superuser: true })).toBe(true);
  });
});

describe('can', () => {
  it('denies everything when nobody is signed in', () => {
    expect(can(null, 'container.create')).toBe(false);
    expect(can(undefined, 'users.manage')).toBe(false);
  });
  it('gives viewers read-only access', () => {
    for (const action of Object.keys(ACTIONS) as Action[]) expect(can({ role: 'viewer' }, action)).toBe(false);
  });
  it('matches the API reference for each role', () => {
    expect(can({ role: 'clerk' }, 'container.create')).toBe(true);
    expect(can({ role: 'clerk' }, 'container.delete')).toBe(false);
    expect(can({ role: 'manager' }, 'container.delete')).toBe(true);
    expect(can({ role: 'manager' }, 'users.manage')).toBe(false);
    expect(can({ role: 'admin' }, 'audit.read')).toBe(true);
    expect(can({ role: 'manager' }, 'report.containers')).toBe(true);
    expect(can({ role: 'viewer' }, 'pricing.generate')).toBe(false);
    expect(can({ role: 'clerk' }, 'pricing.generate')).toBe(true);
    expect(can({ role: 'clerk' }, 'report.containers')).toBe(false);
  });
  it('never lets a lower role do more than a higher one', () => {
    for (const action of Object.keys(ACTIONS) as Action[]) {
      const allowed = roles.map((role) => can({ role }, action));
      for (let i = 1; i < allowed.length; i++) if (allowed[i - 1]) expect(allowed[i]).toBe(true);
    }
  });
  it('treats a platform administrator as allowed everywhere', () => {
    expect(can({ role: 'viewer', is_superuser: true }, 'audit.read')).toBe(true);
    expect(canCreateOrganizations({ role: 'admin' })).toBe(false);
    expect(canCreateOrganizations({ role: 'viewer', is_superuser: true })).toBe(true);
  });
});
