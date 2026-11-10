import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Props {
  page: number;
  pages: number;
  total: number;
  onPage: (page: number) => void;
}

export function Pagination({ page, pages, total, onPage }: Props) {
  if (total === 0) return null;
  return (
    <nav className="mt-3 flex items-center justify-between text-sm text-muted-foreground" aria-label="Pagination">
      <span>
        {total} {total === 1 ? 'result' : 'results'}
        {pages > 1 && ` - page ${page} of ${pages}`}
      </span>
      {pages > 1 && (
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)} aria-label="Previous page">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => onPage(page + 1)} aria-label="Next page">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </nav>
  );
}
