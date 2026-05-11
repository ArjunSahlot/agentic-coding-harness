from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal

from inference.engine import InferenceEngine
from .conversation import Conversation
from .parser import ToolCallParser
from .tools.base import Tool

log = logging.getLogger(__name__)

EventType = Literal[
    "thinking_delta",
    "text_delta",
    "text_final",
    "gen_stats",
    "tool_call_pending",
    "tool_result",
    "tool_rejected",
    "token_importance",
    "error",
    "done",
]


@dataclass
class AgentEvent:
    type: EventType
    data: str | dict

    def to_dict(self) -> dict:
        return {"type": self.type, "data": self.data}


DEFAULT_SYSTEM = (
    "You are a helpful coding assistant. You have access to tools that let you "
    "read files, write files, search code, and run shell commands. Use them to "
    "help the user with their coding tasks. Think step by step."
)

MAX_TOOL_ROUNDS = 15

THINK_CLOSE_RE = re.compile(r"</think>")


def _importance_payload_for_text(
    importance: dict,
    full_response: str,
    text: str,
    *,
    target: str,
    label: str,
) -> dict | None:
    """Return generated-token importance clipped to one rendered text segment."""
    if not text:
        return None
    all_tokens = importance.get("tokens")
    if not isinstance(all_tokens, list):
        return None

    generated_tokens = [t for t in all_tokens if isinstance(t, dict) and t.get("source") == "generated"]
    if not generated_tokens:
        return None

    visible_start = full_response.find(text)
    if visible_start < 0:
        return None
    visible_end = visible_start + len(text)

    cursor = 0
    visible_tokens: list[dict] = []
    for token in generated_tokens:
        text = str(token.get("text", ""))
        start = cursor
        end = cursor + len(text)
        cursor = end
        if end <= visible_start or start >= visible_end:
            continue
        clipped = text[max(0, visible_start - start): len(text) - max(0, end - visible_end)]
        if not clipped:
            continue
        visible_tokens.append({
            "id": token.get("id"),
            "token_id": token.get("token_id"),
            "text": clipped,
            "score": token.get("score", 0.0),
            "raw_score": token.get("raw_score", 0.0),
            "source": f"assistant_{target}",
        })

    if not visible_tokens:
        return None

    return {
        **importance,
        "label": label,
        "target": target,
        "tokens": visible_tokens,
        "visible_text": text,
    }


def _visible_importance_payloads(
    importance: dict,
    full_response: str,
    *,
    thinking_text: str,
    plain_text: str,
) -> list[dict]:
    """Build attention-derived heatmaps for each rendered assistant segment."""
    payloads: list[dict] = []
    thinking_payload = _importance_payload_for_text(
        importance,
        full_response,
        thinking_text,
        target="thinking",
        label="Thought token importance",
    )
    if thinking_payload is not None:
        payloads.append(thinking_payload)

    text_payload = _importance_payload_for_text(
        importance,
        full_response,
        plain_text,
        target="text",
        label="Response token importance",
    )
    if text_payload is not None:
        payloads.append(text_payload)

    return payloads


class Agent:
    """Multi-turn agent with human-in-the-loop tool approval.

    Usage from server::

        agent.start_turn(user_msg)
        for round in range(MAX_ROUNDS):
            pending = []
            for event in agent.generate_round():
                send(event)
                if event.type == "tool_call_pending":
                    pending.append(event.data)
                if event.type == "done":
                    break
            else:
                for tc in pending:
                    if approved:
                        result = agent.execute_tool(tc["name"], tc["arguments"])
                    else:
                        agent.reject_tool(tc["name"])
                continue
            break
    """

    def __init__(
        self,
        engine: InferenceEngine,
        tools: list[Tool],
        *,
        system_prompt: str = DEFAULT_SYSTEM,
        max_tool_rounds: int = MAX_TOOL_ROUNDS,
    ) -> None:
        self.engine = engine
        self.tools = {t.name: t for t in tools}
        self.conversation = Conversation(system_prompt=system_prompt)
        self.parser = ToolCallParser()
        self.max_tool_rounds = max_tool_rounds
        self._tc_counter = 0

    def tool_schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self.tools.values()
        ]

    def start_turn(self, user_message: str) -> None:
        """Begin a new user turn by appending the user message."""
        self.conversation.add_user(user_message)

    def generate_round(
        self,
        *,
        temperature: float = 0.6,
        max_new_tokens: int = 4096,
        token_importance: bool = False,
        token_importance_interval: int = 8,
    ) -> Iterator[AgentEvent]:
        """Run one generation round.

        Yields streaming events:
        - ``thinking_delta`` / ``text_delta``: token-level streaming
        - ``text_final``: clean text with tool XML stripped (replaces streamed text)
        - ``tool_call_pending``: a tool the model wants to call (needs approval)
        - ``done``: no tool calls, turn is finished
        """
        full_response = ""
        in_thinking = True
        think_closed = False

        for token in self.engine.generate(
            self.conversation.snapshot(),
            tools=self.tool_schemas(),
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            stream=True,
            token_importance=token_importance,
            token_importance_interval=token_importance_interval,
        ):
            full_response += token

            if in_thinking:
                if THINK_CLOSE_RE.search(full_response):
                    in_thinking = False
                    think_closed = True
                    idx = full_response.index("</think>") + len("</think>")
                    after = full_response[idx:]
                    tail = token
                    if after:
                        overlap = len(after)
                        text_part = tail[-overlap:] if overlap <= len(tail) else after
                        if text_part.strip():
                            yield AgentEvent(type="text_delta", data=text_part)
                else:
                    yield AgentEvent(type="thinking_delta", data=token)
            else:
                yield AgentEvent(type="text_delta", data=token)

        stats: dict = {
            "assistant_chars_streamed": len(full_response),
            "thinking_closed": think_closed,
        }
        eng_stats = getattr(self.engine, "last_generation_stats", None)
        if isinstance(eng_stats, dict):
            stats.update(eng_stats)
        yield AgentEvent(type="gen_stats", data=stats)

        thinking_text = ""
        clean = full_response
        if think_closed and "</think>" in clean:
            if "<think>" in clean:
                thinking_text = clean[clean.index("<think>") + len("<think>"): clean.index("</think>")].strip()
            clean = clean[clean.index("</think>") + len("</think>"):]
        clean = clean.strip()

        plain_text, tool_calls = self.parser.parse(clean)

        yield AgentEvent(type="text_final", data=plain_text)

        importance = getattr(self.engine, "last_token_importance", None)
        importance_payloads = (
            _visible_importance_payloads(
                importance,
                full_response,
                thinking_text=thinking_text,
                plain_text=plain_text,
            )
            if token_importance and isinstance(importance, dict) and importance.get("tokens")
            else []
        )
        if importance_payloads:
            yield AgentEvent(type="token_importance", data={"segments": importance_payloads})

        metadata = {"token_importance_segments": importance_payloads} if importance_payloads else None
        self.conversation.add_assistant(full_response, metadata=metadata)

        if tool_calls:
            for tc in tool_calls:
                tc_id = self._next_tc_id()
                yield AgentEvent(
                    type="tool_call_pending",
                    data={"id": tc_id, "name": tc.name, "arguments": tc.arguments},
                )
        else:
            yield AgentEvent(type="done", data="")

    def execute_tool(self, name: str, arguments: dict) -> str:
        """Execute a tool and record the result in the conversation."""
        tool = self.tools.get(name)
        if tool is None:
            result = f"Error: unknown tool '{name}'"
        else:
            try:
                result = tool.execute(**arguments)
            except Exception as exc:
                log.exception("Tool %s failed", name)
                result = f"Error executing {name}: {exc}"

        self.conversation.add_tool_result(
            f"<tool_response>\n{result}\n</tool_response>"
        )
        return result

    def reject_tool(self, name: str) -> None:
        """Record a tool rejection in the conversation."""
        self.conversation.add_tool_result(
            "<tool_response>\nTool call rejected by user.\n</tool_response>"
        )

    def _next_tc_id(self) -> str:
        self._tc_counter += 1
        return f"tc_{self._tc_counter}"
