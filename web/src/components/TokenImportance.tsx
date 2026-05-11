export type TokenImportanceItem = {
  text: string;
  score: number;
  id?: number | string;
};

export type TokenImportancePayload = {
  tokens: TokenImportanceItem[];
  label?: string;
  method?: string;
  observations?: number;
};

type Props = {
  payload: TokenImportancePayload;
  compact?: boolean;
};

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(1, value));
}

function tokenGradient(score: number): string {
  const s = clamp01(score);
  if (s >= 0.78) {
    return `linear-gradient(180deg, rgba(244, 63, 94, ${0.24 + s * 0.34}), rgba(251, 113, 133, ${0.18 + s * 0.28}))`;
  }
  if (s >= 0.56) {
    return `linear-gradient(180deg, rgba(245, 158, 11, ${0.2 + s * 0.28}), rgba(251, 191, 36, ${0.16 + s * 0.24}))`;
  }
  if (s >= 0.34) {
    return `linear-gradient(180deg, rgba(20, 184, 166, ${0.18 + s * 0.22}), rgba(45, 212, 191, ${0.12 + s * 0.18}))`;
  }
  return `linear-gradient(180deg, rgba(99, 102, 241, ${0.08 + s * 0.16}), rgba(129, 140, 248, ${0.06 + s * 0.12}))`;
}

function tokenRing(score: number): string {
  const s = clamp01(score);
  if (s >= 0.78) return `rgba(244, 63, 94, ${0.32 + s * 0.28})`;
  if (s >= 0.56) return `rgba(245, 158, 11, ${0.26 + s * 0.22})`;
  if (s >= 0.34) return `rgba(20, 184, 166, ${0.22 + s * 0.18})`;
  return `rgba(99, 102, 241, ${0.12 + s * 0.14})`;
}

export default function TokenImportance({ payload, compact = false }: Props) {
  const { tokens, label, observations } = payload;
  if (tokens.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-white/45 px-3 py-4 text-center text-xs text-slate-500 dark:border-white/10 dark:bg-white/[0.03] dark:text-slate-500">
        No tokens to visualize yet.
      </div>
    );
  }

  const averageScore = tokens.reduce((sum, token) => sum + clamp01(token.score), 0) / tokens.length;
  const hotCount = tokens.filter((token) => token.text.trim() && clamp01(token.score) >= 0.72).length;

  return (
    <span className={`token-importance-inline ${compact ? "token-importance-inline--compact" : ""}`}>
      {!compact && (
        <span className="token-importance-inline__legend" title={payload.method || label || "Attention-derived token importance"}>
          attention heat / {hotCount} hot / {Math.round(averageScore * 100)}% avg
          {observations ? ` / ${observations.toLocaleString()} obs` : ""}
        </span>
      )}
      <span className="token-importance-inline__text" aria-label={label || "attention-derived token importance"}>
        {tokens.map((token, index) => {
          const score = clamp01(token.score);
          return (
            <span
              key={`${token.id ?? index}-${index}`}
              className="token-highlight"
              title={`token ${index + 1} | importance ${Math.round(score * 100)}%`}
              style={{
                background: tokenGradient(score),
                boxShadow: score > 0.72 ? `inset 0 -2px 0 ${tokenRing(score)}, 0 0 0 1px ${tokenRing(score)}` : undefined,
              }}
            >
              {token.text || " "}
            </span>
          );
        })}
      </span>
    </span>
  );
}
