import { z } from 'zod';
import type { Customer, CustomerCreate } from '@/api/types';

const emailCheck = z.string().email();

export const customerSchema = z.object({
  name: z.string().trim().min(1, 'Enter a name').max(255, 'At most 255 characters'),
  email: z.string().trim().refine((v) => v === '' || emailCheck.safeParse(v).success, 'Enter a valid email address'),
  phone: z.string().trim().max(50, 'At most 50 characters'),
  address: z.string().trim(),
  notes: z.string().trim(),
});
export type CustomerFormValues = z.infer<typeof customerSchema>;

export const customerDefaults: CustomerFormValues = { name: '', email: '', phone: '', address: '', notes: '' };

export function valuesFromCustomer(c: Customer): CustomerFormValues {
  return { name: c.name, email: c.email ?? '', phone: c.phone ?? '', address: c.address ?? '', notes: c.notes ?? '' };
}

export function toCustomerBody(v: CustomerFormValues): CustomerCreate {
  return { name: v.name, email: v.email || null, phone: v.phone || null, address: v.address || null, notes: v.notes || null };
}
