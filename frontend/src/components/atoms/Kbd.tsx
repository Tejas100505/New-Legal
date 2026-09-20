/**
 * Kbd atom — keyboard shortcut display.
 */

import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

interface KbdProps {
  children: ReactNode;
  className?: string;
}

export function Kbd({ children, className }: KbdProps) {
  return (
    <kbd
      className={cn(
        'inline-flex items-center justify-center',
        'px-1.5 py-0.5 rounded',
        'bg-slate-800 dark:bg-slate-800 border border-slate-700 dark:border-slate-700',
        'text-[10px] font-mono font-medium text-slate-500 dark:text-slate-500',
        'select-none',
        className
      )}
    >
      {children}
    </kbd>
  );
}
