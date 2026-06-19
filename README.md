# WarehouseBots MAPF Visualizer

A small course project for visualizing classical search algorithms on centralized Multi-Agent Path Finding problems.

The project includes a Tkinter GUI and a CLI. The GUI is the main interface: it loads JSON maps, runs the selected algorithm, shows the solution path or sampled expansion states, and can save logs and visual output files.

## What This Demonstrates

- Centralized MAPF state modeling for multiple warehouse robots
- Classical search implementations with comparable output behavior
- Collision checks for wall hits, vertex conflicts, and edge swaps
- A small GUI for inspecting solutions and expansion behavior step by step

## Run

```bash
python3 app.py
```

Optional visualization dependencies:

```bash
python3 -m pip install -r requirements.txt
```

The search algorithms themselves only use the Python standard library. The dependencies are used for PNG and GIF output.

## GUI Usage

1. Select a map.
2. Select an algorithm.
3. Click `Load Map`.
4. Click `Run Algorithm`.
5. Use `Step` or `Play / Pause` to inspect the result.
6. Switch between `Solution` and `Expansion` if needed.
7. Click `Save Outputs` to write logs and visual files under `outputs/`.

The `Easy Demo` and `4-Agent Challenge` buttons are only shortcuts for loading example maps and parameters.

## Implemented Algorithms

| Type | Algorithms |
| --- | --- |
| Uninformed search | BFS, UCS, DFS, DLS, IDS |
| Informed search | Greedy Best-First Search, A* |
| Bonus | Genetic Algorithm |

Greedy Best-First Search uses `f(n) = h(n)`.

A* uses `f(n) = g(n) + h(n)`.

The Genetic Algorithm is included only as a bonus approximate method. It is not complete or optimal and does not replace the classical search algorithms.

## Problem Model

The project uses a centralized MAPF representation. A state is a tuple containing all agent positions at the same timestep:

```python
((0, 0), (4, 0), (2, 3))
```

A joint action contains one primitive action per agent:

```python
("RIGHT", "WAIT", "UP")
```

Allowed primitive actions:

```text
UP, RIGHT, DOWN, LEFT, WAIT
```

## Collision Rules

A child state is rejected if:

- an agent moves outside the grid,
- an agent moves into a wall,
- two agents end in the same cell,
- two agents swap positions across an edge,
- all agents choose `WAIT` together.

Individual WAIT actions are allowed. The all-agents-WAIT action is rejected to avoid a self-loop.

## Maps

Test maps are stored in `data_test/`.

| Map | Purpose |
| --- | --- |
| `test_2_agents_easy.json` | Small baseline example |
| `test_3_agents_bottleneck_wait.json` | WAIT and bottleneck coordination |
| `test_3_agents_weighted_cost.json` | Weighted-cost comparison |
| `test_3_agents_swap_trap.json` | Collision and edge-swap check |
| `test_3_agents_warehouse.json` | Larger warehouse-style layout |
| `test_4_agents_challenge.json` | Four-agent example |

## CLI

Run A* on the easy map:

```bash
python3 src/main.py --data data_test/test_2_agents_easy.json --algorithm astar
```

Run all algorithms:

```bash
python3 src/main.py --data data_test/test_2_agents_easy.json --algorithm all
```

Print step-by-step expansion output:

```bash
python3 src/main.py --data data_test/test_2_agents_easy.json --algorithm bfs --verbose
```

Run the WAIT rule check:

```bash
python3 src/verify_wait_logic.py
```

## Output Files

Generated files are written under:

```text
outputs/<map_name>/
```

Common files:

```text
<algorithm>_log.txt
<algorithm>_trace.json
<algorithm>_solution_timeline.txt
<algorithm>_final_path.png
<algorithm>_solution.gif
<algorithm>_expansion_heatmap.png
comparison.csv
```

Expansion logs include the selected node, generated children, frontier snapshot, explored count, depth, path cost, and heuristic values for informed search.

Generated output files are ignored by Git. The repository keeps only `outputs/.gitkeep`.

## Structure

```text
.
├── app.py
├── data_test/
├── outputs/
├── src/
│   ├── gui.py
│   ├── main.py
│   ├── mapf_problem.py
│   ├── search_algorithms.py
│   ├── frontier.py
│   ├── logger.py
│   ├── visualizer.py
│   ├── heuristics.py
│   └── genetic_algorithm.py
├── requirements.txt
└── README.md
```

## Clean Generated Files

```bash
find . -name ".DS_Store" -delete
find . -name "__pycache__" -type d -prune -exec rm -rf {} +
find outputs -mindepth 1 ! -name ".gitkeep" -exec rm -rf {} +
touch outputs/.gitkeep
```
