/**
 * Agent Orchestration Store — manages all 14 AI agents' state,
 * pipeline progression, and real-time updates.
 *
 * Uses real API endpoints for initialization and websockets for updates.
 */

import { create } from 'zustand';
import type {
  AgentId, AgentState, AgentStatus, AgentLogEntry,
  PipelineStage, PipelineStageName, AgentUpdatePayload,
} from '@/types';
import { ALL_AGENT_IDS, PIPELINE_STAGES, AGENT_REGISTRY } from '@/lib/constants';
import api from '@/lib/api';

// ── Helper: create initial agent state ──────────────────────────────────────

function createInitialAgentState(agentId: AgentId): AgentState {
  return {
    agentId,
    status: 'idle',
    progress: 0,
    processingTimeMs: 0,
    confidenceScore: 0,
    tokenUsage: 0,
    queuePosition: 0,
    lastExecutionTime: null,
    logs: [],
    errors: [],
    retryCount: 0,
    startedAt: null,
    completedAt: null,
  };
}

// ── Store Interface ─────────────────────────────────────────────────────────

interface AgentStore {
  // State
  agents: Record<AgentId, AgentState>;
  pipelineStages: PipelineStage[];
  currentStage: PipelineStageName | null;
  overallProgress: number;

  // Actions
  updateAgentStatus: (agentId: AgentId, updates: Partial<AgentState>) => void;
  addAgentLog: (agentId: AgentId, log: AgentLogEntry) => void;
  retryAgent: (agentId: AgentId) => Promise<void>;
  resetPipeline: () => void;
  processWebSocketUpdate: (payload: AgentUpdatePayload) => void;
  initializeAgents: () => Promise<void>;

  // Selectors (computed via getters)
  getRunningAgents: () => AgentState[];
  getFailedAgents: () => AgentState[];
  getCompletedAgents: () => AgentState[];
  getQueuedAgents: () => AgentState[];
  getAgentById: (id: AgentId) => AgentState;
  getPipelineProgress: () => number;
}

export const useAgentStore = create<AgentStore>()((set, get) => {
  // Build initial state for all 14 agents
  const initialAgents = {} as Record<AgentId, AgentState>;
  for (const id of ALL_AGENT_IDS) {
    initialAgents[id] = createInitialAgentState(id);
  }

  return {
    agents: initialAgents,
    pipelineStages: PIPELINE_STAGES.map((s) => ({ ...s })),
    currentStage: null,
    overallProgress: 0,

    // ── Actions ──────────────────────────────────────────────────────────

    updateAgentStatus: (agentId, updates) => {
      set((state) => {
        const agent = state.agents[agentId];
        if (!agent) return state;

        const updated = { ...agent, ...updates };

        // Update pipeline stage status based on agent statuses
        const agentInfo = AGENT_REGISTRY[agentId];
        const newStages = state.pipelineStages.map((stage) => {
          if (stage.id !== agentInfo.pipelineStage) return stage;

          const stageAgentIds = stage.agentIds;
          const stageAgents = stageAgentIds.map((id) =>
            id === agentId ? updated : state.agents[id]
          );

          let stageStatus: AgentStatus = 'idle';
          if (stageAgents.some((a) => a.status === 'failed')) stageStatus = 'failed';
          else if (stageAgents.every((a) => a.status === 'completed')) stageStatus = 'completed';
          else if (stageAgents.some((a) => a.status === 'running')) stageStatus = 'running';
          else if (stageAgents.some((a) => a.status === 'queued')) stageStatus = 'queued';

          return { ...stage, status: stageStatus };
        });

        // Calculate overall progress
        const allAgents = Object.values({ ...state.agents, [agentId]: updated });
        const totalProgress = allAgents.reduce((sum, a) => sum + a.progress, 0);
        const overallProgress = Math.round(totalProgress / ALL_AGENT_IDS.length);

        return {
          agents: { ...state.agents, [agentId]: updated },
          pipelineStages: newStages,
          overallProgress,
        };
      });
    },

    addAgentLog: (agentId, log) => {
      set((state) => {
        const agent = state.agents[agentId];
        if (!agent) return state;
        return {
          agents: {
            ...state.agents,
            [agentId]: {
              ...agent,
              logs: [...agent.logs, log].slice(-100), // Keep last 100 logs
            },
          },
        };
      });
    },

    retryAgent: async (agentId) => {
      const state = get();
      const agent = state.agents[agentId];
      if (!agent || agent.status !== 'failed') return;

      set((s) => ({
        agents: {
          ...s.agents,
          [agentId]: {
            ...s.agents[agentId],
            status: 'retrying',
            progress: 0,
            errors: [],
            retryCount: s.agents[agentId].retryCount + 1,
          },
        },
      }));

      try {
        await api.post(`/agents/${agentId}/retry`);
      } catch (err) {
        console.error(`Failed to retry agent ${agentId}`, err);
        set((s) => ({
          agents: {
            ...s.agents,
            [agentId]: {
              ...s.agents[agentId],
              status: 'failed',
            },
          },
        }));
      }
    },

    resetPipeline: () => {
      const resetAgents = {} as Record<AgentId, AgentState>;
      for (const id of ALL_AGENT_IDS) {
        resetAgents[id] = createInitialAgentState(id);
      }

      set({
        agents: resetAgents,
        pipelineStages: PIPELINE_STAGES.map((s) => ({ ...s })),
        currentStage: null,
        overallProgress: 0,
      });
    },

    processWebSocketUpdate: (payload) => {
      const { updateAgentStatus, addAgentLog } = get();

      updateAgentStatus(payload.agentId, {
        status: payload.status,
        progress: payload.progress,
        processingTimeMs: payload.processingTimeMs,
        confidenceScore: payload.confidenceScore,
        tokenUsage: payload.tokenUsage,
        queuePosition: payload.queuePosition,
      });

      if (payload.logEntry) {
        addAgentLog(payload.agentId, payload.logEntry);
      }

      if (payload.error) {
        set((state) => ({
          agents: {
            ...state.agents,
            [payload.agentId]: {
              ...state.agents[payload.agentId],
              errors: [...state.agents[payload.agentId].errors, payload.error!],
            },
          },
        }));
      }
    },

    initializeAgents: async () => {
      try {
        const [agentsRes, pipelineRes] = await Promise.all([
          api.get('/agents'),
          api.get('/agents/pipeline'),
        ]);

        const agentsData = agentsRes.data;
        const pipelineData = pipelineRes.data;

        set((state) => {
          const newAgents = { ...state.agents };
          if (Array.isArray(agentsData)) {
            agentsData.forEach((a) => {
              if (newAgents[a.agentId as AgentId]) {
                newAgents[a.agentId as AgentId] = {
                  ...newAgents[a.agentId as AgentId],
                  ...a,
                };
              }
            });
          }

          return {
            agents: newAgents,
            pipelineStages: pipelineData.stages || state.pipelineStages,
            currentStage: pipelineData.currentStage || state.currentStage,
            overallProgress: pipelineData.overallProgress || 0,
          };
        });
      } catch (err) {
        console.error('Failed to initialize agents', err);
      }
    },

    // ── Selectors ────────────────────────────────────────────────────────

    getRunningAgents: () => {
      const agents = Object.values(get().agents);
      return agents.filter((a) => a.status === 'running');
    },

    getFailedAgents: () => {
      const agents = Object.values(get().agents);
      return agents.filter((a) => a.status === 'failed');
    },

    getCompletedAgents: () => {
      const agents = Object.values(get().agents);
      return agents.filter((a) => a.status === 'completed');
    },

    getQueuedAgents: () => {
      const agents = Object.values(get().agents);
      return agents.filter((a) => a.status === 'queued');
    },

    getAgentById: (id) => get().agents[id],

    getPipelineProgress: () => get().overallProgress,
  };
});
