import { cn } from '@/lib/utils';

export type StatusType = 'healthy' | 'degraded' | 'unhealthy' | 'up' | 'down' | 'pending' | 'active' | 'error' | 'success' | 'warning';

interface StatusBadgeProps {
  status: StatusType;
  label?: string;
  pulse?: boolean;
  size?: 'sm' | 'md';
}

const statusConfig: Record<StatusType, { bg: string; text: string; dot: string }> = {
  healthy:   { bg: 'bg-emerald-500/10', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  up:        { bg: 'bg-emerald-500/10', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  success:   { bg: 'bg-emerald-500/10', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  active:    { bg: 'bg-blue-500/10',    text: 'text-blue-400',    dot: 'bg-blue-400' },
  degraded:  { bg: 'bg-amber-500/10',   text: 'text-amber-400',   dot: 'bg-amber-400' },
  warning:   { bg: 'bg-amber-500/10',   text: 'text-amber-400',   dot: 'bg-amber-400' },
  pending:   { bg: 'bg-slate-500/10',   text: 'text-slate-400',   dot: 'bg-slate-400' },
  unhealthy: { bg: 'bg-red-500/10',     text: 'text-red-400',     dot: 'bg-red-400' },
  down:      { bg: 'bg-red-500/10',     text: 'text-red-400',     dot: 'bg-red-400' },
  error:     { bg: 'bg-red-500/10',     text: 'text-red-400',     dot: 'bg-red-400' },
};

export function StatusBadge({ status, label, pulse = true, size = 'md' }: StatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.pending;
  const displayLabel = label || status.charAt(0).toUpperCase() + status.slice(1);

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-medium',
        config.bg,
        config.text,
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs',
      )}
    >
      <span className="relative flex h-2 w-2">
        {pulse && (
          <span
            className={cn(
              'absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping',
              config.dot,
            )}
          />
        )}
        <span
          className={cn('relative inline-flex h-2 w-2 rounded-full', config.dot)}
        />
      </span>
      {displayLabel}
    </span>
  );
}
