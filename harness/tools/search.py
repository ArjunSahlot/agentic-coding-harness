from __future__ import annotations

from ..sandbox import run_command


class SearchFiles:
    name = "search_files"
    description = "Search for a pattern in files using ripgrep. Returns matching lines with file paths and line numbers."
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern to search for"},
            "path": {
                "type": "string",
                "description": "Directory or file to search in (default: project root)",
            },
            "glob": {
                "type": "string",
                "description": "File glob filter, e.g. '*.py' or '*.ts'",
            },
        },
        "required": ["pattern"],
    }

    def __init__(self, *, default_cwd: str = ".") -> None:
        self.default_cwd = default_cwd

    def execute(
        self,
        *,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
    ) -> str:
        cmd_parts = ["rg", "--line-number", "--no-heading", "--max-count=50"]
        if glob:
            cmd_parts.extend(["--glob", f"'{glob}'"])
        cmd_parts.append(f"'{pattern}'")
        if path:
            cmd_parts.append(path)

        cmd = " ".join(cmd_parts)
        result = run_command(cmd, cwd=self.default_cwd, timeout=15.0)

        if result.exit_code == 1 and not result.stdout.strip():
            return "No matches found."
        return result.output or "No matches found."
