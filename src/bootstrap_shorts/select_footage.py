"""Interactive selection of discovered raw footage files."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import typer

from bootstrap_shorts.errors import SelectionAborted

UNITS = ("B", "KB", "MB", "GB", "TB")


def format_size(size: int) -> str:
    value = float(size)
    for unit in UNITS:
        if value < 1024 or unit == UNITS[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def format_listing(files: list[Path], numbers: list[int] | None = None) -> list[str]:
    labels = numbers if numbers is not None else list(range(1, len(files) + 1))
    width = len(str(max(labels))) if labels else 1
    lines: list[str] = []
    for label, path in zip(labels, files, strict=True):
        try:
            size = format_size(path.stat().st_size)
        except OSError:
            size = "unknown"
        number = str(label).rjust(width)
        lines.append(f"  {number}. {path.name}    {size}")
    return lines


def parse_selection(text: str, count: int) -> list[int]:
    """Parse a selection string into 0-based indexes."""
    cleaned = text.strip().lower()
    if cleaned in {"q", "quit", "cancel"}:
        raise SelectionAborted("Footage selection cancelled")
    if cleaned in {"", "all", "a", "*"}:
        return list(range(count))

    indexes: set[int] = set()
    token = cleaned.replace(" ", ",")
    for part in token.split(","):
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            try:
                start = int(start_text)
                end = int(end_text)
            except ValueError as exc:
                raise ValueError(f"Invalid range: {part}") from exc
            if start < 1 or end > count or start > end:
                raise ValueError(f"Range out of bounds: {part}")
            indexes.update(range(start - 1, end))
            continue
        try:
            number = int(part)
        except ValueError as exc:
            raise ValueError(f"Invalid selection: {part}") from exc
        if number < 1 or number > count:
            raise ValueError(f"Selection out of bounds: {number}")
        indexes.add(number - 1)

    if not indexes:
        raise ValueError("No files selected")
    return sorted(indexes)


def select_raw_footage(
    files: list[Path],
    *,
    directory: Path,
    assume_yes: bool = False,
    echo: Callable[[str], None] = typer.echo,
    prompt: Callable[..., str] = typer.prompt,
    confirm: Callable[..., bool] = typer.confirm,
) -> list[Path]:
    """List discovered files, let the user choose, and confirm the set."""
    if assume_yes:
        return list(files)

    while True:
        echo(f"Discovered {len(files)} .mov file(s) in {directory}:")
        echo("")
        for line in format_listing(files):
            echo(line)
        echo("")
        echo("Enter numbers (1,3), ranges (1-3), all, or q to cancel.")
        raw = prompt("Select files to process", default="all")
        try:
            indexes = parse_selection(raw, len(files))
        except SelectionAborted:
            raise
        except ValueError as exc:
            echo(f"Invalid selection: {exc}")
            echo("")
            continue

        selected = [files[index] for index in indexes]
        echo("")
        echo(f"Selected {len(selected)} file(s):")
        for line in format_listing(selected, [index + 1 for index in indexes]):
            echo(line)
        echo("")
        if confirm("Process these files?", default=True):
            return selected
        echo("Selection cleared. Choose again.")
        echo("")
