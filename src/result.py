# Result model shared by exact searches and the bonus planner.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SearchResult:
    # Summary metrics and output paths for one algorithm run.

    algorithm: str
    success: bool
    solution_states: list
    solution_actions: list
    total_cost: float
    expanded_nodes: int
    generated_nodes: int
    max_frontier_size: int
    depth: int
    message: str
    runtime_seconds: float
    trace_path: Optional[str] = None
    timeline_path: Optional[str] = None
    image_path: Optional[str] = None
    gif_path: Optional[str] = None
    extra: dict = field(default_factory=dict)

