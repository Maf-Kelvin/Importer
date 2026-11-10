import type { FieldValues, Path, UseFormSetError } from 'react-hook-form';
import { ApiError, userMessage } from '@/api/errors';

/**
 * Put a failed request's validation messages next to the fields they belong to.
 * Returns a general message for anything that could not be attached to a field.
 */
export function applyApiError<T extends FieldValues>(err: unknown, setError: UseFormSetError<T>, fields: readonly string[]): string | null {
  if (err instanceof ApiError && Object.keys(err.fieldErrors).length > 0) {
    let attached = 0;
    for (const [name, message] of Object.entries(err.fieldErrors)) {
      if (fields.includes(name)) {
        setError(name as Path<T>, { type: 'server', message });
        attached += 1;
      }
    }
    if (attached === Object.keys(err.fieldErrors).length) return null;
  }
  return userMessage(err);
}
