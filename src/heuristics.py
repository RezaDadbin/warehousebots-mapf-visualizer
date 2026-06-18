# Heuristics for informed centralized MAPF search.

from __future__ import annotations

from typing import Any


Position = tuple[int, int]
State = tuple[Position, ...]


def manhattan(a: Position, b: Position) -> int:
    # Return Manhattan distance between two grid cells.
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def zero_heuristic(problem: Any, state: State) -> float:
    # Admissible baseline heuristic that always returns zero.
    return 0.0


def sum_manhattan_heuristic(problem: Any, state: State) -> float:
    # Return the sum of every agent's Manhattan distance to its goal.
    goals = problem.goal_state()
    return float(sum(manhattan(position, goal) for position, goal in zip(state, goals)))


def max_manhattan_heuristic(problem: Any, state: State) -> float:
    # Return the longest single-agent Manhattan distance to a goal.
    goals = problem.goal_state()
    if not state:
        return 0.0
    return float(max(manhattan(position, goal) for position, goal in zip(state, goals)))


def congestion_aware_heuristic(problem: Any, state: State) -> float:
    # Return sum Manhattan plus a small deterministic congestion penalty.
    #
    # This heuristic is useful for Greedy comparison. It intentionally stays
    # simple and interpretable: agents near each other and agents in narrow cells
    # get a small extra penalty.
    #
    penalty = 0.0
    for index, position in enumerate(state):
        for other in state[index + 1 :]:
            distance = manhattan(position, other)
            if distance == 0:
                penalty += 5.0
            elif distance == 1:
                penalty += 1.0
            elif distance == 2:
                penalty += 0.25

        free_neighbors = 0
        for action in ("UP", "RIGHT", "DOWN", "LEFT"):
            next_position = problem._apply_action(position, action)
            if problem._inside_grid(next_position) and not problem._is_wall(next_position):
                free_neighbors += 1
        if free_neighbors <= 2:
            penalty += 0.5

    return sum_manhattan_heuristic(problem, state) + penalty

