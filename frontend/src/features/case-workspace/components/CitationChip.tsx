import { cn } from '@/lib/utils';

interface CitationChipProps {
  label: string;
  onClick?: () => void;
  className?: string;
}

export function CitationChip({ label, onClick, className }: CitationChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`Jump to citation ${label}`}
      className={cn(
        'inline-flex items-center justify-center font-mono text-[11px] font-semibold tracking-tight',
        'text-indigo-300 hover:text-indigo-100 bg-indigo-500/15 hover:bg-indigo-500/30',
        'border border-indigo-500/30 hover:border-indigo-400/50',
        'px-1.5 py-0.5 rounded cursor-pointer transition-all duration-150 active:scale-95 mx-0.5 select-none align-baseline',
        className
      )}
    >
      {label}
    </button>
  );
}
