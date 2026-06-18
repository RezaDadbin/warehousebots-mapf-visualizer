# Centralized Multi-Agent Path Finding problem definition.

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import json
from pathlib import Path
from typing import Any


Position = tuple[int, int]
State = tuple[Position, ...]
JointAction = tuple[str, ...]


ACTION_NAMES = ("UP", "RIGHT", "DOWN", "LEFT", "WAIT")
ACTION_DELTAS: dict[str, Position] = {
    "UP": (-1, 0),
    "RIGHT": (0, 1),
    "DOWN": (1, 0),
    "LEFT": (0, -1),
    "WAIT": (0, 0),
}


@dataclass(frozen=True)
class Agent:
    # One robot with a fixed start and assigned goal.

    agent_id: str
    start: Position
    goal: Position


@dataclass(frozen=True)
class ChildRecord:
    # A valid child produced by one joint action.

    action: JointAction
    state: State
    cost: float


@dataclass(frozen=True)
class RejectedChildRecord:
    # An invalid child and the reason it was rejected.

    action: JointAction
    attempted_state: State
    reason: str


class MAPFProblem:
    # A grid-based centralized MAPF search problem.
    #
    # Search algorithms operate over joint states, not individual robot plans.
    # A transition applies one joint action to all agents at the same timestep.
    #

    ACTIONS = ACTION_DELTAS

    def __init__(
        self,
        name: str,
        rows: int,
        cols: int,
        grid: list[str],
        agents: list[dict[str, Any]] | list[Agent],
        depth_limit: int | None = None,
        max_depth: int | None = None,
        max_expansions: int | None = None,
        lock_agents_at_goal: bool = False,
        cell_costs: dict[str, int | float] | None = None,
        ga: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.rows = rows
        self.cols = cols
        self.grid = grid
        self.depth_limit = depth_limit
        self.max_depth = max_depth
        self.max_expansions = max_expansions if max_expansions is not None else 10000
        self.lock_agents_at_goal = lock_agents_at_goal
        self.ga = ga or {}

        self.agents = [self._coerce_agent(agent) for agent in agents]
        self.agent_ids = [agent.agent_id for agent in self.agents]
        self.starts = tuple(agent.start for agent in self.agents)
        self.goals = tuple(agent.goal for agent in self.agents)
        self.agent_count = len(self.agents)
        self.cell_costs = self._parse_cell_costs(cell_costs or {})

        self._validate()

    @classmethod
    def from_json(cls, path: str | Path) -> "MAPFProblem":
        # Load and validate a MAPF instance from a JSON file.
        with Path(path).open("r", encoding="utf-8") as file:
            data = json.load(file)
        return cls(
            name=data.get("name", Path(path).stem),
            rows=int(data["rows"]),
            cols=int(data["cols"]),
            grid=list(data["grid"]),
            agents=list(data["agents"]),
            depth_limit=data.get("depth_limit"),
            max_depth=data.get("max_depth"),
            max_expansions=data.get("max_expansions"),
            lock_agents_at_goal=bool(data.get("lock_agents_at_goal", False)),
            cell_costs=data.get("cell_costs", {}),
            ga=data.get("ga", {}),
        )

    def initial_state(self) -> State:
        # Return the tuple of all start positions.
        return self.starts

    def goal_state(self) -> State:
        # Return the tuple of all assigned goal positions.
        return self.goals

    def is_goal(self, state: State) -> bool:
        # Return True when every agent is at its assigned goal.
        return state == self.goals

    def actions(self, state: State) -> list[JointAction]:
        # Return all valid joint actions from ``state``.
        valid_children, _rejected = self.generate_children(state, include_rejected=False)
        return [child.action for child in valid_children]

    def result(self, state: State, joint_action: JointAction) -> State:
        # Apply a joint action without validating it.
        if len(joint_action) != self.agent_count:
            raise ValueError("Joint action length must equal number of agents.")
        return tuple(
            self._apply_action(position, action)
            for position, action in zip(state, joint_action)
        )

    def action_cost(self, state: State, joint_action: JointAction, next_state: State) -> float:
        # Return the configured cost of a valid joint action.
        base_cost = 1.0
        movement_cost = sum(1 for action in joint_action if action != "WAIT")
        terrain_cost = 0.0
        for action, position in zip(joint_action, next_state):
            if action != "WAIT":
                terrain_cost += self._cell_extra_cost(position)
        return base_cost + movement_cost + terrain_cost

    def successors(self, state: State) -> list[tuple[JointAction, State, float]]:
        # Return valid successors as ``(action, state, cost)`` tuples.
        valid_children, _rejected = self.generate_children(state, include_rejected=False)
        return [(child.action, child.state, child.cost) for child in valid_children]

    def generate_children(
        self,
        state: State,
        include_rejected: bool = False,
    ) -> tuple[list[ChildRecord], list[RejectedChildRecord]]:
        # Generate deterministic valid and optionally rejected children.
        valid_children: list[ChildRecord] = []
        rejected_children: list[RejectedChildRecord] = []

        for joint_action in product(ACTION_NAMES, repeat=self.agent_count):
            action = tuple(joint_action)
            attempted_state = self.result(state, action)
            rejection_reason = self._valid_child(state, action, attempted_state)
            if rejection_reason is None:
                cost = self.action_cost(state, action, attempted_state)
                valid_children.append(ChildRecord(action, attempted_state, cost))
            elif include_rejected:
                rejected_children.append(
                    RejectedChildRecord(action, attempted_state, rejection_reason)
                )

        return valid_children, rejected_children

    def _inside_grid(self, position: Position) -> bool:
        # Return True if a cell is within grid bounds.
        row, col = position
        return 0 <= row < self.rows and 0 <= col < self.cols

    def _is_wall(self, position: Position) -> bool:
        # Return True if a cell contains a wall.
        if not self._inside_grid(position):
            return False
        row, col = position
        return self.grid[row][col] == "#"

    def _cell_extra_cost(self, position: Position) -> float:
        # Return terrain extra cost for a cell.
        if position in self.cell_costs:
            return float(self.cell_costs[position])
        if not self._inside_grid(position):
            return 0.0
        symbol = self.grid[position[0]][position[1]]
        if symbol.isdigit():
            return float(int(symbol))
        return 0.0

    def _apply_action(self, position: Position, action: str) -> Position:
        # Return the position reached by applying one primitive action.
        if action not in ACTION_DELTAS:
            raise ValueError(f"Unknown action: {action}")
        dr, dc = ACTION_DELTAS[action]
        return position[0] + dr, position[1] + dc

    def _has_vertex_collision(self, next_state: State) -> bool:
        # Return True if two agents occupy the same final cell.
        return len(set(next_state)) != len(next_state)

    def _has_edge_swap_collision(self, state: State, next_state: State) -> bool:
        # Return True if two agents swap positions in one timestep.
        for first in range(self.agent_count):
            for second in range(first + 1, self.agent_count):
                if state[first] == next_state[second] and state[second] == next_state[first]:
                    return True
        return False

    def _is_all_wait(self, joint_action: JointAction) -> bool:
        # Return True when every agent selected WAIT.
        return all(action == "WAIT" for action in joint_action)

    def _valid_child(
        self,
        state: State,
        joint_action: JointAction,
        next_state: State,
    ) -> str | None:
        # Return ``None`` for a valid transition, otherwise a rejection reason.
        if self._is_all_wait(joint_action):
            return "all agents chose WAIT"

        for index, position in enumerate(next_state):
            if self.lock_agents_at_goal and state[index] == self.goals[index]:
                if joint_action[index] != "WAIT":
                    return f"{self.agent_ids[index]} is locked at its goal"
            if not self._inside_grid(position):
                return f"{self.agent_ids[index]} moves outside the grid"
            if self._is_wall(position):
                return f"{self.agent_ids[index]} moves into a wall"

        if self._has_vertex_collision(next_state):
            return "vertex collision"
        if self._has_edge_swap_collision(state, next_state):
            return "edge-swap collision"
        return None

    def describe_state(self, state: State) -> str:
        # Return a readable state description for logs and console output.
        parts = []
        for agent_id, position, goal in zip(self.agent_ids, state, self.goals):
            marker = "*" if position == goal else ""
            parts.append(f"{agent_id}{marker}@{position}->goal{goal}")
        return ", ".join(parts)

    def _coerce_agent(self, agent: dict[str, Any] | Agent) -> Agent:
        if isinstance(agent, Agent):
            return agent
        return Agent(
            agent_id=str(agent["id"]),
            start=tuple(agent["start"]),
            goal=tuple(agent["goal"]),
        )

    def _parse_cell_costs(self, raw_costs: dict[str, int | float]) -> dict[Position, float]:
        costs: dict[Position, float] = {}
        for key, value in raw_costs.items():
            row_text, col_text = key.split(",", maxsplit=1)
            costs[(int(row_text), int(col_text))] = float(value)
        return costs

    def _validate(self) -> None:
        if self.rows <= 0 or self.cols <= 0:
            raise ValueError("Grid dimensions must be positive.")
        if len(self.grid) != self.rows:
            raise ValueError("Grid row count does not match rows.")
        for row in self.grid:
            if len(row) != self.cols:
                raise ValueError("Every grid row must match cols.")
            invalid_symbols = set(row) - set(".#0123456789")
            if invalid_symbols:
                raise ValueError(f"Invalid grid symbols: {sorted(invalid_symbols)}")
        if not self.agents:
            raise ValueError("At least one agent is required.")
        if len(set(self.agent_ids)) != len(self.agent_ids):
            raise ValueError("Agent IDs must be unique.")

        for agent in self.agents:
            for label, position in (("start", agent.start), ("goal", agent.goal)):
                if not self._inside_grid(position):
                    raise ValueError(f"Agent {agent.agent_id} {label} is outside the grid.")
                if self._is_wall(position):
                    raise ValueError(f"Agent {agent.agent_id} {label} is inside a wall.")
        if self._has_vertex_collision(self.starts):
            raise ValueError("Two agents share the same start cell.")
        if self._has_vertex_collision(self.goals):
            raise ValueError("Two agents share the same goal cell.")

