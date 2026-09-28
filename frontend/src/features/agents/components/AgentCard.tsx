/**
 * AgentCard — Individual AI agent status card with all monitoring fields.
 *
 * Displays: status, progress, processing time, confidence, token usage,
 * queue position, retry option, last execution, logs preview, errors.
 */

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Eye, FolderSearch, UserSearch, GitFork, Share2, CalendarClock,
  Cpu, Database, Scale, BookCheck, ShieldAlert, Link2, Sparkles,
  FileBarChart, RotateCcw, ChevronDown, ChevronUp, Clock, Zap,
  AlertCircle, CheckCircle2, Timer, Hash, FileUp, Layers, FileText,
  Shield, AlertTriangle, Lock, Boxes, Compass,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/atoms/Badge';
import { ProgressBar } from '@/components/atoms/ProgressBar';
import { Skeleton } from '@/components/atoms/Skeleton';
import { AGENT_REGISTRY, AGENT_STATUS_COLORS } from '@/lib/constants';
import type { AgentId, AgentState, AgentStatus } from '@/types';

// ── Icon Map ────────────────────────────────────────────────────────────────

const iconMap: Record<string, React.ElementType> = {
  Eye, FolderSearch, UserSearch, GitFork, Share2, CalendarClock,
  Cpu, Database, Scale, BookCheck, ShieldAlert, Link2, Sparkles,
  FileBarChart, FileUp, Layers, FileText, Shield, AlertTriangle,
  Lock, Boxes, Compass,
};

// ── Status Config ───────────────────────────────────────────────────────────

const statusConfig: Record<AgentStatus, {
  label: string;
  variant: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple';
  dot: boolean;
  pulse: boolean;
}> = {
  idle: { label: 'Idle', variant: 'default', dot: true, pulse: false },
  queued: { label: 'Queued', variant: 'warning', dot: true, pulse: true },
  running: { label: 'Running', variant: 'purple', dot: true, pulse: true },
  completed: { label: 'Completed', variant: 'success', dot: true, pulse: false },
  failed: { label: 'Failed', variant: 'danger', dot: true, pulse: true },
  retrying: { label: 'Retrying', variant: 'warning', dot: true, pulse: true },
};

// ── Props ───────────────────────────────────────────────────────────────────

interface AgentCardProps {
  agentId: AgentId;
  state: AgentState;
  onRetry: (agentId: AgentId) => void;
  onViewDetails: (agentId: AgentId) => void;
  index?: number;
  isLoading?: boolean;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return `${minutes}m ${seconds}s`;
}

function formatTokens(tokens: number): string {
  if (tokens < 1000) return `${tokens}`;
  if (tokens < 1000000) return `${(tokens / 1000).toFixed(1)}k`;
  return `${(tokens / 1000000).toFixed(2)}M`;
}

function formatTime(iso: string | null): string {
  if (!iso) return '—';
  return new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(iso));
}

// ── Component ───────────────────────────────────────────────────────────────

export function AgentCard({
  agentId,
  state,
  onRetry,
  onViewDetails,
  index = 0,
  isLoading = false,
}: AgentCardProps) {
  const info = AGENT_REGISTRY[agentId];
  const Icon = iconMap[info.iconName] || Zap;
  const status = statusConfig[state.status];
  const [logsExpanded, setLogsExpanded] = useState(false);
  const [elapsedMs, setElapsedMs] = useState(state.processingTimeMs);
  const intervalRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  // Live elapsed time counter while running
  useEffect(() => {
    if (state.status === 'running' && state.startedAt) {
      intervalRef.current = setInterval(() => {
        setElapsedMs(Date.now() - new Date(state.startedAt!).getTime());
      }, 100);
      return () => clearInterval(intervalRef.current);
    } else {
      setElapsedMs(state.processingTimeMs);
    }
  }, [state.status, state.startedAt, state.processingTimeMs]);

  // Loading skeleton
  if (isLoading) {
    return <AgentCardSkeleton />;
  }

  // Empty state
  if (state.status === 'idle' && !state.lastExecutionTime) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.04, duration: 0.35 }}
        className="rounded-xl p-4 bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 transition-all duration-300 hover:border-slate-700/50"
      >
        <div className="flex items-center gap-3 mb-3">
          <div
            className="h-9 w-9 rounded-lg flex items-center justify-center"
            style={{ backgroundColor: `${info.color}15` }}
          >
            <Icon className="h-4.5 w-4.5" style={{ color: info.color }} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-slate-200 truncate">{info.shortName}</p>
            <p className="text-[10px] text-slate-600 truncate">{info.name}</p>
          </div>
          <Badge variant="default" size="xs" dot>Idle</Badge>
        </div>
        <p className="text-xs text-slate-600 text-center py-4">No executions yet</p>
      </motion.div>
    );
  }

  const progressVariant = state.status === 'failed' ? 'danger'
    : state.status === 'completed' ? 'success'
    : state.status === 'running' ? 'default'
    : 'warning';

  const glowClass = state.status === 'running' ? 'agent-running'
    : state.status === 'failed' ? 'agent-failed' : '';

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.35 }}
      role="article"
      aria-label={`${info.name}: ${status.label}`}
      tabIndex={0}
      onClick={() => onViewDetails(agentId)}
      onKeyDown={(e) => e.key === 'Enter' && onViewDetails(agentId)}
      className={cn(
        'rounded-xl p-4 cursor-pointer',
        'bg-slate-900/50 backdrop-blur-xl',
        'border transition-all duration-300',
        state.status === 'failed'
          ? 'border-red-500/30 hover:border-red-500/50'
          : state.status === 'completed'
          ? 'border-emerald-500/20 hover:border-emerald-500/40'
          : state.status === 'running'
          ? 'border-indigo-500/30 hover:border-indigo-500/50'
          : 'border-slate-800/50 hover:border-slate-700/50',
        glowClass,
      )}
    >
      {/* ── Header: Icon + Name + Status Badge ─────────────────────── */}
      <div className="flex items-center gap-3 mb-3">
        <div
          className="h-9 w-9 rounded-lg flex items-center justify-center shrink-0 relative"
          style={{ backgroundColor: `${info.color}15` }}
        >
          <Icon className="h-4.5 w-4.5" style={{ color: info.color }} />
          {state.status === 'running' && (
            <span
              className="absolute -top-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-slate-900"
              style={{ backgroundColor: AGENT_STATUS_COLORS[state.status] }}
            />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-slate-200 truncate">{info.shortName}</p>
          <p className="text-[10px] text-slate-600 truncate">{info.name}</p>
        </div>
        <Badge variant={status.variant} size="xs" dot={status.dot} pulse={status.pulse}>
          {status.label}
        </Badge>
      </div>

      {/* ── Progress Bar ───────────────────────────────────────────── */}
      <div className="mb-3">
        <ProgressBar
          value={state.progress}
          variant={progressVariant}
          size="sm"
          showLabel
          animated={state.status === 'running'}
        />
      </div>

      {/* ── Metrics Grid ───────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2 mb-3">
        {/* Processing Time */}
        <div className="flex items-center gap-1.5">
          <Timer className="h-3 w-3 text-slate-600 shrink-0" />
          <span className="text-[10px] text-slate-500">Time</span>
          <span className="text-[10px] font-mono text-slate-300 ml-auto">
            {formatDuration(elapsedMs)}
          </span>
        </div>

        {/* Confidence */}
        <div className="flex items-center gap-1.5">
          <CheckCircle2 className="h-3 w-3 text-slate-600 shrink-0" />
          <span className="text-[10px] text-slate-500">Conf.</span>
          <span className={cn(
            'text-[10px] font-mono ml-auto',
            state.confidenceScore != null && state.confidenceScore >= 90 ? 'text-emerald-400'
              : state.confidenceScore != null && state.confidenceScore >= 70 ? 'text-amber-400'
              : state.confidenceScore != null && state.confidenceScore > 0 ? 'text-red-400'
              : 'text-slate-600'
          )}>
            {state.status !== 'idle' && state.confidenceScore != null && state.confidenceScore > 0
              ? `${state.confidenceScore}%`
              : state.status !== 'idle' && state.confidenceScore === null
              ? 'N/A'
              : '—'}
          </span>
        </div>

        {/* Token Usage */}
        <div className="flex items-center gap-1.5">
          <Zap className="h-3 w-3 text-slate-600 shrink-0" />
          <span className="text-[10px] text-slate-500">Tokens</span>
          <span className="text-[10px] font-mono text-slate-300 ml-auto">
            {state.tokenUsage > 0 ? formatTokens(state.tokenUsage) : '—'}
          </span>
        </div>

        {/* Queue Position */}
        <div className="flex items-center gap-1.5">
          <Hash className="h-3 w-3 text-slate-600 shrink-0" />
          <span className="text-[10px] text-slate-500">Queue</span>
          <span className="text-[10px] font-mono text-slate-300 ml-auto">
            {state.queuePosition > 0 ? `#${state.queuePosition}` : '—'}
          </span>
        </div>
      </div>

      {/* ── Last Execution ─────────────────────────────────────────── */}
      {state.lastExecutionTime && (
        <div className="flex items-center gap-1.5 mb-2">
          <Clock className="h-3 w-3 text-slate-600" />
          <span className="text-[10px] text-slate-600">
            Last run: {formatTime(state.lastExecutionTime)}
          </span>
        </div>
      )}

      {/* ── Error Messages ─────────────────────────────────────────── */}
      <AnimatePresence>
        {state.errors.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-2 rounded-lg bg-red-500/5 border border-red-500/20 p-2"
          >
            <div className="flex items-start gap-2">
              <AlertCircle className="h-3.5 w-3.5 text-red-400 shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-[10px] font-medium text-red-400">
                  {state.errors[state.errors.length - 1]}
                </p>
                {state.retryCount > 0 && (
                  <p className="text-[10px] text-red-400/60 mt-0.5">
                    Retry attempt {state.retryCount}
                  </p>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Logs Preview (expandable) ──────────────────────────────── */}
      {state.logs.length > 0 && (
        <div className="mt-1">
          <button
            onClick={(e) => { e.stopPropagation(); setLogsExpanded(!logsExpanded); }}
            className="flex items-center gap-1 text-[10px] text-slate-500 hover:text-slate-300 transition-colors w-full"
            aria-expanded={logsExpanded}
          >
            {logsExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            <span>Logs ({state.logs.length})</span>
          </button>
          <AnimatePresence>
            {logsExpanded && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-1 max-h-24 overflow-y-auto rounded bg-slate-950/60 p-2 log-viewer"
              >
                {state.logs.slice(-5).map((log) => (
                  <div key={log.id} className={cn('text-[10px] leading-4', `log-level-${log.level}`)}>
                    <span className="text-slate-600">{formatTime(log.timestamp)}</span>{' '}
                    {log.message}
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* ── Retry Button ───────────────────────────────────────────── */}
      {state.status === 'failed' && (
        <button
          onClick={(e) => { e.stopPropagation(); onRetry(agentId); }}
          className="mt-2 w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 text-[11px] font-medium transition-colors"
          aria-label={`Retry ${info.name}`}
        >
          <RotateCcw className="h-3 w-3" />
          Retry Agent
        </button>
      )}
    </motion.div>
  );
}

// ── Skeleton ────────────────────────────────────────────────────────────────

function AgentCardSkeleton() {
  return (
    <div className="rounded-xl p-4 bg-slate-900/50 border border-slate-800/50 space-y-3">
      <div className="flex items-center gap-3">
        <Skeleton variant="rectangular" className="h-9 w-9 rounded-lg" />
        <div className="flex-1 space-y-1.5">
          <Skeleton className="h-3.5 w-20" />
          <Skeleton className="h-2.5 w-32" />
        </div>
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
      <Skeleton className="h-1.5 w-full rounded-full" />
      <div className="grid grid-cols-2 gap-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-full" />
      </div>
    </div>
  );
}
