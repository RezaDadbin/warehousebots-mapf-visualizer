# WarehouseBots MAPF Visualizer

Interactive desktop visualizer for **Multi-Agent Path Finding** with classical AI search.

WarehouseBots turns a grid map into a live search playground: load a JSON scenario, choose an algorithm, run the planner, step through the solution, inspect expansion states, and export logs or visuals. It is built around a centralized MAPF model where each node represents all agents at the same timestep.

```bash
python3 app.py
```

## Highlights

- GUI-first workflow for running and comparing MAPF search algorithms.
- Manual implementations of BFS, UCS, DFS, DLS, IDS, Greedy Best-First Search, and A*.
- Bonus Genetic Algorithm planner for approximate comparison.
- Collision-safe joint-action generation for multiple agents.
- Built-in maps for bottlenecks, weighted-cost routing, swap traps, warehouse layouts, and four-agent cases.
- Step-by-step expansion traces with selected nodes, generated children, frontier snapshots, costs, and heuristic values.
- Export support for text timelines, JSON traces, PNG path images, heatmaps, GIF animations, and comparison CSV files.

## Quick Start

Clone the repository and run the GUI:

```bash
git clone https://github.com/RezaDadbin/warehousebots-mapf-visualizer.git
cd warehousebots-mapf-visualizer
python3 -m pip install -r requirements.txt
python3 app.py
```

The core search code uses the Python standard library. The packages in `requirements.txt` are used for PNG/GIF output.

## GUI Workflow

1. Select a map from the left panel.
2. Select an algorithm.
3. Click `Load Map`.
4. Click `Run Algorithm`.
5. Use `Step` or `Play / Pause` to inspect the path.
6. Switch between `Solution` and `Expansion`.
7. Click `Save Outputs` to write logs and visual files into `outputs/`.

The GUI includes two shortcuts:

- `Easy Demo`: a small two-agent scenario.
- `4-Agent Challenge`: a larger multi-agent case.

These shortcuts only set the map and recommended parameters. The same backend planner is used in every case.

## Algorithms

| Category | Implemented algorithms |
| --- | --- |
| Uninformed search | BFS, UCS, DFS, DLS, IDS |
| Informed search | Greedy Best-First Search, A* |
| Bonus | Genetic Algorithm |

Greedy Best-First Search uses:

```text
f(n) = h(n)
```

A* uses:

```text
f(n) = g(n) + h(n)
```

UCS and A* test for the goal when a node is selected from the priority frontier.

## MAPF Model

The project uses a centralized search state. A state is a tuple of all agent positions:

```python
((0, 0), (4, 0), (2, 3))
```

A joint action contains one primitive action per agent:

```python
("RIGHT", "WAIT", "UP")
```

Available primitive actions:

```text
UP, RIGHT, DOWN, LEFT, WAIT
```

## Collision Handling

Generated children are rejected if they violate the MAPF rules:

- outside-grid movement,
- wall collision,
- vertex collision,
- edge-swap collision,
- all-agents-WAIT self-loop.

Individual WAIT actions are allowed. The all-agents-WAIT action is rejected because it does not change the state.

## Cost Model

Each valid joint action has a positive cost:

```text
action cost = base cost + movement cost + terrain cost
```

- `base cost`: one step is taken.
- `movement cost`: number of agents that moved.
- `terrain cost`: extra cost for weighted cells.

This makes weighted maps useful for showing the difference between depth-based search and cost-based search. BFS finds shallow plans, while UCS and A* optimize the configured path cost.

## Built-In Maps

| Map | Scenario |
| --- | --- |
| `test_2_agents_easy.json` | Small two-agent baseline |
| `test_3_agents_bottleneck_wait.json` | Coordination through a bottleneck |
| `test_3_agents_weighted_cost.json` | Weighted terrain, BFS vs UCS/A* |
| `test_3_agents_swap_trap.json` | Vertex and edge-swap collision check |
| `test_3_agents_warehouse.json` | Warehouse-style corridor layout |
| `test_4_agents_challenge.json` | Four-agent challenge |

## CLI Mode

The GUI is the main interface, but the CLI is useful for automation and detailed logs.

Run A*:

```bash
python3 src/main.py --data data_test/test_2_agents_easy.json --algorithm astar
```

Run all required algorithms plus the bonus GA:

```bash
python3 src/main.py --data data_test/test_2_agents_easy.json --algorithm all
```

Print a complete expansion log in the terminal:

```bash
python3 src/main.py --data data_test/test_2_agents_easy.json --algorithm bfs --verbose
```

Check WAIT behavior:

```bash
python3 src/verify_wait_logic.py
```

## Output Files

Generated files are written under:

```text
outputs/<map_name>/
```

Typical outputs:

```text
<algorithm>_log.txt
<algorithm>_trace.json
<algorithm>_solution_timeline.txt
<algorithm>_final_path.png
<algorithm>_solution.gif
<algorithm>_expansion_heatmap.png
comparison.csv
```

Expansion logs include:

- step number,
- selected node,
- generated children,
- rejected children in verbose mode,
- frontier snapshot,
- explored or visited count,
- depth,
- `g(n)`,
- `h(n)` and `f(n)` for informed search.

Generated outputs are ignored by Git. The repository only keeps `outputs/.gitkeep`.

## Code Structure

```text
.
├── app.py                    # GUI launcher
├── data_test/                # JSON scenarios
├── outputs/                  # Generated output folder
├── src/
│   ├── gui.py                # Tkinter application
│   ├── main.py               # CLI runner and output saving
│   ├── mapf_problem.py       # MAPF state, actions, costs, validation
│   ├── search_algorithms.py  # BFS, UCS, DFS, DLS, IDS, Greedy, A*
│   ├── frontier.py           # FIFO, LIFO, and priority frontiers
│   ├── logger.py             # Text logs and JSON traces
│   ├── visualizer.py         # Timeline, PNG, heatmap, GIF helpers
│   ├── heuristics.py         # Heuristic functions
│   └── genetic_algorithm.py  # Bonus approximate planner
├── requirements.txt
└── README.md
```

## Why This Project Is Useful

MAPF is hard to understand from final paths alone. This app shows both the final solution and the search process behind it. That makes it useful for learning how frontier-based search behaves, how heuristics change the search order, and why collision rules matter in multi-agent planning.

## Notes

The Genetic Algorithm is included as an approximate bonus planner. It is not complete, not guaranteed optimal, and does not replace the classical search algorithms.

## Clean Generated Files

```bash
find . -name ".DS_Store" -delete
find . -name "__pycache__" -type d -prune -exec rm -rf {} +
find outputs -mindepth 1 ! -name ".gitkeep" -exec rm -rf {} +
touch outputs/.gitkeep
```
