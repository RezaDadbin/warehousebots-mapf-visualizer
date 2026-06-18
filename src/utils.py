# General utility helpers for WarehouseBots.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def ensure_output_dir(path: str | Path) -> Path:
    # Create an output directory if needed and return it.
    output_path = Path(path)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def load_json(path: str | Path) -> dict[str, Any]:
    # Load a JSON object from disk.
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def format_state(state: tuple[tuple[int, int], ...]) -> str:
    # Format a MAPF state compactly.
    return "(" + ", ".join(f"({row},{col})" for row, col in state) + ")"


def json_safe(value: Any) -> Any:
    # Convert tuples, dataclasses, and Paths into JSON-safe structures.
    if hasattr(value, "__dataclass_fields__"):
        return {
            key: json_safe(getattr(value, key))
            for key in value.__dataclass_fields__
        }
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    return value


def project_root() -> Path:
    # Return the project directory containing ``src`` and ``data_test``.
    return Path(__file__).resolve().parents[1]


def resolve_project_path(path: str | Path, base: Path | None = None) -> Path:
    # Resolve a user path from cwd first, then from project root.
    candidate = Path(path)
    if candidate.is_absolute() or candidate.exists():
        return candidate
    root_candidate = (base or project_root()) / candidate
    return root_candidate

