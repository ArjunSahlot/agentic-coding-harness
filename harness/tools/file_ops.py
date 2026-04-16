from __future__ import annotations

import os
from pathlib import Path


class ReadFile:
    name = "read_file"
    description = "Read the contents of a file at the given path."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to read"},
        },
        "required": ["path"],
    }

    def execute(self, *, path: str) -> str:
        p = Path(path)
        if not p.exists():
            return f"Error: file not found: {path}"
        if not p.is_file():
            return f"Error: not a file: {path}"
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            if len(text) > 100_000:
                text = text[:100_000] + "\n... (truncated)"
            lines = text.splitlines()
            numbered = [f"{i + 1:>6}|{line}" for i, line in enumerate(lines)]
            return "\n".join(numbered)
        except Exception as exc:
            return f"Error reading {path}: {exc}"


class WriteFile:
    name = "write_file"
    description = "Write content to a file, creating directories as needed."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to write"},
            "content": {"type": "string", "description": "Content to write"},
        },
        "required": ["path", "content"],
    }

    def execute(self, *, path: str, content: str) -> str:
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"Wrote {len(content)} bytes to {path}"
        except Exception as exc:
            return f"Error writing {path}: {exc}"


class ListDirectory:
    name = "list_directory"
    description = "List files and directories at the given path."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path to list (default: current directory)",
            },
        },
        "required": [],
    }

    def execute(self, *, path: str = ".") -> str:
        p = Path(path)
        if not p.exists():
            return f"Error: path not found: {path}"
        if not p.is_dir():
            return f"Error: not a directory: {path}"
        try:
            entries = sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name))
            lines: list[str] = []
            for entry in entries[:200]:
                prefix = "d " if entry.is_dir() else "f "
                size = ""
                if entry.is_file():
                    size = f" ({entry.stat().st_size:,} bytes)"
                lines.append(f"{prefix}{entry.name}{size}")
            if len(entries) > 200:
                lines.append(f"... and {len(entries) - 200} more entries")
            return "\n".join(lines)
        except Exception as exc:
            return f"Error listing {path}: {exc}"
