import type { ComponentProps } from 'react';
import { cn } from '@/lib/utils';

export function Table({ className, ...rest }: ComponentProps<'table'>) {
  return (
    <div className="w-full overflow-x-auto rounded-lg border border-border bg-card">
      <table className={cn('w-full text-left text-sm', className)} {...rest} />
    </div>
  );
}
export function THead(props: ComponentProps<'thead'>) {
  return <thead className="border-b border-border bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground" {...props} />;
}
export function TBody(props: ComponentProps<'tbody'>) {
  return <tbody className="divide-y divide-border" {...props} />;
}
export function Tr({ className, ...rest }: ComponentProps<'tr'>) {
  return <tr className={cn('hover:bg-muted/40', className)} {...rest} />;
}
export function Th({ className, ...rest }: ComponentProps<'th'>) {
  return <th scope="col" className={cn('whitespace-nowrap px-3 py-2 font-medium', className)} {...rest} />;
}
export function Td({ className, ...rest }: ComponentProps<'td'>) {
  return <td className={cn('px-3 py-2 align-middle', className)} {...rest} />;
}
