# Command-line interface for WarehouseBots MAPF search.

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Callable

try:
    from .comparison import format_comparison_table, save_comparison_csv
    from .genetic_algorithm import (
        genetic_algorithm_planner,
        save_ga_fitness_plot,
        save_ga_text_log,
    )
    from .heuristics import (
        congestion_aware_heuristic,
        max_manhattan_heuristic,
        sum_manhattan_heuristic,
        zero_heuristic,
    )
    from .logger import StepLogger
    from .mapf_problem import MAPFProblem
    from .search_algorithms import (
        a_star_search,
        breadth_first_search,
        depth_first_search,
        depth_limited_search,
        greedy_best_first_search,
        iterative_deepening_search,
        uniform_cost_search,
    )
    from .utils import ensure_output_dir, project_root, resolve_project_path
    from .visualizer import (
        render_state,
        save_expansion_heatmap_png,
        save_final_path_png,
        save_solution_gif,
        save_solution_timeline,
    )
except ImportError:
    from comparison import format_comparison_table, save_comparison_csv
    from genetic_algorithm import (
        genetic_algorithm_planner,
        save_ga_fitness_plot,
        save_ga_text_log,
    )
    from heuristics import (
        congestion_aware_heuristic,
        max_manhattan_heuristic,
        sum_manhattan_heuristic,
        zero_heuristic,
    )
    from logger import StepLogger
    from mapf_problem import MAPFProblem
    from search_algorithms import (
        a_star_search,
        breadth_first_search,
        depth_first_search,
        depth_limited_search,
        greedy_best_first_search,
        iterative_deepening_search,
        uniform_cost_search,
    )
    from utils import ensure_output_dir, project_root, resolve_project_path
    from visualizer import (
        render_state,
        save_expansion_heatmap_png,
        save_final_path_png,
        save_solution_gif,
        save_solution_timeline,
    )


ALGORITHM_CHOICES = ("bfs", "ucs", "dfs", "dls", "ids", "greedy", "astar", "ga", "all")
HEURISTIC_CHOICES = ("zero", "sum_manhattan", "max_manhattan", "congestion")
REQUIRED_ALGORITHMS = ("bfs", "ucs", "dfs", "dls", "ids", "greedy", "astar")


def build_parser() -> argparse.ArgumentParser:
    # Build the CLI parser.
    parser = argparse.ArgumentParser(
        description="WarehouseBots: Centralized Multi-Agent Path Finding with Classical AI Search.",
    )
    parser.add_argument("--data", help="Path to a JSON test file.")
    parser.add_argument("--algorithm", choices=ALGORITHM_CHOICES, default="astar")
    parser.add_argument("--heuristic", choices=HEURISTIC_CHOICES, default="sum_manhattan")
    parser.add_argument("--depth-limit", type=int, default=None)
    parser.add_argument("--max-depth", type=int, default=None)
    parser.add_argument("--max-expansions", type=int, default=None)
    parser.add_argument("--verbose", action="store_true", help="Print expansion logs to the console.")
    parser.add_argument("--no-log", action="store_true", help="Skip log/trace file output.")
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--gui", action="store_true", help="Open the Tkinter visualizer.")
    return parser


def main() -> None:
    # Load the requested problem and run the selected interface.
    parser = build_parser()
    args = parser.parse_args()

    if args.gui:
        launch_gui()
        return

    data_path = _resolve_data_path(args.data)
    problem = MAPFProblem.from_json(data_path)
    if args.max_expansions is not None:
        problem.max_expansions = args.max_expansions
    output_root = _resolve_output_root(args.output_dir)

    print(f"Loaded problem: {problem.name}")
    print(f"Agents: {', '.join(problem.agent_ids)}")
    print("Initial grid:")
    print(render_state(problem, problem.initial_state()))
    print("")

    heuristic = get_heuristic(args.heuristic)

    if args.algorithm == "all":
        results = []
        for algorithm in REQUIRED_ALGORITHMS:
            print(f"\nRunning {algorithm.upper()}...")
            results.append(run_algorithm_with_outputs(algorithm, problem, args, output_root, heuristic))
        print("\nBonus method: Genetic Algorithm")
        results.append(run_algorithm_with_outputs("ga", problem, args, output_root, heuristic))
        table = format_comparison_table(results)
        comparison_path = save_comparison_csv(results, output_root / problem.name / "comparison.csv")
        print("\n" + table)
        print(f"\nComparison CSV: {comparison_path}")
        return

    run_algorithm_with_outputs(args.algorithm, problem, args, output_root, heuristic)


def run_algorithm_with_outputs(
    algorithm: str,
    problem: MAPFProblem,
    args: argparse.Namespace,
    output_root: Path,
    heuristic: Callable[[Any, Any], float],
) -> Any:
    # Run one algorithm and save logs/visual output.
    problem_dir = ensure_output_dir(output_root / problem.name)
    logger = None
    if algorithm != "ga":
        logger = StepLogger(
            algorithm=_algorithm_label(algorithm),
            verbose=args.verbose,
            enabled=not args.no_log,
            stream=args.verbose,
        )

    result = run_single_algorithm(algorithm, problem, args, heuristic, logger)
    if logger is not None:
        logger.log_result(result)
        if not args.no_log:
            log_path, trace_path = logger.save(problem_dir)
            result.trace_path = trace_path
            result.extra["log_path"] = log_path
            heatmap_path = save_expansion_heatmap_png(
                problem,
                logger.trace_records,
                problem_dir / f"{_algorithm_slug(result.algorithm)}_expansion_heatmap.png",
                title=f"{result.algorithm} Expansion Heatmap",
            )
            result.extra["heatmap_path"] = heatmap_path

    if algorithm == "ga":
        ga_log_path = save_ga_text_log(result, problem_dir / "ga_log.txt")
        fitness_path = save_ga_fitness_plot(result, problem_dir / "ga_fitness.png")
        result.extra["log_path"] = ga_log_path
        result.extra["fitness_plot_path"] = fitness_path

    if result.solution_states:
        slug = _algorithm_slug(result.algorithm)
        result.timeline_path = save_solution_timeline(
            problem,
            result.solution_states,
            problem_dir / f"{slug}_solution_timeline.txt",
            result.solution_actions,
        )
        result.image_path = save_final_path_png(
            problem,
            result.solution_states,
            problem_dir / f"{slug}_final_path.png",
            title=f"{result.algorithm} Final Solution Path",
        )
        result.gif_path = save_solution_gif(
            problem,
            result.solution_states,
            problem_dir / f"{slug}_solution.gif",
            result.solution_actions,
        )

    print_result_summary(result)
    return result


def run_single_algorithm(
    algorithm: str,
    problem: MAPFProblem,
    args: argparse.Namespace,
    heuristic: Callable[[Any, Any], float],
    logger: StepLogger | None,
) -> Any:
    # Dispatch one selected algorithm.
    depth_limit = args.depth_limit if args.depth_limit is not None else problem.depth_limit or 12
    max_depth = args.max_depth if args.max_depth is not None else problem.max_depth or 20
    if algorithm == "bfs":
        return breadth_first_search(problem, logger)
    if algorithm == "ucs":
        return uniform_cost_search(problem, logger)
    if algorithm == "dfs":
        return depth_first_search(problem, logger)
    if algorithm == "dls":
        return depth_limited_search(problem, depth_limit, logger)
    if algorithm == "ids":
        return iterative_deepening_search(problem, max_depth, logger)
    if algorithm == "greedy":
        return greedy_best_first_search(problem, heuristic, logger)
    if algorithm == "astar":
        return a_star_search(problem, heuristic, logger)
    if algorithm == "ga":
        return genetic_algorithm_planner(problem, logger=None)
    raise ValueError(f"Unknown algorithm: {algorithm}")


def get_heuristic(name: str) -> Callable[[Any, Any], float]:
    # Return a heuristic function by CLI name.
    return {
        "zero": zero_heuristic,
        "sum_manhattan": sum_manhattan_heuristic,
        "max_manhattan": max_manhattan_heuristic,
        "congestion": congestion_aware_heuristic,
    }[name]


def print_result_summary(result: Any) -> None:
    # Print final metrics for one run.
    print(f"\n[{result.algorithm}] success={result.success} cost={result.total_cost} depth={result.depth}")
    print(
        "expanded={expanded} generated={generated} max_frontier={frontier} runtime={runtime:.4f}s".format(
            expanded=result.expanded_nodes,
            generated=result.generated_nodes,
            frontier=result.max_frontier_size,
            runtime=result.runtime_seconds,
        )
    )
    print(result.message)
    if result.solution_states:
        print(f"Final joint path: {result.solution_states}")
    if result.solution_actions:
        print(f"Final joint actions: {result.solution_actions}")
    if result.timeline_path:
        print(f"Timeline: {result.timeline_path}")
    if result.image_path:
        print(f"PNG: {result.image_path}")
    if result.gif_path:
        print(f"GIF/frames: {result.gif_path}")
    if result.trace_path:
        print(f"Trace: {result.trace_path}")


def launch_gui() -> None:
    # Import and run Tkinter GUI only when requested.
    try:
        from .gui import run_gui
    except ImportError:
        from gui import run_gui

    run_gui()


def _resolve_data_path(data: str | None) -> Path:
    root = project_root()
    if data is None:
        return root / "data_test" / "test_2_agents_easy.json"
    return resolve_project_path(data, root)


def _resolve_output_root(output_dir: str) -> Path:
    return ensure_output_dir(resolve_project_path(output_dir, project_root()))


def _algorithm_label(algorithm: str) -> str:
    return {
        "bfs": "BFS",
        "ucs": "UCS",
        "dfs": "DFS",
        "dls": "DLS",
        "ids": "IDS",
        "greedy": "Greedy",
        "astar": "A*",
        "ga": "GA",
    }[algorithm]


def _algorithm_slug(algorithm: str) -> str:
    return algorithm.lower().replace("*", "star").replace(" ", "_").replace("(", "_").replace(")", "")


if __name__ == "__main__":
    main()
