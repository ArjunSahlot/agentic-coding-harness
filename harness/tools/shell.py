from __future__ import annotations

from ..sandbox import run_command


class RunCommand:
    name = "run_command"
    description = "Run a shell command and return its output. Use for git, build tools, tests, etc."
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The shell command to execute"},
            "cwd": {
                "type": "string",
                "description": "Working directory (optional, defaults to project root)",
            },
        },
        "required": ["command"],
    }

    def __init__(self, *, default_cwd: str = ".") -> None:
        self.default_cwd = default_cwd

    def execute(self, *, command: str, cwd: str | None = None) -> str:
        result = run_command(command, cwd=cwd or self.default_cwd, timeout=30.0)
        header = f"exit_code: {result.exit_code}"
        return f"{header}\n{result.output}"
