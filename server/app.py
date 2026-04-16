from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .dev_inspect import build_model_payload, build_runtime_payload, build_tokenizer_sample
from .state import AppState

log = logging.getLogger(__name__)

_SENTINEL = object()
MAX_TOOL_ROUNDS = 15


class LoadModelRequest(BaseModel):
    model_name: str
    device: str = "cuda"
    quantization: str | None = None


class CreateConversationRequest(BaseModel):
    title: str = "New conversation"
    system_prompt: str = ""
    working_directory: str = "."


def create_app(state: AppState | None = None) -> FastAPI:
    app = FastAPI(title="Agentic Coding Harness")
    app_state = state or AppState()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------ #
    # REST
    # ------------------------------------------------------------------ #
    @app.get("/api/models")
    def list_models():
        return {
            "models": app_state.list_models(),
            "loaded": app_state.engine.loaded,
            "current": app_state.engine._model_path,
            "quantization": app_state.engine._quantization,
        }

    @app.post("/api/models/load")
    def load_model(req: LoadModelRequest):
        try:
            app_state.load_model(req.model_name, device=req.device, quantization=req.quantization)
            return {"status": "ok", "model": req.model_name, "quantization": req.quantization}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    @app.get("/api/conversations")
    def list_conversations():
        return {
            "conversations": [
                {"id": c.id, "title": c.title}
                for c in app_state.conversations.values()
            ]
        }

    @app.post("/api/conversations")
    def create_conversation(req: CreateConversationRequest):
        info = app_state.create_conversation(
            title=req.title,
            system_prompt=req.system_prompt,
            working_directory=req.working_directory,
        )
        return {"id": info.id, "title": info.title}

    @app.get("/api/conversations/{conversation_id}/messages")
    def get_messages(conversation_id: str):
        msgs = app_state.get_formatted_messages(conversation_id)
        if msgs is None:
            return {"error": "not found"}
        return {"messages": msgs}

    @app.get("/api/conversations/{conversation_id}/raw")
    def get_raw(conversation_id: str):
        msgs = app_state.get_raw_messages(conversation_id)
        if msgs is None:
            return {"error": "not found"}
        return {"messages": msgs}

    @app.get("/api/dev/runtime")
    def dev_runtime():
        return build_runtime_payload(app_state)

    @app.get("/api/dev/model")
    def dev_model():
        return build_model_payload(app_state)

    @app.get("/api/dev/tokenize")
    def dev_tokenize(text: str = Query("", max_length=8000)):
        if not text:
            return {"error": "pass ?text=..."}
        return build_tokenizer_sample(app_state, text)

    @app.get("/api/conversations/{conversation_id}/token_stats")
    def conversation_token_stats(conversation_id: str):
        """Approximate token counts per raw message (requires loaded tokenizer)."""
        msgs = app_state.get_raw_messages(conversation_id)
        if msgs is None:
            return {"error": "not found"}
        tok = app_state.engine.tokenizer
        if tok is None:
            return {"error": "no tokenizer", "messages": []}
        rows = []
        for i, m in enumerate(msgs):
            role = m.get("role", "")
            content = m.get("content", "")
            if not isinstance(content, str):
                content = json.dumps(content)
            try:
                ids = tok.encode(content, add_special_tokens=False)
                n = len(ids)
            except Exception:
                n = -1
            rows.append(
                {
                    "index": i,
                    "role": role,
                    "chars": len(content),
                    "tokens_approx": n,
                }
            )
        total_tok = sum(r["tokens_approx"] for r in rows if r["tokens_approx"] >= 0)
        return {"messages": rows, "total_tokens_approx": total_tok}

    # ------------------------------------------------------------------ #
    # WebSocket
    # ------------------------------------------------------------------ #
    @app.websocket("/ws/{conversation_id}")
    async def websocket_endpoint(ws: WebSocket, conversation_id: str):
        await ws.accept()
        info = app_state.get_conversation(conversation_id)
        if info is None:
            await ws.send_json({"type": "error", "data": "Conversation not found"})
            await ws.send_json({"type": "done", "data": ""})
            await ws.close()
            return

        try:
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    msg = {"content": raw}

                user_text = msg.get("content", "")
                if not user_text:
                    continue

                if not app_state.engine.loaded:
                    await ws.send_json({"type": "error", "data": "No model loaded. Load a model first."})
                    await ws.send_json({"type": "done", "data": ""})
                    continue

                temperature = msg.get("temperature", 0.6)
                max_tokens = msg.get("max_tokens", 4096)

                await _run_agent_turn(
                    ws, info, user_text, temperature, max_tokens
                )

        except WebSocketDisconnect:
            log.info("Client disconnected from conversation %s", conversation_id)
        except Exception as exc:
            log.exception("WebSocket error for conversation %s", conversation_id)
            try:
                await ws.send_json({"type": "error", "data": str(exc)})
                await ws.send_json({"type": "done", "data": ""})
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Static files
    # ------------------------------------------------------------------ #
    web_dist = Path(__file__).resolve().parent.parent / "web" / "dist"
    if web_dist.exists():
        app.mount("/", StaticFiles(directory=str(web_dist), html=True), name="frontend")

    return app


async def _run_agent_turn(
    ws: WebSocket,
    info,
    user_text: str,
    temperature: float,
    max_tokens: int,
) -> None:
    """Execute one full agent turn with multi-round tool use and approval."""
    agent = info.agent
    agent.start_turn(user_text)
    loop = asyncio.get_running_loop()

    for round_idx in range(MAX_TOOL_ROUNDS):
        event_queue: asyncio.Queue = asyncio.Queue()

        def _gen():
            try:
                for ev in agent.generate_round(
                    temperature=temperature,
                    max_new_tokens=max_tokens,
                ):
                    loop.call_soon_threadsafe(event_queue.put_nowait, ev.to_dict())
            except Exception as exc:
                log.exception("Generation failed round %d", round_idx)
                loop.call_soon_threadsafe(
                    event_queue.put_nowait, {"type": "error", "data": str(exc)}
                )
                loop.call_soon_threadsafe(
                    event_queue.put_nowait, {"type": "done", "data": ""}
                )
            finally:
                loop.call_soon_threadsafe(event_queue.put_nowait, _SENTINEL)

        gen_task = loop.run_in_executor(None, _gen)

        pending_tools: list[dict] = []
        is_done = False

        while True:
            item = await event_queue.get()
            if item is _SENTINEL:
                break
            if item.get("type") == "gen_stats" and isinstance(item.get("data"), dict):
                item = {
                    **item,
                    "data": {**item["data"], "agent_round": round_idx},
                }
            await ws.send_json(item)
            if item["type"] == "tool_call_pending":
                pending_tools.append(item["data"])
            if item["type"] == "done":
                is_done = True

        await gen_task

        if is_done or not pending_tools:
            return

        for tc in pending_tools:
            tc_id = tc["id"]
            tc_name = tc["name"]
            tc_args = tc["arguments"]

            while True:
                approval_raw = await ws.receive_text()
                try:
                    approval_msg = json.loads(approval_raw)
                except json.JSONDecodeError:
                    continue
                msg_type = approval_msg.get("type", "")
                msg_id = approval_msg.get("id", "")
                if msg_type in ("tool_approve", "tool_reject") and msg_id == tc_id:
                    break

            if approval_msg["type"] == "tool_approve":
                result = await asyncio.to_thread(
                    agent.execute_tool, tc_name, tc_args
                )
                await ws.send_json({
                    "type": "tool_result",
                    "data": {"id": tc_id, "name": tc_name, "output": result},
                })
            else:
                agent.reject_tool(tc_name)
                await ws.send_json({
                    "type": "tool_rejected",
                    "data": {"id": tc_id, "name": tc_name},
                })

    await ws.send_json({"type": "error", "data": "Max tool rounds exceeded"})
    await ws.send_json({"type": "done", "data": ""})
