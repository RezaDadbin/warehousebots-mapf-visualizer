# WarehouseBots GUI

A Tkinter desktop app for visualizing centralized Multi-Agent Path Finding with classical AI search algorithms.

The main interface is the GUI. It loads JSON grid maps, runs the implemented algorithms, shows the resulting multi-agent path, shows sampled expansion steps, and can save logs, timelines, PNGs, GIFs, heatmaps, and comparison files.

## What It Does

WarehouseBots solves grid-based MAPF problems. A state contains every agent position at the same timestep:

```python
((0, 0), (4, 0), (2, 3))
```

Each agent can choose:

```text
UP, RIGHT, DOWN, LEFT, WAIT
```

The planner searches over joint actions such as:

```python
("RIGHT", "WAIT", "UP")
```

Invalid moves are rejected before they enter the search frontier.

## Run the GUI

From the project folder:

```bash
python3 app.py
```

Alternative:

```bash
python3 src/main.py --gui
```

## GUI Workflow

1. Choose a map from the map list.
2. Choose an algorithm.
3. Click `Load Map`.
4. Click `Run Algorithm`.
5. Use `Step` or `Play / Pause` to inspect the result.
6. Switch between `Solution` and `Expansion` views.
7. Click `Save Outputs` to write logs and visual files into `outputs/`.

The GUI also has quick buttons:

- `Easy Demo`
- `4-Agent Challenge`

These only set the map and recommended parameters. They do not change the algorithm code.

## Algorithms Included

| Category | Algorithms |
| --- | --- |
| Uninformed search | BFS, UCS, DFS, DLS, IDS |
| Informed search | Greedy Best-First Search, A* |
| Bonus approximate method | Genetic Algorithm |

Greedy Best-First Search uses:

```text
f(n) = h(n)
```

A* uses:

```text
f(n) = g(n) + h(n)
```

UCS and A* perform the goal test when a node is selected from the priority frontier.

## Collision Rules

A generated child is rejected when:

- an agent moves outside the grid,
- an agent moves into a wall,
- two agents end in the same cell,
- two agents swap positions across an edge in one timestep,
- all agents choose `WAIT` together.

Individual WAIT actions are allowed. Only the all-agents-WAIT action is rejected because it creates a self-loop.

## Repository Structure

```text
.
├── app.py                  # Simple GUI launcher
├── data_test/              # JSON map files
├── outputs/                # Generated output folder, kept with .gitkeep
├── src/
│   ├── gui.py              # Main Tkinter GUI
│   ├── main.py             # CLI and output runner
│   ├── mapf_problem.py     # MAPF state, actions, costs, and validation
│   ├── search_algorithms.py# BFS, UCS, DFS, DLS, IDS, Greedy, A*
│   ├── frontier.py         # Queue, stack, and priority queue
│   ├── logger.py           # Step logs and JSON traces
│   ├── visualizer.py       # Timeline, PNG, heatmap, and GIF helpers
│   ├── heuristics.py       # Heuristic functions
│   └── genetic_algorithm.py# Bonus GA planner
├── requirements.txt
└── README.md
```

## Installation

Python 3 is required.

Install optional visualization dependencies:

```bash
python3 -m pip install -r requirements.txt
```

The core search algorithms use the Python standard library. PNG and GIF output need the packages in `requirements.txt`.

## Test Maps

| Map | What it demonstrates |
| --- | --- |
| `test_2_agents_easy.json` | Basic two-agent run |
| `test_3_agents_bottleneck_wait.json` | WAIT and coordination |
| `test_3_agents_weighted_cost.json` | BFS vs UCS/A* on weighted terrain |
| `test_3_agents_swap_trap.json` | Vertex and edge-swap collision handling |
| `test_3_agents_warehouse.json` | Larger warehouse-style layout |
| `test_4_agents_challenge.json` | Four-agent case |

## Output Files

When outputs are saved, files are written under:

```text
outputs/<map_name>/
```

Typical generated files:

```text
<algorithm>_log.txt
<algorithm>_trace.json
<algorithm>_solution_timeline.txt
<algorithm>_final_path.png
<algorithm>_solution.gif
<algorithm>_expansion_heatmap.png
comparison.csv
```

Generated files are ignored by Git. The repository only keeps `outputs/.gitkeep`.

## CLI Usage

The GUI is the main way to use the project, but the CLI is still available.

Run one algorithm:

```bash
python3 src/main.py --data data_test/test_2_agents_easy.json --algorithm astar
```

Run all required algorithms plus the bonus GA:

```bash
python3 src/main.py --data data_test/test_2_agents_easy.json --algorithm all
```

Print complete step-by-step search output:

```bash
python3 src/main.py --data data_test/test_2_agents_easy.json --algorithm bfs --verbose
```

Check WAIT behavior:

```bash
python3 src/verify_wait_logic.py
```

## Step-by-Step Logs

Each expansion log records:

- step number,
- selected node,
- generated child nodes,
- rejected children when verbose mode is enabled,
- frontier snapshot,
- explored or visited count,
- depth,
- `g(n)`,
- `h(n)` and `f(n)` for informed algorithms.

This information is shown in verbose CLI mode and saved in output log/trace files.

## Bonus Genetic Algorithm

The Genetic Algorithm is included as a bonus approximate planner.

It is not complete, not guaranteed optimal, and does not replace BFS, UCS, DFS, DLS, IDS, Greedy, or A*.

## Clean Before Commit

Generated local files should not be committed:

```bash
find . -name ".DS_Store" -delete
find . -name "__pycache__" -type d -prune -exec rm -rf {} +
find outputs -mindepth 1 ! -name ".gitkeep" -exec rm -rf {} +
touch outputs/.gitkeep
```
