from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from inference.engine import LocalEngine
from harness.agent import Agent, DEFAULT_SYSTEM
from harness.parser import ToolCallParser
from harness.tools.base import default_tools

_THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)


@dataclass
class ConversationInfo:
    id: str
    title: str
    agent: Agent


class AppState:
    """Mutable singleton holding the loaded engine and active conversations."""

    def __init__(self) -> None:
        self.engine: LocalEngine = LocalEngine()
        self.conversations: dict[str, ConversationInfo] = {}
        self.models_dir: str = "models"
        self.started_at: float = time.time()

    def list_models(self) -> list[str]:
        p = Path(self.models_dir)
        if not p.exists():
            return []
        return sorted(
            d.name for d in p.iterdir() if d.is_dir() and not d.name.startswith(".")
        )

    def load_model(self, model_name: str, device: str = "cuda", quantization: str | None = None) -> None:
        path = str(Path(self.models_dir) / model_name)
        self.engine.load(path, device=device, quantization=quantization)

    def create_conversation(
        self,
        title: str = "New conversation",
        system_prompt: str | None = None,
        working_directory: str | None = None,
    ) -> ConversationInfo:
        cid = uuid.uuid4().hex[:12]
        tools = default_tools(working_directory=working_directory)
        agent = Agent(
            self.engine,
            tools,
            system_prompt=system_prompt or DEFAULT_SYSTEM,
        )
        info = ConversationInfo(id=cid, title=title, agent=agent)
        self.conversations[cid] = info
        return info

    def get_conversation(self, cid: str) -> ConversationInfo | None:
        return self.conversations.get(cid)

    def get_raw_messages(self, cid: str) -> list[dict] | None:
        info = self.get_conversation(cid)
        if info is None:
            return None
        return info.agent.conversation.snapshot()

    def get_formatted_messages(self, cid: str) -> list[dict] | None:
        info = self.get_conversation(cid)
        if info is None:
            return None
        return format_messages(info.agent.conversation.messages)


def format_messages(raw_messages: list[dict]) -> list[dict]:
    """Convert raw conversation messages to the frontend segment format."""
    parser = ToolCallParser()
    result: list[dict] = []
    tc_counter = 0

    for msg in raw_messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "system":
            continue

        if role == "user":
            metadata = msg.get("metadata") if isinstance(msg.get("metadata"), dict) else {}
            if metadata.get("context_insert"):
                result.append({
                    "role": "user",
                    "segments": [{
                        "type": "context_insert",
                        "content": content,
                        "label": metadata.get("label") or "Manual context insert",
                    }],
                })
            else:
                result.append({
                    "role": "user",
                    "segments": [{"type": "text", "content": content}],
                })

        elif role == "assistant":
            segments: list[dict] = []
            metadata = msg.get("metadata") if isinstance(msg.get("metadata"), dict) else {}
            importance = metadata.get("token_importance") if isinstance(metadata.get("token_importance"), dict) else None
            importance_segments = (
                metadata.get("token_importance_segments")
                if isinstance(metadata.get("token_importance_segments"), list)
                else []
            )
            importance_by_target = {
                item.get("target"): item
                for item in importance_segments
                if isinstance(item, dict) and isinstance(item.get("target"), str)
            }

            think_match = _THINK_RE.search(content)
            if think_match:
                thinking = think_match.group(1).strip()
                if thinking:
                    thinking_segment = {"type": "thinking", "content": thinking}
                    if importance_by_target.get("thinking") is not None:
                        thinking_segment["importance"] = importance_by_target["thinking"]
                    segments.append(thinking_segment)
                text_after = content[think_match.end():].strip()
            else:
                text_after = content.strip()

            plain_text, tool_calls = parser.parse(text_after)
            if plain_text:
                text_segment = {"type": "text", "content": plain_text}
                text_importance = importance_by_target.get("text") or importance
                if text_importance is not None:
                    text_segment["importance"] = text_importance
                segments.append(text_segment)

            for tc in tool_calls:
                tc_counter += 1
                segments.append({
                    "type": "tool_call",
                    "id": f"tc_{tc_counter}",
                    "name": tc.name,
                    "arguments": tc.arguments,
                    "status": "done",
                    "output": None,
                })

            if not segments:
                segments.append({"type": "text", "content": ""})

            result.append({"role": "assistant", "segments": segments})

        elif role == "tool":
            clean = content
            if "<tool_response>" in clean:
                clean = clean.replace("<tool_response>", "").replace("</tool_response>", "").strip()

            if result and result[-1]["role"] == "assistant":
                segs = result[-1]["segments"]
                for seg in reversed(segs):
                    if seg.get("type") == "tool_call" and seg.get("output") is None:
                        seg["output"] = clean
                        break

    return result
