from pathlib import Path

import pytest

from bootstrap_shorts.errors import SelectionAborted
from bootstrap_shorts.select_footage import (
    format_listing,
    format_size,
    parse_selection,
    select_raw_footage,
)


def test_format_size() -> None:
    assert format_size(512) == "512 B"
    assert format_size(2048) == "2.0 KB"
    assert format_size(1024 * 1024) == "1.0 MB"


def test_parse_selection_all_aliases() -> None:
    assert parse_selection("", 3) == [0, 1, 2]
    assert parse_selection("all", 3) == [0, 1, 2]
    assert parse_selection("A", 3) == [0, 1, 2]
    assert parse_selection("*", 3) == [0, 1, 2]


def test_parse_selection_numbers_and_ranges() -> None:
    assert parse_selection("1,3", 4) == [0, 2]
    assert parse_selection("1-3", 4) == [0, 1, 2]
    assert parse_selection("2-3,1", 4) == [0, 1, 2]
    assert parse_selection("1 4", 4) == [0, 3]


def test_parse_selection_invalid() -> None:
    with pytest.raises(ValueError, match="out of bounds"):
        parse_selection("5", 3)
    with pytest.raises(ValueError, match="Range out of bounds"):
        parse_selection("3-1", 3)
    with pytest.raises(ValueError, match="Invalid selection"):
        parse_selection("foo", 3)


def test_parse_selection_cancel() -> None:
    with pytest.raises(SelectionAborted):
        parse_selection("q", 3)


def test_format_listing(tmp_path: Path) -> None:
    first = tmp_path / "a.mov"
    second = tmp_path / "b.mov"
    first.write_bytes(b"x" * 10)
    second.write_bytes(b"y" * 20)
    lines = format_listing([first, second])
    assert "1. a.mov" in lines[0]
    assert "2. b.mov" in lines[1]


def test_select_raw_footage_assume_yes(tmp_path: Path) -> None:
    files = [tmp_path / "a.mov", tmp_path / "b.mov"]
    for path in files:
        path.write_bytes(b"mov")

    selected = select_raw_footage(files, directory=tmp_path, assume_yes=True)
    assert selected == files


def test_select_raw_footage_prompt_and_confirm(tmp_path: Path) -> None:
    files = [tmp_path / "a.mov", tmp_path / "b.mov", tmp_path / "c.mov"]
    for path in files:
        path.write_bytes(b"mov")
    echoes: list[str] = []

    selected = select_raw_footage(
        files,
        directory=tmp_path,
        echo=echoes.append,
        prompt=lambda *_args, **_kwargs: "1,3",
        confirm=lambda *_args, **_kwargs: True,
    )

    assert selected == [files[0], files[2]]
    assert any("Discovered 3 .mov file(s)" in line for line in echoes)
    assert any("a.mov" in line for line in echoes)
    assert any("Selected 2 file(s)" in line for line in echoes)


def test_select_raw_footage_retry_on_invalid_then_confirm(tmp_path: Path) -> None:
    files = [tmp_path / "a.mov", tmp_path / "b.mov"]
    for path in files:
        path.write_bytes(b"mov")
    answers = iter(["nope", "2"])

    selected = select_raw_footage(
        files,
        directory=tmp_path,
        echo=lambda _line: None,
        prompt=lambda *_args, **_kwargs: next(answers),
        confirm=lambda *_args, **_kwargs: True,
    )

    assert selected == [files[1]]


def test_select_raw_footage_reprompt_when_not_confirmed(tmp_path: Path) -> None:
    files = [tmp_path / "a.mov", tmp_path / "b.mov"]
    for path in files:
        path.write_bytes(b"mov")
    answers = iter(["1", "all"])
    confirms = iter([False, True])

    selected = select_raw_footage(
        files,
        directory=tmp_path,
        echo=lambda _line: None,
        prompt=lambda *_args, **_kwargs: next(answers),
        confirm=lambda *_args, **_kwargs: next(confirms),
    )

    assert selected == files
