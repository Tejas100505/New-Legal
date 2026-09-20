/**
 * Agent API — functions for agent operations against the backend.
 * Falls back gracefully when backend is unavailable.
 */

import api from '@/lib/api';
import { API_ENDPOINTS } from '@/lib/constants';
import type { AgentState, AgentLogEntry, PipelineState } from '@/types';

export async function fetchAgentStatuses(): Promise<AgentState[]> {
  const response = await api.get<AgentState[]>(API_ENDPOINTS.AGENTS.LIST);
  return response.data;
}

export async function fetchAgentStatus(agentId: string): Promise<AgentState> {
  const response = await api.get<AgentState>(API_ENDPOINTS.AGENTS.STATUS(agentId));
  return response.data;
}

export async function retryAgent(agentId: string): Promise<{ success: boolean }> {
  const response = await api.post<{ success: boolean }>(API_ENDPOINTS.AGENTS.RETRY(agentId));
  return response.data;
}

export async function fetchAgentLogs(agentId: string): Promise<AgentLogEntry[]> {
  const response = await api.get<AgentLogEntry[]>(API_ENDPOINTS.AGENTS.LOGS(agentId));
  return response.data;
}

export async function fetchPipelineStatus(): Promise<PipelineState> {
  const response = await api.get<PipelineState>(API_ENDPOINTS.AGENTS.PIPELINE);
  return response.data;
}
