/**
 * AgentStatusPanel — grid of all 14 AI agent cards with summary bar,
 * sorting, and bulk retry.
 */

import { useMemo, useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Bot, RotateCcw, Filter } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/atoms/Badge';
import { useAgentStore } from '@/stores/agentStore';
import { ALL_AGENT_IDS, AGENT_REGISTRY } from '@/lib/constants';
import { AgentCard } from './AgentCard';
import type { AgentId, AgentStatus } from '@/types';

type SortMode = 'pipeline' | 'status' | 'name';

interface AgentStatusPanelProps {
  onViewDetails: (agentId: AgentId) => void;
  isLoading?: boolean;
}

const statusOrder: Record<AgentStatus, number> = {
  running: 0,
  retrying: 1,
  queued: 2,
  failed: 3,
  completed: 4,
  idle: 5,
};

export function AgentStatusPanel({ onViewDetails, isLoading = false }: AgentStatusPanelProps) {
  const agents = useAgentStore((s) => s.agents);
  const retryAgent = useAgentStore((s) => s.retryAgent);

  useEffect(() => {
    useAgentStore.getState().initializeAgents();
  }, []);

  const [sortMode, setSortMode] = useState<SortMode>('pipeline');
  const [filterStatus, setFilterStatus] = useState<AgentStatus | 'all'>('all');

  // Compute summary counts
  const summary = useMemo(() => {
    const values = Object.values(agents);
    return {
      running: values.filter((a) => a.status === 'running').length,
      queued: values.filter((a) => a.status === 'queued').length,
      completed: values.filter((a) => a.status === 'completed').length,
      failed: values.filter((a) => a.status === 'failed').length,
      idle: values.filter((a) => a.status === 'idle').length,
      retrying: values.filter((a) => a.status === 'retrying').length,
    };
  }, [agents]);

  // Sort and filter agents
  const sortedAgentIds = useMemo(() => {
    let ids = [...ALL_AGENT_IDS];

    // Filter
    if (filterStatus !== 'all') {
      ids = ids.filter((id) => agents[id].status === filterStatus);
    }

    // Sort
    switch (sortMode) {
      case 'status':
        ids.sort((a, b) => statusOrder[agents[a].status] - statusOrder[agents[b].status]);
        break;
      case 'name':
        ids.sort((a, b) => AGENT_REGISTRY[a].name.localeCompare(AGENT_REGISTRY[b].name));
        break;
      case 'pipeline':
      default:
        ids.sort((a, b) => AGENT_REGISTRY[a].pipelineOrder - AGENT_REGISTRY[b].pipelineOrder);
    }

    return ids;
  }, [agents, sortMode, filterStatus]);

  const handleRetryAll = () => {
    const failed = Object.values(agents).filter((a) => a.status === 'failed');
    for (const agent of failed) {
      retryAgent(agent.agentId);
    }
  };

  return (
    <div className="space-y-4">
      {/* ── Header & Controls ──────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-indigo-400" />
          <h2 className="text-lg font-semibold text-slate-100">AI Agents</h2>
          <Badge variant="info" size="xs">{ALL_AGENT_IDS.length} agents</Badge>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Sort Controls */}
          <div className="flex items-center gap-1 bg-slate-800/50 rounded-lg p-0.5">
            {(['pipeline', 'status', 'name'] as SortMode[]).map((mode) => (
              <button
                key={mode}
                onClick={() => setSortMode(mode)}
                className={cn(
                  'px-2.5 py-1 rounded-md text-[10px] font-medium transition-colors',
                  sortMode === mode
                    ? 'bg-indigo-500/20 text-indigo-300'
                    : 'text-slate-500 hover:text-slate-300'
                )}
              >
                {mode.charAt(0).toUpperCase() + mode.slice(1)}
              </button>
            ))}
          </div>

          {/* Filter */}
          <div className="flex items-center gap-1">
            <Filter className="h-3 w-3 text-slate-500" />
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as AgentStatus | 'all')}
              className="bg-slate-800/50 border border-slate-700/50 rounded-lg px-2 py-1 text-[10px] text-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
              aria-label="Filter agents by status"
            >
              <option value="all">All Status</option>
              <option value="running">Running</option>
              <option value="queued">Queued</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="idle">Idle</option>
            </select>
          </div>



          {summary.failed > 0 && (
            <button
              onClick={handleRetryAll}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 text-xs font-medium transition-colors"
              aria-label="Retry all failed agents"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Retry All ({summary.failed})
            </button>
          )}
        </div>
      </div>

      {/* ── Summary Bar ────────────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-wrap gap-3 px-4 py-2.5 rounded-xl bg-slate-900/30 border border-slate-800/30"
      >
        {[
          { label: 'Running', count: summary.running, color: 'text-indigo-400' },
          { label: 'Queued', count: summary.queued, color: 'text-amber-400' },
          { label: 'Completed', count: summary.completed, color: 'text-emerald-400' },
          { label: 'Failed', count: summary.failed, color: 'text-red-400' },
          { label: 'Idle', count: summary.idle, color: 'text-slate-500' },
        ].map((item) => (
          <div key={item.label} className="flex items-center gap-1.5">
            <span className={cn('text-lg font-bold', item.color)}>{item.count}</span>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider">{item.label}</span>
          </div>
        ))}
      </motion.div>

      {/* ── Agent Grid ─────────────────────────────────────────────── */}
      <div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3"
        role="list"
        aria-label="AI Agent status cards"
      >
        {sortedAgentIds.map((agentId, i) => (
          <div key={agentId} role="listitem">
            <AgentCard
              agentId={agentId}
              state={agents[agentId]}
              onRetry={retryAgent}
              onViewDetails={onViewDetails}
              index={i}
              isLoading={isLoading}
            />
          </div>
        ))}
      </div>

      {/* Empty state when filtered */}
      {sortedAgentIds.length === 0 && (
        <div className="text-center py-8">
          <Bot className="h-10 w-10 text-slate-700 mx-auto mb-2" />
          <p className="text-sm text-slate-500">No agents match the selected filter.</p>
          <button
            onClick={() => setFilterStatus('all')}
            className="mt-2 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            Clear filter
          </button>
        </div>
      )}
    </div>
  );
}
