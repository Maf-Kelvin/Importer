import { z } from 'zod';
import type { OrganizationCreate, Role, User, UserAdminCreate, UserAdminUpdate } from '@/api/types';
import { ROLES } from '@/api/types';

const emailCheck = z.string().email();
const PASSWORD_MIN = 12;

const password = z.string().min(PASSWORD_MIN, `Use at least ${PASSWORD_MIN} characters`).max(128, 'At most 128 characters');
const username = z.string().trim().min(3, 'At least 3 characters').max(50, 'At most 50 characters').regex(/^[A-Za-z0-9_.-]+$/, 'Letters, digits, dot, dash and underscore only');
const email = z.string().trim().refine((v) => emailCheck.safeParse(v).success, 'Enter a valid email address');

// ---------- users ----------
export const newUserSchema = z.object({
  first_name: z.string().trim().min(1, 'Enter a first name').max(100),
  last_name: z.string().trim().min(1, 'Enter a last name').max(100),
  email,
  username,
  password,
  role: z.enum(ROLES),
});
export type NewUserValues = z.infer<typeof newUserSchema>;
export const newUserDefaults: NewUserValues = { first_name: '', last_name: '', email: '', username: '', password: '', role: 'viewer' };
export function toUserCreate(v: NewUserValues): UserAdminCreate {
  return { first_name: v.first_name, last_name: v.last_name, email: v.email, username: v.username, password: v.password, role: v.role as Role, is_active: true };
}

export const editUserSchema = z.object({
  first_name: z.string().trim().min(1, 'Enter a first name').max(100),
  last_name: z.string().trim().min(1, 'Enter a last name').max(100),
  email,
  username,
  role: z.enum(ROLES),
  is_active: z.boolean(),
  password: z.string().refine((v) => v === '' || (v.length >= PASSWORD_MIN && v.length <= 128), `Leave empty to keep the current password, or use at least ${PASSWORD_MIN} characters`),
});
export type EditUserValues = z.infer<typeof editUserSchema>;
export function valuesFromUser(u: User): EditUserValues {
  return { first_name: u.first_name, last_name: u.last_name, email: u.email, username: u.username, role: u.role, is_active: u.is_active, password: '' };
}
/** Only send what the form can change; an empty password means "unchanged". */
export function toUserUpdate(v: EditUserValues, original: User, isSelf: boolean): UserAdminUpdate {
  const body: UserAdminUpdate = { first_name: v.first_name, last_name: v.last_name, email: v.email, username: v.username };
  if (!isSelf) {
    if (v.role !== original.role) body.role = v.role as Role;
    if (v.is_active !== original.is_active) body.is_active = v.is_active;
  }
  if (v.password) body.password = v.password;
  return body;
}

// ---------- organisations ----------
export const organizationSchema = z.object({
  name: z.string().trim().min(2, 'At least 2 characters').max(255),
  slug: z.string().trim().regex(/^[a-z0-9][a-z0-9-]{1,98}[a-z0-9]$/, 'Lowercase letters, digits and hyphens, at least 3 characters'),
  admin_first_name: z.string().trim().min(1, 'Enter a first name').max(100),
  admin_last_name: z.string().trim().min(1, 'Enter a last name').max(100),
  admin_email: email,
  admin_username: username,
  admin_password: password,
});
export type OrganizationValues = z.infer<typeof organizationSchema>;
export const organizationDefaults: OrganizationValues = { name: '', slug: '', admin_first_name: '', admin_last_name: '', admin_email: '', admin_username: '', admin_password: '' };
export const toOrganizationCreate = (v: OrganizationValues): OrganizationCreate => ({ ...v });

/** "Acme Imports Ltd" -> "acme-imports-ltd" */
export function slugify(name: string): string {
  return name.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 100);
}
