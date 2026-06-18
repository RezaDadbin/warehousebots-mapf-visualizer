# Tkinter visualizer for WarehouseBots MAPF runs.

from __future__ import annotations

import argparse
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

try:
    from .genetic_algorithm import genetic_algorithm_planner
    from .heuristics import sum_manhattan_heuristic
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
    from .utils import ensure_output_dir, project_root
    from .visualizer import AGENT_COLORS, save_final_path_png, save_solution_gif, save_solution_timeline
except ImportError:
    from genetic_algorithm import genetic_algorithm_planner
    from heuristics import sum_manhattan_heuristic
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
    from utils import ensure_output_dir, project_root
    from visualizer import AGENT_COLORS, save_final_path_png, save_solution_gif, save_solution_timeline


ALGORITHM_LABELS = ["BFS", "UCS", "DFS", "DLS", "IDS", "Greedy", "A*", "Genetic Algorithm"]

HELP_TEXT = (
    "Max Expansions stops very long searches after that many expanded nodes.\n"
    "DLS Depth Limit is the maximum depth allowed for Depth-Limited Search.\n"
    "IDS Max Depth is the highest depth limit Iterative Deepening will try.\n\n"
    "BFS/UCS/A* are more reliable on moderate maps. DFS and Greedy can fail "
    "or find poor paths when they explore a bad region. DLS fails when the "
    "solution is deeper than its limit. IDS fails when the solution is deeper "
    "than IDS Max Depth."
)

DEMO_PROFILES = {
    "easy": {
        "file": "data_test/test_2_agents_easy.json",
        "algorithm": "A*",
        "depth_limit": "12",
        "max_depth": "18",
        "max_expansions": "8000",
    },
    "challenge": {
        "file": "data_test/test_4_agents_challenge.json",
        "algorithm": "A*",
        "depth_limit": "8",
        "max_depth": "12",
        "max_expansions": "12000",
    },
}


class ToolTip:
    # Minimal tooltip for Tkinter widgets.

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event: tk.Event) -> None:
        if self.window is not None:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(
            self.window,
            text=self.text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            padding=6,
            wraplength=260,
        )
        label.pack()

    def _hide(self, _event: tk.Event) -> None:
        if self.window is not None:
            self.window.destroy()
            self.window = None


class WarehouseBotsGUI:
    # Small interactive Tkinter UI for running and replaying MAPF searches.

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("WarehouseBots MAPF Visualizer")
        self.project_root = project_root()
        self.problem: MAPFProblem | None = None
        self.result: Any | None = None
        self.logger: StepLogger | None = None
        self.solution_frames: list[tuple] = []
        self.expansion_frames: list[dict[str, Any]] = []
        self.file_values: list[str] = []
        self.frame_index = 0
        self.playing = False
        self.mode = tk.StringVar(value="Solution")

        self._configure_style()
        self._build_layout()
        self._populate_files()

    def _configure_style(self) -> None:
        self.root.option_add("*tearOff", False)
        self.root.configure(background="#f4f6f8")
        style = ttk.Style(self.root)
        try:
            style.configure("TFrame", background="#f4f6f8")
            style.configure("TLabelframe", background="#f4f6f8")
            style.configure("TLabelframe.Label", background="#f4f6f8", font=("TkDefaultFont", 12, "bold"))
            style.configure("TLabel", background="#f4f6f8")
            style.configure("TButton", padding=(10, 7))
            style.configure("Primary.TButton", padding=(10, 8), font=("TkDefaultFont", 12, "bold"))
            style.configure("TRadiobutton", background="#f4f6f8", padding=(4, 4))
        except tk.TclError:
            pass

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main = ttk.Frame(self.root, padding=12)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=0, minsize=285)
        main.columnconfigure(1, weight=1)
        main.columnconfigure(2, weight=0, minsize=330)
        main.rowconfigure(0, weight=1)
        main.rowconfigure(1, weight=0)

        self.file_var = tk.StringVar()
        self.algorithm_var = tk.StringVar(value="A*")
        self.depth_limit_var = tk.StringVar(value="12")
        self.max_depth_var = tk.StringVar(value="20")
        self.max_expansions_var = tk.StringVar(value="10000")
        self.speed_var = tk.IntVar(value=500)
        self.status_var = tk.StringVar(value="Choose a map, load it, then run an algorithm.")

        sidebar_shell = ttk.Frame(main)
        sidebar_shell.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        sidebar_shell.columnconfigure(0, weight=1)
        sidebar_shell.rowconfigure(0, weight=1)
        self.sidebar_canvas = tk.Canvas(
            sidebar_shell,
            width=285,
            background="#f4f6f8",
            highlightthickness=0,
            borderwidth=0,
        )
        self.sidebar_canvas.grid(row=0, column=0, sticky="nsew")
        sidebar_scroll = ttk.Scrollbar(sidebar_shell, orient="vertical", command=self.sidebar_canvas.yview)
        sidebar_scroll.grid(row=0, column=1, sticky="ns")
        self.sidebar_canvas.configure(yscrollcommand=sidebar_scroll.set)

        sidebar = ttk.Frame(self.sidebar_canvas)
        sidebar.columnconfigure(0, weight=1)
        self.sidebar_window = self.sidebar_canvas.create_window((0, 0), window=sidebar, anchor="nw")
        sidebar.bind("<Configure>", self._sync_sidebar_scroll)
        self.sidebar_canvas.bind("<Configure>", self._resize_sidebar)
        self.sidebar_canvas.bind("<Enter>", self._bind_sidebar_mousewheel)
        self.sidebar_canvas.bind("<Leave>", self._unbind_sidebar_mousewheel)

        map_frame = ttk.LabelFrame(sidebar, text="Map")
        map_frame.grid(row=0, column=0, sticky="ew")
        map_frame.columnconfigure(0, weight=1)
        map_frame.rowconfigure(0, weight=1)
        self.file_listbox = tk.Listbox(
            map_frame,
            height=7,
            exportselection=False,
            activestyle="dotbox",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#c8ced8",
            selectbackground="#2d6cdf",
            selectforeground="#ffffff",
        )
        self.file_listbox.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(8, 4))
        self.file_listbox.bind("<<ListboxSelect>>", self._on_file_select)
        map_scroll = ttk.Scrollbar(map_frame, orient="vertical", command=self.file_listbox.yview)
        map_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 8), pady=(8, 4))
        self.file_listbox.configure(yscrollcommand=map_scroll.set)
        ttk.Label(map_frame, textvariable=self.file_var, wraplength=240).grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 6))
        demo_buttons = ttk.Frame(map_frame)
        demo_buttons.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        demo_buttons.columnconfigure(0, weight=1)
        demo_buttons.columnconfigure(1, weight=1)
        ttk.Button(demo_buttons, text="Easy Demo", command=lambda: self.apply_preset("easy")).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(demo_buttons, text="4-Agent Challenge", command=lambda: self.apply_preset("challenge")).grid(row=0, column=1, sticky="ew", padx=(4, 0))
        ttk.Button(map_frame, text="Browse JSON", command=self._browse_file).grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))

        algorithm_frame = ttk.LabelFrame(sidebar, text="Algorithm")
        algorithm_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        for col in range(2):
            algorithm_frame.columnconfigure(col, weight=1)
        for index, label in enumerate(ALGORITHM_LABELS):
            ttk.Radiobutton(
                algorithm_frame,
                text=label,
                value=label,
                variable=self.algorithm_var,
            ).grid(row=index // 2, column=index % 2, sticky="w", padx=10, pady=3)

        actions_frame = ttk.LabelFrame(sidebar, text="Run")
        actions_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        actions_frame.columnconfigure(0, weight=1)
        actions_frame.columnconfigure(1, weight=1)
        ttk.Button(actions_frame, text="Load Map", command=self.load_map).grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        ttk.Button(actions_frame, text="Run Algorithm", style="Primary.TButton", command=self.run_algorithm).grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=(8, 4))
        ttk.Button(actions_frame, text="Step", command=self.step).grid(row=1, column=0, sticky="ew", padx=8, pady=4)
        ttk.Button(actions_frame, text="Play / Pause", command=self.toggle_play).grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=4)
        ttk.Button(actions_frame, text="Reset", command=self.reset).grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 8))
        ttk.Button(actions_frame, text="Save Outputs", command=self.save_outputs).grid(row=2, column=1, sticky="ew", padx=(0, 8), pady=(4, 8))

        playback_frame = ttk.LabelFrame(sidebar, text="Playback")
        playback_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        playback_frame.columnconfigure(0, weight=1)
        playback_frame.columnconfigure(1, weight=1)
        ttk.Radiobutton(playback_frame, text="Solution", value="Solution", variable=self.mode, command=self.draw_current_frame).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 4))
        ttk.Radiobutton(playback_frame, text="Expansion", value="Expansion", variable=self.mode, command=self.draw_current_frame).grid(row=0, column=1, sticky="w", padx=10, pady=(8, 4))
        ttk.Label(playback_frame, text="Speed").grid(row=1, column=0, sticky="w", padx=10, pady=(4, 8))
        ttk.Scale(playback_frame, from_=100, to=1500, variable=self.speed_var, orient="horizontal").grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(4, 8))

        params_frame = ttk.LabelFrame(sidebar, text="Limits")
        params_frame.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        params_frame.columnconfigure(1, weight=1)
        dls_label = ttk.Label(params_frame, text="DLS Depth")
        dls_label.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 4))
        ttk.Entry(params_frame, textvariable=self.depth_limit_var, width=8).grid(row=0, column=1, sticky="ew", padx=10, pady=(8, 4))
        ids_label = ttk.Label(params_frame, text="IDS Max Depth")
        ids_label.grid(row=1, column=0, sticky="w", padx=10, pady=4)
        ttk.Entry(params_frame, textvariable=self.max_depth_var, width=8).grid(row=1, column=1, sticky="ew", padx=10, pady=4)
        max_label = ttk.Label(params_frame, text="Max Expansions")
        max_label.grid(row=2, column=0, sticky="w", padx=10, pady=(4, 10))
        ttk.Entry(params_frame, textvariable=self.max_expansions_var, width=8).grid(row=2, column=1, sticky="ew", padx=10, pady=(4, 10))
        ToolTip(dls_label, "Maximum allowed search depth for Depth-Limited Search.")
        ToolTip(ids_label, "Highest depth limit Iterative Deepening will try.")
        ToolTip(max_label, "Maximum expanded nodes before stopping a long search.")

        help_frame = ttk.LabelFrame(sidebar, text="Notes")
        help_frame.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(help_frame, text=HELP_TEXT, wraplength=255, justify="left").grid(row=0, column=0, sticky="ew", padx=10, pady=8)

        self.canvas = tk.Canvas(main, width=620, height=520, background="#ffffff", highlightthickness=1, highlightbackground="#c8ced8")
        self.canvas.grid(row=0, column=1, sticky="nsew")

        info_frame = ttk.LabelFrame(main, text="Run Details")
        info_frame.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        info_frame.rowconfigure(0, weight=1)
        info_frame.columnconfigure(0, weight=1)
        self.info = tk.Text(
            info_frame,
            width=38,
            height=24,
            wrap="word",
            relief="flat",
            background="#fbfcfe",
            foreground="#18202b",
            padx=10,
            pady=10,
        )
        self.info.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        info_scroll = ttk.Scrollbar(info_frame, orient="vertical", command=self.info.yview)
        info_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 8), pady=8)
        self.info.configure(yscrollcommand=info_scroll.set, state="disabled")

        status = ttk.Label(main, textvariable=self.status_var, anchor="w")
        status.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10, 0))

    def _sync_sidebar_scroll(self, _event: tk.Event | None = None) -> None:
        self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all"))

    def _resize_sidebar(self, event: tk.Event) -> None:
        self.sidebar_canvas.itemconfigure(self.sidebar_window, width=event.width)

    def _bind_sidebar_mousewheel(self, _event: tk.Event) -> None:
        self.sidebar_canvas.bind_all("<MouseWheel>", self._on_sidebar_mousewheel)
        self.sidebar_canvas.bind_all("<Button-4>", self._on_sidebar_mousewheel)
        self.sidebar_canvas.bind_all("<Button-5>", self._on_sidebar_mousewheel)

    def _unbind_sidebar_mousewheel(self, _event: tk.Event) -> None:
        self.sidebar_canvas.unbind_all("<MouseWheel>")
        self.sidebar_canvas.unbind_all("<Button-4>")
        self.sidebar_canvas.unbind_all("<Button-5>")

    def _on_sidebar_mousewheel(self, event: tk.Event) -> None:
        if getattr(event, "num", None) == 4:
            units = -3
        elif getattr(event, "num", None) == 5:
            units = 3
        elif getattr(event, "delta", 0) != 0:
            delta = int(event.delta)
            units = -int(delta / abs(delta))
            if abs(delta) >= 120:
                units = -int(delta / 120)
        else:
            return
        self.sidebar_canvas.yview_scroll(units, "units")

    def _populate_files(self) -> None:
        files = sorted((self.project_root / "data_test").glob("*.json"))
        self.file_values = [str(path.relative_to(self.project_root)) for path in files]
        self.file_listbox.delete(0, tk.END)
        for value in self.file_values:
            self.file_listbox.insert(tk.END, value)
        if self.file_values:
            self._select_file_value(self.file_values[0])

    def apply_preset(self, preset: str = "easy") -> None:
        # Apply demo-safe map and parameter shortcuts.
        profile = DEMO_PROFILES["challenge" if preset == "challenge" else "easy"]
        self._select_file_value(profile["file"])
        self.algorithm_var.set(profile["algorithm"])
        self.depth_limit_var.set(profile["depth_limit"])
        self.max_depth_var.set(profile["max_depth"])
        self.max_expansions_var.set(profile["max_expansions"])
        self.load_map()

    def _browse_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if path:
            self._select_file_value(str(Path(path)))

    def _on_file_select(self, _event: tk.Event) -> None:
        selection = self.file_listbox.curselection()
        if selection:
            self.file_var.set(self.file_listbox.get(selection[0]))

    def _select_file_value(self, value: str) -> None:
        self.file_var.set(value)
        if value not in self.file_values:
            self.file_values.insert(0, value)
            self.file_listbox.insert(0, value)
        index = self.file_values.index(value)
        self.file_listbox.selection_clear(0, tk.END)
        self.file_listbox.selection_set(index)
        self.file_listbox.activate(index)
        self.file_listbox.see(index)

    def load_map(self) -> None:
        try:
            path = self._selected_file_path()
            self.problem = MAPFProblem.from_json(path)
            self.problem.max_expansions = int(self.max_expansions_var.get())
            self.result = None
            self.logger = None
            self.solution_frames = [self.problem.initial_state()]
            self.expansion_frames = []
            self.frame_index = 0
            self.draw_state(self.problem.initial_state())
            self._write_info(f"Loaded {self.problem.name}\nAgents: {', '.join(self.problem.agent_ids)}")
            self.status_var.set(f"Loaded {self.problem.name}. Choose an algorithm and run.")
        except Exception as exc:
            self.status_var.set("Map load failed.")
            messagebox.showerror("Load failed", str(exc))

    def run_algorithm(self) -> None:
        if self.problem is None:
            self.load_map()
        if self.problem is None:
            return
        try:
            self.problem.max_expansions = int(self.max_expansions_var.get())
            algorithm = self.algorithm_var.get()
            self.logger = None if algorithm == "Genetic Algorithm" else StepLogger(algorithm=algorithm, verbose=False)
            args = argparse.Namespace(
                depth_limit=int(self.depth_limit_var.get()),
                max_depth=int(self.max_depth_var.get()),
            )
            self._write_info(f"Running {algorithm}...\nThe window may pause until the bounded search finishes.")
            self.status_var.set(f"Running {algorithm}...")
            self.root.update_idletasks()
            self.result = self._dispatch(algorithm, args)
            self.solution_frames = self.result.solution_states or [self.problem.initial_state()]
            self.expansion_frames = self._sample_expansions(self.logger.trace_records if self.logger else [])
            self.frame_index = 0
            self.draw_current_frame()
            self._write_result_info()
            self.status_var.set(f"{algorithm} finished: {self.result.message}")
        except Exception as exc:
            self.status_var.set("Algorithm run failed.")
            messagebox.showerror("Run failed", str(exc))

    def step(self) -> None:
        frames = self._active_frames()
        if not frames:
            return
        self.frame_index = min(self.frame_index + 1, len(frames) - 1)
        self.draw_current_frame()

    def toggle_play(self) -> None:
        self.playing = not self.playing
        if self.playing:
            self._play_tick()

    def reset(self) -> None:
        self.playing = False
        self.frame_index = 0
        self.draw_current_frame()

    def save_outputs(self) -> None:
        if self.problem is None or self.result is None:
            messagebox.showinfo("Nothing to save", "Run an algorithm first.")
            return
        output_dir = ensure_output_dir(self.project_root / "outputs" / self.problem.name)
        slug = self.algorithm_var.get().lower().replace("*", "star").replace(" ", "_")
        if self.result.solution_states:
            save_solution_timeline(self.problem, self.result.solution_states, output_dir / f"{slug}_gui_timeline.txt", self.result.solution_actions)
            save_final_path_png(self.problem, self.result.solution_states, output_dir / f"{slug}_gui_final_path.png")
            save_solution_gif(self.problem, self.result.solution_states, output_dir / f"{slug}_gui_solution.gif", self.result.solution_actions)
        if self.logger:
            self.logger.log_result(self.result)
            self.logger.save(output_dir / f"{slug}_gui_log.txt")
        self.status_var.set(f"Outputs saved in {output_dir}")
        messagebox.showinfo("Saved", f"Outputs saved in {output_dir}")

    def draw_current_frame(self) -> None:
        frames = self._active_frames()
        if not frames or self.problem is None:
            return
        if self.mode.get() == "Expansion":
            record = frames[self.frame_index]
            state = tuple(tuple(cell) for cell in record.get("selected_state", self.problem.initial_state()))
            self.draw_state(state)
            self._write_info(self._expansion_text(record))
        else:
            self.draw_state(frames[self.frame_index])
            if self.result is not None:
                self._write_result_info()

    def draw_state(self, state: tuple) -> None:
        if self.problem is None:
            return
        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        cell_size = min(width / self.problem.cols, height / self.problem.rows)
        x_offset = (width - cell_size * self.problem.cols) / 2
        y_offset = (height - cell_size * self.problem.rows) / 2

        for row in range(self.problem.rows):
            for col in range(self.problem.cols):
                x1 = x_offset + col * cell_size
                y1 = y_offset + row * cell_size
                x2 = x1 + cell_size
                y2 = y1 + cell_size
                symbol = self.problem.grid[row][col]
                color = "#222222" if symbol == "#" else "#ffffff"
                if symbol.isdigit() or self.problem._cell_extra_cost((row, col)) > 0:
                    color = "#ffd9a3"
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#bbbbbb")
                if symbol.isdigit():
                    self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=symbol, fill="#7a3f00")

        for agent in self.problem.agents:
            gx, gy = self._cell_center(agent.goal, x_offset, y_offset, cell_size)
            color = AGENT_COLORS.get(agent.agent_id[0].upper(), "#777777")
            self.canvas.create_text(gx, gy, text="★", fill=color, font=("Arial", max(12, int(cell_size * 0.35)), "bold"))
            sx, sy = self._cell_center(agent.start, x_offset, y_offset, cell_size)
            radius = cell_size * 0.18
            self.canvas.create_oval(sx - radius, sy - radius, sx + radius, sy + radius, outline=color, width=2)

        for agent_id, position in zip(self.problem.agent_ids, state):
            x, y = self._cell_center(position, x_offset, y_offset, cell_size)
            color = AGENT_COLORS.get(agent_id[0].upper(), "#777777")
            radius = cell_size * 0.32
            self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill=color, outline="#111111")
            self.canvas.create_text(x, y, text=agent_id, fill="#ffffff", font=("Arial", max(10, int(cell_size * 0.28)), "bold"))

    def _dispatch(self, algorithm: str, args: argparse.Namespace) -> Any:
        assert self.problem is not None
        if algorithm == "BFS":
            return breadth_first_search(self.problem, self.logger)
        if algorithm == "UCS":
            return uniform_cost_search(self.problem, self.logger)
        if algorithm == "DFS":
            return depth_first_search(self.problem, self.logger)
        if algorithm == "DLS":
            return depth_limited_search(self.problem, args.depth_limit, self.logger)
        if algorithm == "IDS":
            return iterative_deepening_search(self.problem, args.max_depth, self.logger)
        if algorithm == "Greedy":
            return greedy_best_first_search(self.problem, sum_manhattan_heuristic, self.logger)
        if algorithm == "A*":
            return a_star_search(self.problem, sum_manhattan_heuristic, self.logger)
        if algorithm == "Genetic Algorithm":
            return genetic_algorithm_planner(self.problem)
        raise ValueError(f"Unknown algorithm: {algorithm}")

    def _active_frames(self) -> list[Any]:
        if self.mode.get() == "Expansion" and self.expansion_frames:
            return self.expansion_frames
        return self.solution_frames

    def _play_tick(self) -> None:
        if not self.playing:
            return
        frames = self._active_frames()
        if not frames:
            self.playing = False
            return
        if self.frame_index < len(frames) - 1:
            self.frame_index += 1
            self.draw_current_frame()
            self.root.after(int(self.speed_var.get()), self._play_tick)
        else:
            self.playing = False

    def _selected_file_path(self) -> Path:
        text = self.file_var.get()
        path = Path(text)
        if path.is_absolute():
            return path
        return self.project_root / path

    def _cell_center(self, position: tuple[int, int], x_offset: float, y_offset: float, cell_size: float) -> tuple[float, float]:
        row, col = position
        return x_offset + (col + 0.5) * cell_size, y_offset + (row + 0.5) * cell_size

    def _sample_expansions(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        expansions = [record for record in records if record.get("type") == "expansion"]
        if len(expansions) <= 1000:
            return expansions
        step = max(1, len(expansions) // 1000)
        return expansions[::step]

    def _write_result_info(self) -> None:
        if self.result is None:
            return
        frame_text = f"{self.frame_index + 1}/{len(self._active_frames())}" if self._active_frames() else "0/0"
        lines = [
            f"Algorithm: {self.algorithm_var.get()}",
            f"Current frame: {frame_text}",
            f"Success: {self.result.success}",
            f"Cost: {self.result.total_cost}",
            f"Depth: {self.result.depth}",
            f"Expanded: {self.result.expanded_nodes}",
            f"Generated: {self.result.generated_nodes}",
            f"Max frontier: {self.result.max_frontier_size}",
            f"Message: {self.result.message}",
        ]
        guidance = self._failure_guidance()
        if guidance:
            lines.extend(["", guidance])
        if self.result.solution_actions and self.frame_index > 0 and self.frame_index - 1 < len(self.result.solution_actions):
            lines.append(f"Selected joint action: {self.result.solution_actions[self.frame_index - 1]}")
        self._write_info("\n".join(lines))

    def _failure_guidance(self) -> str:
        if self.result is None or self.result.success:
            return ""
        message = self.result.message.lower()
        algorithm = self.algorithm_var.get()
        if "maximum expansion" in message:
            return (
                "Stopped because max_expansions was reached. Try increasing "
                "Max Expansions, using A*/UCS, or choosing an easier map."
            )
        if algorithm == "DLS" or "depth limit" in message:
            return "No solution found within the selected depth limit. Increase DLS Depth Limit."
        if algorithm == "IDS" or "max depth" in message:
            return "No solution found up to IDS Max Depth. Increase IDS Max Depth."
        return "Failure does not necessarily mean the implementation is wrong; try an easier map or a different algorithm."

    def _expansion_text(self, record: dict[str, Any]) -> str:
        children = record.get("valid_children", [])[:15]
        lines = [
            f"Algorithm: {record.get('algorithm')}",
            f"Expansion step: {record.get('step')}",
            f"Selected node ID: {record.get('selected_node_id')}",
            f"Depth: {record.get('depth')}",
            f"g/h/f: {record.get('path_cost')} / {record.get('h')} / {record.get('f')}",
            f"Expanded: {record.get('expanded_nodes')}",
            f"Generated: {record.get('generated_nodes')}",
            f"Frontier size: {record.get('frontier_size')}",
            f"Action: {record.get('action_from_parent')}",
            "",
            "Generated children:",
        ]
        lines.extend(str(child) for child in children)
        return "\n".join(lines)

    def _write_info(self, text: str) -> None:
        self.info.configure(state="normal")
        self.info.delete("1.0", tk.END)
        self.info.insert(tk.END, text)
        self.info.configure(state="disabled")


def run_gui() -> None:
    # Start the Tkinter application.
    root = tk.Tk()
    WarehouseBotsGUI(root)
    root.geometry("1180x720")
    root.minsize(980, 640)
    root.mainloop()
