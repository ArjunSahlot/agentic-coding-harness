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

    Tool calls are JSON objects wrapped in ``<tool_call>`` tags::

        <tool_call>
        {"name": "list_directory", "arguments": {"path": "."}}
        </tool_call>

    Subclass and override :meth:`parse` for other formats.
    """

    TOOL_CALL_RE = re.compile(
        r"<tool_call>\s*(.*?)\s*</tool_call>",
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
            parsed = self._parse_json_call(m.group(1).strip())
            if parsed is None:
                continue

            plain_parts.append(text[last_end : m.start()])
            last_end = m.end()
            calls.append(parsed)

        plain_parts.append(text[last_end:])
        plain = "".join(plain_parts).strip()
        return plain, calls

    def has_tool_call(self, text: str) -> bool:
        return any(
            self._parse_json_call(m.group(1).strip()) is not None
            for m in self.TOOL_CALL_RE.finditer(text)
        )

    @staticmethod
    def _parse_json_call(raw: str) -> ParsedToolCall | None:
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return None

        if not isinstance(payload, dict):
            return None

        name = payload.get("name")
        arguments = payload.get("arguments", {})
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return None

        return ParsedToolCall(name=name, arguments=arguments)
