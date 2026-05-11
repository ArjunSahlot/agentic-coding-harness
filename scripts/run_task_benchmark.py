#!/usr/bin/env python3
"""Run benchmark tasks through the harness without starting the web app."""
from __future__ import annotations

import argparse
import html
import http.server
import json
import os
import queue
import shutil
import socketserver
import subprocess
import sys
import threading
import textwrap
import time
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = ROOT / "tasks"
RUNS_DIR = ROOT / ".benchmark_runs"
RESULT_MARKER = "__ACH_BENCHMARK_RESULT__"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


VERIFY_CODE = rf"""
import json
import sys
import time
import unittest

start = time.perf_counter()
loader = unittest.defaultTestLoader
suite = loader.discover("tests")
total = suite.countTestCases()
runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=2)
result = runner.run(suite)
duration = time.perf_counter() - start
failures = len(result.failures)
errors = len(result.errors)
skipped = len(result.skipped)
unexpected = len(getattr(result, "unexpectedSuccesses", []))
passed = max(0, result.testsRun - failures - errors - skipped - unexpected)
payload = {{
    "total": total,
    "ran": result.testsRun,
    "passed": passed,
    "failures": failures,
    "errors": errors,
    "skipped": skipped,
    "unexpected_successes": unexpected,
    "successful": result.wasSuccessful(),
    "duration_seconds": round(duration, 3),
}}
print("{RESULT_MARKER}" + json.dumps(payload, sort_keys=True))
sys.exit(0 if result.wasSuccessful() else 1)
"""


HEADLESS_SYSTEM = """
You are a coding agent running inside a local benchmark harness. You have tools
for reading files, writing files, searching code, and running shell commands.

Work only in the current benchmark workspace. Use relative paths unless an
absolute path is necessary. Do not use the web, network services, package
installation, or external dependencies. Inspect the repository, make focused
code changes, and run the verification command before you finish.
""".strip()


@dataclass
class TaskSpec:
    task_id: str
    path: Path
    metadata: dict[str, Any]
    prompt: str


@dataclass
class Score:
    passed: int
    total: int
    successful: bool
    duration_seconds: float
    stdout: str
    stderr: str
    returncode: int


@dataclass
class TaskResult:
    task: TaskSpec
    run_dir: Path
    score: Score
    agent_rounds: int
    agent_seconds: float
    error: str | None = None
    reduction_events: list[dict[str, Any]] | None = None


class MonitorState:
    """Small in-process event bus for optional browser monitoring."""

    def __init__(self, *, max_events: int = 2000) -> None:
        self.max_events = max_events
        self.events: list[dict[str, Any]] = []
        self.subscribers: list[queue.Queue] = []
        self.lock = threading.Lock()
        self.started_at = time.time()

    def publish(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        event = {
            "type": event_type,
            "time": round(time.time() - self.started_at, 3),
            "data": data or {},
        }
        with self.lock:
            self.events.append(event)
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events :]
            subscribers = list(self.subscribers)
        for subscriber in subscribers:
            try:
                subscriber.put_nowait(event)
            except queue.Full:
                pass

    def snapshot(self) -> list[dict[str, Any]]:
        with self.lock:
            return list(self.events)

    def subscribe(self) -> queue.Queue:
        subscriber: queue.Queue = queue.Queue(maxsize=500)
        with self.lock:
            self.subscribers.append(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: queue.Queue) -> None:
        with self.lock:
            if subscriber in self.subscribers:
                self.subscribers.remove(subscriber)


@dataclass
class MonitorServer:
    state: MonitorState
    server: socketserver.ThreadingTCPServer
    thread: threading.Thread
    url: str

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class Palette:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def color(self, text: str, code: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    def green(self, text: str) -> str:
        return self.color(text, "32")

    def red(self, text: str) -> str:
        return self.color(text, "31")

    def yellow(self, text: str) -> str:
        return self.color(text, "33")

    def cyan(self, text: str) -> str:
        return self.color(text, "36")

    def bold(self, text: str) -> str:
        return self.color(text, "1")


def truncate(text: str, limit: int = 1200) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + f"\n... truncated {len(text) - limit} chars"


class ImportanceContextReducer:
    """Compress older chat history to the highest-scoring importance tokens."""

    def __init__(
        self,
        *,
        keep_tokens: int,
        trim_tokens: int,
        tail_messages: int,
        min_score: float,
        sources: set[str],
        audit_tokens: int,
        context_preview_chars: int,
    ) -> None:
        self.keep_tokens = keep_tokens
        self.trim_tokens = trim_tokens
        self.tail_messages = tail_messages
        self.min_score = min_score
        self.sources = sources
        self.audit_tokens = audit_tokens
        self.context_preview_chars = context_preview_chars
        self.events: list[dict[str, Any]] = []

    def reduce(self, agent, importance: dict | None, *, round_index: int) -> dict[str, Any] | None:
        if not isinstance(importance, dict):
            return None
        tokens = importance.get("tokens")
        if not isinstance(tokens, list):
            return None

        messages = agent.conversation.messages
        system = [m for m in messages if m.get("role") == "system"]
        rest = [m for m in messages if m.get("role") != "system"]
        rest = [
            m for m in rest
            if not (isinstance(m.get("metadata"), dict) and m["metadata"].get("importance_reduced_context"))
        ]
        if len(rest) <= self.tail_messages:
            return None

        candidates = self._candidate_tokens(tokens)
        selected = self._select_tokens(candidates)
        if not selected:
            return None

        tail = rest[-self.tail_messages :] if self.tail_messages > 0 else []
        unpruned_preview = self._messages_preview(system + rest)
        reduced_text = self._tokens_to_text(selected)
        previous_chars = sum(len(str(m.get("content", ""))) for m in rest)
        tail_chars = sum(len(str(m.get("content", ""))) for m in tail)
        context = self._context_message(reduced_text, selected, len(tokens), round_index)
        agent.conversation.messages = system + [context] + tail
        pruned_preview = self._messages_preview(agent.conversation.messages)

        event = {
            "round": round_index,
            "strategy": "importance_incremental_trim",
            "sources": sorted(self.sources),
            "kept_tokens": len(selected),
            "eligible_tokens": len(candidates),
            "cut_tokens": max(0, len(candidates) - len(selected)),
            "available_tokens": len(tokens),
            "tail_messages": len(tail),
            "messages_before": len(messages),
            "messages_after": len(agent.conversation.messages),
            "chars_before": previous_chars,
            "chars_after": len(context["content"]) + tail_chars,
            "min_kept_score": round(min(float(t.get("score", 0.0)) for t in selected), 4),
            "max_kept_score": round(max(float(t.get("score", 0.0)) for t in selected), 4),
            "kept_preview": truncate(reduced_text, 4000),
            "kept_token_samples": self._token_samples(selected, order="original"),
            "cut_token_samples": self._token_samples(self._cut_tokens(candidates, selected), order="score"),
            "source_counts": self._source_counts(candidates, selected),
            "trim_tokens_requested": self.trim_tokens,
            "keep_tokens_floor": self.keep_tokens,
            "unpruned_context_preview": unpruned_preview,
            "pruned_context_preview": pruned_preview,
        }
        self.events.append(event)
        return event

    def _candidate_tokens(self, tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for token in tokens:
            if not isinstance(token, dict):
                continue
            if str(token.get("source", "")) not in self.sources:
                continue
            text = str(token.get("text", ""))
            if not self._is_context_token(text):
                continue
            score = float(token.get("score", 0.0) or 0.0)
            if score < self.min_score:
                continue
            candidates.append(token)
        return candidates

    def _select_tokens(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(candidates) <= self.keep_tokens:
            return []
        target_count = max(self.keep_tokens, len(candidates) - self.trim_tokens)
        candidates.sort(key=lambda t: float(t.get("score", 0.0) or 0.0), reverse=True)
        kept = candidates[:target_count]
        kept.sort(key=lambda t: int(t.get("id", 0) or 0))
        return kept

    def _cut_tokens(self, candidates: list[dict[str, Any]], selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
        kept_ids = {int(token.get("id", -1) or -1) for token in selected}
        cut = [token for token in candidates if int(token.get("id", -1) or -1) not in kept_ids]
        cut.sort(key=lambda t: float(t.get("score", 0.0) or 0.0), reverse=True)
        return cut

    def _token_samples(self, tokens: list[dict[str, Any]], *, order: str) -> list[dict[str, Any]]:
        sample = tokens[: self.audit_tokens]
        if order == "score":
            sample = sorted(sample, key=lambda t: float(t.get("score", 0.0) or 0.0), reverse=True)
        else:
            sample = sorted(sample, key=lambda t: int(t.get("id", 0) or 0))
        return [
            {
                "id": int(token.get("id", 0) or 0),
                "text": self._display_token(str(token.get("text", ""))),
                "score": round(float(token.get("score", 0.0) or 0.0), 4),
                "raw_score": round(float(token.get("raw_score", 0.0) or 0.0), 6),
                "source": str(token.get("source", "")),
            }
            for token in sample
        ]

    @staticmethod
    def _source_counts(candidates: list[dict[str, Any]], selected: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
        counts: dict[str, dict[str, int]] = {}
        kept_ids = {int(token.get("id", -1) or -1) for token in selected}
        for token in candidates:
            source = str(token.get("source", "unknown"))
            row = counts.setdefault(source, {"eligible": 0, "kept": 0, "cut": 0})
            row["eligible"] += 1
            if int(token.get("id", -1) or -1) in kept_ids:
                row["kept"] += 1
            else:
                row["cut"] += 1
        return counts

    @staticmethod
    def _display_token(text: str) -> str:
        text = text.replace("\n", "\\n").replace("\t", "\\t")
        return text if len(text) <= 80 else text[:77] + "..."

    def _messages_preview(self, messages: list[dict[str, Any]]) -> str:
        chunks: list[str] = []
        for index, message in enumerate(messages):
            role = str(message.get("role", "unknown"))
            content = str(message.get("content", ""))
            chunks.append(f"--- message {index} / {role} ---\n{content}")
        return truncate("\n\n".join(chunks), self.context_preview_chars)

    @staticmethod
    def _is_context_token(text: str) -> bool:
        if not text or not text.strip():
            return False
        stripped = text.strip()
        if stripped.startswith("<|") and stripped.endswith("|>"):
            return False
        return True

    @staticmethod
    def _tokens_to_text(tokens: list[dict[str, Any]]) -> str:
        pieces: list[str] = []
        previous_id: int | None = None
        for token in tokens:
            token_id = int(token.get("id", 0) or 0)
            text = str(token.get("text", ""))
            if previous_id is not None and token_id != previous_id + 1:
                pieces.append(" ... ")
            pieces.append(text)
            previous_id = token_id
        return "".join(pieces).strip()

    @staticmethod
    def _context_message(reduced_text: str, selected: list[dict[str, Any]], total_tokens: int, round_index: int) -> dict:
        header = (
            "[Importance-reduced context]\n"
            f"Round {round_index}: kept {len(selected)} of {total_tokens} scored tokens in original order. "
            "The text below is intentionally fragmentary; it contains only the highest-importance tokens retained from earlier context.\n\n"
        )
        return {
            "role": "user",
            "content": header + reduced_text,
            "metadata": {
                "context_insert": True,
                "label": "Importance-reduced context",
                "importance_reduced_context": True,
            },
        }


def _monitor_html() -> str:
    title = "Agentic Coding Harness Monitor"
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__TITLE__</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0f1115;
      --panel: #161920;
      --panel-2: #1f2430;
      --panel-3: #252b38;
      --text: #ebeef5;
      --muted: #9da6b8;
      --border: #343b4a;
      --green: #62d26f;
      --red: #ff6b6b;
      --cyan: #67d8ef;
      --yellow: #f3c969;
      --blue: #7aa8ff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font: 14px/1.45 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      position: sticky;
      top: 0;
      z-index: 2;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 12px 18px;
      background: rgba(16, 17, 20, 0.94);
      border-bottom: 1px solid var(--border);
    }
    h1 { margin: 0; font-size: 16px; font-weight: 650; }
    main { display: grid; grid-template-columns: 320px minmax(0, 1fr); min-height: calc(100vh - 54px); }
    aside { border-right: 1px solid var(--border); background: var(--panel); padding: 14px; overflow: auto; }
    section { padding: 18px; overflow: auto; }
    .stats { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .stat { background: var(--panel-2); border: 1px solid var(--border); border-radius: 6px; padding: 10px; }
    .stat strong { display: block; font-size: 18px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .muted { color: var(--muted); }
    .controls { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    button, label {
      border: 1px solid var(--border);
      background: var(--panel-2);
      color: var(--text);
      border-radius: 6px;
      padding: 7px 10px;
      cursor: pointer;
    }
    button:hover, label:hover { background: var(--panel-3); }
    label { display: inline-flex; gap: 6px; align-items: center; }
    input { accent-color: var(--cyan); }
    .task-list { margin-top: 14px; display: grid; gap: 6px; }
    .task-pill {
      padding: 8px 10px;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: var(--panel-2);
      color: var(--muted);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .task-pill.active { color: var(--text); border-color: var(--blue); }
    .task-pill.pass { border-color: rgba(98, 210, 111, .65); color: var(--green); }
    .task-pill.fail { border-color: rgba(255, 107, 107, .65); color: var(--red); }
    .timeline { max-width: 980px; margin: 0 auto; display: grid; gap: 14px; }
    .bubble {
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--panel);
      overflow: hidden;
      box-shadow: 0 14px 28px rgba(0, 0, 0, .16);
    }
    .bubble-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      padding: 10px 12px;
      background: var(--panel-2);
      border-bottom: 1px solid var(--border);
    }
    .bubble-title { display: flex; align-items: center; gap: 8px; min-width: 0; }
    .badge { font-size: 12px; color: var(--muted); border: 1px solid var(--border); padding: 2px 6px; border-radius: 999px; }
    .bubble-body { padding: 12px; }
    .content { white-space: pre-wrap; overflow-wrap: anywhere; }
    details {
      border: 1px solid var(--border);
      border-radius: 6px;
      background: rgba(243, 201, 105, .06);
      margin-bottom: 10px;
    }
    summary { cursor: pointer; padding: 8px 10px; color: var(--yellow); }
    .thinking-body { padding: 0 10px 10px; color: #e4d5aa; white-space: pre-wrap; overflow-wrap: anywhere; max-height: 360px; overflow: auto; }
    .tool-card {
      border: 1px solid var(--border);
      border-radius: 6px;
      background: #12151b;
      margin: 10px 0;
      overflow: hidden;
    }
    .tool-head { display: flex; justify-content: space-between; gap: 10px; padding: 8px 10px; background: var(--panel-3); color: var(--cyan); }
    .tool-body { padding: 10px; display: grid; gap: 8px; }
    .tool-output { border-top: 1px solid var(--border); padding-top: 8px; color: #d8deea; max-height: 320px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; }
    .reduction .bubble-head { color: var(--yellow); }
    .reduction-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; margin-bottom: 12px; }
    .reduction-stat { background: #141820; border: 1px solid var(--border); border-radius: 6px; padding: 8px; }
    .reduction-stat span { display: block; color: var(--muted); font-size: 12px; }
    .reduction-stat strong { display: block; font-size: 16px; margin-top: 2px; }
    .token-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .token-panel { border: 1px solid var(--border); border-radius: 6px; overflow: hidden; background: #11141a; }
    .token-panel h3 { margin: 0; padding: 8px 10px; font-size: 13px; background: var(--panel-3); }
    .token-list { display: flex; flex-wrap: wrap; gap: 6px; align-content: flex-start; padding: 10px; max-height: 280px; overflow: auto; }
    .token-chip { display: inline-flex; align-items: center; gap: 6px; max-width: 100%; border: 1px solid var(--border); border-radius: 999px; padding: 4px 8px; background: #181c24; }
    .token-chip.kept { border-color: rgba(98, 210, 111, .45); }
    .token-chip.cut { border-color: rgba(255, 107, 107, .45); }
    .token-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 220px; }
    .token-score { color: var(--muted); font-size: 12px; }
    .source-table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }
    .source-table th, .source-table td { border-bottom: 1px solid var(--border); padding: 6px 8px; text-align: right; }
    .source-table th:first-child, .source-table td:first-child { text-align: left; }
    .preview-details { margin-top: 12px; background: #11141a; }
    .card-actions { display: flex; gap: 8px; align-items: center; margin-top: 12px; flex-wrap: wrap; }
    .modal-backdrop {
      position: fixed;
      inset: 0;
      z-index: 20;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 22px;
      background: rgba(0, 0, 0, .68);
    }
    .modal-backdrop.open { display: flex; }
    .modal {
      width: min(1280px, 100%);
      max-height: min(860px, 94vh);
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--panel);
      box-shadow: 0 22px 80px rgba(0, 0, 0, .5);
      overflow: hidden;
    }
    .modal-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      padding: 12px 14px;
      background: var(--panel-2);
      border-bottom: 1px solid var(--border);
    }
    .modal-title { display: grid; gap: 2px; }
    .modal-body { padding: 14px; overflow: auto; }
    .compare-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; min-height: 0; }
    .compare-panel { border: 1px solid var(--border); border-radius: 6px; overflow: hidden; background: #11141a; min-width: 0; }
    .compare-panel h3 { margin: 0; padding: 9px 10px; font-size: 13px; background: var(--panel-3); }
    .compare-text { margin: 0; padding: 10px; max-height: 620px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; }
    .compare-note { margin-bottom: 10px; color: var(--muted); }
    .system .bubble-head { color: var(--blue); }
    .assistant .bubble-head { color: var(--cyan); }
    .verification.pass .bubble-head, .summary .bubble-head { color: var(--green); }
    .verification.fail .bubble-head, .error .bubble-head { color: var(--red); }
    code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; }
    pre { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; }
    @media (max-width: 760px) {
      main { grid-template-columns: 1fr; }
      aside { border-right: 0; border-bottom: 1px solid var(--border); }
      .reduction-grid, .token-columns, .compare-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>__TITLE__</h1>
    <div class="controls">
      <label><input id="follow" type="checkbox" checked> Follow</label>
      <label><input id="thinking" type="checkbox"> Open thinking</label>
      <button id="clear">Clear</button>
      <span id="status" class="muted">connecting</span>
    </div>
  </header>
  <main>
    <aside>
      <div class="stats">
        <div class="stat"><span class="muted">Task</span><strong id="task">-</strong></div>
        <div class="stat"><span class="muted">Score</span><strong id="score">0/0</strong></div>
        <div class="stat"><span class="muted">Round</span><strong id="round">0</strong></div>
        <div class="stat"><span class="muted">Tokens/s</span><strong id="tps">-</strong></div>
      </div>
      <p class="muted">Streaming is grouped into chat turns so fast token deltas stay readable. Thinking is captured inside collapsible sections.</p>
      <div id="tasks" class="task-list"></div>
    </aside>
    <section><div id="events" class="timeline"></div></section>
  </main>
  <div id="compareModal" class="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="compareTitle">
    <div class="modal">
      <div class="modal-head">
        <div class="modal-title">
          <strong id="compareTitle">Context Comparison</strong>
          <span id="compareSubtitle" class="muted"></span>
        </div>
        <button id="compareClose">Close</button>
      </div>
      <div class="modal-body">
        <div id="compareNote" class="compare-note"></div>
        <div class="compare-grid">
          <div class="compare-panel">
            <h3>Current pruned context</h3>
            <pre id="prunedContext" class="compare-text"></pre>
          </div>
          <div class="compare-panel">
            <h3>Without pruning at this point</h3>
            <pre id="unprunedContext" class="compare-text"></pre>
          </div>
        </div>
      </div>
    </div>
  </div>
  <script>
    const eventsEl = document.getElementById('events');
    const tasksEl = document.getElementById('tasks');
    const statusEl = document.getElementById('status');
    const openThinking = document.getElementById('thinking');
    const follow = document.getElementById('follow');
    const compareModal = document.getElementById('compareModal');
    const compareSubtitle = document.getElementById('compareSubtitle');
    const compareNote = document.getElementById('compareNote');
    const prunedContext = document.getElementById('prunedContext');
    const unprunedContext = document.getElementById('unprunedContext');
    const stats = {
      task: document.getElementById('task'),
      score: document.getElementById('score'),
      round: document.getElementById('round'),
      tps: document.getElementById('tps'),
    };
    const state = {
      currentTask: null,
      currentRound: null,
      currentAssistant: null,
      taskPills: new Map(),
      toolCards: new Map(),
      pendingText: '',
      pendingThinking: '',
      flushScheduled: false,
    };

    document.getElementById('clear').onclick = () => {
      eventsEl.replaceChildren();
      state.currentAssistant = null;
      state.toolCards.clear();
    };
    openThinking.onchange = () => {
      document.querySelectorAll('details.thinking').forEach(el => el.open = openThinking.checked);
    };
    document.getElementById('compareClose').onclick = () => compareModal.classList.remove('open');
    compareModal.addEventListener('click', event => {
      if (event.target === compareModal) compareModal.classList.remove('open');
    });
    window.addEventListener('keydown', event => {
      if (event.key === 'Escape') compareModal.classList.remove('open');
    });

    function scrollIfNeeded() {
      if (follow.checked) window.scrollTo(0, document.body.scrollHeight);
    }

    function textNode(tag, className, text) {
      const el = document.createElement(tag);
      if (className) el.className = className;
      el.textContent = text || '';
      return el;
    }

    function bubble(kind, title, meta) {
      const row = document.createElement('article');
      row.className = `bubble ${kind}`;
      const head = document.createElement('div');
      head.className = 'bubble-head';
      const titleEl = document.createElement('div');
      titleEl.className = 'bubble-title';
      titleEl.append(textNode('strong', '', title));
      if (meta) titleEl.append(textNode('span', 'badge', meta));
      head.append(titleEl, textNode('span', 'muted', ''));
      const body = document.createElement('div');
      body.className = 'bubble-body';
      row.append(head, body);
      eventsEl.append(row);
      scrollIfNeeded();
      return { row, head, body };
    }

    function ensureTaskPill(taskId) {
      if (!taskId) return null;
      if (state.taskPills.has(taskId)) return state.taskPills.get(taskId);
      const pill = textNode('div', 'task-pill', taskId);
      tasksEl.append(pill);
      state.taskPills.set(taskId, pill);
      return pill;
    }

    function setActiveTask(taskId) {
      state.taskPills.forEach(pill => pill.classList.remove('active'));
      const pill = ensureTaskPill(taskId);
      if (pill) pill.classList.add('active');
    }

    function updateStats(type, data) {
      if (type === 'task_start') {
        state.currentTask = data.task_id || null;
        stats.task.textContent = data.task_id || '-';
        stats.score.textContent = '0/0';
        stats.round.textContent = '0';
        stats.tps.textContent = '-';
        setActiveTask(data.task_id);
      }
      if (type === 'round_start') stats.round.textContent = data.round || '0';
      if (type === 'generation_stats') stats.tps.textContent = data.tokens_per_second ?? '-';
      if (type === 'verification') {
        stats.score.textContent = `${data.passed}/${data.total}`;
        const pill = ensureTaskPill(data.task_id);
        if (pill) pill.classList.add(data.successful ? 'pass' : 'fail');
      }
    }

    function ensureAssistant(data) {
      const taskId = data.task_id || state.currentTask || 'task';
      const round = data.round || state.currentRound || 0;
      if (state.currentAssistant && state.currentAssistant.taskId === taskId && state.currentAssistant.round === round) {
        return state.currentAssistant;
      }
      const card = bubble('assistant', 'Assistant', `${taskId} / round ${round}`);
      const thinking = document.createElement('details');
      thinking.className = 'thinking';
      thinking.open = openThinking.checked;
      thinking.append(textNode('summary', '', 'Thinking'));
      const thinkingBody = textNode('div', 'thinking-body', '');
      thinking.append(thinkingBody);
      const content = textNode('div', 'content', '');
      card.body.append(thinking, content);
      state.currentAssistant = { ...card, taskId, round, thinking, thinkingBody, content };
      return state.currentAssistant;
    }

    function scheduleFlush() {
      if (state.flushScheduled) return;
      state.flushScheduled = true;
      requestAnimationFrame(() => {
        state.flushScheduled = false;
        const assistant = state.currentAssistant;
        if (!assistant) return;
        if (state.pendingThinking) {
          assistant.thinkingBody.textContent += state.pendingThinking;
          state.pendingThinking = '';
        }
        if (state.pendingText) {
          assistant.content.textContent += state.pendingText;
          state.pendingText = '';
        }
        if (!assistant.thinkingBody.textContent.trim()) assistant.thinking.style.display = 'none';
        else assistant.thinking.style.display = '';
        scrollIfNeeded();
      });
    }

    function appendToolCall(data) {
      const assistant = ensureAssistant(data);
      const card = document.createElement('div');
      card.className = 'tool-card';
      const head = document.createElement('div');
      head.className = 'tool-head';
      head.append(textNode('strong', '', `Tool: ${data.name || 'unknown'}`), textNode('span', 'muted', `round ${data.round || ''}`));
      const body = document.createElement('div');
      body.className = 'tool-body';
      const args = document.createElement('pre');
      args.textContent = JSON.stringify(data.arguments || {}, null, 2);
      body.append(args);
      card.append(head, body);
      assistant.body.append(card);
      const keyPrefix = `${data.task_id || state.currentTask}:${data.round || state.currentRound}:${data.tool_index || 1}:${data.name || ''}`;
      const key = `${keyPrefix}:${state.toolCards.size}`;
      state.toolCards.set(keyPrefix, { card, body });
      state.toolCards.set(key, { card, body });
      scrollIfNeeded();
    }

    function appendToolResult(data) {
      const keyPrefix = `${data.task_id || state.currentTask}:${data.round || state.currentRound}:${data.tool_index || 1}:${data.name || ''}`;
      let match = state.toolCards.get(keyPrefix);
      if (!match) {
        appendToolCall(data);
        match = state.toolCards.get(keyPrefix);
      }
      const output = textNode('div', 'tool-output', data.output || '');
      match.body.append(output);
      scrollIfNeeded();
    }

    function appendSystem(kind, title, bodyText, meta) {
      const card = bubble(kind, title, meta || '');
      card.body.append(textNode('div', 'content', bodyText || ''));
    }

    function statBox(label, value) {
      const box = document.createElement('div');
      box.className = 'reduction-stat';
      box.append(textNode('span', '', label), textNode('strong', '', String(value ?? '-')));
      return box;
    }

    function tokenChip(token, kind) {
      const chip = document.createElement('div');
      chip.className = `token-chip ${kind}`;
      chip.title = `id=${token.id} source=${token.source} score=${token.score} raw=${token.raw_score}`;
      chip.append(textNode('span', 'token-text', token.text || ''));
      chip.append(textNode('span', 'token-score', `${token.score ?? 0}`));
      return chip;
    }

    function tokenPanel(title, tokens, kind) {
      const panel = document.createElement('div');
      panel.className = 'token-panel';
      panel.append(textNode('h3', '', `${title} (${(tokens || []).length})`));
      const list = document.createElement('div');
      list.className = 'token-list';
      if (!tokens || !tokens.length) {
        list.append(textNode('span', 'muted', 'No sampled tokens.'));
      } else {
        tokens.forEach(token => list.append(tokenChip(token, kind)));
      }
      panel.append(list);
      return panel;
    }

    function sourceTable(counts) {
      const table = document.createElement('table');
      table.className = 'source-table';
      const head = document.createElement('thead');
      head.innerHTML = '<tr><th>source</th><th>eligible</th><th>kept</th><th>cut</th></tr>';
      const body = document.createElement('tbody');
      Object.entries(counts || {}).forEach(([source, row]) => {
        const tr = document.createElement('tr');
        [source, row.eligible, row.kept, row.cut].forEach(value => tr.append(textNode('td', '', String(value ?? 0))));
        body.append(tr);
      });
      table.append(head, body);
      return table;
    }

    function appendReduction(data, eventTime) {
      const card = bubble('reduction', 'Context Reduced', `${data.task_id || state.currentTask || ''} / round ${data.round || ''}`);
      card.head.lastChild.textContent = eventTime;
      const grid = document.createElement('div');
      grid.className = 'reduction-grid';
      grid.append(
        statBox('kept / eligible', `${data.kept_tokens}/${data.eligible_tokens}`),
        statBox('cut', data.cut_tokens),
        statBox('messages', `${data.messages_before}->${data.messages_after}`),
        statBox('chars', `${data.chars_before}->${data.chars_after}`),
        statBox('score range', `${data.min_kept_score}-${data.max_kept_score}`),
        statBox('tail messages', data.tail_messages),
        statBox('trim request', data.trim_tokens_requested),
        statBox('keep floor', data.keep_tokens_floor),
        statBox('available', data.available_tokens),
        statBox('sources', (data.sources || []).join(', '))
      );
      const columns = document.createElement('div');
      columns.className = 'token-columns';
      columns.append(
        tokenPanel('Kept samples (original order)', data.kept_token_samples || [], 'kept'),
        tokenPanel('Highest-scoring cut samples', data.cut_token_samples || [], 'cut')
      );
      const preview = document.createElement('details');
      preview.className = 'preview-details';
      preview.append(textNode('summary', '', 'Retained context preview'));
      preview.append(textNode('div', 'thinking-body', data.kept_preview || ''));
      const actions = document.createElement('div');
      actions.className = 'card-actions';
      const compareButton = textNode('button', '', 'Compare Context');
      compareButton.onclick = () => openContextCompare(data);
      actions.append(compareButton, textNode('span', 'muted', 'Side-by-side current context vs the unpruned snapshot before this incremental trim.'));
      card.body.append(grid, columns, sourceTable(data.source_counts || {}), preview, actions);
      scrollIfNeeded();
    }

    function openContextCompare(data) {
      compareSubtitle.textContent = `${data.task_id || state.currentTask || ''} / round ${data.round || ''}`;
      compareNote.textContent = `Trimmed ${data.cut_tokens || 0} low-importance tokens this pass, with a request of ${data.trim_tokens_requested || 0} and a floor of ${data.keep_tokens_floor || 0}. Kept ${data.kept_tokens || 0}/${data.eligible_tokens || 0} eligible tokens, preserving ${data.tail_messages || 0} recent messages verbatim.`;
      prunedContext.textContent = data.pruned_context_preview || '';
      unprunedContext.textContent = data.unpruned_context_preview || '';
      compareModal.classList.add('open');
    }

    function appendEvent(event) {
      const type = event.type;
      const data = event.data || {};
      updateStats(type, data);

      if (type === 'run_start') {
        tasksEl.replaceChildren();
        (data.tasks || []).forEach(ensureTaskPill);
        appendSystem('system', 'Run Started', `Run root: ${data.run_root || ''}\\nMode: ${data.verify_only ? 'verify-only' : 'agent'}`, `${event.time.toFixed(2)}s`);
      } else if (type === 'model_load_start') {
        appendSystem('system', 'Loading Model', JSON.stringify(data, null, 2), `${event.time.toFixed(2)}s`);
      } else if (type === 'model_load_done') {
        appendSystem('system', 'Model Ready', data.model || '', `${event.time.toFixed(2)}s`);
      } else if (type === 'task_start') {
        state.currentAssistant = null;
        appendSystem('system', `Task: ${data.task_id}`, `${data.title || ''}\\n${data.summary || ''}\\n${data.workdir || ''}`, `${event.time.toFixed(2)}s`);
      } else if (type === 'round_start') {
        state.currentRound = data.round || 0;
        ensureAssistant(data);
      } else if (type === 'thinking_delta') {
        ensureAssistant(data);
        state.pendingThinking += data.text || '';
        scheduleFlush();
      } else if (type === 'text_delta') {
        ensureAssistant(data);
        state.pendingText += data.text || '';
        scheduleFlush();
      } else if (type === 'text_final') {
        const assistant = ensureAssistant(data);
        state.pendingText = '';
        assistant.content.textContent = data.text || assistant.content.textContent;
        scrollIfNeeded();
      } else if (type === 'tool_call') {
        appendToolCall(data);
      } else if (type === 'tool_result') {
        appendToolResult(data);
      } else if (type === 'generation_stats') {
        const assistant = ensureAssistant(data);
        assistant.head.lastChild.textContent = `tokens/s ${data.tokens_per_second ?? '-'} · ${data.completion_tokens ?? '?'} tokens`;
      } else if (type === 'context_reduction') {
        appendReduction(data, `${event.time.toFixed(2)}s`);
      } else if (type === 'verification') {
        const cls = data.successful ? 'verification pass' : 'verification fail';
        appendSystem(cls, data.successful ? 'Verification Passed' : 'Verification Failed', `score=${data.passed}/${data.total}\\n${data.stderr || ''}`, `${data.duration_seconds || 0}s`);
      } else if (type === 'agent_error') {
        appendSystem('error', 'Agent Error', data.error || '', `${event.time.toFixed(2)}s`);
      } else if (type === 'summary') {
        appendSystem('summary', 'Summary', JSON.stringify(data, null, 2), `${event.time.toFixed(2)}s`);
      }
    }

    fetch('/history').then(r => r.json()).then(rows => rows.forEach(appendEvent));
    const source = new EventSource('/events');
    source.onopen = () => statusEl.textContent = 'live';
    source.onerror = () => statusEl.textContent = 'reconnecting';
    source.onmessage = msg => appendEvent(JSON.parse(msg.data));
  </script>
</body>
</html>
""".replace("__TITLE__", html.escape(title))


def start_monitor(host: str, port: int) -> MonitorServer:
    state = MonitorState()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            if self.path == "/" or self.path.startswith("/?"):
                body = _monitor_html().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if self.path == "/history":
                body = json.dumps(state.snapshot()).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if self.path == "/events":
                subscriber = state.subscribe()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                try:
                    while True:
                        event = subscriber.get(timeout=15)
                        payload = json.dumps(event, ensure_ascii=False)
                        self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, queue.Empty):
                    pass
                finally:
                    state.unsubscribe(subscriber)
                return

            self.send_error(404)

    class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True
        allow_reuse_address = True

    server = ThreadingHTTPServer((host, port), Handler)
    actual_host, actual_port = server.server_address
    display_host = "localhost" if actual_host in ("0.0.0.0", "::") else actual_host
    thread = threading.Thread(target=server.serve_forever, name="benchmark-monitor", daemon=True)
    thread.start()
    return MonitorServer(state, server, thread, f"http://{display_host}:{actual_port}")


def load_tasks(tasks_dir: Path, selected: list[str] | None) -> list[TaskSpec]:
    if not tasks_dir.exists():
        raise SystemExit(f"tasks directory not found: {tasks_dir}")

    wanted = set(selected or [])
    specs: list[TaskSpec] = []
    for path in sorted(p for p in tasks_dir.iterdir() if p.is_dir()):
        if wanted and path.name not in wanted:
            continue
        metadata_path = path / "metadata.json"
        prompt_path = path / "prompt.md"
        repo_path = path / "repo"
        if not metadata_path.exists() or not prompt_path.exists() or not repo_path.exists():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        prompt = prompt_path.read_text(encoding="utf-8")
        specs.append(TaskSpec(path.name, path, metadata, prompt))

    missing = wanted - {task.task_id for task in specs}
    if missing:
        raise SystemExit(f"unknown task id(s): {', '.join(sorted(missing))}")
    return specs


def make_run_root(runs_dir: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = runs_dir / f"run-{stamp}"
    suffix = 2
    while candidate.exists():
        candidate = runs_dir / f"run-{stamp}-{suffix}"
        suffix += 1
    candidate.mkdir(parents=True)
    return candidate


def copy_task_repo(task: TaskSpec, run_root: Path) -> Path:
    destination = run_root / task.task_id
    shutil.copytree(task.path / "repo", destination)
    return destination


def run_verification(workdir: Path, timeout: float) -> Score:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(workdir) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        proc = subprocess.run(
            [sys.executable, "-c", VERIFY_CODE],
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode(errors="replace")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode(errors="replace")
        return Score(
            passed=0,
            total=0,
            successful=False,
            duration_seconds=timeout,
            stdout=stdout,
            stderr=(stderr + f"\nverification timed out after {timeout:.1f}s").strip(),
            returncode=-1,
        )

    payload = None
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARKER):
            payload = json.loads(line[len(RESULT_MARKER):])
            break

    if payload is None:
        return Score(
            passed=0,
            total=0,
            successful=False,
            duration_seconds=0.0,
            stdout=proc.stdout,
            stderr=proc.stderr,
            returncode=proc.returncode,
        )

    return Score(
        passed=int(payload["passed"]),
        total=int(payload["total"]),
        successful=bool(payload["successful"]),
        duration_seconds=float(payload["duration_seconds"]),
        stdout=proc.stdout,
        stderr=proc.stderr,
        returncode=proc.returncode,
    )


def resolve_model_path(model: str, models_dir: str) -> str:
    direct = Path(model)
    if direct.exists():
        return str(direct)
    under_models = Path(models_dir) / model
    if under_models.exists():
        return str(under_models)
    return model


def load_engine(args: argparse.Namespace):
    import torch

    from inference.engine import LocalEngine

    engine = LocalEngine()
    dtype = torch.bfloat16
    model_path = resolve_model_path(args.model, args.models_dir)
    engine.load(model_path, dtype=dtype, device=args.device, quantization=args.quantize)
    return engine


def run_agent_on_task(
    task: TaskSpec,
    workdir: Path,
    engine,
    args: argparse.Namespace,
    palette: Palette,
    monitor: MonitorState | None = None,
) -> tuple[int, float, str | None, list[dict[str, Any]]]:
    from harness.agent import Agent
    from harness.tools.base import default_tools

    agent = Agent(
        engine,
        default_tools(working_directory=str(workdir)),
        system_prompt=HEADLESS_SYSTEM,
        max_tool_rounds=args.max_rounds,
    )

    user_prompt = f"""
    {task.prompt}

    Current workspace: {workdir}

    Start by inspecting the README and tests, then fix the implementation.
    """
    agent.start_turn(textwrap.dedent(user_prompt).strip())

    old_cwd = Path.cwd()
    os.chdir(workdir)
    started = time.perf_counter()
    rounds = 0
    reducer = build_context_reducer(args)
    try:
        for round_index in range(1, args.max_rounds + 1):
            rounds = round_index
            pending: list[dict] = []
            final_text = ""
            stats: dict[str, Any] | None = None
            done = False

            print(palette.cyan(f"  round {round_index}"), flush=True)
            if monitor:
                monitor.publish("round_start", {"task_id": task.task_id, "round": round_index})
            for event in agent.generate_round(
                temperature=args.temperature,
                max_new_tokens=args.max_new_tokens,
                token_importance=reducer is not None,
                token_importance_interval=args.importance_sample_interval,
            ):
                if monitor and args.monitor_stream == "all" and event.type in ("thinking_delta", "text_delta"):
                    monitor.publish(event.type, {"task_id": task.task_id, "round": round_index, "text": str(event.data)})
                if event.type == "text_final":
                    final_text = str(event.data or "").strip()
                    if monitor and args.monitor_stream in ("final", "all"):
                        monitor.publish("text_final", {"task_id": task.task_id, "round": round_index, "text": final_text})
                elif event.type == "gen_stats" and isinstance(event.data, dict):
                    stats = event.data
                    if monitor:
                        monitor.publish("generation_stats", {"task_id": task.task_id, "round": round_index, **stats})
                elif event.type == "tool_call_pending" and isinstance(event.data, dict):
                    pending.append(event.data)
                elif event.type == "done":
                    done = True
                elif event.type == "error":
                    if monitor:
                        monitor.publish("agent_error", {"task_id": task.task_id, "round": round_index, "error": str(event.data)})
                    return rounds, time.perf_counter() - started, str(event.data), reducer.events if reducer else []

            if stats:
                prompt_tokens = stats.get("prompt_tokens", "?")
                completion_tokens = stats.get("completion_tokens", "?")
                tok_s = stats.get("tokens_per_second", "?")
                print(f"    generated: prompt={prompt_tokens} completion={completion_tokens} tok/s={tok_s}")

            if final_text and not args.quiet_text:
                print("    assistant:")
                print(textwrap.indent(truncate(final_text, args.text_limit), "      "))

            if done or not pending:
                return rounds, time.perf_counter() - started, None, reducer.events if reducer else []

            if reducer is not None:
                reduction = reducer.reduce(
                    agent,
                    getattr(engine, "last_token_importance", None),
                    round_index=round_index,
                )
                if reduction:
                    print(
                        "    context reduction: "
                        f"kept={reduction['kept_tokens']}/{reduction['eligible_tokens']} "
                        f"cut={reduction['cut_tokens']} "
                        f"trim_request={reduction['trim_tokens_requested']} "
                        f"floor={reduction['keep_tokens_floor']} "
                        f"messages={reduction['messages_before']}->{reduction['messages_after']} "
                        f"chars={reduction['chars_before']}->{reduction['chars_after']}"
                    )
                    if monitor:
                        monitor.publish("context_reduction", {"task_id": task.task_id, **reduction})

            for tool_index, tool_call in enumerate(pending, start=1):
                name = str(tool_call.get("name"))
                arguments = tool_call.get("arguments") if isinstance(tool_call.get("arguments"), dict) else {}
                print(f"    tool: {name} {json.dumps(arguments, sort_keys=True)}")
                if monitor:
                    monitor.publish(
                        "tool_call",
                        {
                            "task_id": task.task_id,
                            "round": round_index,
                            "tool_index": tool_index,
                            "name": name,
                            "arguments": arguments,
                        },
                    )
                output = agent.execute_tool(name, arguments)
                if monitor:
                    monitor.publish(
                        "tool_result",
                        {
                            "task_id": task.task_id,
                            "round": round_index,
                            "tool_index": tool_index,
                            "name": name,
                            "output": truncate(output, args.monitor_tool_output_limit),
                        },
                    )
                if not args.quiet_tools:
                    print(textwrap.indent(truncate(output, args.tool_output_limit), "      "))

        error = "max tool rounds exceeded"
        if monitor:
            monitor.publish("agent_error", {"task_id": task.task_id, "round": rounds, "error": error})
        return rounds, time.perf_counter() - started, error, reducer.events if reducer else []
    finally:
        os.chdir(old_cwd)


def build_context_reducer(args: argparse.Namespace) -> ImportanceContextReducer | None:
    if args.context_reduction == "none":
        return None
    sources = {"prompt", "generated"} if args.importance_sources == "all" else {args.importance_sources}
    return ImportanceContextReducer(
        keep_tokens=args.importance_keep_tokens,
        trim_tokens=args.importance_trim_tokens,
        tail_messages=args.importance_tail_messages,
        min_score=args.importance_min_score,
        sources=sources,
        audit_tokens=args.importance_audit_tokens,
        context_preview_chars=args.importance_context_preview_chars,
    )


def print_score(task_id: str, score: Score, palette: Palette) -> None:
    label = f"{score.passed}/{score.total}"
    status = palette.green("PASS") if score.successful else palette.red("FAIL")
    print(f"  verify: {status} score={label} tests={score.duration_seconds:.2f}s")
    if not score.successful:
        stderr = truncate(score.stderr.strip(), 1800)
        if stderr:
            print(textwrap.indent(stderr, "    "))


def print_summary(results: list[TaskResult], run_root: Path, palette: Palette) -> None:
    print()
    print(palette.bold("Summary"))
    print("-" * 88)
    print(f"{'task':28} {'score':>9} {'status':>8} {'agent_s':>9} {'test_s':>8}  run_dir")
    print("-" * 88)
    total_passed = 0
    total_tests = 0
    for result in results:
        score = result.score
        total_passed += score.passed
        total_tests += score.total
        status_text = "PASS" if score.successful else "FAIL"
        if result.error:
            status_text = "ERROR"
        status_cell = f"{status_text:>8}"
        status = palette.green(status_cell) if score.successful and not result.error else palette.red(status_cell)
        print(
            f"{result.task.task_id:28} "
            f"{score.passed:>4}/{score.total:<4} "
            f"{status} "
            f"{result.agent_seconds:>9.1f} "
            f"{score.duration_seconds:>8.2f}  "
            f"{result.run_dir}"
        )
    print("-" * 88)
    overall = f"{total_passed}/{total_tests}"
    print(f"overall score: {palette.bold(overall)}")
    print(f"run root: {run_root}")


def context_reduction_config(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "policy": args.context_reduction,
        "importance_keep_tokens": args.importance_keep_tokens,
        "importance_trim_tokens": args.importance_trim_tokens,
        "importance_tail_messages": args.importance_tail_messages,
        "importance_min_score": args.importance_min_score,
        "importance_audit_tokens": args.importance_audit_tokens,
        "importance_context_preview_chars": args.importance_context_preview_chars,
        "importance_sample_interval": args.importance_sample_interval,
        "importance_sources": args.importance_sources,
    }


def write_results_json(path: Path, args: argparse.Namespace, results: list[TaskResult], run_root: Path) -> None:
    payload = {
        "run_root": str(run_root),
        "model": args.model,
        "device": args.device,
        "quantize": args.quantize,
        "temperature": args.temperature,
        "max_new_tokens": args.max_new_tokens,
        "max_rounds": args.max_rounds,
        "context_reduction": context_reduction_config(args),
        "overall": {
            "passed": sum(result.score.passed for result in results),
            "total": sum(result.score.total for result in results),
            "successful_tasks": sum(1 for result in results if result.score.successful and not result.error),
            "task_count": len(results),
        },
        "tasks": [
            {
                "id": result.task.task_id,
                "title": result.task.metadata.get("title", result.task.task_id),
                "run_dir": str(result.run_dir),
                "score": {
                    "passed": result.score.passed,
                    "total": result.score.total,
                    "successful": result.score.successful,
                    "duration_seconds": result.score.duration_seconds,
                    "returncode": result.score.returncode,
                },
                "agent_rounds": result.agent_rounds,
                "agent_seconds": round(result.agent_seconds, 3),
                "error": result.error,
                "context_reductions": result.reduction_events or [],
            }
            for result in results
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote results json: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local benchmark tasks through the headless agent harness.")
    parser.add_argument("--task", action="append", help="Task id to run. Repeat for multiple tasks. Defaults to all tasks.")
    parser.add_argument("--tasks-dir", default=str(TASKS_DIR), help="Directory containing task definitions.")
    parser.add_argument("--runs-dir", default=str(RUNS_DIR), help="Directory for disposable benchmark workspaces.")
    parser.add_argument("--verify-only", action="store_true", help="Copy each task and run tests without invoking the agent.")
    parser.add_argument("--list", action="store_true", help="List available tasks and exit.")

    parser.add_argument("--model", help="Model directory or model name under --models-dir.")
    parser.add_argument("--models-dir", default="models", help="Directory containing local models.")
    parser.add_argument("--device", default="cuda", help="Inference device, for example cuda or cpu.")
    parser.add_argument("--quantize", choices=["4bit", "8bit"], default=None, help="Optional quantization mode.")

    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-new-tokens", type=int, default=3072)
    parser.add_argument("--max-rounds", type=int, default=20)
    parser.add_argument("--test-timeout", type=float, default=30.0)

    parser.add_argument("--quiet-tools", action="store_true", help="Hide tool outputs.")
    parser.add_argument("--quiet-text", action="store_true", help="Hide assistant final text per round.")
    parser.add_argument("--tool-output-limit", type=int, default=1200)
    parser.add_argument("--text-limit", type=int, default=800)
    parser.add_argument("--color", choices=["auto", "always", "never"], default="auto")
    parser.add_argument(
        "--context-reduction",
        choices=["none", "importance"],
        default="none",
        help="Optional context reduction policy. 'importance' incrementally trims low-importance tokens from older history.",
    )
    parser.add_argument("--importance-keep-tokens", type=int, default=2048, help="Minimum number of eligible importance tokens to keep as a floor.")
    parser.add_argument("--importance-trim-tokens", type=int, default=256, help="Number of low-importance eligible tokens to trim per reduction pass.")
    parser.add_argument("--importance-tail-messages", type=int, default=6, help="Recent non-system messages to keep verbatim after reduction.")
    parser.add_argument("--importance-min-score", type=float, default=0.0, help="Minimum normalized importance score required for a token to be kept.")
    parser.add_argument("--importance-audit-tokens", type=int, default=80, help="How many kept/cut token samples to include in monitor and JSON reduction audits.")
    parser.add_argument("--importance-context-preview-chars", type=int, default=12000, help="Max chars per pruned/unpruned context preview in reduction audit events.")
    parser.add_argument("--importance-sample-interval", type=int, default=8, help="Collect attention importance every N decode tokens. Higher values use less GPU memory/time.")
    parser.add_argument(
        "--importance-sources",
        choices=["prompt", "generated", "all"],
        default="prompt",
        help="Which token sources to consider for context reduction.",
    )
    parser.add_argument("--results-json", help="Write machine-readable benchmark results to this JSON file.")
    parser.add_argument("--monitor", action="store_true", help="Serve an optional realtime web monitor for this run.")
    parser.add_argument("--monitor-host", default="127.0.0.1", help="Host for the realtime monitor.")
    parser.add_argument("--monitor-port", type=int, default=8765, help="Port for the realtime monitor. Use 0 for any free port.")
    parser.add_argument("--monitor-open", action="store_true", help="Open the monitor URL in the default browser.")
    parser.add_argument(
        "--monitor-stream",
        choices=["off", "final", "all"],
        default="all",
        help="How much model output to send to the monitor: off, final messages only, or all thinking/text deltas.",
    )
    parser.add_argument("--monitor-tool-output-limit", type=int, default=3000, help="Max chars of each tool result sent to the monitor.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    color_enabled = args.color == "always" or (args.color == "auto" and sys.stdout.isatty())
    palette = Palette(color_enabled)

    tasks = load_tasks(Path(args.tasks_dir), args.task)
    if args.list:
        for task in tasks:
            tags = ", ".join(task.metadata.get("tags", []))
            estimate = task.metadata.get("estimated_context_tokens", "?")
            print(f"{task.task_id:28} {estimate:>6} tokens  {tags}")
        return 0

    if not tasks:
        raise SystemExit("no tasks selected")
    if not args.verify_only and not args.model:
        raise SystemExit("--model is required unless --verify-only or --list is set")
    if args.importance_keep_tokens <= 0:
        raise SystemExit("--importance-keep-tokens must be positive")
    if args.importance_trim_tokens <= 0:
        raise SystemExit("--importance-trim-tokens must be positive")
    if args.importance_tail_messages < 0:
        raise SystemExit("--importance-tail-messages must be non-negative")
    if not 0.0 <= args.importance_min_score <= 1.0:
        raise SystemExit("--importance-min-score must be between 0.0 and 1.0")
    if args.importance_audit_tokens < 0:
        raise SystemExit("--importance-audit-tokens must be non-negative")
    if args.importance_context_preview_chars < 1000:
        raise SystemExit("--importance-context-preview-chars must be at least 1000")
    if args.importance_sample_interval <= 0:
        raise SystemExit("--importance-sample-interval must be positive")

    monitor_server: MonitorServer | None = None
    if args.monitor:
        monitor_server = start_monitor(args.monitor_host, args.monitor_port)
        print(f"monitor: {monitor_server.url}")
        if args.monitor_open:
            webbrowser.open(monitor_server.url)

    try:
        run_root = make_run_root(Path(args.runs_dir))
        if monitor_server:
            monitor_server.state.publish(
                "run_start",
                {
                    "tasks": [task.task_id for task in tasks],
                    "run_root": str(run_root),
                    "verify_only": args.verify_only,
                    "monitor_stream": args.monitor_stream,
                    "context_reduction": context_reduction_config(args),
                },
            )
            if not args.verify_only:
                monitor_server.state.publish("model_load_start", {"model": args.model, "device": args.device, "quantize": args.quantize})

        engine = None if args.verify_only else load_engine(args)
        if monitor_server and not args.verify_only:
            monitor_server.state.publish("model_load_done", {"model": args.model})

        results: list[TaskResult] = []

        print(palette.bold("Agentic Coding Harness Benchmark"))
        print(f"tasks: {len(tasks)}")
        print(f"run root: {run_root}")
        if args.verify_only:
            print("mode: verify-only")
        print()

        for task in tasks:
            print(palette.bold(task.task_id))
            print(f"  {task.metadata.get('title', task.task_id)}")
            workdir = copy_task_repo(task, run_root)
            if monitor_server:
                monitor_server.state.publish(
                    "task_start",
                    {
                        "task_id": task.task_id,
                        "title": task.metadata.get("title", task.task_id),
                        "summary": task.metadata.get("summary", ""),
                        "workdir": str(workdir),
                    },
                )
            error = None
            rounds = 0
            agent_seconds = 0.0
            reduction_events: list[dict[str, Any]] = []

            if not args.verify_only:
                rounds, agent_seconds, error, reduction_events = run_agent_on_task(task, workdir, engine, args, palette, monitor_server.state if monitor_server else None)
                if error:
                    print(f"  agent error: {palette.red(error)}")

            if monitor_server:
                monitor_server.state.publish("verification_start", {"task_id": task.task_id, "workdir": str(workdir)})
            score = run_verification(workdir, args.test_timeout)
            if monitor_server:
                monitor_server.state.publish(
                    "verification",
                    {
                        "task_id": task.task_id,
                        "passed": score.passed,
                        "total": score.total,
                        "successful": score.successful,
                        "duration_seconds": score.duration_seconds,
                        "stderr": truncate(score.stderr.strip(), 3000),
                    },
                )
            print_score(task.task_id, score, palette)
            results.append(TaskResult(task, workdir, score, rounds, agent_seconds, error, reduction_events))
            print()

        if monitor_server:
            monitor_server.state.publish(
                "summary",
                {
                    "passed": sum(result.score.passed for result in results),
                    "total": sum(result.score.total for result in results),
                    "successful_tasks": sum(1 for result in results if result.score.successful and not result.error),
                    "task_count": len(results),
                    "run_root": str(run_root),
                },
            )
        print_summary(results, run_root, palette)
        if args.results_json:
            write_results_json(Path(args.results_json), args, results, run_root)
        return 0 if all(result.score.successful and not result.error for result in results) else 1
    finally:
        if monitor_server:
            time.sleep(0.2)
            monitor_server.stop()


if __name__ == "__main__":
    raise SystemExit(main())
