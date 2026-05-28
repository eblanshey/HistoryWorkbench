# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for GitPortAdapter restore/query methods.
"""Unit tests for git restore and FCStd path queries."""

import subprocess
from unittest.mock import patch

import pytest

from freecad.history_wb.infrastructure.git import GitPortAdapter


class TestGitPortAdapterRestoreMethods:
    """Tests for restore and FCStd path query methods."""

    def setup_method(self) -> None:
        self.adapter = GitPortAdapter()
        self.adapter._git_executable = "git"

    def test_restore_paths_from_commit_uses_restore_source(self) -> None:
        result_ok = subprocess.CompletedProcess(args=["git"], returncode=0, stdout="", stderr="")

        with patch.object(self.adapter, "_run_git", return_value=result_ok) as run_git:
            result = self.adapter.restore_paths_from_ref("/repo", "abc123", ["a.FCStd"])

        assert result is True
        run_git.assert_called_once_with(
            ["restore", "--worktree", "--source=abc123", "--", "a.FCStd"],
            cwd="/repo",
            timeout=30,
        )

    def test_restore_paths_from_index_uses_restore_without_source(self) -> None:
        result_ok = subprocess.CompletedProcess(args=["git"], returncode=0, stdout="", stderr="")

        with patch.object(self.adapter, "_run_git", return_value=result_ok) as run_git:
            result = self.adapter.restore_paths_from_ref("/repo", None, ["a.FCStd", "b.FCStd"])

        assert result is True
        run_git.assert_called_once_with(
            ["restore", "--worktree", "--", "a.FCStd", "b.FCStd"],
            cwd="/repo",
            timeout=30,
        )

    def test_restore_paths_empty_list_succeeds_without_git_call(self) -> None:
        with patch.object(self.adapter, "_run_git") as run_git:
            result = self.adapter.restore_paths_from_ref("/repo", None, [])

        assert result is True
        run_git.assert_not_called()

    @pytest.mark.parametrize("commit", ["abc123", None])
    def test_get_all_fcstd_paths_uses_expected_git_command(self, commit: str | None) -> None:
        stdout = "a.FCStd\x00a.txt\x00nested/b.FCStd\x00"
        result_ok = subprocess.CompletedProcess(args=["git"], returncode=0, stdout=stdout, stderr="")
        expected_args = ["ls-files", "-z"] if commit is None else ["ls-tree", "-r", "-z", "--name-only", commit]

        with patch.object(self.adapter, "_run_git", return_value=result_ok) as run_git:
            result = self.adapter.get_all_fcstd_paths("/repo", commit)

        assert result == ["a.FCStd", "nested/b.FCStd"]
        run_git.assert_called_once_with(expected_args, cwd="/repo", timeout=30)

    @pytest.mark.parametrize(
        ("method_name", "expected"),
        [
            ("restore_paths_from_ref", False),
            ("get_all_fcstd_paths", []),
        ],
    )
    def test_restore_methods_handle_timeout(self, method_name: str, expected: object) -> None:
        with patch.object(self.adapter, "_run_git", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=30)):
            if method_name == "restore_paths_from_ref":
                result = self.adapter.restore_paths_from_ref("/repo", None, ["a.FCStd"])
            else:
                result = self.adapter.get_all_fcstd_paths("/repo", None)

        assert result == expected
