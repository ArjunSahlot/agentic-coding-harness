# Agentic Coding Harness

A modular, model-agnostic agentic coding harness for local model inference. Designed as a research-friendly platform with plug-and-play components.

## Architecture

```
inference/    Torch + HF tokenizer. Direct model.forward(), manual KV cache, attention hooks.
harness/      Agent loop, tool protocol, conversation management, output parsing.
server/       Thin FastAPI layer with WebSocket streaming.
web/          React + Vite + Tailwind chat UI.
```

## Quick Start

```bash
# Install Python dependencies
uv sync

# Install frontend dependencies
cd web && npm install && cd ..

# Start the server and frontend (loads model via UI)
python main.py

# Or pre-load a model
python main.py --model models/qwen-3.5-2b

# Optional: for frontend development with hot reload, run Vite separately
cd web && npm run dev
```

The normal app runs on `http://localhost:8000`; `main.py` builds `web/dist` when needed and serves the frontend from the same FastAPI process. The Vite dev server is only for hot-reload frontend work and proxies API/WebSocket requests to the backend.

## Adding Tools

Create a class implementing the `Tool` protocol and register it:

```python
from harness.tools.base import Tool

class MyTool:
    name = "my_tool"
    description = "Does something useful."
    parameters = {
        "type": "object",
        "properties": {"input": {"type": "string"}},
        "required": ["input"],
    }

    def execute(self, *, input: str) -> str:
        return f"Result: {input}"
```

Models call tools by emitting a JSON object wrapped in a `tool_call` block:

```xml
<tool_call>
{"name": "list_directory", "arguments": {"path": "."}}
</tool_call>
```

## Swapping the Inference Engine

Any object satisfying the `InferenceEngine` protocol works:

```python
from inference.engine import InferenceEngine

class MyCustomEngine:
    def load(self, model_path, *, dtype=..., device=...): ...
    def generate(self, messages, tools=None, *, max_new_tokens=4096, ...): ...
    def get_attention_weights(self): ...
```

## Benchmark Tasks

The local SWE benchmark tasks live in `tasks/` and can be run without starting
the web app:

```bash
python3 scripts/run_task_benchmark.py --list
python3 scripts/run_task_benchmark.py --verify-only
python3 scripts/run_task_benchmark.py --model models/your-model --task ledger_proration
```

For optional realtime browser monitoring, add `--monitor`. The monitor presents
a chat-style transcript with assistant rounds, collapsible thinking, tool cards,
generation stats, and verification results. The default runner path has no
monitor overhead; `--monitor-stream final` sends only completed assistant
messages, while `--monitor-stream all` also streams thinking/text deltas and
tool activity.

```bash
python3 scripts/run_task_benchmark.py --model models/your-model --monitor --monitor-open
```

## License

GNU GPL v3


### DO NOT REMOVE PLEASE
Summary
----------------------------------------------------------------------------------------
task                             score   status   agent_s   test_s  run_dir
----------------------------------------------------------------------------------------
csv_schema_migrator             0/7        FAIL     192.4     0.00  /home/arjun/projects/agentic-coding-harness/.benchmark_runs/run-20260507-220030/csv_schema_migrator
event_store_snapshots           6/7        FAIL     296.8     0.01  /home/arjun/projects/agentic-coding-harness/.benchmark_runs/run-20260507-220030/event_store_snapshots
feature_flags                   0/8       ERROR     125.0     0.01  /home/arjun/projects/agentic-coding-harness/.benchmark_runs/run-20260507-220030/feature_flags
inventory_forecast              3/7        FAIL     339.6     0.00  /home/arjun/projects/agentic-coding-harness/.benchmark_runs/run-20260507-220030/inventory_forecast
ledger_proration                0/7       ERROR      98.8     0.01  /home/arjun/projects/agentic-coding-harness/.benchmark_runs/run-20260507-220030/ledger_proration
license_audit                   0/8        FAIL     183.3     0.00  /home/arjun/projects/agentic-coding-harness/.benchmark_runs/run-20260507-220030/license_audit
line_diff_reporter              4/7        FAIL     272.6     0.00  /home/arjun/projects/agentic-coding-harness/.benchmark_runs/run-20260507-220030/line_diff_reporter
log_window_rollups              0/6        FAIL     231.8     0.01  /home/arjun/projects/agentic-coding-harness/.benchmark_runs/run-20260507-220030/log_window_rollups
markdown_outline                0/6        FAIL     189.3     0.00  /home/arjun/projects/agentic-coding-harness/.benchmark_runs/run-20260507-220030/markdown_outline
route_planner                   0/6        FAIL     248.2     0.00  /home/arjun/projects/agentic-coding-harness/.benchmark_runs/run-20260507-220030/route_planner
semver_resolver                 1/8        FAIL     337.0     0.01  /home/arjun/projects/agentic-coding-harness/.benchmark_runs/run-20260507-220030/semver_resolver
template_engine                 0/8       ERROR      85.5     0.01  /home/arjun/projects/agentic-coding-harness/.benchmark_runs/run-20260507-220030/template_engine
----------------------------------------------------------------------------------------
overall score: 14/85
run root: /home/arjun/projects/agentic-coding-harness/.benchmark_runs/run-20260507-220030