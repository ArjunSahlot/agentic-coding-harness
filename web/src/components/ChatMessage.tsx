import ToolCall from "./ToolCall.tsx";

export type ThinkingSegment = { type: "thinking"; content: string };
export type TextSegment = { type: "text"; content: string };
export type ToolCallSegment = {
  type: "tool_call";
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  status: "pending" | "running" | "done" | "rejected";
  output?: string;
};

export type Segment = ThinkingSegment | TextSegment | ToolCallSegment;

export type Message = {
  role: "user" | "assistant";
  segments: Segment[];
  error?: string;
};

type Props = {
  message: Message;
  isStreaming?: boolean;
  onToolApproval?: (id: string, approved: boolean) => void;
};

function cleanThinking(text: string): string {
  return text.replace(/<\/?think>/g, "").replace(/\n+$/, "").trim();
}

export default function ChatMessage({ message, isStreaming, onToolApproval }: Props) {
  const isUser = message.role === "user";
  const segments = message.segments;

  if (isUser) {
    const text = segments.find((s) => s.type === "text") as TextSegment | undefined;
    return (
      <div className="animate-in flex justify-end">
        <div className="max-w-[min(85%,38rem)] rounded-2xl bg-violet-500/[0.08] border border-violet-500/10
                        text-zinc-100 px-4 py-2.5 text-[13.5px] leading-[1.7] whitespace-pre-wrap">
          {text?.content}
        </div>
      </div>
    );
  }

  const lastSeg = segments[segments.length - 1];
  const isLastText = lastSeg?.type === "text";

  return (
    <div className="animate-in flex justify-start">
      <div className="max-w-[min(90%,44rem)] text-[13.5px] leading-[1.7] text-zinc-300 px-1 py-1 space-y-2">
        {segments.map((seg, i) => {
          const isLast = i === segments.length - 1;

          if (seg.type === "thinking") {
            const cleaned = cleanThinking(seg.content);
            if (!cleaned) return null;
            const isActiveThinking = isStreaming && isLast;
            return (
              <details key={i} className="group" open={isActiveThinking}>
                <summary className="cursor-pointer select-none text-[11px] font-medium text-zinc-500
                                    hover:text-zinc-400 transition-colors duration-150 flex items-center gap-1.5 py-0.5">
                  <svg className="size-3 text-zinc-600 transition-transform duration-200 group-open:rotate-90"
                       viewBox="0 0 16 16" fill="currentColor">
                    <path d="M6.5 3.5l5 4.5-5 4.5V3.5z"/>
                  </svg>
                  {isActiveThinking ? "Thinking..." : "Thought process"}
                </summary>
                <div className="mt-1.5 whitespace-pre-wrap font-mono text-[11px] text-zinc-500/80
                                border-l-2 border-zinc-800 pl-3 ml-0.5 max-h-64 overflow-y-auto leading-relaxed">
                  {cleaned}
                  {isActiveThinking && <span className="typing-cursor" />}
                </div>
              </details>
            );
          }

          if (seg.type === "text") {
            if (!seg.content && !(isStreaming && isLast)) return null;
            return (
              <div key={i} className="whitespace-pre-wrap">
                {seg.content}
                {isStreaming && isLast && isLastText && <span className="typing-cursor" />}
              </div>
            );
          }

          if (seg.type === "tool_call") {
            return (
              <ToolCall
                key={seg.id || i}
                id={seg.id}
                name={seg.name}
                arguments={seg.arguments}
                status={seg.status}
                output={seg.output}
                onApproval={onToolApproval}
              />
            );
          }

          return null;
        })}

        {/* Empty streaming state */}
        {isStreaming && segments.length === 0 && (
          <div className="py-0.5"><span className="typing-cursor" /></div>
        )}

        {message.error && (
          <div className="mt-2 rounded-lg bg-red-500/[0.07] border border-red-500/20 px-3 py-2
                          text-[12px] text-red-400/90 font-mono">
            {message.error}
          </div>
        )}
      </div>
    </div>
  );
}
