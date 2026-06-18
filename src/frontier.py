# Frontier data structures for classical graph search.

from __future__ import annotations

from collections import deque
import heapq
from itertools import count
from typing import Any


def _node_snapshot(node: Any, priority: float | None = None) -> dict[str, Any]:
    # Return compact node metadata for logs and GUI panels.
    item = {
        "node_id": getattr(node, "node_id", None),
        "state": getattr(node, "state", None),
        "depth": getattr(node, "depth", None),
        "path_cost": getattr(node, "path_cost", None),
    }
    if priority is not None:
        item["priority"] = priority
    return item


class FIFOFrontier:
    # First-in, first-out frontier used by breadth-first search.

    def __init__(self) -> None:
        self._items: deque[Any] = deque()

    def push(self, node: Any, priority: float | None = None) -> None:
        # Add a node to the back of the queue.
        self._items.append(node)

    def pop(self) -> Any:
        # Remove and return the oldest queued node.
        return self._items.popleft()

    def is_empty(self) -> bool:
        # Return True if no nodes are waiting in the frontier.
        return not self._items

    def __len__(self) -> int:
        return len(self._items)

    def snapshot(self, limit: int = 20) -> list[dict[str, Any]]:
        # Return the first ``limit`` queued nodes for trace output.
        return [_node_snapshot(node) for node in list(self._items)[:limit]]


class LIFOFrontier:
    # Last-in, first-out frontier used by depth-first style searches.

    def __init__(self) -> None:
        self._items: list[Any] = []

    def push(self, node: Any, priority: float | None = None) -> None:
        # Push a node onto the stack.
        self._items.append(node)

    def pop(self) -> Any:
        # Pop and return the most recently pushed node.
        return self._items.pop()

    def is_empty(self) -> bool:
        # Return True if the stack has no nodes.
        return not self._items

    def __len__(self) -> int:
        return len(self._items)

    def snapshot(self, limit: int = 20) -> list[dict[str, Any]]:
        # Return the next ``limit`` nodes in pop order.
        return [_node_snapshot(node) for node in reversed(self._items[-limit:])]


class PriorityFrontier:
    # Stable min-priority frontier used by UCS, greedy search, and A*.

    def __init__(self) -> None:
        self._heap: list[tuple[float, int, Any]] = []
        self._counter = count()

    def push(self, node: Any, priority: float | None = None) -> None:
        # Push a node with a priority value and deterministic tie-break.
        if priority is None:
            raise ValueError("PriorityFrontier requires a priority.")
        heapq.heappush(self._heap, (priority, next(self._counter), node))

    def pop(self) -> Any:
        # Pop and return the node with the smallest priority.
        return heapq.heappop(self._heap)[2]

    def is_empty(self) -> bool:
        # Return True if the heap is empty.
        return not self._heap

    def __len__(self) -> int:
        return len(self._heap)

    def snapshot(self, limit: int = 20) -> list[dict[str, Any]]:
        # Return the lowest-priority nodes visible in the heap.
        ordered = sorted(self._heap)[:limit]
        return [_node_snapshot(node, priority) for priority, _counter, node in ordered]

