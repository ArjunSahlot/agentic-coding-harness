# Agentic Coding Harness Tasks

This directory contains self-contained SWE benchmark tasks for the
headless harness runner in `scripts/run_task_benchmark.py`.

Each task directory contains:

- `metadata.json`: task id, tags, estimated context size, and scoring
  command.
- `prompt.md`: the user prompt sent to the coding agent.
- `repo/`: a disposable Python project copied into a benchmark run
  workspace.

The task repos intentionally contain failing implementations. The agent
should inspect the project, edit the implementation, and run:

```bash
python -m unittest discover -s tests -v
```

All tasks use only the Python standard library and are designed to be
scoreable by counting passing unittest cases.
