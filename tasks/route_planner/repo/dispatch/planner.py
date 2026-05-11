from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Edge:
    to: str
    minutes: int
    closed: list[tuple[int, int]] = field(default_factory=list)


def _can_traverse(edge: Edge, start: int) -> bool:
    end = start + edge.minutes
    return all(end <= close_start or start >= close_end for close_start, close_end in edge.closed)


def best_route(graph: dict[str, list[Edge]], start: str, end: str, depart_minute: int = 0) -> dict:
    # BUG: This is hop-count BFS and skips closed edges instead of
    # considering waits. It can miss the earliest arrival.
    queue = deque([(start, [start], depart_minute)])
    seen = {start}
    while queue:
        node, path, minute = queue.popleft()
        if node == end:
            return {"path": path, "travel_minutes": minute - depart_minute, "arrival_minute": minute}
        for edge in graph.get(node, []):
            if edge.to in seen or not _can_traverse(edge, minute):
                continue
            seen.add(edge.to)
            queue.append((edge.to, path + [edge.to], minute + edge.minutes))
    raise ValueError(f"no route from {start} to {end}")
