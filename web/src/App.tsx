import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ChatInput from "./components/ChatInput.tsx";
import ChatMessage, { type Message, type Segment, type ToolCallSegment } from "./components/ChatMessage.tsx";
import DevPanel from "./components/DevPanel.tsx";
import TokenImportance, { type TokenImportancePayload } from "./components/TokenImportance.tsx";
import { useWebSocket, type AgentEvent } from "./hooks/useWebSocket.ts";

type ConvSummary = { id: string; title: string };
type ModelInfo = { models: string[]; loaded: boolean; current: string | null; quantization?: string | null };
type ImportanceView = {
  id: string;
  messageIndex: number;
  segmentKind: "thinking" | "text" | "token_importance";
  payload: TokenImportancePayload;
};

export default function App() {
  const [models, setModels] = useState<ModelInfo>({ models: [], loaded: false, current: null });
  const [conversations, setConversations] = useState<ConvSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [loadingModel, setLoadingModel] = useState(false);
  const [quantMode, setQuantMode] = useState<string>("none");
  const [devOpen, setDevOpen] = useState(false);
  const [contextOpen, setContextOpen] = useState(false);
  const [importanceOpen, setImportanceOpen] = useState(false);
  const [backendOffline, setBackendOffline] = useState(false);
  const tokenImportanceEnabled = true;
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  const onEvent = useCallback((event: AgentEvent) => {
    setMessages((prev) => applyEvent(prev, event));
    if (event.type === "done" || event.type === "error") {
      setStreaming(false);
    }
  }, []);

  const { status, send, sendToolApproval, sendContextInsert, eventLog, clearLog } = useWebSocket(activeId, onEvent);

  // Keyboard shortcut: Ctrl+Shift+D for dev panel
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === "D") {
        e.preventDefault();
        setDevOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const refreshBackendState = useCallback(async () => {
    try {
      const [modelsRes, conversationsRes] = await Promise.all([
        fetch("/api/models"),
        fetch("/api/conversations"),
      ]);
      if (!modelsRes.ok || !conversationsRes.ok) {
        throw new Error("backend unavailable");
      }
      const [modelsData, conversationsData] = await Promise.all([
        modelsRes.json(),
        conversationsRes.json(),
      ]);
      setModels(modelsData);
      setConversations(conversationsData.conversations || []);
      setBackendOffline(false);
    } catch {
      setBackendOffline(true);
      setModels({ models: [], loaded: false, current: null });
      setConversations([]);
    }
  }, []);

  useEffect(() => {
    refreshBackendState();
  }, [refreshBackendState]);

  // Auto-scroll
  useEffect(() => {
    const el = scrollAreaRef.current;
    if (!el) return;
    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
    if (isNearBottom) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Fetch messages when switching conversations (persistence)
  useEffect(() => {
    if (!activeId) {
      setMessages([]);
      return;
    }
    setMessages([]);
    setStreaming(false);
    clearLog();
    fetch(`/api/conversations/${activeId}/messages`)
      .then((r) => r.json())
      .then((d) => {
        if (d.messages) {
          setMessages(d.messages as Message[]);
        }
      })
      .catch(() => {});
  }, [activeId, clearLog]);

  const loadModel = useCallback(async (name: string) => {
    setLoadingModel(true);
    try {
      const quant = quantMode === "none" ? null : quantMode;
      const res = await fetch("/api/models/load", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_name: name, quantization: quant }),
      });
      const data = await res.json();
      if (data.status === "ok") {
        setModels((m) => ({ ...m, loaded: true, current: name, quantization: quant }));
      }
    } finally {
      setLoadingModel(false);
    }
  }, [quantMode]);

  const newConversation = useCallback(async () => {
    const res = await fetch("/api/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "Chat" }),
    });
    const data = await res.json();
    setConversations((prev) => [...prev, { id: data.id, title: data.title }]);
    setActiveId(data.id);
    setMessages([]);
  }, []);

  const handleSend = useCallback(
    (text: string) => {
      const userMsg: Message = { role: "user", segments: [{ type: "text", content: text }] };
      setMessages((prev) => [...prev, userMsg]);
      setStreaming(true);
      send(text, { token_importance: tokenImportanceEnabled });
    },
    [send, tokenImportanceEnabled],
  );

  const handleToolApproval = useCallback(
    (id: string, approved: boolean) => {
      sendToolApproval(id, approved);
      setMessages((prev) =>
        prev.map((m) => ({
          ...m,
          segments: m.segments.map((s) =>
            s.type === "tool_call" && s.id === id
              ? { ...s, status: (approved ? "running" : "rejected") as ToolCallSegment["status"] }
              : s,
          ),
        })),
      );
    },
    [sendToolApproval],
  );

  const handleContextInsert = useCallback(
    (content: string, label?: string) => {
      sendContextInsert(content, label || "Manual context insert");
    },
    [sendContextInsert],
  );

  const hasPendingApproval = messages.some((m) =>
    m.segments.some((s) => s.type === "tool_call" && s.status === "pending"),
  );
  const isReady = status === "connected" && !streaming && !hasPendingApproval;
  const importanceViews = useMemo(() => collectImportanceViews(messages), [messages]);
  const latestImportance = importanceViews[importanceViews.length - 1];

  return (
    <div className="app-shell flex h-full text-slate-900">
      {/* Sidebar */}
      <aside className="flex w-72 shrink-0 flex-col border-r border-slate-200/80 bg-white/82 shadow-xl shadow-slate-900/[0.04] backdrop-blur-xl">
        <div className="flex items-center gap-3 px-5 py-5 border-b border-slate-200/80">
          <div className="grid size-9 place-items-center rounded-lg bg-slate-950 text-white shadow-lg shadow-slate-900/10">
            <span className="text-sm font-bold">H</span>
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-tight text-slate-950">Harness</h1>
            <p className="text-[11px] text-slate-500">Agent runtime cockpit</p>
          </div>
        </div>

        {/* Model selector */}
        <div className="px-4 py-4 border-b border-slate-200/80 space-y-2">
          <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400 px-1">Model</div>
          {models.models.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-3 py-3 text-xs text-slate-500">
              {backendOffline ? "Backend offline" : "No models found"}
            </div>
          ) : (
            models.models.map((m) => (
              <button
                key={m}
                onClick={() => loadModel(m)}
                disabled={loadingModel}
                className={`flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-xs transition-all duration-150
                  ${models.current === m
                    ? "bg-blue-50 text-blue-700 ring-1 ring-blue-200 shadow-sm"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                  } disabled:opacity-40`}
              >
                <span className="truncate flex-1">{m}</span>
                {models.current === m && (
                  <span className="flex items-center gap-1 shrink-0">
                    {models.quantization && (
                      <span className="text-[9px] font-semibold text-teal-600 uppercase">{models.quantization}</span>
                    )}
                    <span className="size-1.5 rounded-full bg-teal-500" />
                  </span>
                )}
              </button>
            ))
          )}
          <div className="flex items-center gap-1.5 px-1 pt-1">
            <span className="text-[10px] text-slate-500 shrink-0">Quant:</span>
            {(["none", "8bit", "4bit"] as const).map((q) => (
              <button
                key={q}
                onClick={() => setQuantMode(q)}
                className={`rounded-md px-2 py-1 text-[10px] font-semibold transition-all duration-150
                  ${quantMode === q
                    ? "bg-slate-950 text-white"
                    : "text-slate-500 hover:text-slate-800 hover:bg-slate-100"
                  }`}
              >
                {q === "none" ? "FP16" : q.toUpperCase()}
              </button>
            ))}
          </div>
          {loadingModel && (
            <div className="flex items-center gap-2 px-1 text-[11px] text-slate-500">
              <span className="inline-block size-3 rounded-full border-2 border-slate-300 border-t-blue-500 animate-spin" />
              Loading{quantMode !== "none" ? ` (${quantMode})` : ""}...
            </div>
          )}
        </div>

        {/* Conversations */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
          <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400 px-1 mb-2">Chats</div>
          {conversations.map((c) => (
            <button
              key={c.id}
              onClick={() => { setActiveId(c.id); }}
              className={`block w-full rounded-lg px-3 py-2.5 text-left text-xs transition-all duration-150 truncate
                ${activeId === c.id
                  ? "bg-slate-950 text-white shadow-sm"
                  : "text-slate-500 hover:bg-slate-100 hover:text-slate-900"
                }`}
            >
              {c.title}
            </button>
          ))}
          {conversations.length === 0 && (
            <p className="text-[11px] text-slate-500 px-1">No chats yet</p>
          )}
        </div>

        <div className="p-4 space-y-2 border-t border-slate-200/80">
          {backendOffline && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-[11px] leading-relaxed text-amber-800">
              API server unavailable. Run <span className="font-mono font-semibold">python main.py</span> at the repo root, then retry.
              <button
                type="button"
                onClick={refreshBackendState}
                className="mt-2 w-full rounded-md bg-amber-600 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-white hover:bg-amber-500"
              >
                Retry backend
              </button>
            </div>
          )}
          <button
            onClick={newConversation}
            disabled={!models.loaded}
            className="w-full rounded-lg bg-blue-600 py-2.5 text-xs font-semibold text-white shadow-lg shadow-blue-600/15
                       transition-all duration-150 hover:bg-blue-500 active:scale-[0.98]
                       disabled:opacity-25 disabled:pointer-events-none"
          >
            + New Chat
          </button>
          <button
            onClick={() => setDevOpen((v) => !v)}
            className={`w-full rounded-lg py-2 text-[10px] font-semibold uppercase tracking-[0.16em] transition-all duration-150
              ${devOpen
                ? "bg-teal-50 text-teal-700 ring-1 ring-teal-200"
                : "bg-slate-100 text-slate-500 hover:text-slate-900 hover:bg-slate-200"
              }`}
          >
            Dev Panel {devOpen ? "On" : "Off"}
          </button>
        </div>
      </aside>

      {/* Main + Dev */}
      <div className="flex flex-1 flex-col">
        <div className="flex flex-1 overflow-hidden">
          {/* Chat area */}
          <main className={`technical-grid flex flex-1 flex-col bg-slate-50/55 ${devOpen ? "border-r border-slate-200/80" : ""}`}>
            {activeId === null ? (
              <div className="flex flex-1 items-center justify-center">
                <div className="text-center space-y-3 max-w-xs">
                  <div className="mx-auto grid size-14 place-items-center rounded-2xl bg-white text-3xl text-blue-600 shadow-lg shadow-slate-900/5">&#x2756;</div>
                  <p className="text-slate-500 text-sm leading-relaxed">
                    {models.loaded
                      ? "Create a new chat to get started."
                      : "Select and load a model from the sidebar to begin."}
                  </p>
                </div>
              </div>
            ) : (
              <>
                {/* Status bar */}
                <div className="flex items-center justify-between border-b border-slate-200/80 bg-white/72 px-6 py-3 shrink-0 backdrop-blur-xl">
                  <div className="flex items-center gap-2">
                    <span className={`size-2 rounded-full transition-colors duration-500 ${
                      status === "connected" ? "bg-teal-500" :
                      status === "connecting" ? "bg-amber-500 animate-pulse" :
                      "bg-slate-300"
                    }`} />
                    <span className="text-[11px] font-medium text-slate-500">
                      {status === "connected" ? "Connected" :
                       status === "connecting" ? "Connecting..." : "Disconnected"}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    {hasPendingApproval && (
                      <span className="text-[11px] text-amber-600 font-semibold flex items-center gap-1.5">
                        <span className="size-1.5 rounded-full bg-amber-500 animate-pulse" />
                        Awaiting approval
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={() => setImportanceOpen(true)}
                      className="rounded-full bg-indigo-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-indigo-700 ring-1 ring-indigo-200 transition-all hover:bg-indigo-100 hover:text-indigo-800"
                      title="Future-attention token importance is captured for chat turns"
                    >
                      Token heat {importanceViews.length ? `(${importanceViews.length})` : ""}
                    </button>
                    <button
                      type="button"
                      onClick={() => setContextOpen((value) => !value)}
                      className={`rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] transition-all ${
                        contextOpen
                          ? "bg-teal-50 text-teal-700 ring-1 ring-teal-200"
                          : "bg-slate-100 text-slate-500 hover:bg-slate-200 hover:text-slate-900"
                      }`}
                      title="Insert text directly into the model context without generating"
                    >
                      Context {contextOpen ? "open" : "insert"}
                    </button>
                    {streaming && !hasPendingApproval && (
                      <div className="flex items-center gap-2 text-[11px] text-blue-600">
                        <span className="flex gap-0.5">
                          <span className="size-1 rounded-full bg-blue-500 animate-bounce [animation-delay:0ms]" />
                          <span className="size-1 rounded-full bg-blue-500 animate-bounce [animation-delay:150ms]" />
                          <span className="size-1 rounded-full bg-blue-500 animate-bounce [animation-delay:300ms]" />
                        </span>
                        {tokenImportanceEnabled ? "Generating + capturing attention" : "Generating"}
                      </div>
                    )}
                  </div>
                </div>

                {/* Messages */}
                <div ref={scrollAreaRef} className="flex-1 overflow-y-auto">
                  <div className="mx-auto max-w-4xl px-6 py-7 space-y-5">
                    {messages.length === 0 && !streaming && (
                      <div className="text-center py-20">
                        <p className="text-slate-500 text-sm">Send a message to start the conversation.</p>
                      </div>
                    )}
                    {messages.map((m, i) => (
                      <ChatMessage
                        key={i}
                        message={m}
                        isStreaming={streaming && i === messages.length - 1 && m.role === "assistant"}
                        onToolApproval={handleToolApproval}
                      />
                    ))}
                    <div ref={bottomRef} className="h-1" />
                  </div>
                </div>

                {contextOpen && (
                  <ContextInsertPanel onInsert={handleContextInsert} disabled={!isReady} />
                )}
                <ChatInput onSend={handleSend} disabled={!isReady} />
              </>
            )}
          </main>

          {/* Dev panel */}
          {devOpen && (
            <div className="w-[min(100%,520px)] min-w-[340px] max-w-[50vw] shrink-0 border-l border-slate-200/80">
              <DevPanel
                conversationId={activeId}
                eventLog={eventLog}
                modelInfo={models}
                onClearLog={clearLog}
              />
            </div>
          )}
        </div>
      </div>
      {importanceOpen && (
        <TokenImportanceModal
          views={importanceViews}
          latest={latestImportance}
          streaming={streaming}
          onClose={() => setImportanceOpen(false)}
        />
      )}
    </div>
  );
}

// ----- Segment-based event reducer ----- //
function applyEvent(messages: Message[], event: AgentEvent): Message[] {
  const copy = messages.map((m) => ({ ...m, segments: [...m.segments] }));

  const ensureAssistant = (): Message => {
    const last = copy[copy.length - 1];
    if (last && last.role === "assistant") return last;
    const msg: Message = { role: "assistant", segments: [] };
    copy.push(msg);
    return msg;
  };

  const lastSegOfType = (msg: Message, type: string) => {
    for (let i = msg.segments.length - 1; i >= 0; i--) {
      if (msg.segments[i].type === type) return msg.segments[i];
    }
    return null;
  };

  switch (event.type) {
    case "thinking_delta": {
      const msg = ensureAssistant();
      const seg = lastSegOfType(msg, "thinking");
      if (seg && seg.type === "thinking" && msg.segments[msg.segments.length - 1] === seg) {
        msg.segments = msg.segments.map((s) =>
          s === seg ? { ...s, content: s.content + (event.data as string) } : s,
        );
      } else {
        msg.segments = [...msg.segments, { type: "thinking", content: event.data as string }];
      }
      break;
    }

    case "text_delta": {
      const msg = ensureAssistant();
      const last = msg.segments[msg.segments.length - 1];
      if (last && last.type === "text") {
        msg.segments = msg.segments.map((s, i) =>
          i === msg.segments.length - 1 && s.type === "text"
            ? { ...s, content: s.content + (event.data as string) }
            : s,
        );
      } else {
        msg.segments = [...msg.segments, { type: "text", content: event.data as string }];
      }
      break;
    }

    case "text_final": {
      const msg = ensureAssistant();
      const cleanText = event.data as string;
      let found = false;
      msg.segments = msg.segments.map((s) => {
        if (!found && s.type === "text") {
          found = true;
          return { ...s, content: cleanText };
        }
        return s;
      });
      if (!found && cleanText) {
        msg.segments = [...msg.segments, { type: "text", content: cleanText }];
      }
      // Remove empty text segments (text_final might be "")
      if (!cleanText) {
        msg.segments = msg.segments.filter((s) => !(s.type === "text" && !s.content));
      }
      break;
    }

    case "tool_call_pending": {
      const msg = ensureAssistant();
      const tc = event.data as { id: string; name: string; arguments: Record<string, unknown> };
      msg.segments = [
        ...msg.segments,
        { type: "tool_call", id: tc.id, name: tc.name, arguments: tc.arguments, status: "pending" as const },
      ];
      break;
    }

    case "tool_result": {
      const msg = ensureAssistant();
      const tr = event.data as { id: string; name: string; output: string };
      msg.segments = msg.segments.map((s) =>
        s.type === "tool_call" && s.id === tr.id
          ? { ...s, status: "done" as const, output: tr.output }
          : s,
      );
      break;
    }

    case "tool_rejected": {
      const msg = ensureAssistant();
      const rej = event.data as { id: string; name: string };
      msg.segments = msg.segments.map((s) =>
        s.type === "tool_call" && s.id === rej.id ? { ...s, status: "rejected" as const } : s,
      );
      break;
    }

    case "token_importance": {
      const msg = ensureAssistant();
      type RawImportancePayload = {
        tokens?: { text: string; score?: number; importance?: number; id?: number | string }[];
        label?: string;
        method?: string;
        observations?: number;
        target?: string;
      };
      const eventPayload = event.data as RawImportancePayload & { segments?: RawImportancePayload[] };
      const payloads = Array.isArray(eventPayload.segments) ? eventPayload.segments : [eventPayload];
      for (const payload of payloads) {
        const tokens = Array.isArray(payload.tokens)
          ? payload.tokens.map((t) => ({
              text: String(t.text ?? ""),
              score: Number(t.score ?? t.importance ?? 0),
              id: t.id,
            }))
          : [];
        if (tokens.length > 0) {
          const target = payload.target === "thinking" ? "thinking" : "text";
          let attached = false;
          msg.segments = msg.segments.map((s) => {
            if (!attached && s.type === target) {
              attached = true;
              return {
                ...s,
                importance: {
                  tokens,
                  label: payload.label,
                  method: payload.method,
                  observations: payload.observations,
                },
              };
            }
            return s;
          });
          if (!attached) {
            msg.segments = [...msg.segments, { type: "token_importance", tokens, label: payload.label }];
          }
        }
      }
      break;
    }

    case "context_inserted": {
      const payload = event.data as { content?: string; label?: string; chars?: number };
      copy.push({
        role: "user",
        segments: [{
          type: "context_insert",
          content: String(payload.content ?? ""),
          label: payload.label,
          chars: Number(payload.chars ?? String(payload.content ?? "").length),
        }],
      });
      break;
    }

    case "error": {
      const msg = ensureAssistant();
      const errText = typeof event.data === "string" ? event.data : JSON.stringify(event.data);
      msg.error = errText;
      break;
    }

    case "gen_stats":
      break;

    case "done":
      break;
  }

  return copy;
}

function collectImportanceViews(messages: Message[]): ImportanceView[] {
  const views: ImportanceView[] = [];
  messages.forEach((message, messageIndex) => {
    if (message.role !== "assistant") return;
    message.segments.forEach((segment, segmentIndex) => {
      if (
        (segment.type === "thinking" || segment.type === "text") &&
        segment.importance?.tokens?.length
      ) {
        views.push({
          id: `${messageIndex}-${segmentIndex}-${segment.type}`,
          messageIndex,
          segmentKind: segment.type,
          payload: segment.importance,
        });
      }
      if (segment.type === "token_importance" && segment.tokens.length) {
        views.push({
          id: `${messageIndex}-${segmentIndex}-token_importance`,
          messageIndex,
          segmentKind: "token_importance",
          payload: segment,
        });
      }
    });
  });
  return views;
}

function TokenImportanceModal({
  views,
  latest,
  streaming,
  onClose,
}: {
  views: ImportanceView[];
  latest?: ImportanceView;
  streaming: boolean;
  onClose: () => void;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(latest?.id ?? null);
  const selected = views.find((view) => view.id === selectedId) ?? latest ?? views[0];

  useEffect(() => {
    if (!selectedId && latest) {
      setSelectedId(latest.id);
    }
  }, [latest, selectedId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-5 py-6 backdrop-blur-sm">
      <div className="flex h-[min(86vh,820px)] w-[min(96vw,1120px)] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl shadow-slate-950/20">
        <aside className="w-72 shrink-0 border-r border-slate-200 bg-slate-50/80 p-4">
          <div className="mb-4">
            <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-indigo-600">Token Heat</div>
            <h2 className="mt-1 text-base font-semibold text-slate-950">Attention Importance</h2>
            <p className="mt-1 text-xs leading-relaxed text-slate-500">
              Actual tokenizer pieces scored from inference attention capture.
            </p>
          </div>

          {streaming && (
            <div className="mb-3 rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-700">
              Generating and capturing attention...
            </div>
          )}

          <div className="space-y-1 overflow-y-auto pr-1">
            {views.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-white px-3 py-4 text-xs text-slate-500">
                No token-importance payloads yet. Send a message and reopen this view when generation finishes.
              </div>
            ) : (
              views.map((view) => (
                <button
                  key={view.id}
                  type="button"
                  onClick={() => setSelectedId(view.id)}
                  className={`w-full rounded-xl px-3 py-2 text-left text-xs transition-all ${
                    selected?.id === view.id
                      ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/15"
                      : "bg-white text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                  }`}
                >
                  <div className="font-semibold">
                    Message {view.messageIndex + 1} / {view.segmentKind === "thinking" ? "Thoughts" : "Response"}
                  </div>
                  <div className={selected?.id === view.id ? "text-indigo-100" : "text-slate-400"}>
                    {view.payload.tokens.length.toLocaleString()} tokens
                    {view.payload.observations ? ` / ${view.payload.observations.toLocaleString()} obs` : ""}
                  </div>
                </button>
              ))
            )}
          </div>
        </aside>

        <section className="flex min-w-0 flex-1 flex-col">
          <header className="flex items-center justify-between gap-4 border-b border-slate-200 px-5 py-4">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                {selected ? `Message ${selected.messageIndex + 1} / ${selected.segmentKind}` : "No selection"}
              </div>
              <h3 className="mt-1 text-sm font-semibold text-slate-950">
                {selected?.payload.label || "Token importance"}
              </h3>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-200 hover:text-slate-950"
            >
              Close
            </button>
          </header>

          <div className="min-h-0 flex-1 overflow-y-auto p-5">
            {selected ? (
              <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-5">
                <TokenImportance payload={selected.payload} />
              </div>
            ) : (
              <div className="grid h-full place-items-center text-sm text-slate-500">
                No captured token importance yet.
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function ContextInsertPanel({
  onInsert,
  disabled,
}: {
  onInsert: (content: string, label?: string) => void;
  disabled?: boolean;
}) {
  const [label, setLabel] = useState("Manual context insert");
  const [value, setValue] = useState("");
  const [repeat, setRepeat] = useState(1);

  const payload = Array.from({ length: Math.max(1, repeat) }, (_, i) => {
    if (repeat <= 1) return value;
    return `[chunk ${i + 1}/${repeat}]\n${value}`;
  }).join("\n\n");
  const approxTokens = Math.ceil(payload.length / 4);

  const insert = () => {
    const trimmed = payload.trim();
    if (!trimmed || disabled) return;
    onInsert(trimmed, label.trim() || "Manual context insert");
    setValue("");
    setRepeat(1);
  };

  const fillSample = () => {
    setValue(
      "Synthetic context pressure block. This text is intentionally inserted before the next user turn so the model must carry it in the active prompt. Change the repeat count to probe context length, latency, and failure behavior.",
    );
  };

  return (
    <div className="border-t border-slate-200/80 bg-white/82 px-6 py-3 backdrop-blur-xl">
      <div className="mx-auto max-w-4xl space-y-2">
        <div className="flex items-center gap-2">
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            disabled={disabled}
            className="h-8 w-56 rounded-lg border border-slate-200 bg-white px-3 text-[12px] text-slate-700 outline-none focus:border-teal-300 disabled:opacity-40"
            aria-label="Context insert label"
          />
          <input
            type="number"
            min={1}
            max={200}
            value={repeat}
            onChange={(e) => setRepeat(Math.max(1, Math.min(200, Number(e.target.value) || 1)))}
            disabled={disabled}
            className="h-8 w-20 rounded-lg border border-slate-200 bg-white px-2 text-[12px] tabular-nums text-slate-700 outline-none focus:border-teal-300 disabled:opacity-40"
            aria-label="Repeat count"
          />
          <button
            type="button"
            onClick={fillSample}
            disabled={disabled}
            className="h-8 rounded-lg bg-slate-100 px-3 text-[11px] font-semibold text-slate-600 hover:bg-slate-200 disabled:opacity-40"
          >
            Sample
          </button>
          <div className="ml-auto text-[10px] tabular-nums text-slate-400">
            {payload.length.toLocaleString()} chars / ~{approxTokens.toLocaleString()} tokens
          </div>
        </div>
        <div className="flex gap-2">
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            disabled={disabled}
            rows={3}
            placeholder="Insert text into the conversation context without asking the model to answer yet..."
            className="min-h-20 flex-1 resize-y rounded-xl border border-slate-200 bg-white px-3 py-2 font-mono text-[12px] leading-relaxed text-slate-700 outline-none focus:border-teal-300 disabled:opacity-40"
          />
          <button
            type="button"
            onClick={insert}
            disabled={disabled || !payload.trim()}
            className="w-24 rounded-xl bg-teal-600 text-[11px] font-semibold uppercase tracking-[0.14em] text-white shadow-lg shadow-teal-600/15 hover:bg-teal-500 disabled:pointer-events-none disabled:opacity-25"
          >
            Insert
          </button>
        </div>
      </div>
    </div>
  );
}
