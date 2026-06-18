# Bonus approximate genetic planner for MAPF comparison.

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import random
import time
from pathlib import Path
from typing import Any

try:
    from .heuristics import sum_manhattan_heuristic
    from .result import SearchResult
    from .visualizer import save_solution_timeline
except ImportError:
    from heuristics import sum_manhattan_heuristic
    from result import SearchResult
    from visualizer import save_solution_timeline


JointAction = tuple[str, ...]
Chromosome = list[JointAction]


@dataclass
class EvaluatedChromosome:
    # Fitness and simulated plan for one chromosome.

    chromosome: Chromosome
    fitness_cost: float
    states: list[tuple]
    actions: list[JointAction]
    plan_cost: float
    success: bool
    invalid_penalty: float


def genetic_algorithm_planner(
    problem: Any,
    logger: Any = None,
    horizon: int | None = None,
    population_size: int | None = None,
    generations: int | None = None,
    mutation_rate: float | None = None,
    elite_size: int | None = None,
    seed: int | None = None,
) -> SearchResult:
    # Run a bonus approximate planner based on a fixed-horizon GA.
    start_time = time.perf_counter()
    config = problem.ga or {}
    horizon = int(horizon if horizon is not None else config.get("horizon", 18))
    population_size = int(population_size if population_size is not None else config.get("population_size", 80))
    generations = int(generations if generations is not None else config.get("generations", 100))
    mutation_rate = float(mutation_rate if mutation_rate is not None else config.get("mutation_rate", 0.08))
    elite_size = int(elite_size if elite_size is not None else config.get("elite_size", 4))
    seed = int(seed if seed is not None else config.get("seed", 42))

    population_size = max(2, population_size)
    elite_size = max(1, min(elite_size, population_size))
    rng = random.Random(seed)
    possible_actions = [tuple(action) for action in product(problem.ACTIONS.keys(), repeat=problem.agent_count)]
    possible_actions = [action for action in possible_actions if not problem._is_all_wait(action)]

    population = [_random_chromosome(rng, possible_actions, horizon) for _ in range(population_size)]
    best: EvaluatedChromosome | None = None
    history: list[float] = []

    for generation in range(generations):
        evaluated = sorted((_evaluate(problem, chromosome) for chromosome in population), key=lambda item: item.fitness_cost)
        if best is None or evaluated[0].fitness_cost < best.fitness_cost:
            best = evaluated[0]
        history.append(best.fitness_cost)
        if logger is not None and getattr(logger, "stream", False):
            print(f"GA generation {generation + 1}/{generations}: best fitness {best.fitness_cost:.2f}")

        next_population = [item.chromosome[:] for item in evaluated[:elite_size]]
        while len(next_population) < population_size:
            parent_a = _tournament(rng, evaluated)
            parent_b = _tournament(rng, evaluated)
            child = _crossover(rng, parent_a.chromosome, parent_b.chromosome)
            _mutate(rng, child, possible_actions, mutation_rate)
            next_population.append(child)
        population = next_population

    assert best is not None
    message = "Bonus GA approximate planner reached the goal." if best.success else (
        "Bonus GA did not reach the goal; result is approximate and not guaranteed complete or optimal."
    )
    return SearchResult(
        algorithm="GA",
        success=best.success,
        solution_states=best.states if best.success else best.states,
        solution_actions=best.actions,
        total_cost=best.plan_cost,
        expanded_nodes=generations * population_size,
        generated_nodes=generations * population_size,
        max_frontier_size=population_size,
        depth=len(best.actions),
        message=message,
        runtime_seconds=time.perf_counter() - start_time,
        extra={
            "best_fitness_history": history,
            "best_fitness_cost": best.fitness_cost,
            "invalid_penalty": best.invalid_penalty,
            "horizon": horizon,
            "population_size": population_size,
            "generations": generations,
            "mutation_rate": mutation_rate,
            "elite_size": elite_size,
            "seed": seed,
        },
    )


def save_ga_fitness_plot(result: SearchResult, path: str | Path) -> str | None:
    # Save the GA best-fitness curve as PNG.
    history = result.extra.get("best_fitness_history", [])
    if not history:
        return None
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(range(1, len(history) + 1), history, color="#1f77b4", linewidth=2)
    ax.set_xlabel("Generation")
    ax.set_ylabel("Best fitness cost")
    ax.set_title("Genetic Algorithm Fitness")
    ax.grid(True, alpha=0.3)
    fig.savefig(target, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return str(target)


def save_ga_text_log(result: SearchResult, path: str | Path) -> str:
    # Save a concise GA log with configuration and fitness history.
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "Genetic Algorithm Bonus Planner",
        f"Success: {result.success}",
        f"Message: {result.message}",
        f"Plan cost: {result.total_cost}",
        f"Steps used: {result.depth}",
        f"Best fitness: {result.extra.get('best_fitness_cost')}",
        f"Invalid penalty: {result.extra.get('invalid_penalty')}",
        "",
        "Fitness history:",
    ]
    lines.extend(f"{index + 1},{value}" for index, value in enumerate(result.extra.get("best_fitness_history", [])))
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(target)


def _random_chromosome(rng: random.Random, possible_actions: list[JointAction], horizon: int) -> Chromosome:
    return [rng.choice(possible_actions) for _ in range(horizon)]


def _evaluate(problem: Any, chromosome: Chromosome) -> EvaluatedChromosome:
    state = problem.initial_state()
    states = [state]
    actions: list[JointAction] = []
    plan_cost = 0.0
    invalid_penalty = 0.0
    success = problem.is_goal(state)

    for action in chromosome:
        attempted_state = problem.result(state, action)
        rejection_reason = problem._valid_child(state, action, attempted_state)
        if rejection_reason is None:
            step_cost = problem.action_cost(state, action, attempted_state)
            plan_cost += step_cost
            state = attempted_state
            states.append(state)
            actions.append(action)
        else:
            invalid_penalty += 25.0
        if problem.is_goal(state):
            success = True
            break

    if success:
        fitness_cost = plan_cost + 2 * len(actions) + invalid_penalty
    else:
        fitness_cost = 1000 + 20 * sum_manhattan_heuristic(problem, state) + plan_cost + invalid_penalty

    return EvaluatedChromosome(chromosome, fitness_cost, states, actions, plan_cost, success, invalid_penalty)


def _tournament(rng: random.Random, evaluated: list[EvaluatedChromosome], size: int = 3) -> EvaluatedChromosome:
    contestants = rng.sample(evaluated, k=min(size, len(evaluated)))
    return min(contestants, key=lambda item: item.fitness_cost)


def _crossover(rng: random.Random, first: Chromosome, second: Chromosome) -> Chromosome:
    if len(first) <= 1:
        return first[:]
    point = rng.randint(1, len(first) - 1)
    return first[:point] + second[point:]


def _mutate(
    rng: random.Random,
    chromosome: Chromosome,
    possible_actions: list[JointAction],
    mutation_rate: float,
) -> None:
    for index in range(len(chromosome)):
        if rng.random() < mutation_rate:
            chromosome[index] = rng.choice(possible_actions)
