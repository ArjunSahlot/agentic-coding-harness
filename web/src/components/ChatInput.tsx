import { useState, useRef, useCallback, type KeyboardEvent } from "react";

type Props = {
  onSend: (message: string) => void;
  disabled?: boolean;
};

export default function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  const submit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (ref.current) {
      ref.current.style.height = "auto";
    }
    requestAnimationFrame(() => ref.current?.focus());
  }, [value, disabled, onSend]);

  const onKey = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        submit();
      }
    },
    [submit],
  );

  const handleInput = useCallback((e: React.FormEvent<HTMLTextAreaElement>) => {
    const el = e.currentTarget;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 180) + "px";
  }, []);

  return (
    <div className="border-t border-zinc-800/60 bg-zinc-950 px-6 py-4">
      <div className="mx-auto flex max-w-3xl items-end gap-3">
        <div className="relative flex-1">
          <textarea
            ref={ref}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={onKey}
            onInput={handleInput}
            placeholder={disabled ? "Waiting..." : "Message..."}
            rows={1}
            disabled={disabled}
            className="w-full resize-none rounded-xl border border-zinc-800 bg-zinc-900/80 px-4 py-3 pr-3
                       text-[13px] text-zinc-100 placeholder-zinc-600 caret-violet-400 outline-none
                       transition-all duration-200
                       focus:border-zinc-700 focus:bg-zinc-900 focus:shadow-[0_0_0_1px_rgba(139,92,246,0.1)]
                       disabled:opacity-30 disabled:cursor-not-allowed"
            style={{ minHeight: 44, maxHeight: 180 }}
          />
        </div>
        <button
          onClick={submit}
          disabled={disabled || !value.trim()}
          className="flex items-center justify-center size-[44px] shrink-0 rounded-xl
                     bg-violet-600 text-white transition-all duration-150
                     hover:bg-violet-500 active:scale-95
                     disabled:opacity-20 disabled:pointer-events-none"
        >
          <svg className="size-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M2 8h12M9 3l5 5-5 5"/>
          </svg>
        </button>
      </div>
      <div className="mx-auto max-w-3xl mt-1.5">
        <p className="text-[10px] text-zinc-700 text-center">
          Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
