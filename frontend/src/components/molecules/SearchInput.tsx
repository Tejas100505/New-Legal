/**
 * SearchInput molecule — search field with icon.
 */

import { forwardRef, type InputHTMLAttributes } from 'react';
import { Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Kbd } from '@/components/atoms/Kbd';

interface SearchInputProps extends InputHTMLAttributes<HTMLInputElement> {
  shortcut?: string;
  onShortcutClick?: () => void;
}

export const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(
  ({ className, shortcut, onShortcutClick, ...props }, ref) => {
    return (
      <div
        className={cn(
          'flex items-center gap-2 px-3 py-2 rounded-lg',
          'bg-slate-900/80 dark:bg-slate-900/80 border border-slate-800 dark:border-slate-800',
          'text-slate-400 text-sm',
          'focus-within:ring-2 focus-within:ring-indigo-500/30 focus-within:border-indigo-500/30',
          'transition-all duration-200',
          'cursor-text',
          className
        )}
        onClick={onShortcutClick}
        role={onShortcutClick ? 'button' : undefined}
        tabIndex={onShortcutClick ? 0 : undefined}
      >
        <Search className="h-4 w-4 shrink-0" />
        <input
          ref={ref}
          className={cn(
            'flex-1 bg-transparent border-none outline-none text-sm',
            'text-slate-200 dark:text-slate-200 placeholder:text-slate-600 dark:placeholder:text-slate-600',
          )}
          {...props}
        />
        {shortcut && <Kbd>{shortcut}</Kbd>}
      </div>
    );
  }
);

SearchInput.displayName = 'SearchInput';
