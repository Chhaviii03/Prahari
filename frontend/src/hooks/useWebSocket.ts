import { useEffect, useRef, useState } from 'react';

type WsEvent = { type: string; data?: unknown };

export function useWebSocket(onEvent?: (event: WsEvent) => void) {
  const [connected, setConnected] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const cbRef = useRef(onEvent);
  cbRef.current = onEvent;

  useEffect(() => {
    let ws: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout>;
    let alive = true;

    const connect = () => {
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const host = window.location.host;
      ws = new WebSocket(`${proto}://${host}/v1/ops/stream`);

      ws.onopen = () => {
        if (!alive) return;
        setConnected(true);
        setReconnecting(false);
      };

      ws.onclose = () => {
        if (!alive) return;
        setConnected(false);
        setReconnecting(true);
        timer = setTimeout(connect, 3000);
      };

      ws.onmessage = (msg) => {
        try {
          const event = JSON.parse(msg.data) as WsEvent;
          if (event.type !== 'ping') cbRef.current?.(event);
        } catch {}
      };
    };

    connect();
    return () => {
      alive = false;
      clearTimeout(timer);
      ws?.close();
    };
  }, []);

  return { connected, reconnecting };
}
