/**
 * ProgressBar atom — animated progress indicator.
 */

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface ProgressBarProps {
  value: number; // 0-100
  max?: number;
  size?: 'xs' | 'sm' | 'md';
  variant?: 'default' | 'success' | 'warning' | 'danger';
  showLabel?: boolean;
  animated?: boolean;
  className?: string;
}

const sizeStyles = {
  xs: 'h-1',
  sm: 'h-1.5',
  md: 'h-2',
};

const variantStyles = {
  default: 'from-indigo-500 to-violet-500',
  success: 'from-emerald-500 to-teal-500',
  warning: 'from-amber-500 to-orange-500',
  danger: 'from-red-500 to-rose-500',
};

export function ProgressBar({
  value,
  max = 100,
  size = 'sm',
  variant = 'default',
  showLabel = false,
  animated = true,
  className,
}: ProgressBarProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div className={cn('w-full', className)}>
      {showLabel && (
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-slate-500">{Math.round(percentage)}%</span>
        </div>
      )}
      <div
        className={cn(
          'w-full rounded-full overflow-hidden',
          'bg-slate-800/60',
          sizeStyles[size]
        )}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
      >
        {animated ? (
          <motion.div
            className={cn('h-full rounded-full bg-gradient-to-r', variantStyles[variant])}
            initial={{ width: 0 }}
            animate={{ width: `${percentage}%` }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
          />
        ) : (
          <div
            className={cn('h-full rounded-full bg-gradient-to-r transition-all duration-300', variantStyles[variant])}
            style={{ width: `${percentage}%` }}
          />
        )}
      </div>
    </div>
  );
}
