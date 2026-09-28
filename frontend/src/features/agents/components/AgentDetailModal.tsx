/**
 * AgentDetailModal — full-screen modal for deep agent inspection.
 * Shows all metrics, full scrollable logs, error traces, and performance charts.
 */

import { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, RotateCcw, Clock, Zap, CheckCircle2, Hash,
  AlertCircle, Timer, Copy,
} from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip as ReTooltip } from 'recharts';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/atoms/Badge';
import { ProgressBar } from '@/components/atoms/ProgressBar';
import { AGENT_REGISTRY } from '@/lib/constants';
import { useFocusTrap } from '@/hooks/useAccessibility';
import type { AgentId, AgentState, AgentStatus } from '@/types';

interface AgentDetailModalProps {
  agentId: AgentId | null;
  state: AgentState | null;
  isOpen: boolean;
  onClose: () => void;
  onRetry: (agentId: AgentId) => void;
}

const statusLabels: Record<AgentStatus, { label: string; variant: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple' }> = {
  idle: { label: 'Idle', variant: 'default' },
  queued: { label: 'Queued', variant: 'warning' },
  running: { label: 'Running', variant: 'purple' },
  completed: { label: 'Completed', variant: 'success' },
  failed: { label: 'Failed', variant: 'danger' },
  retrying: { label: 'Retrying', variant: 'warning' },
};

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  return `${m}m ${s}s`;
}

function formatTokens(tokens: number): string {
  if (tokens < 1000) return `${tokens}`;
  if (tokens < 1000000) return `${(tokens / 1000).toFixed(1)}k`;
  return `${(tokens / 1000000).toFixed(2)}M`;
}

export function AgentDetailModal({ agentId, state, isOpen, onClose, onRetry }: AgentDetailModalProps) {
  const focusTrapRef = useFocusTrap(isOpen);
  const logEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll logs to bottom
  useEffect(() => {
    if (isOpen && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [isOpen, state?.logs.length]);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!agentId || !state) return null;
  const info = AGENT_REGISTRY[agentId];
  const statusCfg = statusLabels[state.status];

  // Performance chart data derived from real log metadata / agent state
  const perfData = state.logs
    .filter((_l) => _l.level === 'info' && (_l.metadata?.duration_ms !== undefined || state.processingTimeMs > 0))
    .slice(-10)
    .map((_l, i) => ({
      name: `T${i + 1}`,
      time: _l.metadata?.duration_ms ? Number(_l.metadata.duration_ms) : state.processingTimeMs,
    }));

  const handleCopyLogs = () => {
    const text = state.logs
      .map((l) => `[${l.timestamp}] [${l.level.toUpperCase()}] ${l.message}`)
      .join('\n');
    navigator.clipboard.writeText(text);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
            aria-hidden="true"
          />

          {/* Modal */}
          <motion.div
            ref={focusTrapRef}
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.25 }}
            className="fixed inset-4 sm:inset-8 md:inset-12 lg:inset-16 z-50 flex flex-col rounded-2xl bg-slate-900 border border-slate-700/50 shadow-2xl overflow-hidden"
            role="dialog"
            aria-modal="true"
            aria-label={`${info.name} details`}
          >
            {/* ── Header ─────────────────────────────────────────────── */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800/50 shrink-0">
              <div className="flex items-center gap-3">
                <div
                  className="h-10 w-10 rounded-xl flex items-center justify-center"
                  style={{ backgroundColor: `${info.color}15` }}
                >
                  <div className="h-5 w-5" style={{ color: info.color }}>●</div>
                </div>
                <div>
                  <h2 className="text-lg font-bold text-slate-100">{info.name}</h2>
                  <p className="text-xs text-slate-500">{info.description}</p>
                </div>
                <Badge variant={statusCfg.variant} size="sm" dot pulse={state.status === 'running'}>
                  {statusCfg.label}
                </Badge>
              </div>
              <button
                onClick={onClose}
                className="h-8 w-8 rounded-lg flex items-center justify-center hover:bg-slate-800 transition-colors"
                aria-label="Close modal"
              >
                <X className="h-4 w-4 text-slate-400" />
              </button>
            </div>

            {/* ── Body (scrollable) ──────────────────────────────────── */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Progress */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-slate-300">Progress</span>
                  <span className="text-sm font-mono text-slate-400">{state.progress}%</span>
                </div>
                <ProgressBar
                  value={state.progress}
                  variant={state.status === 'failed' ? 'danger' : state.status === 'completed' ? 'success' : 'default'}
                  size="md"
                  animated={state.status === 'running'}
                />
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <MetricTile icon={<Timer className="h-4 w-4" />} label="Processing Time" value={formatDuration(state.processingTimeMs)} />
                <MetricTile
                  icon={<CheckCircle2 className="h-4 w-4" />}
                  label="Confidence"
                  value={
                    state.status !== 'idle' && state.confidenceScore != null && state.confidenceScore > 0
                      ? `${state.confidenceScore}%`
                      : state.status !== 'idle' && state.confidenceScore === null
                      ? 'N/A'
                      : '—'
                  }
                />
                <MetricTile icon={<Zap className="h-4 w-4" />} label="Token Usage" value={formatTokens(state.tokenUsage)} />
                <MetricTile icon={<Hash className="h-4 w-4" />} label="Queue Position" value={state.queuePosition > 0 ? `#${state.queuePosition}` : '—'} />
                <MetricTile icon={<Clock className="h-4 w-4" />} label="Started At" value={state.startedAt ? new Date(state.startedAt).toLocaleTimeString() : '—'} />
                <MetricTile icon={<Clock className="h-4 w-4" />} label="Completed At" value={state.completedAt ? new Date(state.completedAt).toLocaleTimeString() : '—'} />
                <MetricTile icon={<RotateCcw className="h-4 w-4" />} label="Retry Count" value={String(state.retryCount)} />
                <MetricTile icon={<Clock className="h-4 w-4" />} label="Last Execution" value={state.lastExecutionTime ? new Date(state.lastExecutionTime).toLocaleTimeString() : '—'} />
              </div>

              {/* Performance Chart */}
              {perfData.length > 2 && (
                <div>
                  <h3 className="text-sm font-medium text-slate-300 mb-3">Processing Time Trend</h3>
                  <div className="h-[150px] rounded-xl bg-slate-950/40 p-3">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={perfData}>
                        <defs>
                          <linearGradient id="perfGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor={info.color} stopOpacity={0.3} />
                            <stop offset="100%" stopColor={info.color} stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#64748b' }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fontSize: 10, fill: '#64748b' }} axisLine={false} tickLine={false} />
                        <ReTooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '0.75rem', fontSize: '0.75rem', color: '#e2e8f0' }} />
                        <Area type="monotone" dataKey="time" stroke={info.color} strokeWidth={2} fill="url(#perfGradient)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Errors */}
              {state.errors.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-red-400 mb-3 flex items-center gap-2">
                    <AlertCircle className="h-4 w-4" />
                    Errors ({state.errors.length})
                  </h3>
                  <div className="space-y-2">
                    {state.errors.map((err, i) => (
                      <div key={i} className="p-3 rounded-lg bg-red-500/5 border border-red-500/20">
                        <p className="text-xs text-red-300 font-mono">{err}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Logs */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-slate-300">Execution Logs ({state.logs.length})</h3>
                  <button
                    onClick={handleCopyLogs}
                    className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors"
                    aria-label="Copy all logs"
                  >
                    <Copy className="h-3 w-3" />
                    Copy
                  </button>
                </div>
                <div className="max-h-[300px] overflow-y-auto rounded-xl bg-slate-950/60 p-4 log-viewer">
                  {state.logs.length === 0 ? (
                    <p className="text-xs text-slate-600 text-center py-4">No logs recorded yet.</p>
                  ) : (
                    state.logs.map((log) => (
                      <div key={log.id} className={cn('py-0.5', `log-level-${log.level}`)}>
                        <span className="text-slate-600 select-none">
                          [{new Date(log.timestamp).toLocaleTimeString()}]
                        </span>{' '}
                        <span className="text-slate-600 select-none">[{log.level.toUpperCase()}]</span>{' '}
                        {log.message}
                      </div>
                    ))
                  )}
                  <div ref={logEndRef} />
                </div>
              </div>
            </div>

            {/* ── Footer ─────────────────────────────────────────────── */}
            <div className="flex items-center justify-between px-6 py-3 border-t border-slate-800/50 shrink-0">
              <span className="text-xs text-slate-600">
                Pipeline Stage: {info.pipelineStage.replace(/_/g, ' ')} • Order: #{info.pipelineOrder}
              </span>
              <div className="flex items-center gap-2">
                {state.status === 'failed' && (
                  <button
                    onClick={() => onRetry(agentId)}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 text-xs font-medium transition-colors"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    Retry Agent
                  </button>
                )}
                <button
                  onClick={onClose}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// ── Metric Tile Helper ──────────────────────────────────────────────────────

function MetricTile({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="p-3 rounded-xl bg-slate-800/30 border border-slate-800/30">
      <div className="flex items-center gap-1.5 mb-1.5">
        <span className="text-slate-500">{icon}</span>
        <span className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</span>
      </div>
      <p className="text-sm font-mono font-semibold text-slate-200">{value}</p>
    </div>
  );
}
