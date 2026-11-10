import { useState } from 'react';
import { userMessage } from '@/api/errors';
import { Button } from '@/components/ui/button';
import { Dialog } from '@/components/ui/dialog';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel: string;
  destructive?: boolean;
  onConfirm: () => Promise<unknown>;
}

export function ConfirmDialog({ open, onOpenChange, title, description, confirmLabel, destructive, onConfirm }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      await onConfirm();
      onOpenChange(false);
    } catch (e) {
      setError(userMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!busy) { setError(null); onOpenChange(o); } }} title={title} description={description}>
      {error && <p role="alert" className="mb-3 rounded-md bg-destructive/10 p-2 text-sm text-destructive">{error}</p>}
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>Cancel</Button>
        <Button variant={destructive ? 'destructive' : 'default'} onClick={run} loading={busy}>{confirmLabel}</Button>
      </div>
    </Dialog>
  );
}
