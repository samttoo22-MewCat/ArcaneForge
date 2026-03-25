import { useCallback, useEffect, useRef } from "react";
import type { GameEvent } from "../types";

interface UseSSEOptions {
  playerId: string;
  onEvent: (event: GameEvent) => void;
  onConnected: (connected: boolean) => void;
}

export function useSSE({ playerId, onEvent, onConnected }: UseSSEOptions) {
  const esRef = useRef<EventSource | null>(null);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryCount = useRef(0);

  const connect = useCallback(() => {
    if (esRef.current) esRef.current.close();

    const es = new EventSource(`/events?player_id=${playerId}`);
    esRef.current = es;

    es.onopen = () => {
      retryCount.current = 0;
      onConnected(true);
    };

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as Record<string, unknown>;
        // Normalize: backend may send `type` instead of `event_type`
        const event_type = (data.event_type ?? data.type) as string | undefined;
        // Skip internal connection handshake events
        if (!event_type || event_type === "connected") return;
        const timestamp = (data.timestamp as number | undefined) ?? Date.now() / 1000;
        const event = {
          ...data,
          event_type,
          timestamp,
          id: `${event_type}-${timestamp}-${Math.random()}`,
        } as GameEvent;
        onEvent(event);
      } catch {
        // ignore malformed events
      }
    };

    es.onerror = () => {
      onConnected(false);
      es.close();
      esRef.current = null;

      // exponential backoff: 1s, 2s, 4s, 8s, max 30s
      const delay = Math.min(1000 * 2 ** retryCount.current, 30_000);
      retryCount.current++;
      retryTimer.current = setTimeout(connect, delay);
    };
  }, [playerId, onEvent, onConnected]);

  useEffect(() => {
    connect();
    return () => {
      esRef.current?.close();
      if (retryTimer.current) clearTimeout(retryTimer.current);
    };
  }, [connect]);
}
