/**
 * WebSocketProvider — React Context provider for WebSocket connectivity.
 * Provides connection status, send function, and subscribes to agent updates
 * when a case is active.
 */

import { createContext, useContext, useCallback, type ReactNode } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAgentStore } from '@/stores/agentStore';
import { useAnalyticsStore } from '@/stores/analyticsStore';
import { useAuthStore } from '@/features/auth/store';
import type { WebSocketConnectionState, WebSocketMessage, AgentUpdatePayload, AnalyticsUpdatePayload, DashboardAnalytics } from '@/types';

interface WebSocketContextValue {
  connectionState: WebSocketConnectionState;
  isConnected: boolean;
  send: (message: WebSocketMessage) => void;
  reconnect: () => void;
  disconnect: () => void;
}

const WebSocketContext = createContext<WebSocketContextValue | null>(null);

interface WebSocketProviderProps {
  children: ReactNode;
}

export function WebSocketProvider({ children }: WebSocketProviderProps) {
  const processAgentUpdate = useAgentStore((s) => s.processWebSocketUpdate);
  const updateMetric = useAnalyticsStore((s) => s.updateMetric);
  const token = useAuthStore((s) => s.token);

  const handleMessage = useCallback(
    (message: WebSocketMessage) => {
      switch (message.type) {
        case 'agent_update': {
          const payload = message.payload as AgentUpdatePayload;
          processAgentUpdate(payload);
          break;
        }
        case 'analytics_update': {
          const payload = message.payload as AnalyticsUpdatePayload;
          updateMetric(payload.metric as keyof DashboardAnalytics, payload.value, payload.trend);
          break;
        }
        case 'heartbeat':
          // Heartbeat acknowledged, no action needed
          break;
        default:
          break;
      }
    },
    [processAgentUpdate, updateMetric]
  );

  // Build WS URL from current location
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${window.location.host}/api/v1/ws`;

  const { connectionState, isConnected, send, reconnect, disconnect } = useWebSocket({
    url: wsUrl,
    onMessage: handleMessage,
    reconnect: true,
    maxRetries: 10,
    heartbeatInterval: 30000,
    enabled: !!token,
  });

  return (
    <WebSocketContext.Provider
      value={{ connectionState, isConnected, send, reconnect, disconnect }}
    >
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocketContext(): WebSocketContextValue {
  const context = useContext(WebSocketContext);
  if (!context) {
    // Return a no-op context when outside provider (for testing/SSR)
    return {
      connectionState: 'disconnected',
      isConnected: false,
      send: () => {},
      reconnect: () => {},
      disconnect: () => {},
    };
  }
  return context;
}
