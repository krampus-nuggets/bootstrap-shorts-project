from pathlib import Path

import pytest
import yaml

from bootstrap_shorts.config import load_config, parse_raw_config, resolve_config
from bootstrap_shorts.errors import ConfigError, ProjectExistsError


def _write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def _layout(tmp_path: Path) -> dict[str, Path]:
    templates = tmp_path / "templates"
    projects = tmp_path / "projects"
    footage = tmp_path / "clips"
    templates.mkdir()
    projects.mkdir()
    footage.mkdir()
    main = templates / "portrait-short-form.aep"
    preprocess = templates / "portrait-short-form-pre-process.aep"
    clip = footage / "clip-a.mp4"
    main.write_bytes(b"aep")
    preprocess.write_bytes(b"aep")
    clip.write_bytes(b"mp4")
    return {
        "templates": templates,
        "projects": projects,
        "clip": clip,
        "main": main,
        "preprocess": preprocess,
    }


def test_load_config_resolves_absolute_paths(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    config_path = _write_config(
        tmp_path,
        {
            "templates": str(layout["templates"]),
            "raw_footage": [str(layout["clip"])],
            "projects": str(layout["projects"]),
            "name": "client-short-01",
        },
    )

    resolved = load_config(config_path)

    assert resolved.name == "client-short-01"
    assert resolved.main_template == layout["main"].resolve()
    assert resolved.preprocess_template == layout["preprocess"].resolve()
    assert resolved.raw_footage == [layout["clip"].resolve()]
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
            "templates": "../templates",
            "raw_footage": ["../clips/clip-a.mp4"],
            "projects": "../projects",
            "name": "rel-project",
        },
    )

    resolved = load_config(config_path)

    assert resolved.templates_dir == layout["templates"].resolve()
    assert resolved.raw_footage[0] == layout["clip"].resolve()


def test_cli_overrides_win(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    extra = tmp_path / "clips" / "clip-b.mp4"
    extra.write_bytes(b"mp4")
    config_path = _write_config(
        tmp_path,
        {
            "templates": str(layout["templates"]),
            "raw_footage": [str(layout["clip"])],
            "projects": str(layout["projects"]),
            "name": "from-file",
        },
    )

    resolved = load_config(config_path, name="from-cli", raw_footage=[extra])

    assert resolved.name == "from-cli"
    assert resolved.raw_footage == [extra.resolve()]
    assert resolved.project_dir == (layout["projects"] / "from-cli").resolve()


def test_missing_key_is_invalid() -> None:
    with pytest.raises(ConfigError, match="Invalid config"):
        parse_raw_config({"templates": "x", "projects": "y", "raw_footage": []})


def test_unknown_key_is_rejected() -> None:
    with pytest.raises(ConfigError, match="Invalid config"):
        parse_raw_config(
            {
                "templates": "x",
                "projects": "y",
                "raw_footage": [],
                "name": "ok",
                "unexpected": True,
            }
        )


def test_missing_template(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    layout["main"].unlink()
    raw = parse_raw_config(
        {
            "templates": str(layout["templates"]),
            "raw_footage": [str(layout["clip"])],
            "projects": str(layout["projects"]),
            "name": "missing-template",
        }
    )

    with pytest.raises(ConfigError, match="Main template not found"):
        resolve_config(raw, config_dir=tmp_path)


def test_missing_footage(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    raw = parse_raw_config(
        {
            "templates": str(layout["templates"]),
            "raw_footage": [str(tmp_path / "missing.mp4")],
            "projects": str(layout["projects"]),
            "name": "missing-clip",
        }
    )

    with pytest.raises(ConfigError, match="Raw footage file not found"):
        resolve_config(raw, config_dir=tmp_path)


def test_existing_project_dir_without_force(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    existing = layout["projects"] / "already"
    existing.mkdir()
    raw = parse_raw_config(
        {
            "templates": str(layout["templates"]),
            "raw_footage": [str(layout["clip"])],
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
            "templates": str(layout["templates"]),
            "raw_footage": [str(layout["clip"])],
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
                "templates": "x",
                "projects": "y",
                "raw_footage": [],
                "name": "nested/name",
            }
        )


def test_missing_config_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="Config not found"):
        load_config(tmp_path / "nope.yaml")
