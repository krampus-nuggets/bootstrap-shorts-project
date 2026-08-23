from pathlib import Path

import pytest

from bootstrap_shorts.detect_ae import discover_afterfx, resolve_afterfx
from bootstrap_shorts.errors import AfterFXNotFoundError, ConfigError


def _fake_install(root: Path, folder_name: str) -> Path:
    exe = root / "Adobe" / folder_name / "Support Files" / "AfterFX.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"mz")
    return exe


def test_discovers_newest_release(tmp_path: Path) -> None:
    older = _fake_install(tmp_path, "Adobe After Effects 2024")
    newer = _fake_install(tmp_path, "Adobe After Effects 2025")
    _fake_install(tmp_path, "Adobe After Effects 2025 Beta")

    found = discover_afterfx([tmp_path])
    chosen = resolve_afterfx(search_roots=[tmp_path])

    assert older in found
    assert newer in found
    assert chosen == newer.resolve()


def test_explicit_path_wins(tmp_path: Path) -> None:
    _fake_install(tmp_path, "Adobe After Effects 2025")
    explicit = tmp_path / "custom" / "AfterFX.exe"
    explicit.parent.mkdir()
    explicit.write_bytes(b"mz")

    assert resolve_afterfx(explicit, search_roots=[tmp_path]) == explicit.resolve()


def test_explicit_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="after_effects_exe is not a file"):
        resolve_afterfx(tmp_path / "missing.exe", search_roots=[tmp_path])


def test_not_found(tmp_path: Path) -> None:
    with pytest.raises(AfterFXNotFoundError, match="Could not find AfterFX.exe"):
        resolve_afterfx(search_roots=[tmp_path])
