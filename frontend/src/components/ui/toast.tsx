import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

type Variant = 'success' | 'error' | 'info';
interface ToastInput {
  title: string;
  description?: string;
  variant?: Variant;
}
interface ToastItem extends ToastInput {
  id: number;
}

const ToastContext = createContext<((t: ToastInput) => void) | null>(null);
let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const push = useCallback((t: ToastInput) => {
    const id = nextId++;
    setItems((cur) => [...cur, { ...t, id }]);
    window.setTimeout(() => setItems((cur) => cur.filter((x) => x.id !== id)), 5000);
  }, []);

  const color: Record<Variant, string> = {
    success: 'border-success',
    error: 'border-destructive',
    info: 'border-primary',
  };

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-4 z-[100] flex flex-col items-center gap-2 px-4 sm:items-end sm:px-6" role="status" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={cn('pointer-events-auto w-full max-w-sm rounded-md border-l-4 bg-card p-3 text-sm shadow-lg ring-1 ring-border', color[t.variant ?? 'info'])}>
            <p className="font-medium">{t.title}</p>
            {t.description && <p className="mt-0.5 text-muted-foreground">{t.description}</p>}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): (t: ToastInput) => void {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>');
  return ctx;
}