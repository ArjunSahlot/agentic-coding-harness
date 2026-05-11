from __future__ import annotations

import copy
from dataclasses import dataclass, field


@dataclass
class Conversation:
    """Ordered list of chat messages with role-based helpers."""

    messages: list[dict] = field(default_factory=list)
    system_prompt: str = ""

    def __post_init__(self) -> None:
        if self.system_prompt and (
            not self.messages or self.messages[0].get("role") != "system"
        ):
            self.messages.insert(0, {"role": "system", "content": self.system_prompt})

    def add_user(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_context(self, content: str, label: str = "Manual context insert") -> None:
        self.messages.append({
            "role": "user",
            "content": f"[{label}]\n{content}",
            "metadata": {"context_insert": True, "label": label},
        })

    def add_assistant(self, content: str, metadata: dict | None = None) -> None:
        msg: dict = {"role": "assistant", "content": content}
        if metadata:
            msg["metadata"] = metadata
        self.messages.append(msg)

    def add_tool_result(self, content: str) -> None:
        self.messages.append({"role": "tool", "content": content})

    def truncate_to(self, max_messages: int) -> None:
        """Keep system + the last *max_messages* non-system messages."""
        system = [m for m in self.messages if m["role"] == "system"]
        rest = [m for m in self.messages if m["role"] != "system"]
        self.messages = system + rest[-max_messages:]

    def snapshot(self) -> list[dict]:
        """Return a deep copy of the message list."""
        return copy.deepcopy(self.messages)

    def __len__(self) -> int:
        return len(self.messages)
