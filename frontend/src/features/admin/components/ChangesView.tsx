function isChange(v: unknown): v is { from: unknown; to: unknown } {
  return typeof v === 'object' && v !== null && 'from' in v && 'to' in v;
}

function show(v: unknown): string {
  if (v === null || v === undefined || v === '') return '-';
  return typeof v === 'object' ? JSON.stringify(v) : String(v);
}

/** What an audit entry recorded: "field: old -> new" for edits, "field: value" for creations. */
export function ChangesView({ data }: { data: Record<string, unknown> | null }) {
  const entries = data ? Object.entries(data) : [];
  if (entries.length === 0) return <p className="text-sm text-muted-foreground">No details were recorded for this action.</p>;
  return (
    <dl className="grid grid-cols-[10rem_1fr] gap-x-4 gap-y-1 text-sm">
      {entries.map(([key, value]) => (
        <div key={key} className="contents">
          <dt className="text-muted-foreground">{key.replace(/_/g, ' ')}</dt>
          <dd className="break-words tabular-nums">
            {isChange(value) ? (
              <>
                <span className="text-muted-foreground line-through">{show(value.from)}</span>
                <span aria-hidden> &rarr; </span>
                <span className="sr-only"> changed to </span>
                <span className="font-medium">{show(value.to)}</span>
              </>
            ) : (
              show(value)
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}
