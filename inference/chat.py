from __future__ import annotations

from pathlib import Path

from jinja2 import BaseLoader, Environment
from transformers import AutoTokenizer


class ChatRenderer:
    """Render chat messages into token ids using the model's Jinja template.

    Supports tool definitions following the Qwen/ChatML convention: tools are
    injected into the system prompt by the template itself.
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
        if self._template is not None:
            return self._template.render(
                messages=messages,
                tools=tools or [],
                add_generation_prompt=add_generation_prompt,
                enable_thinking=enable_thinking,
                add_vision_id=False,
                raise_exception=_raise,
            )
        return self.tokenizer.apply_chat_template(
            messages,
            tools=tools,
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
    import json
    return json.dumps(value, ensure_ascii=False)
