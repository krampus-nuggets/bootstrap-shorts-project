from pathlib import Path

import pytest
import yaml

from bootstrap_shorts.config import (
    discover_mov_files,
    load_config,
    parse_raw_config,
    resolve_config,
)
from bootstrap_shorts.errors import ConfigError, ProjectExistsError


def _write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def _layout(tmp_path: Path) -> dict[str, Path]:
    main_dir = tmp_path / "templates" / "portrait-short-form"
    preprocess_dir = tmp_path / "templates" / "portrait-short-form-pre-process"
    projects = tmp_path / "projects"
    footage = tmp_path / "clips"
    main_dir.mkdir(parents=True)
    preprocess_dir.mkdir(parents=True)
    projects.mkdir()
    footage.mkdir()
    main = main_dir / "portrait-short-form.aep"
    preprocess = preprocess_dir / "portrait-short-form-pre-process.aep"
    clip = footage / "clip-a.mov"
    other = footage / "notes.txt"
    ignored = footage / "clip-b.mp4"
    main.write_bytes(b"aep")
    preprocess.write_bytes(b"aep")
    clip.write_bytes(b"mov")
    other.write_bytes(b"txt")
    ignored.write_bytes(b"mp4")
    return {
        "main_dir": main_dir,
        "preprocess_dir": preprocess_dir,
        "projects": projects,
        "footage": footage,
        "clip": clip,
        "main": main,
        "preprocess": preprocess,
    }


def _templates(layout: dict[str, Path]) -> dict[str, str]:
    return {
        "main": str(layout["main_dir"]),
        "pre_process": str(layout["preprocess_dir"]),
    }


def test_load_config_discovers_mov_files(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    extra = layout["footage"] / "clip-c.MOV"
    extra.write_bytes(b"mov")
    config_path = _write_config(
        tmp_path,
        {
            "templates": _templates(layout),
            "raw_footage": str(layout["footage"]),
            "projects": str(layout["projects"]),
            "name": "client-short-01",
        },
    )

    resolved = load_config(config_path)

    assert resolved.name == "client-short-01"
    assert resolved.main_template == layout["main"].resolve()
    assert resolved.preprocess_template == layout["preprocess"].resolve()
    assert resolved.raw_footage_dir == layout["footage"].resolve()
    assert resolved.raw_footage == [layout["clip"].resolve(), extra.resolve()]
    assert resolved.project_dir == (layout["projects"] / "client-short-01").resolve()
    assert resolved.main_import_folder == "01-footage"
    assert resolved.preprocess_import_folder == "footage"


def test_relative_paths_resolve_against_config_dir(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    nested = tmp_path / "cfg"
    nested.mkdir()
    config_path = _write_config(
        nested,
        {
            "templates": {
                "main": "../templates/portrait-short-form",
                "pre_process": "../templates/portrait-short-form-pre-process",
            },
            "raw_footage": "../clips",
            "projects": "../projects",
            "name": "rel-project",
        },
    )

    resolved = load_config(config_path)

    assert resolved.main_template == layout["main"].resolve()
    assert resolved.preprocess_template == layout["preprocess"].resolve()
    assert resolved.raw_footage_dir == layout["footage"].resolve()
    assert resolved.raw_footage[0] == layout["clip"].resolve()


def test_template_file_paths_are_accepted(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    raw = parse_raw_config(
        {
            "templates": {
                "main": str(layout["main"]),
                "pre_process": str(layout["preprocess"]),
            },
            "raw_footage": str(layout["footage"]),
            "projects": str(layout["projects"]),
            "name": "direct-files",
        }
    )

    resolved = resolve_config(raw, config_dir=tmp_path)
    assert resolved.main_template == layout["main"].resolve()
    assert resolved.preprocess_template == layout["preprocess"].resolve()


def test_cli_overrides_win(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    override = tmp_path / "other-clips"
    override.mkdir()
    extra = override / "override.mov"
    extra.write_bytes(b"mov")
    config_path = _write_config(
        tmp_path,
        {
            "templates": _templates(layout),
            "raw_footage": str(layout["footage"]),
            "projects": str(layout["projects"]),
            "name": "from-file",
        },
    )

    resolved = load_config(config_path, name="from-cli", raw_footage=override)

    assert resolved.name == "from-cli"
    assert resolved.raw_footage_dir == override.resolve()
    assert resolved.raw_footage == [extra.resolve()]
    assert resolved.project_dir == (layout["projects"] / "from-cli").resolve()


def test_discover_mov_skips_non_mov(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    found = discover_mov_files(layout["footage"])
    assert found == [layout["clip"].resolve()]


def test_missing_key_is_invalid() -> None:
    with pytest.raises(ConfigError, match="Invalid config"):
        parse_raw_config({"projects": "y", "raw_footage": "clips"})


def test_unknown_key_is_rejected() -> None:
    with pytest.raises(ConfigError, match="Invalid config"):
        parse_raw_config(
            {
                "templates": {"main": "a", "pre_process": "b"},
                "projects": "y",
                "raw_footage": "clips",
                "name": "ok",
                "unexpected": True,
            }
        )


def test_missing_template(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    layout["main"].unlink()
    raw = parse_raw_config(
        {
            "templates": _templates(layout),
            "raw_footage": str(layout["footage"]),
            "projects": str(layout["projects"]),
            "name": "missing-template",
        }
    )

    with pytest.raises(ConfigError, match="Main template not found"):
        resolve_config(raw, config_dir=tmp_path)


def test_missing_template_directory(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    raw = parse_raw_config(
        {
            "templates": {
                "main": str(tmp_path / "missing-main"),
                "pre_process": str(layout["preprocess_dir"]),
            },
            "raw_footage": str(layout["footage"]),
            "projects": str(layout["projects"]),
            "name": "missing-dir",
        }
    )

    with pytest.raises(ConfigError, match="Main template path does not exist"):
        resolve_config(raw, config_dir=tmp_path)


def test_missing_footage_directory(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    raw = parse_raw_config(
        {
            "templates": _templates(layout),
            "raw_footage": str(tmp_path / "missing-clips"),
            "projects": str(layout["projects"]),
            "name": "missing-dir",
        }
    )

    with pytest.raises(ConfigError, match="raw_footage directory does not exist"):
        resolve_config(raw, config_dir=tmp_path)


def test_no_mov_files(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    empty = tmp_path / "empty"
    empty.mkdir()
    raw = parse_raw_config(
        {
            "templates": _templates(layout),
            "raw_footage": str(empty),
            "projects": str(layout["projects"]),
            "name": "empty-dir",
        }
    )

    with pytest.raises(ConfigError, match="No .mov files found"):
        resolve_config(raw, config_dir=tmp_path)


def test_existing_project_dir_without_force(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    existing = layout["projects"] / "already"
    existing.mkdir()
    raw = parse_raw_config(
        {
            "templates": _templates(layout),
            "raw_footage": str(layout["footage"]),
            "projects": str(layout["projects"]),
            "name": "already",
        }
    )

    with pytest.raises(ProjectExistsError, match="already exists"):
        resolve_config(raw, config_dir=tmp_path, force=False)


def test_existing_project_dir_allowed_with_force(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    (layout["projects"] / "already").mkdir()
    raw = parse_raw_config(
        {
            "templates": _templates(layout),
            "raw_footage": str(layout["footage"]),
            "projects": str(layout["projects"]),
            "name": "already",
        }
    )

    resolved = resolve_config(raw, config_dir=tmp_path, force=True)
    assert resolved.force is True


def test_invalid_name_rejected() -> None:
    with pytest.raises(ConfigError, match="Invalid config"):
        parse_raw_config(
            {
                "templates": {"main": "a", "pre_process": "b"},
                "projects": "y",
                "raw_footage": "clips",
                "name": "nested/name",
            }
        )


def test_missing_config_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="Config not found"):
        load_config(tmp_path / "nope.yaml")
