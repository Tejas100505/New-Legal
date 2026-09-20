/**
 * AnalyticsGrid — dashboard analytics with 11 metric widgets.
 * Each metric includes value, trend, sparkline, and threshold indicators.
 */

import { motion } from 'framer-motion';
import {
  Eye, Brain, FileText, Timer, Clock, Search,
  FolderOpen, Database, ShieldAlert, HardDrive, Activity,
  TrendingUp, TrendingDown, Minus,
} from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import { cn } from '@/lib/utils';
import { useAnalyticsStore } from '@/stores/analyticsStore';
import { Skeleton } from '@/components/atoms/Skeleton';
import type { AnalyticsMetric, DashboardAnalytics } from '@/types';

// ── Metric Config ───────────────────────────────────────────────────────────

interface MetricConfig {
  key: keyof DashboardAnalytics;
  icon: React.ElementType;
  color: string;
  format: (v: number, u: string) => string;
  invertTrend?: boolean; // Lower is better (e.g. hallucination rate)
}

const METRIC_CONFIGS: MetricConfig[] = [
  { key: 'ocrAccuracy', icon: Eye, color: '#6366f1', format: (v, u) => `${v.toFixed(1)}${u}` },
  { key: 'aiConfidence', icon: Brain, color: '#8b5cf6', format: (v, u) => `${v.toFixed(1)}${u}` },
  { key: 'documentsProcessed', icon: FileText, color: '#06b6d4', format: (v) => v.toLocaleString() },
  { key: 'agentRuntime', icon: Timer, color: '#10b981', format: (v, u) => `${v.toFixed(1)} ${u}` },
  { key: 'processingTime', icon: Clock, color: '#f59e0b', format: (v, u) => `${v.toFixed(1)} ${u}`, invertTrend: true },
  { key: 'evidenceCount', icon: Search, color: '#3b82f6', format: (v) => v.toLocaleString() },
  { key: 'similarCases', icon: FolderOpen, color: '#a855f7', format: (v) => `${v}` },
  { key: 'retrievalQuality', icon: Database, color: '#14b8a6', format: (v, u) => `${v.toFixed(1)}${u}` },
  { key: 'hallucinationRate', icon: ShieldAlert, color: '#ef4444', format: (v, u) => `${v.toFixed(1)}${u}`, invertTrend: true },
  { key: 'storageUsage', icon: HardDrive, color: '#f97316', format: (v, u) => `${v.toFixed(1)} ${u}` },
  { key: 'apiUsage', icon: Activity, color: '#84cc16', format: (v) => v.toLocaleString() },
];

// ── Component ───────────────────────────────────────────────────────────────

interface AnalyticsGridProps {
  isLoading?: boolean;
}

export function AnalyticsGrid({ isLoading = false }: AnalyticsGridProps) {
  const analytics = useAnalyticsStore((s) => s.analytics);
  const error = useAnalyticsStore((s) => s.error);

  if (error) {
    return (
      <div className="rounded-xl p-8 bg-slate-900/50 border border-red-500/20 text-center">
        <ShieldAlert className="h-8 w-8 text-red-400 mx-auto mb-2" />
        <p className="text-sm text-red-400">Failed to load analytics</p>
        <p className="text-xs text-slate-500 mt-1">{error}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <Activity className="h-5 w-5 text-cyan-400" />
        <h2 className="text-lg font-semibold text-slate-100">Dashboard Analytics</h2>
      </div>

      <div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3"
        role="list"
        aria-label="Analytics metrics"
      >
        {METRIC_CONFIGS.map((config, i) => {
          const metric = analytics[config.key];
          return (
            <div key={config.key} role="listitem">
              {isLoading ? (
                <AnalyticsSkeleton />
              ) : (
                <AnalyticsCard config={config} metric={metric} index={i} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Analytics Card ──────────────────────────────────────────────────────────

function AnalyticsCard({
  config,
  metric,
  index,
}: {
  config: MetricConfig;
  metric: AnalyticsMetric;
  index: number;
}) {
  const Icon = config.icon;
  const isPositive = config.invertTrend
    ? metric.trend < 0
    : metric.trend > 0;
  const isNeutral = metric.trend === 0;
  const TrendIcon = isNeutral ? Minus : isPositive ? TrendingUp : TrendingDown;
  const trendColor = isNeutral
    ? 'text-slate-500'
    : isPositive
    ? 'text-emerald-400'
    : 'text-red-400';

  const sparklineData = metric.sparkline.map((v, i) => ({ v, i }));

  // Threshold indicator
  const hasThreshold = metric.threshold !== undefined && metric.value !== null;
  const isAboveThreshold = hasThreshold && (metric.value as number) >= metric.threshold!;
  const thresholdStatus = config.invertTrend
    ? ((metric.value as number) <= metric.threshold! ? 'good' : 'bad')
    : (isAboveThreshold ? 'good' : 'bad');

  // Storage bar (for metrics with max)
  const hasMax = metric.max !== undefined && metric.value !== null;
  const usagePercent = hasMax ? ((metric.value as number) / metric.max!) * 100 : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.3 }}
      className={cn(
        'rounded-xl p-4',
        'bg-slate-900/50 backdrop-blur-xl',
        'border border-slate-800/50',
        'hover:border-slate-700/50 transition-all duration-300',
      )}
      role="article"
      aria-label={`${metric.label}: ${metric.value !== null ? config.format(metric.value, metric.unit) : 'N/A'}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">
          {metric.label}
        </span>
        <div
          className="h-7 w-7 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: `${config.color}15` }}
        >
          <Icon className="h-3.5 w-3.5" style={{ color: config.color }} />
        </div>
      </div>

      {/* Value */}
      <div className="mb-1">
        <span className="text-xl font-bold text-slate-100 tracking-tight">
          {metric.value !== null ? config.format(metric.value, metric.unit) : 'N/A'}
        </span>
      </div>

      {/* Trend */}
      {metric.value !== null ? (
        <div className="flex items-center gap-1.5 mb-2">
          <TrendIcon className={cn('h-3 w-3', trendColor)} />
          <span className={cn('text-[10px] font-medium', trendColor)}>
            {metric.trend > 0 ? '+' : ''}{metric.trend}{metric.unit === '%' ? '%' : ''} from last period
          </span>
        </div>
      ) : (
        <div className="flex items-center gap-1.5 mb-2">
          <Minus className="h-3 w-3 text-slate-600" />
          <span className="text-[10px] font-medium text-slate-600">
            Pending measurement
          </span>
        </div>
      )}

      {/* Threshold indicator */}
      {hasThreshold && (
        <div className="flex items-center gap-1 mb-2">
          <div className={cn(
            'h-1.5 w-1.5 rounded-full',
            thresholdStatus === 'good' ? 'bg-emerald-400' : 'bg-red-400'
          )} />
          <span className="text-[9px] text-slate-600">
            Threshold: {metric.threshold}{metric.unit}
          </span>
        </div>
      )}

      {/* Storage bar */}
      {hasMax && (
        <div className="mb-2">
          <div className="h-1.5 w-full rounded-full bg-slate-800/60 overflow-hidden">
            <div
              className={cn(
                'h-full rounded-full transition-all duration-500',
                usagePercent > 80 ? 'bg-red-500' : usagePercent > 60 ? 'bg-amber-500' : 'bg-emerald-500'
              )}
              style={{ width: `${usagePercent}%` }}
            />
          </div>
          <p className="text-[9px] text-slate-600 mt-0.5 text-right">{metric.max} {metric.unit} total</p>
        </div>
      )}

      {/* Sparkline */}
      <div className="h-[32px] -mx-1 flex items-center">
        {metric.value !== null && metric.sparkline.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparklineData}>
              <defs>
                <linearGradient id={`spark-${config.key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={config.color} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={config.color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="v"
                stroke={config.color}
                strokeWidth={1.5}
                fill={`url(#spark-${config.key})`}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="w-full border-t border-dashed border-slate-800/80 my-auto" />
        )}
      </div>
    </motion.div>
  );
}

// ── Skeleton ────────────────────────────────────────────────────────────────

function AnalyticsSkeleton() {
  return (
    <div className="rounded-xl p-4 bg-slate-900/50 border border-slate-800/50 space-y-2">
      <div className="flex items-center justify-between">
        <Skeleton className="h-3 w-20" />
        <Skeleton variant="rectangular" className="h-7 w-7 rounded-lg" />
      </div>
      <Skeleton className="h-6 w-16" />
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-8 w-full" />
    </div>
  );
}
