import type { ComponentProps } from 'react';
import { cn } from '@/lib/utils';

const field = 'w-full rounded-md border border-input bg-card px-3 text-sm placeholder:text-muted-foreground disabled:opacity-50 aria-[invalid=true]:border-destructive';

export function Input({ className, ...rest }: ComponentProps<'input'>) {
  return <input className={cn(field, 'h-10', className)} {...rest} />;
}
export function Textarea({ className, ...rest }: ComponentProps<'textarea'>) {
  return <textarea className={cn(field, 'min-h-20 py-2', className)} {...rest} />;
}
export function Select({ className, children, ...rest }: ComponentProps<'select'>) {
  return (
    <select className={cn(field, 'h-10 pr-8', className)} {...rest}>
      {children}
    </select>
  );
}
