import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <p className="text-sm text-muted-foreground">The page you are looking for does not exist or has moved.</p>
      <Link to="/" className="text-sm font-medium text-primary underline">Back to the dashboard</Link>
    </div>
  );
}
