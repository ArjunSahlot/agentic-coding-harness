from __future__ import annotations

import copy
import json

from jinja2 import BaseLoader, Environment
from transformers import AutoTokenizer

TOOL_CALL_INSTRUCTIONS = """You have access to tools. When you need to call a tool, emit exactly one JSON object inside a <tool_call> block:
<tool_call>
{"name": "list_directory", "arguments": {"path": "."}}
</tool_call>

The JSON object must have:
- "name": the tool name.
- "arguments": an object containing the tool arguments. Use {} when there are no arguments.

Available tools:
__TOOLS_JSON__"""


class ChatRenderer:
    """Render chat messages into token ids using the model's Jinja template.

    Tool definitions are injected into the system prompt so models use the
    harness tool-call format regardless of tokenizer template defaults.
    """

    def __init__(self, tokenizer: AutoTokenizer) -> None:
        self.tokenizer = tokenizer
        self._template = self._load_template(tokenizer)

    def render(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        add_generation_prompt: bool = True,
        enable_thinking: bool = True,
    ) -> list[int]:
        """Return token ids for the full conversation."""
        text = self.render_text(
            messages,
            tools=tools,
            add_generation_prompt=add_generation_prompt,
            enable_thinking=enable_thinking,
        )
        return self.tokenizer.encode(text, add_special_tokens=False)

    def render_text(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        add_generation_prompt: bool = True,
        enable_thinking: bool = True,
    ) -> str:
        """Return the rendered prompt string (before tokenisation)."""
        render_messages, render_tools = _prepare_tool_prompt(messages, tools)
        if self._template is not None:
            return self._template.render(
                messages=render_messages,
                tools=render_tools,
                add_generation_prompt=add_generation_prompt,
                enable_thinking=enable_thinking,
                add_vision_id=False,
                raise_exception=_raise,
            )
        return self.tokenizer.apply_chat_template(
            render_messages,
            tools=render_tools,
            tokenize=False,
            add_generation_prompt=add_generation_prompt,
        )

    def decode(self, token_ids: list[int], skip_special: bool = True) -> str:
        return self.tokenizer.decode(token_ids, skip_special_tokens=skip_special)

    @staticmethod
    def _load_template(tokenizer: AutoTokenizer):
        template_str: str | None = getattr(tokenizer, "chat_template", None)
        if template_str is None:
            return None
        env = Environment(loader=BaseLoader(), keep_trailing_newline=True)
        env.filters["tojson"] = _tojson
        return env.from_string(template_str)


def _raise(msg: str) -> None:
    raise ValueError(msg)


def _tojson(value, **_kw):
    return json.dumps(value, ensure_ascii=False)


def _prepare_tool_prompt(
    messages: list[dict],
    tools: list[dict] | None,
) -> tuple[list[dict], list[dict]]:
    """Inject project-owned tool instructions and bypass template defaults."""
    if not tools:
        return messages, []

    render_messages = copy.deepcopy(messages)
    instructions = TOOL_CALL_INSTRUCTIONS.replace(
        "__TOOLS_JSON__",
        json.dumps(tools, ensure_ascii=False, indent=2),
    )

    if render_messages and render_messages[0].get("role") == "system":
        render_messages[0]["content"] = (
            f"{render_messages[0].get('content', '').rstrip()}\n\n{instructions}"
        )
    else:
        render_messages.insert(0, {"role": "system", "content": instructions})

    return render_messages, []
