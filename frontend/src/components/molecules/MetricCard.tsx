/**
 * MetricCard molecule — dashboard stat card with icon, value, and trend.
 */

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import {
  FolderOpen, Clock, FileText, Eye, Brain, Search,
  AlertTriangle, Layers, CheckCircle, TrendingUp, TrendingDown, Minus,
} from 'lucide-react';
import type { MetricCardData } from '@/types';

const iconMap: Record<string, React.ElementType> = {
  FolderOpen, Clock, FileText, Eye, Brain, Search,
  AlertTriangle, Layers, CheckCircle,
};

const colorMap: Record<string, { bg: string; icon: string; glow: string }> = {
  indigo:  { bg: 'bg-indigo-500/10', icon: 'text-indigo-400', glow: 'shadow-indigo-500/5' },
  violet:  { bg: 'bg-violet-500/10', icon: 'text-violet-400', glow: 'shadow-violet-500/5' },
  cyan:    { bg: 'bg-cyan-500/10',   icon: 'text-cyan-400',   glow: 'shadow-cyan-500/5' },
  emerald: { bg: 'bg-emerald-500/10',icon: 'text-emerald-400',glow: 'shadow-emerald-500/5' },
  blue:    { bg: 'bg-blue-500/10',   icon: 'text-blue-400',   glow: 'shadow-blue-500/5' },
  orange:  { bg: 'bg-orange-500/10', icon: 'text-orange-400', glow: 'shadow-orange-500/5' },
  rose:    { bg: 'bg-rose-500/10',   icon: 'text-rose-400',   glow: 'shadow-rose-500/5' },
  amber:   { bg: 'bg-amber-500/10',  icon: 'text-amber-400',  glow: 'shadow-amber-500/5' },
  teal:    { bg: 'bg-teal-500/10',   icon: 'text-teal-400',   glow: 'shadow-teal-500/5' },
};

interface MetricCardProps {
  metric: MetricCardData;
  index?: number;
}

export function MetricCard({ metric, index = 0 }: MetricCardProps) {
  const Icon = iconMap[metric.icon] || FileText;
  const colors = colorMap[metric.color] || colorMap.indigo;

  const TrendIcon = metric.trend === 'up' ? TrendingUp : metric.trend === 'down' ? TrendingDown : Minus;
  const trendColor = metric.trend === 'up' ? 'text-emerald-400' : metric.trend === 'down' ? 'text-rose-400' : 'text-slate-500';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.4 }}
      className={cn(
        'rounded-xl p-5',
        'bg-slate-900/50 dark:bg-slate-900/50 backdrop-blur-xl',
        'border border-slate-800/50 dark:border-slate-800/50',
        'hover:border-indigo-500/20 hover:shadow-xl',
        'transition-all duration-300 hover:-translate-y-0.5',
        colors.glow
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
          {metric.label}
        </span>
        <div className={cn('h-9 w-9 rounded-lg flex items-center justify-center', colors.bg)}>
          <Icon className={cn('h-4.5 w-4.5', colors.icon)} />
        </div>
      </div>
      <div className="mb-1">
        <span className="text-2xl font-bold text-slate-100 dark:text-slate-100 tracking-tight">
          {metric.value}
        </span>
      </div>
      <div className="flex items-center gap-1.5">
        <TrendIcon className={cn('h-3.5 w-3.5', trendColor)} />
        <span className={cn('text-xs font-medium', trendColor)}>
          {metric.changeLabel}
        </span>
      </div>
    </motion.div>
  );
}
