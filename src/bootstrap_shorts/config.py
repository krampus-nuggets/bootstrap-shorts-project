"""Load and validate the universal YAML config."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from bootstrap_shorts.errors import ConfigError, ProjectExistsError

DEFAULT_MAIN_TEMPLATE = "portrait-short-form.aep"
DEFAULT_PREPROCESS_TEMPLATE = "portrait-short-form-pre-process.aep"
DEFAULT_MAIN_IMPORT_FOLDER = "01-footage"
DEFAULT_PREPROCESS_IMPORT_FOLDER = "footage"


class TemplatesMap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    main: str = DEFAULT_MAIN_TEMPLATE
    pre_process: str = DEFAULT_PREPROCESS_TEMPLATE


class ProjectFolders(BaseModel):
    model_config = ConfigDict(extra="forbid")

    main_import: str = DEFAULT_MAIN_IMPORT_FOLDER
    preprocess_import: str = DEFAULT_PREPROCESS_IMPORT_FOLDER


class RawConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    templates: Path
    raw_footage: list[Path] = Field(default_factory=list)
    projects: Path
    name: str
    after_effects_exe: Path | None = None
    templates_map: TemplatesMap = Field(default_factory=TemplatesMap)
    project_folders: ProjectFolders = Field(default_factory=ProjectFolders)

    @field_validator("name")
    @classmethod
    def name_is_single_segment(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("name must not be empty")
        if "/" in name or "\\" in name or name in {".", ".."}:
            raise ValueError("name must be a single folder segment")
        return name


class ResolvedConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    name: str
    templates_dir: Path
    projects_dir: Path
    project_dir: Path
    raw_footage: list[Path]
    main_template: Path
    preprocess_template: Path
    after_effects_exe: Path | None
    main_import_folder: str
    preprocess_import_folder: str
    force: bool = False


def _resolve_path(value: Path, base: Path) -> Path:
    path = value.expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        raise ConfigError(f"Config not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"Config root must be a mapping: {path}")
    return data


def parse_raw_config(
    data: dict,
    *,
    name: str | None = None,
    raw_footage: list[Path] | None = None,
) -> RawConfig:
    payload = dict(data)
    if name:
        payload["name"] = name
    if raw_footage:
        payload["raw_footage"] = [str(path) for path in raw_footage]
    try:
        return RawConfig.model_validate(payload)
    except Exception as exc:
        raise ConfigError(f"Invalid config: {exc}") from exc


def resolve_config(
    raw: RawConfig,
    *,
    config_dir: Path,
    force: bool = False,
) -> ResolvedConfig:
    base = config_dir.resolve()
    templates_dir = _resolve_path(raw.templates, base)
    projects_dir = _resolve_path(raw.projects, base)
    after_effects_exe = (
        _resolve_path(raw.after_effects_exe, base) if raw.after_effects_exe else None
    )

    if not templates_dir.is_dir():
        raise ConfigError(f"templates directory does not exist: {templates_dir}")
    if not projects_dir.exists():
        raise ConfigError(f"projects directory does not exist: {projects_dir}")
    if not projects_dir.is_dir():
        raise ConfigError(f"projects is not a directory: {projects_dir}")

    main_template = (templates_dir / raw.templates_map.main).resolve()
    preprocess_template = (templates_dir / raw.templates_map.pre_process).resolve()
    if not main_template.is_file():
        raise ConfigError(f"Main template not found: {main_template}")
    if not preprocess_template.is_file():
        raise ConfigError(f"Pre-process template not found: {preprocess_template}")

    footage: list[Path] = []
    for item in raw.raw_footage:
        path = _resolve_path(item, base)
        if not path.is_file():
            raise ConfigError(f"Raw footage file not found: {path}")
        footage.append(path)

    project_dir = (projects_dir / raw.name).resolve()
    if project_dir.exists() and not force:
        raise ProjectExistsError(
            f"Project directory already exists: {project_dir} (use --force to replace it)"
        )

    return ResolvedConfig(
        name=raw.name,
        templates_dir=templates_dir,
        projects_dir=projects_dir,
        project_dir=project_dir,
        raw_footage=footage,
        main_template=main_template,
        preprocess_template=preprocess_template,
        after_effects_exe=after_effects_exe,
        main_import_folder=raw.project_folders.main_import,
        preprocess_import_folder=raw.project_folders.preprocess_import,
        force=force,
    )


def load_config(
    path: Path,
    *,
    name: str | None = None,
    raw_footage: list[Path] | None = None,
    force: bool = False,
) -> ResolvedConfig:
    data = load_yaml(path)
    raw = parse_raw_config(data, name=name, raw_footage=raw_footage)
    return resolve_config(raw, config_dir=path.parent, force=force)
