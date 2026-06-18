# Comparison table and CSV helpers.

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

try:
    from .utils import ensure_output_dir
except ImportError:
    from utils import ensure_output_dir


def format_comparison_table(results: Iterable[object]) -> str:
    # Return a plain-text comparison table for algorithm results.
    rows = [
        [
            result.algorithm,
            str(result.success),
            _fmt(result.total_cost),
            str(result.depth),
            str(result.expanded_nodes),
            str(result.generated_nodes),
            str(result.max_frontier_size),
            f"{result.runtime_seconds:.4f}",
            result.timeline_path or result.trace_path or "",
        ]
        for result in results
    ]
    headers = [
        "Algorithm",
        "Success",
        "Cost",
        "Depth",
        "Expanded",
        "Generated",
        "Max Frontier",
        "Runtime",
        "Output Path",
    ]
    widths = [
        max(len(str(row[index])) for row in rows + [headers])
        for index in range(len(headers))
    ]
    lines = [" | ".join(header.ljust(widths[index]) for index, header in enumerate(headers))]
    lines.append("-+-".join("-" * width for width in widths))
    lines.extend(
        " | ".join(str(value).ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    )
    return "\n".join(lines)


def save_comparison_csv(results: Iterable[object], path: str | Path) -> str:
    # Save algorithm metrics to a CSV file.
    target = Path(path)
    ensure_output_dir(target.parent)
    with target.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "Algorithm",
                "Success",
                "Cost",
                "Depth",
                "Expanded",
                "Generated",
                "Max Frontier",
                "Runtime Seconds",
                "Message",
                "Trace Path",
                "Timeline Path",
                "Image Path",
                "GIF Path",
            ]
        )
        for result in results:
            writer.writerow(
                [
                    result.algorithm,
                    result.success,
                    result.total_cost,
                    result.depth,
                    result.expanded_nodes,
                    result.generated_nodes,
                    result.max_frontier_size,
                    f"{result.runtime_seconds:.6f}",
                    result.message,
                    result.trace_path or "",
                    result.timeline_path or "",
                    result.image_path or "",
                    result.gif_path or "",
                ]
            )
    return str(target)


def _fmt(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.2f}"
