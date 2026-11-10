import type { ComponentProps } from 'react';
import { cn } from '@/lib/utils';

export function Card({ className, ...rest }: ComponentProps<'div'>) {
  return <div className={cn('rounded-lg border border-border bg-card text-card-foreground shadow-sm', className)} {...rest} />;
}
export function CardHeader({ className, ...rest }: ComponentProps<'div'>) {
  return <div className={cn('flex flex-col gap-1 p-4 pb-2', className)} {...rest} />;
}
export function CardTitle({ className, ...rest }: ComponentProps<'h3'>) {
  return <h3 className={cn('text-sm font-medium text-muted-foreground', className)} {...rest} />;
}
export function CardContent({ className, ...rest }: ComponentProps<'div'>) {
  return <div className={cn('p-4 pt-2', className)} {...rest} />;
}
