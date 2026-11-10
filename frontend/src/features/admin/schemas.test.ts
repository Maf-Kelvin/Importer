import { describe, expect, it } from 'vitest';
import { editUserSchema, newUserSchema, organizationSchema, slugify, toUserUpdate, valuesFromUser } from './schemas';
import type { User } from '@/api/types';

const user: User = {
  id: 1, email: 'a@b.com', username: 'ann', first_name: 'Ann', last_name: 'Lee', is_active: true, role: 'clerk',
  is_superuser: false, tenant_id: 1, last_login: null, created_at: '', updated_at: '',
};

describe('slugify', () => {
  it('makes a valid organisation slug from a name', () => {
    expect(slugify('Acme Imports Ltd.')).toBe('acme-imports-ltd');
    expect(slugify('  --Hello,   World!-- ')).toBe('hello-world');
  });
});

describe('passwords', () => {
  const base = { first_name: 'A', last_name: 'B', email: 'a@b.com', username: 'abc', role: 'viewer' as const };
  it('are at least 12 characters for a new user', () => {
    expect(newUserSchema.safeParse({ ...base, password: 'short' }).success).toBe(false);
    expect(newUserSchema.safeParse({ ...base, password: 'long-enough-password' }).success).toBe(true);
  });
  it('may be left empty when editing, otherwise must be 12+', () => {
    const v = { ...valuesFromUser(user) };
    expect(editUserSchema.safeParse({ ...v, password: '' }).success).toBe(true);
    expect(editUserSchema.safeParse({ ...v, password: 'tooshort' }).success).toBe(false);
  });
});

describe('toUserUpdate', () => {
  it('sends only role/status changes, never for yourself, and omits an empty password', () => {
    const v = { ...valuesFromUser(user), role: 'manager' as const, is_active: false };
    const other = toUserUpdate(v, user, false);
    expect(other.role).toBe('manager');
    expect(other.is_active).toBe(false);
    expect(other.password).toBeUndefined();
    const self = toUserUpdate(v, user, true);
    expect(self.role).toBeUndefined();
    expect(self.is_active).toBeUndefined();
  });
});

describe('organisation form', () => {
  it('requires a valid slug and a 12+ character admin password', () => {
    const ok = { name: 'Acme', slug: 'acme', admin_first_name: 'A', admin_last_name: 'B', admin_email: 'a@b.com', admin_username: 'acme_admin', admin_password: 'long-enough-password' };
    expect(organizationSchema.safeParse(ok).success).toBe(true);
    expect(organizationSchema.safeParse({ ...ok, slug: 'Bad Slug' }).success).toBe(false);
    expect(organizationSchema.safeParse({ ...ok, admin_password: 'short' }).success).toBe(false);
  });
});
