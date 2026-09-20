/**
 * Logo atom — brand mark for the platform.
 */

import { Scale } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LogoProps {
  collapsed?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeConfig = {
  sm: { container: 'h-7 w-7', icon: 'h-4 w-4', title: 'text-xs', subtitle: 'text-[9px]' },
  md: { container: 'h-9 w-9', icon: 'h-5 w-5', title: 'text-sm', subtitle: 'text-[10px]' },
  lg: { container: 'h-11 w-11', icon: 'h-6 w-6', title: 'text-base', subtitle: 'text-[11px]' },
};

export function Logo({ collapsed = false, size = 'md', className }: LogoProps) {
  const cfg = sizeConfig[size];

  return (
    <div className={cn('flex items-center gap-3', className)}>
      <div
        className={cn(
          'shrink-0 flex items-center justify-center rounded-xl',
          'bg-gradient-to-br from-indigo-500 to-violet-600',
          'shadow-lg shadow-indigo-500/20',
          cfg.container
        )}
      >
        <Scale className={cn('text-white', cfg.icon)} />
      </div>
      {!collapsed && (
        <div className="overflow-hidden">
          <h1 className={cn('font-bold text-slate-100 dark:text-slate-100 tracking-tight truncate', cfg.title)}>
            E-Discovery AI
          </h1>
          <p className={cn('font-medium text-indigo-400/80 tracking-wider uppercase', cfg.subtitle)}>
            Legal Intelligence
          </p>
        </div>
      )}
    </div>
  );
}
