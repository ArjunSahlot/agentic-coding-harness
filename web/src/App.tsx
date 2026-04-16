import { useCallback, useEffect, useRef, useState } from "react";
import ChatInput from "./components/ChatInput.tsx";
import ChatMessage, { type Message, type Segment, type ToolCallSegment } from "./components/ChatMessage.tsx";
import DevPanel from "./components/DevPanel.tsx";
import { useWebSocket, type AgentEvent } from "./hooks/useWebSocket.ts";

type ConvSummary = { id: string; title: string };
type ModelInfo = { models: string[]; loaded: boolean; current: string | null; quantization?: string | null };

export default function App() {
  const [models, setModels] = useState<ModelInfo>({ models: [], loaded: false, current: null });
  const [conversations, setConversations] = useState<ConvSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [loadingModel, setLoadingModel] = useState(false);
  const [quantMode, setQuantMode] = useState<string>("none");
  const [devOpen, setDevOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  const onEvent = useCallback((event: AgentEvent) => {
    setMessages((prev) => applyEvent(prev, event));
    if (event.type === "done" || event.type === "error") {
      setStreaming(false);
    }
  }, []);

  const { status, send, sendToolApproval, eventLog, clearLog } = useWebSocket(activeId, onEvent);

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

  // Fetch models + conversations on mount
  useEffect(() => {
    fetch("/api/models").then((r) => r.json()).then(setModels).catch(() => {});
    fetch("/api/conversations").then((r) => r.json()).then((d) => setConversations(d.conversations)).catch(() => {});
  }, []);

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
      send(text);
    },
    [send],
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

  const hasPendingApproval = messages.some((m) =>
    m.segments.some((s) => s.type === "tool_call" && s.status === "pending"),
  );
  const isReady = status === "connected" && !streaming && !hasPendingApproval;

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <aside className="flex w-60 shrink-0 flex-col border-r border-zinc-800/80 bg-zinc-950">
        <div className="flex items-center gap-2 px-4 py-4 border-b border-zinc-800/80">
          <div className="size-2 rounded-full bg-violet-500" />
          <h1 className="text-xs font-semibold tracking-widest uppercase text-zinc-300">Harness</h1>
        </div>

        {/* Model selector */}
        <div className="px-3 py-3 border-b border-zinc-800/80 space-y-1.5">
          <div className="text-[10px] font-medium uppercase tracking-wider text-zinc-500 px-1">Model</div>
          {models.models.length === 0 ? (
            <div className="text-xs text-zinc-600 px-1">No models found</div>
          ) : (
            models.models.map((m) => (
              <button
                key={m}
                onClick={() => loadModel(m)}
                disabled={loadingModel}
                className={`flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-xs transition-all duration-150
                  ${models.current === m
                    ? "bg-violet-500/10 text-violet-300 ring-1 ring-violet-500/20"
                    : "text-zinc-400 hover:bg-zinc-800/70 hover:text-zinc-200"
                  } disabled:opacity-40`}
              >
                <span className="truncate flex-1">{m}</span>
                {models.current === m && (
                  <span className="flex items-center gap-1 shrink-0">
                    {models.quantization && (
                      <span className="text-[9px] font-medium text-emerald-400/70 uppercase">{models.quantization}</span>
                    )}
                    <span className="size-1.5 rounded-full bg-emerald-400" />
                  </span>
                )}
              </button>
            ))
          )}
          <div className="flex items-center gap-1.5 px-1 pt-1">
            <span className="text-[10px] text-zinc-600 shrink-0">Quant:</span>
            {(["none", "8bit", "4bit"] as const).map((q) => (
              <button
                key={q}
                onClick={() => setQuantMode(q)}
                className={`rounded px-1.5 py-0.5 text-[10px] font-medium transition-all duration-150
                  ${quantMode === q
                    ? "bg-violet-500/15 text-violet-300 ring-1 ring-violet-500/25"
                    : "text-zinc-600 hover:text-zinc-400 hover:bg-zinc-800/60"
                  }`}
              >
                {q === "none" ? "FP16" : q.toUpperCase()}
              </button>
            ))}
          </div>
          {loadingModel && (
            <div className="flex items-center gap-2 px-1 text-[11px] text-zinc-500">
              <span className="inline-block size-3 rounded-full border-2 border-zinc-600 border-t-violet-400 animate-spin" />
              Loading{quantMode !== "none" ? ` (${quantMode})` : ""}...
            </div>
          )}
        </div>

        {/* Conversations */}
        <div className="flex-1 overflow-y-auto px-3 py-3 space-y-0.5">
          <div className="text-[10px] font-medium uppercase tracking-wider text-zinc-500 px-1 mb-2">Chats</div>
          {conversations.map((c) => (
            <button
              key={c.id}
              onClick={() => { setActiveId(c.id); }}
              className={`block w-full rounded-md px-2.5 py-2 text-left text-xs transition-all duration-150 truncate
                ${activeId === c.id
                  ? "bg-zinc-800 text-zinc-100"
                  : "text-zinc-500 hover:bg-zinc-800/50 hover:text-zinc-300"
                }`}
            >
              {c.title}
            </button>
          ))}
          {conversations.length === 0 && (
            <p className="text-[11px] text-zinc-600 px-1">No chats yet</p>
          )}
        </div>

        <div className="p-3 space-y-1.5 border-t border-zinc-800/80">
          <button
            onClick={newConversation}
            disabled={!models.loaded}
            className="w-full rounded-lg bg-zinc-800/80 py-2.5 text-xs font-medium text-zinc-300
                       transition-all duration-150 hover:bg-zinc-700 active:scale-[0.98]
                       disabled:opacity-25 disabled:pointer-events-none"
          >
            + New Chat
          </button>
          <button
            onClick={() => setDevOpen((v) => !v)}
            className={`w-full rounded-lg py-2 text-[10px] font-medium uppercase tracking-wider transition-all duration-150
              ${devOpen
                ? "bg-violet-500/10 text-violet-400 ring-1 ring-violet-500/20"
                : "bg-zinc-900 text-zinc-600 hover:text-zinc-400 hover:bg-zinc-800/50"
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
          <main className={`flex flex-1 flex-col bg-zinc-950 ${devOpen ? "border-r border-zinc-800/60" : ""}`}>
            {activeId === null ? (
              <div className="flex flex-1 items-center justify-center">
                <div className="text-center space-y-3 max-w-xs">
                  <div className="text-zinc-600 text-4xl">&#x2756;</div>
                  <p className="text-zinc-400 text-sm leading-relaxed">
                    {models.loaded
                      ? "Create a new chat to get started."
                      : "Select and load a model from the sidebar to begin."}
                  </p>
                </div>
              </div>
            ) : (
              <>
                {/* Status bar */}
                <div className="flex items-center justify-between px-6 py-2 border-b border-zinc-800/60 shrink-0">
                  <div className="flex items-center gap-2">
                    <span className={`size-1.5 rounded-full transition-colors duration-500 ${
                      status === "connected" ? "bg-emerald-400" :
                      status === "connecting" ? "bg-amber-400 animate-pulse" :
                      "bg-zinc-600"
                    }`} />
                    <span className="text-[11px] text-zinc-500">
                      {status === "connected" ? "Connected" :
                       status === "connecting" ? "Connecting..." : "Disconnected"}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    {hasPendingApproval && (
                      <span className="text-[11px] text-amber-400 font-medium flex items-center gap-1.5">
                        <span className="size-1.5 rounded-full bg-amber-400 animate-pulse" />
                        Awaiting approval
                      </span>
                    )}
                    {streaming && !hasPendingApproval && (
                      <div className="flex items-center gap-2 text-[11px] text-violet-400">
                        <span className="flex gap-0.5">
                          <span className="size-1 rounded-full bg-violet-400 animate-bounce [animation-delay:0ms]" />
                          <span className="size-1 rounded-full bg-violet-400 animate-bounce [animation-delay:150ms]" />
                          <span className="size-1 rounded-full bg-violet-400 animate-bounce [animation-delay:300ms]" />
                        </span>
                        Generating
                      </div>
                    )}
                  </div>
                </div>

                {/* Messages */}
                <div ref={scrollAreaRef} className="flex-1 overflow-y-auto">
                  <div className="mx-auto max-w-3xl px-6 py-6 space-y-5">
                    {messages.length === 0 && !streaming && (
                      <div className="text-center py-20">
                        <p className="text-zinc-600 text-sm">Send a message to start the conversation.</p>
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

                <ChatInput onSend={handleSend} disabled={!isReady} />
              </>
            )}
          </main>

          {/* Dev panel */}
          {devOpen && (
            <div className="w-[min(100%,480px)] min-w-[320px] max-w-[50vw] shrink-0 border-l border-zinc-800/60">
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
