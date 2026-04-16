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

# Start the server (loads model via UI)
python main.py

# Or pre-load a model
python main.py --model models/qwen-3.5-2b

# For development, run the Vite dev server in a separate terminal
cd web && npm run dev
```

The API server runs on `http://localhost:8000`. The Vite dev server (with hot reload) runs on `http://localhost:5173` and proxies API/WebSocket requests to the backend.

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

## Swapping the Inference Engine

Any object satisfying the `InferenceEngine` protocol works:

```python
from inference.engine import InferenceEngine

class MyCustomEngine:
    def load(self, model_path, *, dtype=..., device=...): ...
    def generate(self, messages, tools=None, *, max_new_tokens=4096, ...): ...
    def get_attention_weights(self): ...
```

## License

GNU GPL v3
