import { useState } from "react";

type Props = {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  status: "pending" | "running" | "done" | "rejected";
  output?: string;
  onApproval?: (id: string, approved: boolean) => void;
};

export default function ToolCall({ id, name, arguments: args, status, output, onApproval }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="my-1.5 overflow-hidden rounded-xl border border-slate-200 bg-white/78 shadow-sm transition-all duration-200">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-3 py-2.5 text-left transition-colors duration-150
                   hover:bg-slate-50"
      >
        <span className="select-none text-slate-400 text-[10px] transition-transform duration-200"
              style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}>&#9654;</span>
        <span className="font-mono text-[11px] font-semibold text-blue-700">{name}</span>
        <span className="font-mono text-[11px] text-slate-400 truncate flex-1">{summarizeArgs(args)}</span>

        {status === "pending" && (
          <span className="shrink-0 text-[10px] font-semibold text-amber-600 uppercase tracking-wider">
            awaiting
          </span>
        )}
        {status === "running" && (
          <span className="shrink-0 size-3 rounded-full border-[1.5px] border-slate-300 border-t-blue-500 animate-spin" />
        )}
        {status === "done" && (
          <span className="shrink-0 text-teal-600">
            <svg className="size-3.5" viewBox="0 0 16 16" fill="currentColor">
              <path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z"/>
            </svg>
          </span>
        )}
        {status === "rejected" && (
          <span className="shrink-0 text-[10px] font-semibold text-red-600 uppercase tracking-wider">
            rejected
          </span>
        )}
      </button>

      {/* Approval bar */}
      {status === "pending" && onApproval && (
        <div className="flex items-center gap-2 border-t border-amber-200 bg-amber-50/70 px-3 py-2">
          <span className="text-[11px] text-slate-600 flex-1">Allow this tool call?</span>
          <button
            onClick={(e) => { e.stopPropagation(); onApproval(id, true); }}
            className="rounded-md bg-teal-600 px-3 py-1 text-[11px] font-semibold text-white
                       hover:bg-teal-500 transition-colors active:scale-95"
          >
            Approve
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onApproval(id, false); }}
            className="rounded-md bg-white px-3 py-1 text-[11px] font-semibold text-slate-600 ring-1 ring-slate-200
                       hover:bg-slate-50 transition-colors active:scale-95"
          >
            Reject
          </button>
        </div>
      )}

      {/* Expandable details */}
      <div className="grid transition-all duration-200"
           style={{ gridTemplateRows: open ? "1fr" : "0fr" }}>
        <div className="overflow-hidden">
          <div className="border-t border-slate-200 px-3 py-2.5 space-y-2.5">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Args</div>
              <pre className="whitespace-pre-wrap font-mono text-[11px] text-slate-600 bg-slate-50
                              rounded-md px-2.5 py-2 overflow-x-auto leading-relaxed">
                {JSON.stringify(args, null, 2)}
              </pre>
            </div>
            {output != null && (
              <div>
                <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Output</div>
                <pre className="whitespace-pre-wrap font-mono text-[11px] text-slate-600 bg-slate-50
                                rounded-md px-2.5 py-2 max-h-60 overflow-auto leading-relaxed">
                  {output}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function summarizeArgs(args: Record<string, unknown>): string {
  const entries = Object.entries(args);
  if (entries.length === 0) return "";
  const [key, val] = entries[0];
  const str = typeof val === "string" ? val : JSON.stringify(val);
  const truncated = str.length > 50 ? str.slice(0, 50) + "..." : str;
  const suffix = entries.length > 1 ? ` +${entries.length - 1}` : "";
  return `${key}=${truncated}${suffix}`;
}
