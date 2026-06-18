# Manual classical search algorithms for centralized MAPF.

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import time
from typing import Any

try:
    from .frontier import FIFOFrontier, LIFOFrontier, PriorityFrontier
    from .models import Node, solution_actions, solution_node_ids, solution_states
    from .result import SearchResult
except ImportError:
    from frontier import FIFOFrontier, LIFOFrontier, PriorityFrontier
    from models import Node, solution_actions, solution_node_ids, solution_states
    from result import SearchResult


Heuristic = Callable[[Any, Any], float]


@dataclass
class NodeFactory:
    # Assign deterministic IDs to generated search-tree nodes.

    next_id: int = 1

    def create(
        self,
        state: tuple,
        parent: Node | None = None,
        action: tuple | None = None,
        path_cost: float = 0.0,
        depth: int = 0,
    ) -> Node:
        node = Node(
            state=state,
            parent=parent,
            action=action,
            path_cost=path_cost,
            depth=depth,
            node_id=self.next_id,
        )
        self.next_id += 1
        return node


def breadth_first_search(problem: Any, logger: Any = None) -> SearchResult:
    # Run breadth-first graph search over joint states.
    start_time = time.perf_counter()
    factory = NodeFactory()
    root = factory.create(problem.initial_state())
    generated_nodes = 1

    if problem.is_goal(root.state):
        return _result("BFS", True, root, "Initial state is already the goal.", 0, 1, 0, start_time)

    frontier = FIFOFrontier()
    frontier.push(root)
    visited = {root.state}
    expanded_nodes = 0
    max_frontier_size = len(frontier)

    while not frontier.is_empty():
        if _hit_expansion_limit(problem, expanded_nodes):
            return _failure_result("BFS", "Maximum expansion limit reached.", expanded_nodes, generated_nodes, max_frontier_size, start_time)

        node = frontier.pop()
        expanded_nodes += 1
        valid_records, rejected_records = problem.generate_children(
            node.state,
            include_rejected=_include_rejected(logger),
        )

        child_infos = []
        goal_node: Node | None = None
        for record in valid_records:
            if record.state in visited:
                child_infos.append(_skipped_child_info(record, "already visited"))
                continue
            child = factory.create(
                state=record.state,
                parent=node,
                action=record.action,
                path_cost=node.path_cost + record.cost,
                depth=node.depth + 1,
            )
            generated_nodes += 1
            visited.add(child.state)
            child_infos.append(_child_info(child, record.cost))
            if problem.is_goal(child.state):
                goal_node = child
                break
            frontier.push(child)

        max_frontier_size = max(max_frontier_size, len(frontier))
        _log_expansion(
            logger,
            "BFS",
            node,
            child_infos,
            rejected_records,
            frontier,
            len(visited),
            expanded_nodes,
            generated_nodes,
        )
        if goal_node is not None:
            return _result("BFS", True, goal_node, "Goal found by BFS.", expanded_nodes, generated_nodes, max_frontier_size, start_time)

    return _failure_result("BFS", "No solution found.", expanded_nodes, generated_nodes, max_frontier_size, start_time)


def uniform_cost_search(problem: Any, logger: Any = None) -> SearchResult:
    # Run uniform-cost search ordered by accumulated path cost.
    return _cost_search(problem, logger, algorithm="UCS", heuristic=None, use_f_cost=False)


def depth_first_search(problem: Any, logger: Any = None) -> SearchResult:
    # Run deterministic depth-first graph search.
    start_time = time.perf_counter()
    factory = NodeFactory()
    root = factory.create(problem.initial_state())
    generated_nodes = 1
    if problem.is_goal(root.state):
        return _result("DFS", True, root, "Initial state is already the goal.", 0, 1, 0, start_time)

    frontier = LIFOFrontier()
    frontier.push(root)
    visited = {root.state}
    expanded_nodes = 0
    max_frontier_size = len(frontier)

    while not frontier.is_empty():
        if _hit_expansion_limit(problem, expanded_nodes):
            return _failure_result("DFS", "Maximum expansion limit reached.", expanded_nodes, generated_nodes, max_frontier_size, start_time)

        node = frontier.pop()
        if problem.is_goal(node.state):
            return _result("DFS", True, node, "Goal found by DFS.", expanded_nodes, generated_nodes, max_frontier_size, start_time)

        expanded_nodes += 1
        valid_records, rejected_records = problem.generate_children(
            node.state,
            include_rejected=_include_rejected(logger),
        )
        child_nodes: list[tuple[Node, float]] = []
        child_infos = []
        for record in valid_records:
            if record.state in visited:
                child_infos.append(_skipped_child_info(record, "already visited"))
                continue
            child = factory.create(
                state=record.state,
                parent=node,
                action=record.action,
                path_cost=node.path_cost + record.cost,
                depth=node.depth + 1,
            )
            generated_nodes += 1
            visited.add(child.state)
            child_nodes.append((child, record.cost))
            child_infos.append(_child_info(child, record.cost))

        for child, _step_cost in reversed(child_nodes):
            frontier.push(child)

        max_frontier_size = max(max_frontier_size, len(frontier))
        _log_expansion(
            logger,
            "DFS",
            node,
            child_infos,
            rejected_records,
            frontier,
            len(visited),
            expanded_nodes,
            generated_nodes,
        )

    return _failure_result("DFS", "No solution found.", expanded_nodes, generated_nodes, max_frontier_size, start_time)


def depth_limited_search(problem: Any, limit: int, logger: Any = None) -> SearchResult:
    # Run graph-aware depth-limited search.
    return _depth_limited_core(problem, limit, logger, algorithm="DLS")


def iterative_deepening_search(problem: Any, max_depth: int, logger: Any = None) -> SearchResult:
    # Run DLS repeatedly for limits from 0 through ``max_depth``.
    start_time = time.perf_counter()
    total_expanded = 0
    total_generated = 0
    max_frontier_size = 0
    last_message = "No solution found."

    for limit in range(max_depth + 1):
        if logger is not None and hasattr(logger, "mark_iteration"):
            logger.mark_iteration(f"IDS iteration with depth limit = {limit}")
        result = _depth_limited_core(problem, limit, logger, algorithm=f"IDS(limit={limit})")
        total_expanded += result.expanded_nodes
        total_generated += result.generated_nodes
        max_frontier_size = max(max_frontier_size, result.max_frontier_size)
        last_message = result.message
        if result.success:
            result.algorithm = "IDS"
            result.expanded_nodes = total_expanded
            result.generated_nodes = total_generated
            result.max_frontier_size = max_frontier_size
            result.runtime_seconds = time.perf_counter() - start_time
            result.message = f"Goal found by IDS at depth limit {limit}."
            return result

    return SearchResult(
        algorithm="IDS",
        success=False,
        solution_states=[],
        solution_actions=[],
        total_cost=0.0,
        expanded_nodes=total_expanded,
        generated_nodes=total_generated,
        max_frontier_size=max_frontier_size,
        depth=0,
        message=f"IDS exhausted limits through {max_depth}. Last status: {last_message}",
        runtime_seconds=time.perf_counter() - start_time,
    )


def greedy_best_first_search(
    problem: Any,
    heuristic: Heuristic,
    logger: Any = None,
) -> SearchResult:
    # Run Greedy Best-First Search ordered by ``h(n)``.
    start_time = time.perf_counter()
    factory = NodeFactory()
    root = factory.create(problem.initial_state())
    generated_nodes = 1
    frontier = PriorityFrontier()
    frontier.push(root, heuristic(problem, root.state))
    visited = {root.state}
    expanded_nodes = 0
    max_frontier_size = len(frontier)

    while not frontier.is_empty():
        if _hit_expansion_limit(problem, expanded_nodes):
            return _failure_result("Greedy", "Maximum expansion limit reached.", expanded_nodes, generated_nodes, max_frontier_size, start_time)

        node = frontier.pop()
        h_value = heuristic(problem, node.state)
        if problem.is_goal(node.state):
            return _result("Greedy", True, node, "Goal found by Greedy Best-First Search.", expanded_nodes, generated_nodes, max_frontier_size, start_time)

        expanded_nodes += 1
        valid_records, rejected_records = problem.generate_children(
            node.state,
            include_rejected=_include_rejected(logger),
        )
        child_infos = []
        for record in valid_records:
            if record.state in visited:
                child_infos.append(_skipped_child_info(record, "already visited"))
                continue
            child_h = heuristic(problem, record.state)
            child = factory.create(
                state=record.state,
                parent=node,
                action=record.action,
                path_cost=node.path_cost + record.cost,
                depth=node.depth + 1,
            )
            generated_nodes += 1
            visited.add(child.state)
            frontier.push(child, child_h)
            child_infos.append(_child_info(child, record.cost, h=child_h, f=child_h))

        max_frontier_size = max(max_frontier_size, len(frontier))
        _log_expansion(
            logger,
            "Greedy",
            node,
            child_infos,
            rejected_records,
            frontier,
            len(visited),
            expanded_nodes,
            generated_nodes,
            h=h_value,
            f=h_value,
        )

    return _failure_result("Greedy", "No solution found.", expanded_nodes, generated_nodes, max_frontier_size, start_time)


def a_star_search(
    problem: Any,
    heuristic: Heuristic,
    logger: Any = None,
) -> SearchResult:
    # Run A* ordered by ``g(n) + h(n)``.
    return _cost_search(problem, logger, algorithm="A*", heuristic=heuristic, use_f_cost=True)


def _cost_search(
    problem: Any,
    logger: Any,
    algorithm: str,
    heuristic: Heuristic | None,
    use_f_cost: bool,
) -> SearchResult:
    start_time = time.perf_counter()
    factory = NodeFactory()
    root = factory.create(problem.initial_state())
    generated_nodes = 1
    frontier = PriorityFrontier()
    root_h = heuristic(problem, root.state) if heuristic else 0.0
    frontier.push(root, root.path_cost + root_h if use_f_cost else root.path_cost)
    best_g = {root.state: 0.0}
    expanded_nodes = 0
    max_frontier_size = len(frontier)

    while not frontier.is_empty():
        if _hit_expansion_limit(problem, expanded_nodes):
            return _failure_result(algorithm, "Maximum expansion limit reached.", expanded_nodes, generated_nodes, max_frontier_size, start_time)

        node = frontier.pop()
        if node.path_cost > best_g.get(node.state, float("inf")):
            continue
        h_value = heuristic(problem, node.state) if heuristic else 0.0
        f_value = node.path_cost + h_value if use_f_cost else node.path_cost
        if problem.is_goal(node.state):
            return _result(algorithm, True, node, f"Goal found by {algorithm}.", expanded_nodes, generated_nodes, max_frontier_size, start_time)

        expanded_nodes += 1
        valid_records, rejected_records = problem.generate_children(
            node.state,
            include_rejected=_include_rejected(logger),
        )
        child_infos = []
        for record in valid_records:
            new_g = node.path_cost + record.cost
            if new_g >= best_g.get(record.state, float("inf")):
                child_infos.append(_skipped_child_info(record, "not a cheaper path"))
                continue
            best_g[record.state] = new_g
            child_h = heuristic(problem, record.state) if heuristic else 0.0
            priority = new_g + child_h if use_f_cost else new_g
            child = factory.create(
                state=record.state,
                parent=node,
                action=record.action,
                path_cost=new_g,
                depth=node.depth + 1,
            )
            generated_nodes += 1
            frontier.push(child, priority)
            child_infos.append(_child_info(child, record.cost, h=child_h if heuristic else None, f=priority))

        max_frontier_size = max(max_frontier_size, len(frontier))
        _log_expansion(
            logger,
            algorithm,
            node,
            child_infos,
            rejected_records,
            frontier,
            len(best_g),
            expanded_nodes,
            generated_nodes,
            h=h_value if heuristic else None,
            f=f_value,
        )

    return _failure_result(algorithm, "No solution found.", expanded_nodes, generated_nodes, max_frontier_size, start_time)


def _depth_limited_core(problem: Any, limit: int, logger: Any, algorithm: str) -> SearchResult:
    start_time = time.perf_counter()
    factory = NodeFactory()
    root = factory.create(problem.initial_state())
    generated_nodes = 1
    if problem.is_goal(root.state):
        return _result(algorithm, True, root, "Initial state is already the goal.", 0, 1, 0, start_time)

    frontier = LIFOFrontier()
    frontier.push(root)
    best_depth_seen = {root.state: 0}
    expanded_nodes = 0
    max_frontier_size = len(frontier)
    cutoff = False

    while not frontier.is_empty():
        if _hit_expansion_limit(problem, expanded_nodes):
            return _failure_result(algorithm, "Maximum expansion limit reached.", expanded_nodes, generated_nodes, max_frontier_size, start_time)

        node = frontier.pop()
        if problem.is_goal(node.state):
            return _result(algorithm, True, node, f"Goal found by {algorithm}.", expanded_nodes, generated_nodes, max_frontier_size, start_time)
        if node.depth >= limit:
            cutoff = True
            continue

        expanded_nodes += 1
        valid_records, rejected_records = problem.generate_children(
            node.state,
            include_rejected=_include_rejected(logger),
        )
        child_nodes: list[tuple[Node, float]] = []
        child_infos = []
        for record in valid_records:
            child_depth = node.depth + 1
            if child_depth > limit:
                cutoff = True
                child_infos.append(_skipped_child_info(record, "beyond depth limit"))
                continue
            if child_depth >= best_depth_seen.get(record.state, float("inf")):
                child_infos.append(_skipped_child_info(record, "seen at smaller or equal depth"))
                continue
            child = factory.create(
                state=record.state,
                parent=node,
                action=record.action,
                path_cost=node.path_cost + record.cost,
                depth=child_depth,
            )
            generated_nodes += 1
            best_depth_seen[child.state] = child.depth
            child_nodes.append((child, record.cost))
            child_infos.append(_child_info(child, record.cost))

        for child, _step_cost in reversed(child_nodes):
            frontier.push(child)

        max_frontier_size = max(max_frontier_size, len(frontier))
        _log_expansion(
            logger,
            algorithm,
            node,
            child_infos,
            rejected_records,
            frontier,
            len(best_depth_seen),
            expanded_nodes,
            generated_nodes,
        )

    status = "cutoff" if cutoff else "failure"
    message = f"{algorithm} ended with {status} at depth limit {limit}."
    return _failure_result(algorithm, message, expanded_nodes, generated_nodes, max_frontier_size, start_time)


def _result(
    algorithm: str,
    success: bool,
    node: Node,
    message: str,
    expanded_nodes: int,
    generated_nodes: int,
    max_frontier_size: int,
    start_time: float,
) -> SearchResult:
    return SearchResult(
        algorithm=algorithm,
        success=success,
        solution_states=solution_states(node),
        solution_actions=solution_actions(node),
        total_cost=node.path_cost,
        expanded_nodes=expanded_nodes,
        generated_nodes=generated_nodes,
        max_frontier_size=max_frontier_size,
        depth=node.depth,
        message=message,
        runtime_seconds=time.perf_counter() - start_time,
        extra={"solution_node_ids": solution_node_ids(node)},
    )


def _failure_result(
    algorithm: str,
    message: str,
    expanded_nodes: int,
    generated_nodes: int,
    max_frontier_size: int,
    start_time: float,
) -> SearchResult:
    return SearchResult(
        algorithm=algorithm,
        success=False,
        solution_states=[],
        solution_actions=[],
        total_cost=0.0,
        expanded_nodes=expanded_nodes,
        generated_nodes=generated_nodes,
        max_frontier_size=max_frontier_size,
        depth=0,
        message=message,
        runtime_seconds=time.perf_counter() - start_time,
    )


def _hit_expansion_limit(problem: Any, expanded_nodes: int) -> bool:
    return problem.max_expansions is not None and expanded_nodes >= problem.max_expansions


def _include_rejected(logger: Any) -> bool:
    return bool(logger is not None and getattr(logger, "verbose", False))


def _child_info(
    child: Node,
    step_cost: float,
    h: float | None = None,
    f: float | None = None,
) -> dict[str, Any]:
    info: dict[str, Any] = {
        "node_id": child.node_id,
        "parent_node_id": child.parent.node_id if child.parent else None,
        "action": child.action,
        "state": child.state,
        "step_cost": step_cost,
        "path_cost": child.path_cost,
        "depth": child.depth,
    }
    if h is not None:
        info["h"] = h
    if f is not None:
        info["f"] = f
    return info


def _skipped_child_info(record: Any, reason: str) -> dict[str, Any]:
    return {
        "node_id": None,
        "action": record.action,
        "state": record.state,
        "step_cost": record.cost,
        "skipped": reason,
    }


def _log_expansion(
    logger: Any,
    algorithm: str,
    node: Node,
    valid_children: list[dict[str, Any]],
    rejected_children: list[Any],
    frontier: Any,
    explored_count: int,
    expanded_nodes: int,
    generated_nodes: int,
    h: float | None = None,
    f: float | None = None,
) -> None:
    if logger is None:
        return
    logger.log_expansion(
        algorithm=algorithm,
        node=node,
        valid_children=valid_children,
        rejected_children=rejected_children,
        frontier_snapshot=frontier.snapshot(limit=20),
        frontier_size=len(frontier),
        explored_count=explored_count,
        expanded_nodes=expanded_nodes,
        generated_nodes=generated_nodes,
        h=h,
        f=f,
    )
