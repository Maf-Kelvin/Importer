import { z } from 'zod';
import type { Container, ContainerCreate } from '@/api/types';
import { ALLOCATION_METHODS, CONTAINER_TYPES } from '@/api/types';

export const containerSchema = z.object({
  name: z.string().trim().min(1, 'Enter a name').max(255, 'At most 255 characters'),
  container_type: z.enum(CONTAINER_TYPES),
  msc_container_number: z.string().trim().max(50, 'At most 50 characters'),
  allocation_method: z.enum(ALLOCATION_METHODS),
  notes: z.string().trim(),
});
export type ContainerFormValues = z.infer<typeof containerSchema>;

export const containerDefaults: ContainerFormValues = {
  name: '',
  container_type: '40ft',
  msc_container_number: '',
  allocation_method: 'weight_based',
  notes: '',
};

export function valuesFromContainer(c: Container): ContainerFormValues {
  return {
    name: c.name,
    container_type: c.container_type,
    msc_container_number: c.msc_container_number ?? '',
    allocation_method: c.allocation_method,
    notes: c.notes ?? '',
  };
}

export function toCreateBody(v: ContainerFormValues): ContainerCreate {
  return {
    name: v.name,
    container_type: v.container_type,
    allocation_method: v.allocation_method,
    msc_container_number: v.msc_container_number || null,
    notes: v.notes || null,
  };
}
