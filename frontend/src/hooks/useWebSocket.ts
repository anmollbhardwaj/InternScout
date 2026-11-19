import { useEffect, useRef, useState, useCallback } from 'react';
import { WebSocketMessage, WSMatchAlertPayload, ApplicationProgressEvent } from '../types';

interface UseWebSocketOptions {
  url?: string;
  onMatchAlert?: (payload: WSMatchAlertPayload) => void;
  onProgress?: (payload: ApplicationProgressEvent) => void;
}

export function useWebSocket({
  url = 'ws://localhost:8000/ws',
  onMatchAlert,
  onProgress,
}: UseWebSocketOptions = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);

  const connect = useCallback(() => {
    try {
      const socket = new WebSocket(url);
      wsRef.current = socket;

      socket.onopen = () => {
        setIsConnected(true);
        reconnectAttempts.current = 0;
        console.log('[WebSocket] Connected to InternScout engine');
      };

      socket.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(data);

          if (data.type === 'NEW_MATCH_ALERT' && onMatchAlert) {
            onMatchAlert(data.payload);
          } else if (data.type === 'APPLICATION_PROGRESS' && onProgress) {
            onProgress(data.payload);
          }
        } catch (err) {
          console.error('[WebSocket] Error parsing incoming frame:', err);
        }
      };

      socket.onclose = () => {
        setIsConnected(false);
        const timeout = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 15000);
        console.warn(`[WebSocket] Closed. Reconnecting in ${timeout}ms...`);
        reconnectAttempts.current += 1;
        reconnectTimeoutRef.current = setTimeout(connect, timeout);
      };

      socket.onerror = (error) => {
        console.error('[WebSocket] Socket encountered error:', error);
        socket.close();
      };
    } catch (err) {
      console.error('[WebSocket] Connection attempt failed:', err);
    }
  }, [url, onMatchAlert, onProgress]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  return { isConnected, lastMessage };
}
