import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { FormField } from './FormField';

describe('FormField', () => {
  it('connects the label to the control', () => {
    render(<FormField label="Email"><input /></FormField>);
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
  });

  it('announces an error and marks the control invalid', () => {
    render(<FormField label="Email" error="Enter a valid email"><input /></FormField>);
    const input = screen.getByLabelText('Email');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByRole('alert')).toHaveTextContent('Enter a valid email');
    expect(input).toHaveAccessibleDescription('Enter a valid email');
  });

  it('shows a hint when there is no error', () => {
    render(<FormField label="Weight" hint="In kilograms"><input /></FormField>);
    expect(screen.getByLabelText('Weight')).toHaveAccessibleDescription('In kilograms');
  });
});
