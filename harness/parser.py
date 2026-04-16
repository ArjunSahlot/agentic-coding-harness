from __future__ import annotations

import json
import re
from dataclasses import dataclass


@dataclass
class ParsedToolCall:
    name: str
    arguments: dict


class ToolCallParser:
    """Parse tool calls from model output.

    Default format matches the Qwen chat-template convention::

        <tool_call>
        <function=function_name>
        <parameter=param1>
        value1
        </parameter>
        </function>
        </tool_call>

    Subclass and override :meth:`parse` for other formats.
    """

    TOOL_CALL_RE = re.compile(
        r"<tool_call>\s*<function=(\w+)>(.*?)</function>\s*</tool_call>",
        re.DOTALL,
    )
    PARAM_RE = re.compile(
        r"<parameter=(\w+)>\s*(.*?)\s*</parameter>",
        re.DOTALL,
    )

    def parse(self, text: str) -> tuple[str, list[ParsedToolCall]]:
        """Return ``(plain_text, tool_calls)`` extracted from *text*.

        ``plain_text`` is the text with tool-call blocks removed.
        """
        calls: list[ParsedToolCall] = []
        plain_parts: list[str] = []
        last_end = 0

        for m in self.TOOL_CALL_RE.finditer(text):
            plain_parts.append(text[last_end : m.start()])
            last_end = m.end()

            fn_name = m.group(1)
            body = m.group(2)
            args = {}
            for pm in self.PARAM_RE.finditer(body):
                key = pm.group(1)
                raw = pm.group(2).strip()
                args[key] = self._coerce(raw)
            calls.append(ParsedToolCall(name=fn_name, arguments=args))

        plain_parts.append(text[last_end:])
        plain = "".join(plain_parts).strip()
        return plain, calls

    def has_tool_call(self, text: str) -> bool:
        return bool(self.TOOL_CALL_RE.search(text))

    @staticmethod
    def _coerce(raw: str):
        """Try to parse JSON values; fall back to string."""
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return raw
