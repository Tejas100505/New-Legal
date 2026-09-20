/**
 * useAgentUpdates — hook consuming WebSocket agent updates
 * and keeping the agent store in sync.
 */

import { useEffect } from 'react';
import { useAgentStore } from '@/stores/agentStore';
import { useAnalyticsStore } from '@/stores/analyticsStore';
import { useAriaAnnounce } from '@/hooks/useAccessibility';
import { AGENT_REGISTRY } from '@/lib/constants';
import type { AgentId } from '@/types';

/**
 * Hook that watches agent state changes and announces them
 * to screen readers via aria-live regions.
 */
export function useAgentUpdates() {
  const agents = useAgentStore((s) => s.agents);
  const announce = useAriaAnnounce();
  const refreshAnalytics = useAnalyticsStore((s) => s.refreshAnalytics);

  // Announce agent status changes to screen readers
  useEffect(() => {
    const agentValues = Object.values(agents);
    const running = agentValues.filter((a) => a.status === 'running');
    const completed = agentValues.filter((a) => a.status === 'completed');
    const failed = agentValues.filter((a) => a.status === 'failed');

    if (failed.length > 0) {
      const names = failed.map((a) => AGENT_REGISTRY[a.agentId as AgentId]?.shortName).join(', ');
      announce(`Alert: ${failed.length} agent${failed.length > 1 ? 's' : ''} failed: ${names}`, 'assertive');
    } else if (completed.length === 14) {
      announce('All 14 AI agents have completed processing successfully.', 'polite');
    } else if (running.length > 0) {
      // Don't announce every running update to avoid noise
    }
  }, [
    // Only re-run when status composition changes
    Object.values(agents).map((a) => a.status).join(','),
    announce,
  ]);

  // Periodically refresh analytics while agents are running
  useEffect(() => {
    const hasRunning = Object.values(agents).some((a) => a.status === 'running');
    if (!hasRunning) return;

    const interval = setInterval(refreshAnalytics, 5000);
    return () => clearInterval(interval);
  }, [agents, refreshAnalytics]);
}
