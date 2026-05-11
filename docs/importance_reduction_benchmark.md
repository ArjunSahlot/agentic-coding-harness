# Importance-Reduced Benchmark Runs

Use this mode to compare the base benchmark run against a modified run where
older conversation history is incrementally trimmed using attention-derived
token importance. Each reduction pass removes a small number of low-importance
eligible tokens instead of repeatedly collapsing back to a fixed tiny window.
The existing README baseline is left untouched.

## Run Command

```bash
python3 scripts/run_task_benchmark.py \
  --model models/your-model \
  --context-reduction importance \
  --importance-keep-tokens 2048 \
  --importance-trim-tokens 256 \
  --importance-sample-interval 8 \
  --importance-tail-messages 6 \
  --importance-sources prompt \
  --results-json .benchmark_runs/importance-results.json
```

Add `--monitor --monitor-open` if you want to watch the run. The monitor will
show `Context Reduced` cards whenever older history is trimmed. Each card has a
`Compare Context` button that opens a side-by-side modal showing the current
pruned context and the unpruned snapshot from just before that trim.

## Flags

- `--context-reduction importance`: enables the reducer.
- `--importance-keep-tokens`: minimum number of eligible normalized-importance
  tokens to keep. This is a floor, not the number trimmed to on every pass.
- `--importance-trim-tokens`: maximum number of low-importance eligible tokens
  to remove per reduction pass. Lower values reduce redo loops by letting fresh
  context survive longer.
- `--importance-tail-messages`: keeps the most recent non-system messages
  verbatim so the model still sees the latest tool call/result exchange.
- `--importance-min-score`: drops tokens below this normalized score before
  applying the top-k cutoff.
- `--importance-audit-tokens`: controls how many kept and cut token samples are
  written to the JSON output and realtime monitor.
- `--importance-context-preview-chars`: controls how much of each pruned and
  unpruned context snapshot is included for the monitor comparison modal and
  JSON audit.
- `--importance-sample-interval`: collects attention importance every N decode
  tokens. Larger values reduce GPU memory/time; `8` is the default. Prefill
  attentions are intentionally skipped because they are full prompt-by-prompt
  matrices and are the easiest way to blow up VRAM on long tasks.
- `--importance-sources`: chooses `prompt`, `generated`, or `all` tokens from
  the model's attention-derived importance payload. Use `prompt` for the
  cleanest context-history comparison.
- `--results-json`: writes scores and reduction statistics in machine-readable
  form for later analysis.

## Output

The JSON output includes:

- overall score and per-task scores,
- model/run configuration,
- per-task runtime and errors,
- every context reduction event with token counts, message counts, character
  counts, source counts, kept/cut token samples, trim request/floor settings, a
  retained-context preview, pruned/unpruned context previews, and min/max kept
  importance scores.

## Compare Against README Baseline

After the reduced run finishes, compare it to the baseline summary stored in
`README.md`:

```bash
python3 scripts/compare_benchmark_results.py \
  --baseline-readme README.md \
  --candidate-json .benchmark_runs/importance-results.json
```
