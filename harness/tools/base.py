from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Tool(Protocol):
    """Interface every tool must satisfy."""

    name: str
    description: str
    parameters: dict

    def execute(self, **kwargs) -> str: ...


class ToolRegistry:
    """Simple registry for auto-discovering and collecting tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def __len__(self) -> int:
        return len(self._tools)


def default_tools(*, working_directory: str | None = None) -> list[Tool]:
    """Return instances of all built-in tools."""
    from .file_ops import ReadFile, WriteFile, ListDirectory
    from .shell import RunCommand
    from .search import SearchFiles

    cwd = working_directory or "."
    return [
        ReadFile(),
        WriteFile(),
        ListDirectory(),
        RunCommand(default_cwd=cwd),
        SearchFiles(default_cwd=cwd),
    ]
