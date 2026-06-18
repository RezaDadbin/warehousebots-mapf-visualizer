# Core search-tree data models and solution reconstruction helpers.

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


Position = tuple[int, int]
State = tuple[Position, ...]
JointAction = tuple[str, ...]


@dataclass
class Node:
    # A generated search-tree node for centralized MAPF.
    #
    # ``node_id`` identifies a generated tree node in logs. Multiple nodes may
    # refer to the same MAPF state when a cost-based search later finds a cheaper
    # route.
    #

    state: State
    parent: Optional["Node"] = None
    action: Optional[JointAction] = None
    path_cost: float = 0.0
    depth: int = 0
    node_id: int = 0


def solution_states(node: Node) -> list[State]:
    # Reconstruct the state path from the root node to ``node``.
    states: list[State] = []
    current: Node | None = node
    while current is not None:
        states.append(current.state)
        current = current.parent
    states.reverse()
    return states


def solution_actions(node: Node) -> list[JointAction]:
    # Reconstruct the joint-action path from the root node to ``node``.
    actions: list[JointAction] = []
    current: Node | None = node
    while current is not None:
        if current.action is not None:
            actions.append(current.action)
        current = current.parent
    actions.reverse()
    return actions


def solution_node_ids(node: Node) -> list[int]:
    # Reconstruct generated node IDs along the selected solution branch.
    node_ids: list[int] = []
    current: Node | None = node
    while current is not None:
        node_ids.append(current.node_id)
        current = current.parent
    node_ids.reverse()
    return node_ids

