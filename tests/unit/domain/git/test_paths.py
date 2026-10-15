# File responsibility: Unit tests for Git path normalization helpers.
"""Unit tests for Git path helpers."""

import ntpath
from pathlib import Path
from unittest.mock import patch

import pytest

from freecad.history_wb.domain.git.paths import git_path_name, is_fcstd_path, relative_git_path, to_git_path


def test_to_git_path_normalizes_windows_separators() -> None:
    """Test Windows separators become Git POSIX separators."""
    assert to_git_path("assemblies\\sub\\Widget.FCStd") == "assemblies/sub/Widget.FCStd"


def test_relative_git_path_normalizes_os_relative_path() -> None:
    """Test relative paths are normalized after OS relpath computation."""
    with patch(
        "freecad.history_wb.domain.git.paths.relpath",
        lambda path, root: "assemblies\\sub\\Widget.FCStd",
    ):
        assert relative_git_path("C:\\repo\\assemblies\\sub\\Widget.FCStd", "C:\\repo") == "assemblies/sub/Widget.FCStd"


@pytest.mark.parametrize("alias_document", [False, True])
def test_relative_git_path_resolves_directory_aliases(tmp_path: Path, alias_document: bool) -> None:
    """Keep repository-relative spelling when root or document uses a symlink."""
    root = tmp_path / "project"
    root.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    document_root, repository_root = (alias, root) if alias_document else (root, alias)

    assert relative_git_path(str(document_root / "Parts" / "Widget.FCStd"), str(repository_root)) == "Parts/Widget.FCStd"


def test_relative_git_path_resolves_mapped_drive_to_unc() -> None:
    """Use Windows relative-path semantics after resolving a mapped drive."""
    root = "//server/share/Tempo/test"
    document = "Z:/Tempo/test/Parts/Widget.FCStd"
    resolved = {
        root: r"\\server\share\Tempo\test",
        document: r"\\server\share\Tempo\test\Parts\Widget.FCStd",
    }
    with (
        patch("freecad.history_wb.domain.git.paths.realpath", side_effect=resolved.__getitem__),
        patch("freecad.history_wb.domain.git.paths.relpath", side_effect=ntpath.relpath),
    ):
        assert relative_git_path(document, root) == "Parts/Widget.FCStd"


def test_git_path_name_handles_windows_and_trailing_separator() -> None:
    """Test final name extraction works for Windows-style paths."""
    assert git_path_name("C:\\repo\\project\\") == "project"


@pytest.mark.parametrize("path", ["part.FCStd", "part.fcstd", "part.FCSTD"])
def test_is_fcstd_path_is_case_insensitive(path: str) -> None:
    """Test FCStd extension matching works across case-insensitive filesystems."""
    assert is_fcstd_path(path) is True
