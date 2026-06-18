# Readable and structured logging for search expansions.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .utils import ensure_output_dir, json_safe
except ImportError:
    from utils import ensure_output_dir, json_safe


class StepLogger:
    # Collect selected-node, child, frontier, and final-result traces.

    def __init__(
        self,
        algorithm: str = "search",
        verbose: bool = False,
        enabled: bool = True,
        stream: bool = False,
    ) -> None:
        self.algorithm = algorithm
        self.verbose = verbose
        self.enabled = enabled
        self.stream = stream
        self.step = 0
        self.text_lines: list[str] = []
        self.trace_records: list[dict[str, Any]] = []
        self.result_record: dict[str, Any] | None = None

    def mark_iteration(self, message: str) -> None:
        # Insert an iteration marker, used by IDS.
        line = f"\n=== {message} ==="
        self.text_lines.append(line)
        self.trace_records.append({"type": "iteration", "message": message})
        if self.stream:
            print(line)

    def log_expansion(
        self,
        algorithm: str,
        node: Any,
        valid_children: list[dict[str, Any]],
        rejected_children: list[Any],
        frontier_snapshot: list[dict[str, Any]],
        frontier_size: int,
        explored_count: int,
        expanded_nodes: int,
        generated_nodes: int,
        h: float | None = None,
        f: float | None = None,
    ) -> None:
        # Record one expansion with children and frontier metadata.
        self.step += 1
        parent_id = node.parent.node_id if getattr(node, "parent", None) else None
        action = getattr(node, "action", None)
        record = {
            "type": "expansion",
            "step": self.step,
            "algorithm": algorithm,
            "selected_node_id": node.node_id,
            "parent_node_id": parent_id,
            "selected_state": node.state,
            "depth": node.depth,
            "path_cost": node.path_cost,
            "h": h,
            "f": f,
            "action_from_parent": action,
            "valid_children_total": len(valid_children),
            "valid_children": valid_children[:50],
            "rejected_children_total": len(rejected_children),
            "rejected_children": rejected_children[:50] if self.verbose else [],
            "frontier_snapshot": frontier_snapshot[:20],
            "frontier_size": frontier_size,
            "explored_count": explored_count,
            "expanded_nodes": expanded_nodes,
            "generated_nodes": generated_nodes,
        }
        self.trace_records.append(record)
        lines = self._format_expansion(record)
        self.text_lines.extend(lines)
        if self.stream:
            print("\n".join(lines))

    def log_result(self, result: Any) -> None:
        # Record final metrics for an algorithm.
        self.result_record = json_safe(result)
        lines = [
            "",
            f"=== Final Result: {result.algorithm} ===",
            f"Success: {result.success}",
            f"Message: {result.message}",
            f"Final joint path: {result.solution_states}",
            f"Final joint actions: {result.solution_actions}",
            f"Total cost: {result.total_cost}",
            f"Depth: {result.depth}",
            f"Expanded nodes: {result.expanded_nodes}",
            f"Generated nodes: {result.generated_nodes}",
            f"Max frontier size: {result.max_frontier_size}",
            f"Runtime seconds: {result.runtime_seconds:.6f}",
        ]
        self.text_lines.extend(lines)
        if self.stream:
            print("\n".join(lines))

    def save(self, path: str | Path) -> tuple[str, str]:
        # Save text and JSON traces.
        #
        # If ``path`` is a directory, files are named from ``self.algorithm``.
        # If ``path`` has a suffix, it is treated as a text-log path and the JSON
        # trace is placed beside it.
        #
        target = Path(path)
        if target.suffix:
            ensure_output_dir(target.parent)
            log_path = target
            trace_path = target.with_name(target.stem.replace("_log", "") + "_trace.json")
        else:
            ensure_output_dir(target)
            algorithm_name = self.algorithm.lower().replace("*", "star").replace(" ", "_")
            log_path = target / f"{algorithm_name}_log.txt"
            trace_path = target / f"{algorithm_name}_trace.json"

        log_path.write_text("\n".join(self.text_lines) + "\n", encoding="utf-8")
        payload = {
            "algorithm": self.algorithm,
            "trace": json_safe(self.trace_records),
            "result": json_safe(self.result_record),
        }
        trace_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(log_path), str(trace_path)

    def _format_expansion(self, record: dict[str, Any]) -> list[str]:
        lines = [
            "",
            f"Step {record['step']} | Algorithm: {record['algorithm']}",
            f"Selected node ID: {record['selected_node_id']}",
            f"Parent node ID: {record['parent_node_id']}",
            f"Selected state: {record['selected_state']}",
            f"Depth: {record['depth']}",
            f"g(n): {record['path_cost']}",
        ]
        if record.get("h") is not None:
            lines.append(f"h(n): {record['h']}")
        if record.get("f") is not None:
            lines.append(f"f(n): {record['f']}")
        lines.extend(
            [
                f"Action from parent: {record['action_from_parent']}",
                f"Generated valid children: {record['valid_children_total']}",
            ]
        )
        for child in record["valid_children"][:20]:
            lines.append(
                "  "
                f"child={child.get('node_id')} action={child.get('action')} "
                f"state={child.get('state')} step_cost={child.get('step_cost')} "
                f"g={child.get('path_cost')} h={child.get('h')} f={child.get('f')} "
                f"skipped={child.get('skipped')}"
            )
        if record["valid_children_total"] > 20:
            lines.append("  ... valid child list truncated")

        if self.verbose:
            lines.append(f"Rejected children: {record['rejected_children_total']}")
            for rejected in record["rejected_children"][:20]:
                lines.append(
                    "  "
                    f"action={getattr(rejected, 'action', None)} "
                    f"state={getattr(rejected, 'attempted_state', None)} "
                    f"reason={getattr(rejected, 'reason', None)}"
                )
            if record["rejected_children_total"] > 20:
                lines.append("  ... rejected child list truncated")

        lines.extend(
            [
                f"Frontier snapshot first 20 of {record['frontier_size']}:",
            ]
        )
        for item in record["frontier_snapshot"]:
            lines.append(f"  {item}")
        lines.extend(
            [
                f"Explored/visited count: {record['explored_count']}",
                f"Expanded count so far: {record['expanded_nodes']}",
                f"Generated count so far: {record['generated_nodes']}",
            ]
        )
        return lines
