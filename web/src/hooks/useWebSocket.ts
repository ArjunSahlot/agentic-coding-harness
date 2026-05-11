import { useCallback, useEffect, useRef, useState } from "react";

export type AgentEvent = {
  type:
    | "thinking_delta"
    | "text_delta"
    | "text_final"
    | "gen_stats"
    | "tool_call_pending"
    | "tool_result"
    | "tool_rejected"
    | "token_importance"
    | "context_inserted"
    | "error"
    | "done";
  data: string | Record<string, unknown>;
};

export type EventLogEntry = {
  timestamp: number;
  event: AgentEvent;
};

type Status = "disconnected" | "connecting" | "connected";

export function useWebSocket(
  conversationId: string | null,
  onEvent: (event: AgentEvent) => void,
) {
  const wsRef = useRef<WebSocket | null>(null);
  const onEventRef = useRef(onEvent);
  const [status, setStatus] = useState<Status>("disconnected");
  const [eventLog, setEventLog] = useState<EventLogEntry[]>([]);

  onEventRef.current = onEvent;

  useEffect(() => {
    if (!conversationId) {
      setStatus("disconnected");
      return;
    }

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${protocol}://${window.location.host}/ws/${conversationId}`;
    setStatus("connecting");

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setStatus("connected");
    ws.onclose = () => setStatus("disconnected");
    ws.onerror = () => setStatus("disconnected");

    ws.onmessage = (e) => {
      try {
        const event: AgentEvent = JSON.parse(e.data);
        setEventLog((prev) => [...prev, { timestamp: Date.now(), event }]);
        onEventRef.current(event);
      } catch {
        /* malformed */
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [conversationId]);

  const send = useCallback(
    (content: string, opts?: { temperature?: number; max_tokens?: number; token_importance?: boolean }) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ content, ...opts }));
      }
    },
    [],
  );

  const sendContextInsert = useCallback((content: string, label?: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "context_insert", content, label }));
    }
  }, []);

  const sendToolApproval = useCallback((id: string, approved: boolean) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({ type: approved ? "tool_approve" : "tool_reject", id }),
      );
    }
  }, []);

  const clearLog = useCallback(() => setEventLog([]), []);

  return { status, send, sendToolApproval, sendContextInsert, eventLog, clearLog };
}
