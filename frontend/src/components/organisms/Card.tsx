import { type HTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/utils';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'glass' | 'solid' | 'outlined';
  hover?: boolean;
  glow?: boolean;
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'glass', hover = true, glow = false, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'rounded-xl p-5 transition-all duration-300',
        variant === 'glass' && [
          'bg-slate-900/50 backdrop-blur-xl',
          'border border-slate-800/50',
          'shadow-lg shadow-black/20',
        ],
        variant === 'solid' && [
          'bg-slate-900',
          'border border-slate-800',
        ],
        variant === 'outlined' && [
          'bg-transparent',
          'border border-slate-700',
        ],
        hover && [
          'hover:border-indigo-500/20',
          'hover:shadow-xl hover:shadow-indigo-500/5',
          'hover:-translate-y-0.5',
        ],
        glow && 'shadow-lg shadow-indigo-500/10',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
);

Card.displayName = 'Card';

const CardHeader = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex items-center justify-between mb-4', className)} {...props} />
  )
);
CardHeader.displayName = 'CardHeader';

const CardTitle = forwardRef<HTMLHeadingElement, HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn('text-lg font-semibold text-slate-100', className)} {...props} />
  )
);
CardTitle.displayName = 'CardTitle';

const CardContent = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('text-slate-300', className)} {...props} />
  )
);
CardContent.displayName = 'CardContent';

export { Card, CardHeader, CardTitle, CardContent };
