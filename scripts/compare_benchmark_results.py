#!/usr/bin/env python3
"""Compare README baseline benchmark results with a JSON benchmark run."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROW_RE = re.compile(
    r"^(?P<task>\S+)\s+"
    r"(?P<passed>\d+)/(?P<total>\d+)\s+"
    r"(?P<status>\S+)\s+"
    r"(?P<agent_s>[\d.]+)\s+"
    r"(?P<test_s>[\d.]+)\s+"
    r"(?P<run_dir>.+)$"
)
OVERALL_RE = re.compile(r"^overall score:\s+(?P<passed>\d+)/(?P<total>\d+)")


def parse_readme_baseline(path: Path) -> dict:
    rows: dict[str, dict] = {}
    overall: dict | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        row_match = ROW_RE.match(line.strip())
        if row_match:
            data = row_match.groupdict()
            rows[data["task"]] = {
                "passed": int(data["passed"]),
                "total": int(data["total"]),
                "status": data["status"],
                "agent_s": float(data["agent_s"]),
                "test_s": float(data["test_s"]),
                "run_dir": data["run_dir"],
            }
            continue
        overall_match = OVERALL_RE.match(line.strip())
        if overall_match:
            overall = {
                "passed": int(overall_match.group("passed")),
                "total": int(overall_match.group("total")),
            }
    if not rows:
        raise SystemExit(f"no benchmark summary rows found in {path}")
    return {"tasks": rows, "overall": overall}


def load_json_run(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "tasks": {
            task["id"]: {
                "passed": int(task["score"]["passed"]),
                "total": int(task["score"]["total"]),
                "status": "PASS" if task["score"]["successful"] else ("ERROR" if task.get("error") else "FAIL"),
                "agent_s": float(task.get("agent_seconds", 0.0)),
                "test_s": float(task["score"].get("duration_seconds", 0.0)),
                "reductions": len(task.get("context_reductions") or []),
            }
            for task in data.get("tasks", [])
        },
        "overall": data.get("overall", {}),
        "context_reduction": data.get("context_reduction", {}),
    }


def print_comparison(base: dict, candidate: dict) -> None:
    print("Benchmark Comparison")
    print(f"context reduction: {candidate.get('context_reduction', {})}")
    print("-" * 96)
    print(f"{'task':28} {'base':>9} {'candidate':>11} {'delta':>7} {'base_s':>8} {'cand_s':>8} {'reductions':>10}")
    print("-" * 96)
    base_tasks = base["tasks"]
    candidate_tasks = candidate["tasks"]
    all_tasks = sorted(set(base_tasks) | set(candidate_tasks))
    for task_id in all_tasks:
        b = base_tasks.get(task_id, {"passed": 0, "total": 0, "agent_s": 0.0})
        c = candidate_tasks.get(task_id, {"passed": 0, "total": 0, "agent_s": 0.0, "reductions": 0})
        delta = c["passed"] - b["passed"]
        delta_text = f"{delta:+d}"
        print(
            f"{task_id:28} "
            f"{b['passed']:>4}/{b['total']:<4} "
            f"{c['passed']:>5}/{c['total']:<5} "
            f"{delta_text:>7} "
            f"{b['agent_s']:>8.1f} "
            f"{c['agent_s']:>8.1f} "
            f"{c.get('reductions', 0):>10}"
        )
    print("-" * 96)
    base_overall = base.get("overall") or {}
    candidate_overall = candidate.get("overall") or {}
    if base_overall and candidate_overall:
        delta = int(candidate_overall.get("passed", 0)) - int(base_overall.get("passed", 0))
        print(
            "overall: "
            f"{base_overall.get('passed', 0)}/{base_overall.get('total', 0)} -> "
            f"{candidate_overall.get('passed', 0)}/{candidate_overall.get('total', 0)} "
            f"({delta:+d})"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare README baseline results with a benchmark JSON run.")
    parser.add_argument("--baseline-readme", default="README.md", help="README containing the baseline summary table.")
    parser.add_argument("--candidate-json", required=True, help="JSON file written by run_task_benchmark.py --results-json.")
    args = parser.parse_args()

    base = parse_readme_baseline(Path(args.baseline_readme))
    candidate = load_json_run(Path(args.candidate_json))
    print_comparison(base, candidate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
