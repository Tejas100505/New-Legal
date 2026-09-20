/**
 * Toggle atom — for theme and settings switches.
 */

import { cn } from '@/lib/utils';

interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
  size?: 'sm' | 'md';
  id?: string;
}

export function Toggle({ checked, onChange, label, description, disabled, size = 'md', id }: ToggleProps) {
  const toggleId = id || label?.toLowerCase().replace(/\s+/g, '-') || 'toggle';

  return (
    <label
      htmlFor={toggleId}
      className={cn(
        'flex items-center gap-3 cursor-pointer select-none',
        disabled && 'opacity-50 cursor-not-allowed'
      )}
    >
      <button
        id={toggleId}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={cn(
          'relative inline-flex shrink-0 rounded-full transition-colors duration-200 ease-in-out',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950',
          checked ? 'bg-indigo-500' : 'bg-slate-700',
          size === 'sm' ? 'h-5 w-9' : 'h-6 w-11'
        )}
      >
        <span
          className={cn(
            'pointer-events-none inline-block rounded-full bg-white shadow-lg transform transition-transform duration-200 ease-in-out',
            size === 'sm' ? 'h-4 w-4 mt-0.5 ml-0.5' : 'h-5 w-5 mt-0.5 ml-0.5',
            checked && (size === 'sm' ? 'translate-x-4' : 'translate-x-5')
          )}
        />
      </button>
      {(label || description) && (
        <div>
          {label && <span className="text-sm font-medium text-slate-200 dark:text-slate-200">{label}</span>}
          {description && <p className="text-xs text-slate-500">{description}</p>}
        </div>
      )}
    </label>
  );
}
