"""Command-line entry point."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer

from bootstrap_shorts.ae_bridge import DEFAULT_TIMEOUT_SECONDS
from bootstrap_shorts.config import load_config
from bootstrap_shorts.errors import BootstrapError
from bootstrap_shorts.pipeline import run_bootstrap


def main(
    config: Annotated[
        Path,
        typer.Option("--config", "-c", help="Path to the YAML config file."),
    ] = Path("config.yaml"),
    name: Annotated[
        str | None,
        typer.Option("--name", help="Override the new project name."),
    ] = None,
    raw_footage: Annotated[
        Path | None,
        typer.Option("--raw-footage", help="Override the raw footage directory."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Replace an existing project directory."),
    ] = False,
    timeout: Annotated[
        float,
        typer.Option("--timeout", help="Seconds to wait for After Effects to finish."),
    ] = DEFAULT_TIMEOUT_SECONDS,
) -> None:
    """Bootstrap a new After Effects shorts project from templates."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        resolved = load_config(
            config,
            name=name,
            raw_footage=raw_footage,
            force=force,
        )
        run_bootstrap(resolved, timeout=timeout)
    except BootstrapError as exc:
        typer.secho(str(exc), fg="red", err=True)
        raise typer.Exit(code=1) from exc


def app() -> None:
    typer.run(main)


if __name__ == "__main__":
    app()
