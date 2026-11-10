import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Pagination } from './Pagination';

describe('Pagination', () => {
  it('shows the range and moves to the next page', async () => {
    const onPage = vi.fn();
    render(<Pagination page={2} pages={3} total={45} onPage={onPage} />);
    expect(screen.getByText(/45 results/)).toBeInTheDocument();
    expect(screen.getByText(/page 2 of 3/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Next page' }));
    expect(onPage).toHaveBeenCalledWith(3);
  });

  it('disables Previous on the first page and Next on the last', () => {
    const { rerender } = render(<Pagination page={1} pages={2} total={30} onPage={() => undefined} />);
    expect(screen.getByRole('button', { name: 'Previous page' })).toBeDisabled();
    rerender(<Pagination page={2} pages={2} total={30} onPage={() => undefined} />);
    expect(screen.getByRole('button', { name: 'Next page' })).toBeDisabled();
  });

  it('renders nothing when there are no results', () => {
    const { container } = render(<Pagination page={1} pages={1} total={0} onPage={() => undefined} />);
    expect(container).toBeEmptyDOMElement();
  });
});
