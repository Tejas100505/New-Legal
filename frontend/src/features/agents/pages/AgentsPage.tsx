/**
 * AgentsPage — full-page agent management view.
 * Displays all 14 agents with detailed monitoring, pipeline visualization,
 * and analytics on a dedicated page.
 */

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Bot, Activity } from 'lucide-react';
import { useAgentStore } from '@/stores/agentStore';
import { useAgentUpdates } from '@/features/agents/hooks/useAgentUpdates';
import { PipelineVisualizer } from '@/features/agents/components/PipelineVisualizer';
import { AgentStatusPanel } from '@/features/agents/components/AgentStatusPanel';
import { AgentDetailModal } from '@/features/agents/components/AgentDetailModal';
import { AnalyticsGrid } from '@/features/analytics/components/AnalyticsGrid';
import { useWebSocketContext } from '@/providers/WebSocketProvider';
import { Badge } from '@/components/atoms/Badge';
import type { AgentId } from '@/types';

export function AgentsPage() {
  const agents = useAgentStore((s) => s.agents);
  const retryAgent = useAgentStore((s) => s.retryAgent);
  const [selectedAgent, setSelectedAgent] = useState<AgentId | null>(null);
  const { connectionState } = useWebSocketContext();

  useEffect(() => {
    useAgentStore.getState().initializeAgents();
  }, []);

  // Subscribe to agent updates
  useAgentUpdates();

  const agentCount = Object.values(agents);
  const running = agentCount.filter((a) => a.status === 'running').length;
  const completed = agentCount.filter((a) => a.status === 'completed').length;
  const failed = agentCount.filter((a) => a.status === 'failed').length;

  return (
    <motion.div
      className="space-y-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      id="main-content"
    >
      {/* ── Header ───────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Bot className="h-6 w-6 text-indigo-400" />
            <h1 className="text-2xl font-bold text-slate-100">AI Agent Monitor</h1>
          </div>
          <p className="text-sm text-slate-500">
            Real-time monitoring of all {agentCount.length} specialized AI agents.{' '}
            {running > 0 ? `${running} running, ` : ''}
            {completed > 0 ? `${completed} completed` : ''}
            {failed > 0 ? `, ${failed} need attention.` : '.'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge
            variant={connectionState === 'connected' ? 'success' : connectionState === 'reconnecting' ? 'warning' : 'danger'}
            size="sm"
            dot
            pulse={connectionState === 'reconnecting'}
          >
            WS: {connectionState}
          </Badge>
          <Badge variant="info" size="sm">
            <Activity className="h-3 w-3 mr-1 inline-block" />
            Live
          </Badge>
        </div>
      </div>

      {/* ── Pipeline ─────────────────────────────────────────────── */}
      <PipelineVisualizer />

      {/* ── Agent Status Panel ───────────────────────────────────── */}
      <AgentStatusPanel onViewDetails={(id) => setSelectedAgent(id)} />

      {/* ── Analytics ────────────────────────────────────────────── */}
      <AnalyticsGrid />

      {/* ── Detail Modal ─────────────────────────────────────────── */}
      <AgentDetailModal
        agentId={selectedAgent}
        state={selectedAgent ? agents[selectedAgent] : null}
        isOpen={selectedAgent !== null}
        onClose={() => setSelectedAgent(null)}
        onRetry={(id) => {
          retryAgent(id);
          setSelectedAgent(null);
        }}
      />
    </motion.div>
  );
}
