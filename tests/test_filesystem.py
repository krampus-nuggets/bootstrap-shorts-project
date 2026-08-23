from pathlib import Path

import pytest

from bootstrap_shorts.config import ResolvedConfig
from bootstrap_shorts.errors import ConfigError
from bootstrap_shorts.filesystem import (
    as_ae_path,
    build_job_payload,
    copy_raw_footage,
    disk_footage_dir,
    job_path,
    prepare_project_dir,
    result_path,
    write_job_json,
)


def _config(tmp_path: Path, name: str = "client-short-01") -> ResolvedConfig:
    templates = tmp_path / "templates"
    projects = tmp_path / "projects"
    templates.mkdir()
    projects.mkdir()
    main = templates / "portrait-short-form.aep"
    preprocess = templates / "portrait-short-form-pre-process.aep"
    footage_dir = tmp_path / "clips"
    footage_dir.mkdir()
    clip = footage_dir / "clip-a.mov"
    main.write_bytes(b"aep")
    preprocess.write_bytes(b"aep")
    clip.write_bytes(b"clip")
    return ResolvedConfig(
        name=name,
        projects_dir=projects,
        project_dir=projects / name,
        raw_footage_dir=footage_dir,
        raw_footage=[clip],
        main_template=main,
        preprocess_template=preprocess,
        after_effects_exe=None,
        main_import_folder="01-footage",
        preprocess_import_folder="footage",
        force=False,
    )


def test_prepare_and_copy_footage(tmp_path: Path) -> None:
    config = _config(tmp_path)
    prepare_project_dir(config.project_dir, force=False)
    dest = disk_footage_dir(config.project_dir, config.main_import_folder)
    copied = copy_raw_footage(config.raw_footage, dest)

    assert dest.is_dir()
    assert copied == [dest / "clip-a.mov"]
    assert (dest / "clip-a.mov").read_bytes() == b"clip"
    assert (config.project_dir / ".bootstrap").is_dir()


def test_force_replaces_existing_project_dir(tmp_path: Path) -> None:
    config = _config(tmp_path)
    leftover = config.project_dir / "old.txt"
    leftover.parent.mkdir(parents=True)
    leftover.write_text("stale", encoding="utf-8")

    prepare_project_dir(config.project_dir, force=True)

    assert not leftover.exists()
    assert config.project_dir.is_dir()


def test_duplicate_filenames_rejected(tmp_path: Path) -> None:
    dest = tmp_path / "out"
    dest.mkdir()
    first = tmp_path / "a" / "same.mp4"
    second = tmp_path / "b" / "same.mp4"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_bytes(b"1")
    second.write_bytes(b"2")

    with pytest.raises(ConfigError, match="Duplicate raw footage filename"):
        copy_raw_footage([first, second], dest)


def test_job_json_shape(tmp_path: Path) -> None:
    config = _config(tmp_path)
    prepare_project_dir(config.project_dir, force=False)
    dest = disk_footage_dir(config.project_dir, config.main_import_folder)
    copied = copy_raw_footage(config.raw_footage, dest)
    payload = build_job_payload(config, copied)
    written = write_job_json(job_path(config.project_dir), payload)

    assert written == config.project_dir / ".bootstrap" / "job.json"
    assert payload["project_root"] == as_ae_path(config.project_dir)
    assert payload["main_template"] == as_ae_path(config.main_template)
    assert payload["preprocess_template"] == as_ae_path(config.preprocess_template)
    assert payload["main_save_as"] == as_ae_path(config.project_dir / "client-short-01.aep")
    assert payload["preprocess_save_as"] == as_ae_path(
        config.project_dir / "client-short-01-pre-process.aep"
    )
    assert payload["import_files"] == [as_ae_path(copied[0])]
    assert payload["main_import_folder"] == "01-footage"
    assert payload["preprocess_import_folder"] == "footage"
    assert payload["collect_existing"] is True
    assert payload["result_path"] == as_ae_path(result_path(config.project_dir))
    assert "/" in payload["project_root"]
    assert "\\" not in payload["project_root"]
