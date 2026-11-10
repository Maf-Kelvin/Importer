import { Moon, Sun } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { getTheme, setTheme, type Theme } from '@/lib/theme';

export function ThemeToggle() {
  const [theme, setLocal] = useState<Theme>(getTheme);
  const next: Theme = theme === 'dark' ? 'light' : 'dark';
  return (
    <Button variant="ghost" size="icon" aria-label={`Switch to ${next} mode`} onClick={() => { setTheme(next); setLocal(next); }}>
      {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  );
}
