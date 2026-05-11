import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { EventLogEntry } from "../hooks/useWebSocket.ts";

type Tab =
  | "summary"
  | "events"
  | "generation"
  | "tokens"
  | "raw"
  | "runtime"
  | "model";

type Props = {
  conversationId: string | null;
  eventLog: EventLogEntry[];
  modelInfo: { loaded: boolean; current: string | null };
  onClearLog: () => void;
};

const EVENT_COLORS: Record<string, string> = {
  thinking_delta: "text-sky-600",
  text_delta: "text-slate-600",
  text_final: "text-teal-600",
  gen_stats: "text-blue-600",
  tool_call_pending: "text-amber-600",
  tool_result: "text-teal-600",
  tool_rejected: "text-red-600",
  token_importance: "text-indigo-600",
  error: "text-red-700",
  done: "text-slate-500",
};

function formatBytes(n: number | undefined | null): string {
  if (n == null || Number.isNaN(n)) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KiB`;
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MiB`;
  return `${(n / 1024 ** 3).toFixed(2)} GiB`;
}

function formatNum(n: number | undefined | null): string {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toLocaleString();
}

export default function DevPanel({ conversationId, eventLog, modelInfo, onClearLog }: Props) {
  const [tab, setTab] = useState<Tab>("summary");
  const [rawMessages, setRawMessages] = useState<unknown[]>([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const [runtime, setRuntime] = useState<Record<string, unknown> | null>(null);
  const [modelPayload, setModelPayload] = useState<Record<string, unknown> | null>(null);
  const [tokenRows, setTokenRows] = useState<
    { index: number; role: string; chars: number; tokens_approx: number }[]
  >([]);
  const [tokenTotal, setTokenTotal] = useState(0);
  const [tokenizeInput, setTokenizeInput] = useState("");
  const [tokenizeResult, setTokenizeResult] = useState<Record<string, unknown> | null>(null);
  const [tokenizeLoading, setTokenizeLoading] = useState(false);
  const logEndRef = useRef<HTMLDivElement>(null);

  const genStatsEvents = useMemo(
    () =>
      eventLog.filter((e) => e.event.type === "gen_stats").map((e) => e.event.data as Record<string, unknown>),
    [eventLog],
  );

  const eventCounts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const { event } of eventLog) {
      c[event.type] = (c[event.type] || 0) + 1;
    }
    return c;
  }, [eventLog]);

  const totalsFromGen = useMemo(() => {
    let prompt = 0;
    let completion = 0;
    let forwards = 0;
    for (const d of genStatsEvents) {
      prompt += Number(d.prompt_tokens) || 0;
      completion += Number(d.completion_tokens) || 0;
      forwards += Number(d.forward_passes) || 0;
    }
    return {
      rounds: genStatsEvents.length,
      sumPromptTokens: prompt,
      sumCompletionTokens: completion,
      sumForwardPasses: forwards,
    };
  }, [genStatsEvents]);

  useEffect(() => {
    if (!conversationId) return;
    if (tab === "raw") {
      fetch(`/api/conversations/${conversationId}/raw`)
        .then((r) => r.json())
        .then((d) => setRawMessages(d.messages || []))
        .catch(() => {});
    }
  }, [conversationId, tab, eventLog.length]);

  useEffect(() => {
    if (!conversationId || tab !== "tokens") return;
    fetch(`/api/conversations/${conversationId}/token_stats`)
      .then((r) => r.json())
      .then((d) => {
        setTokenRows(d.messages || []);
        setTokenTotal(d.total_tokens_approx ?? 0);
      })
      .catch(() => {});
  }, [conversationId, tab, eventLog.length]);

  const fetchRuntime = useCallback(() => {
    fetch("/api/dev/runtime")
      .then((r) => r.json())
      .then(setRuntime)
      .catch(() => setRuntime({ error: "fetch failed" }));
  }, []);

  const fetchModel = useCallback(() => {
    fetch("/api/dev/model")
      .then((r) => r.json())
      .then(setModelPayload)
      .catch(() => setModelPayload({ error: "fetch failed" }));
  }, []);

  useEffect(() => {
    if (tab === "runtime") fetchRuntime();
    if (tab === "model") fetchModel();
  }, [tab, fetchRuntime, fetchModel]);

  useEffect(() => {
    if (tab !== "runtime") return;
    const id = window.setInterval(fetchRuntime, 2500);
    return () => clearInterval(id);
  }, [tab, fetchRuntime]);

  useEffect(() => {
    if (autoScroll && tab === "events") {
      logEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [eventLog.length, autoScroll, tab]);

  const refreshRaw = useCallback(() => {
    if (!conversationId) return;
    fetch(`/api/conversations/${conversationId}/raw`)
      .then((r) => r.json())
      .then((d) => setRawMessages(d.messages || []))
      .catch(() => {});
  }, [conversationId]);

  const runTokenize = useCallback(() => {
    if (!tokenizeInput.trim()) return;
    setTokenizeLoading(true);
    const q = new URLSearchParams({ text: tokenizeInput.slice(0, 8000) });
    fetch(`/api/dev/tokenize?${q}`)
      .then((r) => r.json())
      .then(setTokenizeResult)
      .finally(() => setTokenizeLoading(false));
  }, [tokenizeInput]);

  const tabs: { id: Tab; label: string }[] = [
    { id: "summary", label: "Summary" },
    { id: "events", label: "Events" },
    { id: "generation", label: "Generation" },
    { id: "tokens", label: "Tokens" },
    { id: "raw", label: "Raw" },
    { id: "runtime", label: "Runtime" },
    { id: "model", label: "Model" },
  ];

  return (
    <div className="flex h-full min-w-0 flex-col bg-white/86 text-[11px] font-mono text-slate-700 backdrop-blur-xl">
      <div className="flex flex-wrap items-center gap-1 border-b border-slate-200/80 px-2 py-2 shrink-0">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`rounded-md px-2 py-1.5 text-[9px] font-semibold uppercase tracking-wider transition-colors
              ${tab === t.id ? "bg-slate-950 text-white shadow-sm" : "text-slate-500 hover:text-slate-900 hover:bg-slate-100"}`}
          >
            {t.label}
          </button>
        ))}
        <div className="flex-1 min-w-2" />
        {tab === "events" && (
          <>
            <button
              type="button"
              onClick={() => setAutoScroll(!autoScroll)}
              className={`px-2 py-1 text-[9px] uppercase tracking-wider rounded
                ${autoScroll ? "text-teal-600" : "text-slate-400"}`}
            >
              auto-scroll
            </button>
            <button type="button" onClick={onClearLog} className="px-2 py-1 text-[9px] text-slate-400 hover:text-slate-900">
              Clear
            </button>
          </>
        )}
        {tab === "raw" && (
          <button type="button" onClick={refreshRaw} className="px-2 py-1 text-[9px] text-slate-400 hover:text-slate-900">
            Refresh
          </button>
        )}
        {tab === "runtime" && (
          <button type="button" onClick={fetchRuntime} className="px-2 py-1 text-[9px] text-slate-400 hover:text-slate-900">
            Refresh
          </button>
        )}
        {tab === "model" && (
          <button type="button" onClick={fetchModel} className="px-2 py-1 text-[9px] text-slate-400 hover:text-slate-900">
            Refresh
          </button>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-4">
        {tab === "summary" && (
          <div className="space-y-4">
            <section>
              <h3 className="text-[10px] uppercase tracking-wider text-zinc-600 mb-2">Session</h3>
              <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-zinc-400">
                <dt className="text-zinc-600">Model</dt>
                <dd className="text-slate-800">{modelInfo.current || "—"}</dd>
                <dt className="text-zinc-600">Loaded</dt>
                <dd>{modelInfo.loaded ? <span className="text-emerald-400/80">yes</span> : <span className="text-zinc-600">no</span>}</dd>
                <dt className="text-zinc-600">Conversation</dt>
                <dd className="truncate text-slate-800">{conversationId || "—"}</dd>
                <dt className="text-zinc-600">Events logged</dt>
                <dd>{eventLog.length.toLocaleString()}</dd>
                <dt className="text-zinc-600">Generation rounds</dt>
                <dd>{totalsFromGen.rounds}</dd>
                <dt className="text-zinc-600">Σ prompt tok</dt>
                <dd>{formatNum(totalsFromGen.sumPromptTokens)}</dd>
                <dt className="text-zinc-600">Σ completion tok</dt>
                <dd>{formatNum(totalsFromGen.sumCompletionTokens)}</dd>
                <dt className="text-zinc-600">Σ forward passes</dt>
                <dd>{formatNum(totalsFromGen.sumForwardPasses)}</dd>
              </dl>
            </section>

            <section>
              <h3 className="text-[10px] uppercase tracking-wider text-zinc-600 mb-2">Event type counts</h3>
              <div className="flex flex-wrap gap-1">
                {Object.entries(eventCounts)
                  .sort((a, b) => b[1] - a[1])
                  .map(([k, v]) => (
                    <span
                      key={k}
                      className={`rounded px-1.5 py-0.5 text-[10px] ${EVENT_COLORS[k] || "text-zinc-400"} bg-zinc-900/80`}
                    >
                      {k}: {v}
                    </span>
                  ))}
                {Object.keys(eventCounts).length === 0 && (
                  <span className="text-zinc-600">No events yet</span>
                )}
              </div>
            </section>

            {genStatsEvents.length > 0 && (
              <section>
                <h3 className="text-[10px] uppercase tracking-wider text-zinc-600 mb-2">Last generation</h3>
                <pre className="text-[10px] text-zinc-500 bg-zinc-900/40 rounded p-2 overflow-x-auto max-h-48">
                  {JSON.stringify(genStatsEvents[genStatsEvents.length - 1], null, 2)}
                </pre>
              </section>
            )}
          </div>
        )}

        {tab === "events" && (
          <div className="space-y-px">
            {eventLog.length === 0 && (
              <div className="text-zinc-600 py-4 text-center">No events yet</div>
            )}
            {eventLog.map((entry, i) => {
              const time = new Date(entry.timestamp);
              const ts = `${time.getHours().toString().padStart(2, "0")}:${time.getMinutes().toString().padStart(2, "0")}:${time.getSeconds().toString().padStart(2, "0")}.${time.getMilliseconds().toString().padStart(3, "0")}`;
              const color = EVENT_COLORS[entry.event.type] || "text-zinc-400";
              const isCompact =
                entry.event.type === "thinking_delta" ||
                entry.event.type === "text_delta";
              const isStats = entry.event.type === "gen_stats";
              const dataStr =
                typeof entry.event.data === "string"
                  ? isCompact
                    ? entry.event.data.replace(/\n/g, "\\n")
                    : entry.event.data
                  : JSON.stringify(entry.event.data);
              const truncated =
                isStats && dataStr.length > 400
                  ? dataStr.slice(0, 400) + "…"
                  : dataStr.length > 200
                    ? dataStr.slice(0, 200) + "…"
                    : dataStr;

              return (
                <div key={i} className="flex gap-2 py-0.5 hover:bg-zinc-900/50 px-1 rounded group">
                  <span className="text-zinc-700 shrink-0 tabular-nums w-[88px]">{ts}</span>
                  <span className={`shrink-0 w-[8.5rem] ${color}`}>{entry.event.type}</span>
                  <span className="text-zinc-500 truncate flex-1 min-w-0 group-hover:whitespace-pre-wrap group-hover:text-zinc-400">
                    {truncated}
                  </span>
                </div>
              );
            })}
            <div ref={logEndRef} />
          </div>
        )}

        {tab === "generation" && (
          <div className="space-y-2">
            {genStatsEvents.length === 0 ? (
              <p className="text-zinc-600 py-4 text-center">No gen_stats events yet — send a message after loading a model.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-[10px] border-collapse">
                  <thead>
                    <tr className="text-zinc-600 border-b border-zinc-800">
                      <th className="py-1 pr-2">#</th>
                      <th className="py-1 pr-2">round</th>
                      <th className="py-1 pr-2">prompt</th>
                      <th className="py-1 pr-2">new</th>
                      <th className="py-1 pr-2">forwards</th>
                      <th className="py-1 pr-2">stop</th>
                      <th className="py-1 pr-2">T</th>
                      <th className="py-1 pr-2">chars</th>
                    </tr>
                  </thead>
                  <tbody className="text-zinc-400">
                    {genStatsEvents.map((d, i) => (
                      <tr key={i} className="border-b border-zinc-800/50 hover:bg-zinc-900/30">
                        <td className="py-1 pr-2 text-zinc-600">{i + 1}</td>
                        <td className="py-1 pr-2">{String(d.agent_round ?? "—")}</td>
                        <td className="py-1 pr-2 tabular-nums">{formatNum(Number(d.prompt_tokens))}</td>
                        <td className="py-1 pr-2 tabular-nums">{formatNum(Number(d.completion_tokens))}</td>
                        <td className="py-1 pr-2 tabular-nums">{formatNum(Number(d.forward_passes))}</td>
                        <td className="py-1 pr-2 text-zinc-500">{String(d.stop_reason ?? "")}</td>
                        <td className="py-1 pr-2">{String(d.temperature ?? "")}</td>
                        <td className="py-1 pr-2 tabular-nums">{formatNum(Number(d.assistant_chars_streamed))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <details className="mt-3 group">
                  <summary className="cursor-pointer text-zinc-600 hover:text-zinc-400 text-[10px] uppercase tracking-wider">
                    Full JSON (all rounds)
                  </summary>
                  <pre className="mt-2 text-[10px] text-zinc-500 bg-zinc-900/40 rounded p-2 overflow-auto max-h-80">
                    {JSON.stringify(genStatsEvents, null, 2)}
                  </pre>
                </details>
              </div>
            )}
          </div>
        )}

        {tab === "tokens" && (
          <div className="space-y-4">
            <section>
              <h3 className="text-[10px] uppercase tracking-wider text-zinc-600 mb-2">
                Conversation messages (tokenizer length)
              </h3>
              {!conversationId ? (
                <p className="text-zinc-600">No conversation selected.</p>
              ) : tokenRows.length === 0 ? (
                <p className="text-zinc-600">No messages or still loading.</p>
              ) : (
                <>
                  <p className="text-zinc-500 mb-2">
                    Total approx tokens (sum of messages):{" "}
                    <span className="text-blue-600 tabular-nums">{formatNum(tokenTotal)}</span>
                  </p>
                  <div className="overflow-x-auto max-h-40 overflow-y-auto">
                    <table className="w-full text-left text-[10px]">
                      <thead>
                        <tr className="text-zinc-600 border-b border-zinc-800">
                          <th className="py-1 pr-2">#</th>
                          <th className="py-1 pr-2">role</th>
                          <th className="py-1 pr-2">chars</th>
                          <th className="py-1 pr-2">tok≈</th>
                        </tr>
                      </thead>
                      <tbody className="text-zinc-400">
                        {tokenRows.map((r) => (
                          <tr key={r.index} className="border-b border-zinc-800/40">
                            <td className="py-0.5 pr-2 text-zinc-600">{r.index}</td>
                            <td className="py-0.5 pr-2">{r.role}</td>
                            <td className="py-0.5 pr-2 tabular-nums">{r.chars}</td>
                            <td className="py-0.5 pr-2 tabular-nums">{r.tokens_approx}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </section>

            <section>
              <h3 className="text-[10px] uppercase tracking-wider text-slate-500 mb-2">Tokenize playground</h3>
              <textarea
                value={tokenizeInput}
                onChange={(e) => setTokenizeInput(e.target.value)}
                placeholder="Paste text to inspect tokenizer output..."
                rows={3}
                className="min-h-[72px] w-full resize-y rounded-lg border border-slate-200 bg-white px-3 py-2 text-[11px] text-slate-800 placeholder-slate-400 shadow-sm outline-none focus:border-blue-200 focus:ring-4 focus:ring-blue-500/10"
              />
              <button
                type="button"
                onClick={runTokenize}
                disabled={tokenizeLoading || !modelInfo.loaded}
                className="mt-2 rounded-md bg-slate-950 px-3 py-1.5 text-[10px] font-semibold text-white hover:bg-blue-600 disabled:opacity-40"
              >
                {tokenizeLoading ? "..." : "Tokenize"}
              </button>
              {tokenizeResult && !("error" in tokenizeResult) && (
                <pre className="mt-2 max-h-56 overflow-auto rounded-lg bg-slate-950 p-2 text-[10px] text-slate-300">
                  {JSON.stringify(tokenizeResult, null, 2)}
                </pre>
              )}
              {tokenizeResult && "error" in tokenizeResult && (
                <p className="mt-2 text-red-600">{String((tokenizeResult as { error: string }).error)}</p>
              )}
            </section>

            {genStatsEvents.length > 0 && (
              <section>
                <h3 className="text-[10px] uppercase tracking-wider text-zinc-600 mb-2">ID preview (last round)</h3>
                <pre className="text-[10px] text-zinc-500 bg-zinc-900/40 rounded p-2 overflow-auto max-h-40">
                  {JSON.stringify(
                    {
                      head: genStatsEvents[genStatsEvents.length - 1].generated_token_ids_head,
                      tail: genStatsEvents[genStatsEvents.length - 1].generated_token_ids_tail,
                      count: genStatsEvents[genStatsEvents.length - 1].generated_token_ids_count,
                    },
                    null,
                    2,
                  )}
                </pre>
              </section>
            )}
          </div>
        )}

        {tab === "raw" && (
          <div>
            {rawMessages.length === 0 ? (
              <div className="text-zinc-600 py-4 text-center">
                {conversationId ? "No messages" : "No conversation selected"}
              </div>
            ) : (
              rawMessages.map((msg, i) => {
                const role = (msg as Record<string, unknown>).role as string;
                const roleColor =
                  role === "system"
                    ? "text-cyan-400/70"
                    : role === "user"
                      ? "text-blue-600"
                      : role === "assistant"
                        ? "text-emerald-400/70"
                        : role === "tool"
                          ? "text-amber-400/70"
                          : "text-zinc-400";
                const raw = JSON.stringify(msg);
                return (
                  <details key={i} className="mb-1 group">
                    <summary className={`cursor-pointer py-1 px-1 rounded hover:bg-zinc-900/50 ${roleColor}`}>
                      <span className="font-semibold">[{i}]</span> {role}
                      <span className="text-zinc-700 ml-2">{raw.length.toLocaleString()} chars</span>
                    </summary>
                    <pre className="whitespace-pre-wrap text-zinc-500 bg-zinc-900/30 rounded p-2 mt-1 mb-2 ml-2 max-h-96 overflow-auto">
                      {JSON.stringify(msg, null, 2)}
                    </pre>
                  </details>
                );
              })
            )}
          </div>
        )}

        {tab === "runtime" && (
          <div className="space-y-2">
            <p className="text-[10px] text-zinc-600">Auto-refresh every 2.5s</p>
            {runtime ? (
              <>
                <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[10px] text-zinc-400 mb-3">
                  <dt className="text-zinc-600">Uptime</dt>
                  <dd>{formatNum(Number(runtime.uptime_seconds))} s</dd>
                  <dt className="text-zinc-600">Python</dt>
                  <dd>{String(runtime.python_version)}</dd>
                  <dt className="text-zinc-600">Torch</dt>
                  <dd>{String(runtime.torch_version ?? "—")}</dd>
                  <dt className="text-zinc-600">CUDA</dt>
                  <dd>{runtime.cuda_available ? "available" : "no"}</dd>
                  {Array.isArray(runtime.cuda_devices) && (runtime.cuda_devices as { name: string }[]).length > 0 && (
                    <>
                      <dt className="text-zinc-600">GPU</dt>
                      <dd className="truncate">
                        {String((runtime.cuda_devices as { name: string }[])[0]?.name)}
                      </dd>
                    </>
                  )}
                  <dt className="text-zinc-600">CUDA mem</dt>
                  <dd>
                    {formatBytes(Number(runtime.cuda_mem_used_bytes))} /{" "}
                    {formatBytes(Number(runtime.cuda_mem_total_bytes))}
                  </dd>
                  <dt className="text-zinc-600">Host RAM</dt>
                  <dd>
                    {formatBytes(Number(runtime.host_mem_available_bytes))} free /{" "}
                    {formatBytes(Number(runtime.host_mem_total_bytes))} total
                    {runtime.host_mem_percent != null && ` (${String(runtime.host_mem_percent)}%)`}
                  </dd>
                  <dt className="text-zinc-600">Process RSS</dt>
                  <dd>{formatBytes(Number(runtime.process_rss_bytes))}</dd>
                </dl>
                <details>
                  <summary className="cursor-pointer text-zinc-600 text-[10px] uppercase tracking-wider">
                    Full JSON
                  </summary>
                  <pre className="mt-2 text-[10px] text-zinc-500 bg-zinc-900/40 rounded p-2 overflow-auto max-h-72">
                    {JSON.stringify(runtime, null, 2)}
                  </pre>
                </details>
              </>
            ) : (
              <p className="text-slate-500">Loading...</p>
            )}
          </div>
        )}

        {tab === "model" && (
          <div className="space-y-2">
            {modelPayload ? (
              modelPayload.loaded === false ? (
                <p className="text-zinc-600">{String(modelPayload.message ?? "Model not loaded")}</p>
              ) : (
                <>
                  <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[10px] text-zinc-400 mb-3">
                    <dt className="text-zinc-600">Class</dt>
                    <dd>{String(modelPayload.model_class)}</dd>
                    <dt className="text-zinc-600">Path</dt>
                    <dd className="truncate text-slate-800">{String(modelPayload.model_path)}</dd>
                    <dt className="text-zinc-600">Params</dt>
                    <dd>{formatNum(Number(modelPayload.parameters_total))}</dd>
                    <dt className="text-zinc-600">Trainable</dt>
                    <dd>{formatNum(Number(modelPayload.parameters_trainable))}</dd>
                    <dt className="text-zinc-600">Tokenizer vocab</dt>
                    <dd>{formatNum(Number((modelPayload.tokenizer as Record<string, unknown>)?.vocab_size))}</dd>
                    <dt className="text-zinc-600">EOS / PAD</dt>
                    <dd>
                      {String((modelPayload.tokenizer as Record<string, unknown>)?.eos_token_id ?? "—")} /{" "}
                      {String((modelPayload.tokenizer as Record<string, unknown>)?.pad_token_id ?? "—")}
                    </dd>
                  </dl>
                  <details open>
                    <summary className="cursor-pointer text-zinc-600 text-[10px] uppercase tracking-wider mb-1">
                      config_summary
                    </summary>
                    <pre className="text-[10px] text-zinc-500 bg-zinc-900/40 rounded p-2 overflow-auto max-h-48">
                      {JSON.stringify(modelPayload.config_summary, null, 2)}
                    </pre>
                  </details>
                  <details className="mt-2">
                    <summary className="cursor-pointer text-zinc-600 text-[10px] uppercase tracking-wider">
                      Full JSON
                    </summary>
                    <pre className="mt-2 text-[10px] text-zinc-500 bg-zinc-900/40 rounded p-2 overflow-auto max-h-64">
                      {JSON.stringify(modelPayload, null, 2)}
                    </pre>
                  </details>
                </>
              )
            ) : (
              <p className="text-slate-500">Loading...</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
