import { useEffect, useRef, useState } from 'react';

type WSMessage = {
  type: string;
  data: Record<string, unknown>;
  timestamp: string;
};

type UseWebSocketOptions = {
  onMessage?: (msg: WSMessage) => void;
  onCollectionStarted?: (data: { competitor_id: number; competitor_name: string }) => void;
  onCollectionCompleted?: (data: {
    competitor_id: number;
    competitor_name: string;
    records_collected: number;
    elapsed_seconds: number;
    changes_detected: number;
  }) => void;
  onCollectionFailed?: (data: { competitor_id: number; competitor_name: string; error: string }) => void;
  onChangesDetected?: (data: { competitor_id: number; changes: unknown[] }) => void;
};

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const optionsRef = useRef(options);
  optionsRef.current = options;
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let ws: WebSocket;
    let interval: ReturnType<typeof setInterval>;

    function connect() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const url = `${protocol}//${host}/ws`;

      ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        interval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        try {
          const msg: WSMessage = JSON.parse(event.data);
          if (msg.type === 'pong') return;
          const opts = optionsRef.current;
          opts.onMessage?.(msg);

          switch (msg.type) {
            case 'collection_started':
              opts.onCollectionStarted?.(msg.data as any);
              break;
            case 'collection_completed':
              opts.onCollectionCompleted?.(msg.data as any);
              break;
            case 'collection_failed':
              opts.onCollectionFailed?.(msg.data as any);
              break;
            case 'changes_detected':
              opts.onChangesDetected?.(msg.data as any);
              break;
          }
        } catch {
          // Ignore non-JSON messages (like pong)
        }
      };

      ws.onclose = () => {
        setConnected(false);
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      clearInterval(interval);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      ws.close();
    };
  }, []);

  return { connected };
}
