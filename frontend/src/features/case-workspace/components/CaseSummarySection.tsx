import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';

interface CaseSummarySectionProps {
  title: string;
  icon: React.ReactNode;
  badge?: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
  className?: string;
  id?: string;
}

export function CaseSummarySection({
  title,
  icon,
  badge,
  defaultOpen = true,
  children,
  className,
  id,
}: CaseSummarySectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div
      id={id}
      className={cn(
        'rounded-xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm overflow-hidden transition-all',
        className
      )}
    >
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 bg-slate-900/60 hover:bg-slate-800/40 transition-colors text-left"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className="h-8 w-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
            {icon}
          </div>
          <div className="flex items-center gap-2.5 flex-wrap min-w-0">
            <h3 className="text-sm font-semibold text-slate-100 tracking-tight">{title}</h3>
            {badge}
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-400 pl-2">
          <span className="text-[11px] uppercase tracking-wider font-mono text-slate-500 hidden sm:inline">
            {isOpen ? 'Collapse' : 'Expand'}
          </span>
          {isOpen ? (
            <ChevronUp className="h-4 w-4 text-slate-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-slate-400" />
          )}
        </div>
      </button>

      {isOpen && (
        <div className="p-5 border-t border-slate-800/50 space-y-4 text-slate-300 text-sm leading-relaxed">
          {children}
        </div>
      )}
    </div>
  );
}
