/**
 * useWebSocket — custom hook for WebSocket connection management.
 *
 * Features:
 * - Auto-connect/reconnect with exponential backoff
 * - Type-safe message dispatch
 * - Connection state tracking
 * - Heartbeat keep-alive
 * - Clean disconnect on unmount
 * - Offline queue for messages sent while disconnected
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { WebSocketConnectionState, WebSocketMessage } from '@/types';

interface UseWebSocketOptions {
  url: string;
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  reconnect?: boolean;
  maxRetries?: number;
  heartbeatInterval?: number;
  enabled?: boolean;
}

interface UseWebSocketReturn {
  connectionState: WebSocketConnectionState;
  send: (message: WebSocketMessage) => void;
  disconnect: () => void;
  reconnect: () => void;
  isConnected: boolean;
}

export function useWebSocket({
  url,
  onMessage,
  onConnect,
  onDisconnect,
  onError,
  reconnect: shouldReconnect = true,
  maxRetries = 10,
  heartbeatInterval = 30000,
  enabled = true,
}: UseWebSocketOptions): UseWebSocketReturn {
  const [connectionState, setConnectionState] = useState<WebSocketConnectionState>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);
  const messageQueueRef = useRef<WebSocketMessage[]>([]);
  const mountedRef = useRef(true);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const clearHeartbeat = useCallback(() => {
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
      heartbeatRef.current = undefined;
    }
  }, []);

  const startHeartbeat = useCallback(() => {
    clearHeartbeat();
    heartbeatRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'heartbeat',
          payload: null,
          timestamp: new Date().toISOString(),
        }));
      }
    }, heartbeatInterval);
  }, [clearHeartbeat, heartbeatInterval]);

  const flushQueue = useCallback(() => {
    const ws = wsRef.current;
    if (ws?.readyState !== WebSocket.OPEN) return;

    while (messageQueueRef.current.length > 0) {
      const msg = messageQueueRef.current.shift();
      if (msg) {
        ws.send(JSON.stringify(msg));
      }
    }
  }, []);

  const connect = useCallback(() => {
    if (!enabled || !mountedRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setConnectionState(retriesRef.current > 0 ? 'reconnecting' : 'connecting');

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        const token = localStorage.getItem('auth_token');
        if (token) {
          ws.send(JSON.stringify({ type: 'auth', token }));
        }
        setConnectionState('connected');
        retriesRef.current = 0;
        startHeartbeat();
        flushQueue();
        onConnect?.();
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const message = JSON.parse(event.data) as WebSocketMessage;
          onMessage?.(message);
        } catch {
          // Non-JSON message, ignore
        }
      };

      ws.onerror = (event) => {
        if (!mountedRef.current) return;
        onError?.(event);
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        clearHeartbeat();
        setConnectionState('disconnected');
        onDisconnect?.();

        // Auto-reconnect with exponential backoff
        if (shouldReconnect && retriesRef.current < maxRetries && mountedRef.current) {
          const delay = Math.min(1000 * Math.pow(2, retriesRef.current), 30000);
          retriesRef.current++;
          setConnectionState('reconnecting');
          reconnectTimerRef.current = setTimeout(connect, delay);
        }
      };
    } catch {
      setConnectionState('disconnected');
    }
  }, [url, enabled, shouldReconnect, maxRetries, onMessage, onConnect, onDisconnect, onError, startHeartbeat, clearHeartbeat, flushQueue]);

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
    }
    clearHeartbeat();
    retriesRef.current = maxRetries; // Prevent reconnection
    if (wsRef.current) {
      const ws = wsRef.current;
      wsRef.current = null;
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      } else if (ws.readyState === WebSocket.CONNECTING) {
        ws.onopen = () => {
          try { ws.close(); } catch {}
        };
        ws.onerror = () => {};
      }
    }
    setConnectionState('disconnected');
  }, [clearHeartbeat, maxRetries]);

  const send = useCallback((message: WebSocketMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      // Queue message for when connection is restored
      messageQueueRef.current.push(message);
    }
  }, []);

  const reconnectFn = useCallback(() => {
    retriesRef.current = 0;
    disconnect();
    setTimeout(connect, 100);
  }, [connect, disconnect]);

  useEffect(() => {
    mountedRef.current = true;
    if (enabled) connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      clearHeartbeat();
      if (wsRef.current) {
        const ws = wsRef.current;
        wsRef.current = null;
        if (ws.readyState === WebSocket.OPEN) {
          ws.close();
        } else if (ws.readyState === WebSocket.CONNECTING) {
          ws.onopen = () => {
            try { ws.close(); } catch {}
          };
          ws.onerror = () => {};
        }
      }
    };
  }, [enabled, connect, clearHeartbeat]);

  return {
    connectionState,
    send,
    disconnect,
    reconnect: reconnectFn,
    isConnected: connectionState === 'connected',
  };
}
