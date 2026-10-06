/**
 * Tooltip atom — hover tooltip using native CSS.
 */

import { cn } from '@/lib/utils';
import { useState, type ReactNode } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

interface TooltipProps {
  children: ReactNode;
  content: string;
  side?: 'top' | 'bottom' | 'left' | 'right';
  className?: string;
}

const positionStyles = {
  top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
  bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
  left: 'right-full top-1/2 -translate-y-1/2 mr-2',
  right: 'left-full top-1/2 -translate-y-1/2 ml-2',
};

export function Tooltip({ children, content, side = 'top', className }: TooltipProps) {
  const [show, setShow] = useState(false);

  return (
    <div
      className={cn('relative inline-flex', className)}
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      <AnimatePresence>
        {show && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className={cn(
              'absolute z-50 pointer-events-none',
              'px-2.5 py-1.5 rounded-lg',
              'bg-slate-800 border border-slate-700',
              'text-xs font-medium text-slate-200 whitespace-nowrap',
              'shadow-xl shadow-black/20',
              positionStyles[side]
            )}
            role="tooltip"
          >
            {content}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
