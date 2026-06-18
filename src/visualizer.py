# ASCII, PNG, heatmap, and GIF visualization helpers.

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from .utils import ensure_output_dir
except ImportError:
    from utils import ensure_output_dir


AGENT_COLORS = {
    "A": "#1f77b4",
    "B": "#2ca02c",
    "C": "#ff7f0e",
    "D": "#9467bd",
    "E": "#d62728",
    "F": "#8c564b",
}


def render_joint_action(action: tuple[str, ...], agent_ids: list[str] | None = None) -> str:
    # Render a joint action as ``A:UP, B:WAIT`` text.
    if agent_ids is None:
        agent_ids = [chr(ord("A") + index) for index in range(len(action))]
    return ", ".join(f"{agent_id}:{move}" for agent_id, move in zip(agent_ids, action))


def render_state(problem: Any, state: tuple[tuple[int, int], ...], show_goals: bool = True) -> str:
    # Render one MAPF state as an ASCII grid.
    cells = [[problem.grid[row][col] for col in range(problem.cols)] for row in range(problem.rows)]
    if show_goals:
        for agent_id, goal in zip(problem.agent_ids, problem.goal_state()):
            row, col = goal
            if cells[row][col] == ".":
                cells[row][col] = agent_id.lower()[0]

    for agent_id, position in zip(problem.agent_ids, state):
        row, col = position
        cells[row][col] = agent_id.upper()[0]

    width = 3
    separator = "+" + "+".join("-" * width for _ in range(problem.cols)) + "+"
    lines = [separator]
    for row in cells:
        lines.append("|" + "|".join(f"{value:^{width}}" for value in row) + "|")
        lines.append(separator)

    at_goal = [
        f"{agent_id}✓"
        for agent_id, position, goal in zip(problem.agent_ids, state, problem.goal_state())
        if position == goal
    ]
    if at_goal:
        lines.append("At goal: " + ", ".join(at_goal))
    return "\n".join(lines)


def render_state_with_metadata(
    problem: Any,
    state: tuple[tuple[int, int], ...],
    step: int,
    g: float | None = None,
    h: float | None = None,
    f: float | None = None,
) -> str:
    # Render a state with search metadata above it.
    metadata = [f"Step {step}"]
    if g is not None:
        metadata.append(f"g(n)={g}")
    if h is not None:
        metadata.append(f"h(n)={h}")
    if f is not None:
        metadata.append(f"f(n)={f}")
    return " | ".join(metadata) + "\n" + render_state(problem, state)


def render_solution_timeline(
    problem: Any,
    states: list[tuple[tuple[int, int], ...]],
    actions: list[tuple[str, ...]] | None = None,
) -> str:
    # Render a complete solution as text frames.
    parts: list[str] = []
    for index, state in enumerate(states):
        parts.append(f"Step {index}")
        if actions is not None and index > 0 and index - 1 < len(actions):
            parts.append("Action: " + render_joint_action(actions[index - 1], problem.agent_ids))
        parts.append(render_state(problem, state))
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def save_solution_timeline(
    problem: Any,
    states: list[tuple[tuple[int, int], ...]],
    path: str | Path,
    actions: list[tuple[str, ...]] | None = None,
) -> str:
    # Save the ASCII solution timeline to disk.
    target = Path(path)
    ensure_output_dir(target.parent)
    target.write_text(render_solution_timeline(problem, states, actions), encoding="utf-8")
    return str(target)


def save_final_path_png(
    problem: Any,
    states: list[tuple[tuple[int, int], ...]],
    path: str | Path,
    title: str = "Final MAPF Solution Path",
) -> str | None:
    # Save a static PNG showing starts, goals, and final paths.
    if not states:
        return None
    plt = _load_pyplot()
    if plt is None:
        return None

    fig, ax = plt.subplots(figsize=(max(6, problem.cols), max(5, problem.rows)))
    _draw_base_grid(ax, problem)
    _draw_starts_goals(ax, problem)
    for agent_index, agent_id in enumerate(problem.agent_ids):
        color = AGENT_COLORS.get(agent_id[0].upper(), "#7f7f7f")
        xs = [state[agent_index][1] + 0.5 for state in states]
        ys = [state[agent_index][0] + 0.5 for state in states]
        ax.plot(xs, ys, color=color, linewidth=2.5, marker="o", markersize=4, label=agent_id)
        ax.text(xs[-1], ys[-1], agent_id, color="white", ha="center", va="center", weight="bold")
    ax.set_title(title)
    ax.legend(loc="upper right", bbox_to_anchor=(1.15, 1.0))
    _finish_axes(ax, problem)
    target = Path(path)
    ensure_output_dir(target.parent)
    fig.savefig(target, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return str(target)


def save_expansion_heatmap_png(
    problem: Any,
    trace_records: list[dict[str, Any]],
    path: str | Path,
    title: str = "Expansion Heatmap",
) -> str | None:
    # Save a heatmap showing where selected states were expanded.
    plt = _load_pyplot()
    if plt is None:
        return None
    heat = [[0 for _ in range(problem.cols)] for _ in range(problem.rows)]
    for record in trace_records:
        if record.get("type") != "expansion":
            continue
        for row, col in record.get("selected_state", []):
            if 0 <= row < problem.rows and 0 <= col < problem.cols:
                heat[row][col] += 1

    fig, ax = plt.subplots(figsize=(max(6, problem.cols), max(5, problem.rows)))
    _draw_base_grid(ax, problem)
    max_value = max((max(row) for row in heat), default=0)
    if max_value > 0:
        for row in range(problem.rows):
            for col in range(problem.cols):
                if heat[row][col] > 0:
                    alpha = 0.15 + 0.65 * (heat[row][col] / max_value)
                    ax.add_patch(
                        _rectangle(plt, col, row, facecolor="#6a5acd", alpha=alpha, edgecolor="none")
                    )
    _draw_starts_goals(ax, problem)
    ax.set_title(title)
    _finish_axes(ax, problem)
    target = Path(path)
    ensure_output_dir(target.parent)
    fig.savefig(target, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return str(target)


def save_solution_gif(
    problem: Any,
    states: list[tuple[tuple[int, int], ...]],
    path: str | Path,
    actions: list[tuple[str, ...]] | None = None,
    interval_ms: int = 700,
) -> str | None:
    # Save an animated GIF of the final solution if matplotlib/Pillow work.
    if not states:
        return None
    plt = _load_pyplot()
    if plt is None:
        return None
    try:
        from matplotlib.animation import FuncAnimation, PillowWriter
    except Exception:
        return _save_solution_frames(problem, states, path, actions)

    fig, ax = plt.subplots(figsize=(max(6, problem.cols), max(5, problem.rows)))

    def draw_frame(frame_index: int) -> None:
        ax.clear()
        _draw_base_grid(ax, problem)
        _draw_starts_goals(ax, problem)
        state = states[frame_index]
        for agent_id, position in zip(problem.agent_ids, state):
            color = AGENT_COLORS.get(agent_id[0].upper(), "#7f7f7f")
            circle = plt.Circle((position[1] + 0.5, position[0] + 0.5), 0.32, color=color)
            ax.add_patch(circle)
            ax.text(position[1] + 0.5, position[0] + 0.5, agent_id, color="white", ha="center", va="center", weight="bold")
        title = f"Timestep {frame_index}"
        if actions is not None and frame_index > 0 and frame_index - 1 < len(actions):
            title += " | " + render_joint_action(actions[frame_index - 1], problem.agent_ids)
        ax.set_title(title)
        _finish_axes(ax, problem)

    animation = FuncAnimation(fig, draw_frame, frames=len(states), interval=interval_ms, repeat=False)
    target = Path(path)
    ensure_output_dir(target.parent)
    try:
        animation.save(target, writer=PillowWriter(fps=max(1, int(1000 / interval_ms))))
    except Exception:
        plt.close(fig)
        return _save_solution_frames(problem, states, path, actions)
    plt.close(fig)
    return str(target)


def _save_solution_frames(
    problem: Any,
    states: list[tuple[tuple[int, int], ...]],
    path: str | Path,
    actions: list[tuple[str, ...]] | None,
) -> str | None:
    # Fallback: save sequential PNG frames if GIF saving fails.
    target = Path(path)
    frame_dir = target.with_suffix("")
    ensure_output_dir(frame_dir)
    for index, state in enumerate(states):
        save_final_path_png(problem, states[: index + 1], frame_dir / f"frame_{index:03d}.png", title=f"Timestep {index}")
    return str(frame_dir)


def _load_pyplot() -> Any:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        return plt
    except Exception:
        return None


def _draw_base_grid(ax: Any, problem: Any) -> None:
    plt = _load_pyplot()
    if plt is None:
        return
    for row in range(problem.rows):
        for col in range(problem.cols):
            symbol = problem.grid[row][col]
            if symbol == "#":
                color = "#222222"
            elif symbol.isdigit() or problem._cell_extra_cost((row, col)) > 0:
                extra = min(problem._cell_extra_cost((row, col)), 6)
                intensity = int(240 - extra * 18)
                color = f"#ff{intensity:02x}{max(120, intensity - 40):02x}"
            else:
                color = "#ffffff"
            ax.add_patch(_rectangle(plt, col, row, facecolor=color, edgecolor="#999999", linewidth=0.8))
            if symbol.isdigit():
                ax.text(col + 0.5, row + 0.5, symbol, ha="center", va="center", color="#7a3f00")


def _draw_starts_goals(ax: Any, problem: Any) -> None:
    plt = _load_pyplot()
    if plt is None:
        return
    for agent in problem.agents:
        color = AGENT_COLORS.get(agent.agent_id[0].upper(), "#7f7f7f")
        ax.add_patch(plt.Circle((agent.start[1] + 0.5, agent.start[0] + 0.5), 0.18, fill=False, edgecolor=color, linewidth=2))
        ax.scatter([agent.goal[1] + 0.5], [agent.goal[0] + 0.5], marker="*", s=180, color=color, edgecolors="#111111", zorder=5)
        ax.text(agent.goal[1] + 0.5, agent.goal[0] + 0.82, agent.agent_id.lower(), ha="center", va="center", color=color, fontsize=9)


def _finish_axes(ax: Any, problem: Any) -> None:
    ax.set_xlim(0, problem.cols)
    ax.set_ylim(problem.rows, 0)
    ax.set_aspect("equal")
    ax.set_xticks(range(problem.cols + 1))
    ax.set_yticks(range(problem.rows + 1))
    ax.grid(color="#cccccc", linewidth=0.5)
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)


def _rectangle(plt: Any, col: int, row: int, **kwargs: Any) -> Any:
    from matplotlib.patches import Rectangle

    return Rectangle((col, row), 1, 1, **kwargs)
