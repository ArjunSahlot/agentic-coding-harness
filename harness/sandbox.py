from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(f"[stderr]\n{self.stderr}")
        return "\n".join(parts) if parts else "(no output)"


def run_command(
    command: str,
    *,
    cwd: str | None = None,
    timeout: float = 30.0,
    max_output: int = 50_000,
) -> CommandResult:
    """Run *command* in a subprocess with timeout and output limits."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return CommandResult(
            exit_code=result.returncode,
            stdout=result.stdout[:max_output],
            stderr=result.stderr[:max_output],
        )
    except subprocess.TimeoutExpired:
        return CommandResult(exit_code=-1, stdout="", stderr=f"Command timed out after {timeout}s")
    except Exception as exc:
        return CommandResult(exit_code=-1, stdout="", stderr=str(exc))


async def run_command_async(
    command: str,
    *,
    cwd: str | None = None,
    timeout: float = 30.0,
    max_output: int = 50_000,
) -> CommandResult:
    """Async version of :func:`run_command`."""
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return CommandResult(
            exit_code=proc.returncode or 0,
            stdout=(stdout_b or b"").decode(errors="replace")[:max_output],
            stderr=(stderr_b or b"").decode(errors="replace")[:max_output],
        )
    except asyncio.TimeoutError:
        proc.kill()
        return CommandResult(exit_code=-1, stdout="", stderr=f"Command timed out after {timeout}s")
    except Exception as exc:
        return CommandResult(exit_code=-1, stdout="", stderr=str(exc))
