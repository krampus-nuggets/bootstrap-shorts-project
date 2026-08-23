"""Locate AfterFX.exe on Windows."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from pathlib import Path

from bootstrap_shorts.errors import AfterFXNotFoundError, ConfigError

_YEAR = re.compile(r"(\d{4})")


def default_search_roots() -> list[Path]:
    roots: list[Path] = []
    for key in ("ProgramFiles", "PROGRAMFILES", "ProgramFiles(x86)", "PROGRAMFILES(X86)"):
        value = os.environ.get(key)
        if value:
            roots.append(Path(value))
    if not roots:
        roots = [Path(r"C:\Program Files"), Path(r"C:\Program Files (x86)")]
    # Preserve order while dropping duplicates.
    unique: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        resolved = root.resolve() if root.exists() else root
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return unique


def _sort_key(exe: Path) -> tuple[int, int]:
    folder = exe.parent.parent.name
    match = _YEAR.search(folder)
    year = int(match.group(1)) if match else 0
    prefer_release = 0 if "beta" in folder.lower() else 1
    return (year, prefer_release)


def discover_afterfx(search_roots: Iterable[Path]) -> list[Path]:
    found: list[Path] = []
    for root in search_roots:
        adobe = root / "Adobe"
        if not adobe.is_dir():
            continue
        for child in adobe.iterdir():
            if not child.is_dir() or not child.name.startswith("Adobe After Effects"):
                continue
            exe = child / "Support Files" / "AfterFX.exe"
            if exe.is_file():
                found.append(exe.resolve())
    found.sort(key=_sort_key)
    return found


def resolve_afterfx(
    explicit: Path | None = None,
    search_roots: Iterable[Path] | None = None,
) -> Path:
    if explicit is not None:
        path = explicit.expanduser().resolve()
        if not path.is_file():
            raise ConfigError(f"after_effects_exe is not a file: {path}")
        return path

    roots = list(search_roots) if search_roots is not None else default_search_roots()
    candidates = discover_afterfx(roots)
    if not candidates:
        searched = ", ".join(str(root) for root in roots) or "(none)"
        raise AfterFXNotFoundError(
            "Could not find AfterFX.exe. Set after_effects_exe in the config "
            f"or install After Effects. Searched: {searched}"
        )
    return candidates[-1]
