"""File responsibility: Unit tests for OpenVisualFeatureDiffAction orchestration and failure handling."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

from freecad.diff_wb.application.actions.open_visual_feature_diff import (
    OpenVisualFeatureDiffAction,
    OpenVisualFeatureDiffRequest,
)
from freecad.diff_wb.domain.git.git_service import GitService
from freecad.diff_wb.domain.git.models import GitRepository
from tests.fakes.fake_git_port import FakeGitPort


@dataclass
class FakeVisualDiff:
    old_path: str | None = None
    new_path: str | None = None

    def open_brep_visual_diff(self, old_brep_path: str | None, new_brep_path: str | None) -> object:
        self.old_path = old_brep_path
        self.new_path = new_brep_path
        return object()


def _write_fcstd(path: Path, object_name: str, include_shape: bool = True) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        if include_shape:
            archive.writestr(f"PartData/{object_name}.Shape.brp", "BREP")


def test_execute_opens_visual_diff_when_shape_present(tmp_path: Path) -> None:
    repo = GitRepository(name="repo", absolute_path="/repo")
    fake_port = FakeGitPort()
    service = GitService(git_port=fake_port)
    visual_diff = FakeVisualDiff()
    action = OpenVisualFeatureDiffAction(git_service=service, visual_diff=visual_diff)

    new_fcstd = tmp_path / "new.FCStd"
    old_fcstd = tmp_path / "old.FCStd"
    _write_fcstd(new_fcstd, "Pad")
    _write_fcstd(old_fcstd, "Pad")
    fake_port.set_file_bytes(None, "doc.FCStd", old_fcstd.read_bytes())

    result = action.execute(
        OpenVisualFeatureDiffRequest(
            repo=repo,
            git_path="doc.FCStd",
            node_path="Body/Pad",
            old_commit=None,
            new_commit=None,
            working_tree_document_path=str(new_fcstd),
        )
    )

    assert result.is_success is True
    assert visual_diff.old_path is not None and visual_diff.old_path.endswith("Pad.Shape.brp")
    assert visual_diff.new_path is not None and visual_diff.new_path.endswith("Pad.Shape.brp")


def test_execute_opens_visual_diff_when_new_brep_missing(tmp_path: Path) -> None:
    repo = GitRepository(name="repo", absolute_path="/repo")
    fake_port = FakeGitPort()
    service = GitService(git_port=fake_port)
    visual_diff = FakeVisualDiff()
    action = OpenVisualFeatureDiffAction(git_service=service, visual_diff=visual_diff)

    new_fcstd = tmp_path / "new.FCStd"
    old_fcstd = tmp_path / "old.FCStd"
    _write_fcstd(new_fcstd, "Pad", include_shape=False)
    _write_fcstd(old_fcstd, "Pad")
    fake_port.set_file_bytes(None, "doc.FCStd", old_fcstd.read_bytes())

    result = action.execute(
        OpenVisualFeatureDiffRequest(
            repo=repo,
            git_path="doc.FCStd",
            node_path="Body/Pad",
            old_commit=None,
            new_commit=None,
            working_tree_document_path=str(new_fcstd),
        )
    )

    assert result.is_success is True
    assert visual_diff.old_path is not None and visual_diff.old_path.endswith("Pad.Shape.brp")
    assert visual_diff.new_path is None


def test_execute_opens_visual_diff_when_old_brep_missing(tmp_path: Path) -> None:
    repo = GitRepository(name="repo", absolute_path="/repo")
    fake_port = FakeGitPort()
    service = GitService(git_port=fake_port)
    visual_diff = FakeVisualDiff()
    action = OpenVisualFeatureDiffAction(git_service=service, visual_diff=visual_diff)

    new_fcstd = tmp_path / "new.FCStd"
    old_fcstd = tmp_path / "old.FCStd"
    _write_fcstd(new_fcstd, "Pad")
    _write_fcstd(old_fcstd, "Pad", include_shape=False)
    fake_port.set_file_bytes(None, "doc.FCStd", old_fcstd.read_bytes())

    result = action.execute(
        OpenVisualFeatureDiffRequest(
            repo=repo,
            git_path="doc.FCStd",
            node_path="Body/Pad",
            old_commit=None,
            new_commit=None,
            working_tree_document_path=str(new_fcstd),
        )
    )

    assert result.is_success is True
    assert visual_diff.old_path is None
    assert visual_diff.new_path is not None and visual_diff.new_path.endswith("Pad.Shape.brp")


def test_execute_fails_when_brep_missing_from_both_sides(tmp_path: Path) -> None:
    repo = GitRepository(name="repo", absolute_path="/repo")
    fake_port = FakeGitPort()
    service = GitService(git_port=fake_port)
    visual_diff = FakeVisualDiff()
    action = OpenVisualFeatureDiffAction(git_service=service, visual_diff=visual_diff)

    new_fcstd = tmp_path / "new.FCStd"
    old_fcstd = tmp_path / "old.FCStd"
    _write_fcstd(new_fcstd, "Pad", include_shape=False)
    _write_fcstd(old_fcstd, "Pad", include_shape=False)
    fake_port.set_file_bytes(None, "doc.FCStd", old_fcstd.read_bytes())

    result = action.execute(
        OpenVisualFeatureDiffRequest(
            repo=repo,
            git_path="doc.FCStd",
            node_path="Body/Pad",
            old_commit=None,
            new_commit=None,
            working_tree_document_path=str(new_fcstd),
        )
    )

    assert result.is_success is False


def test_execute_reads_old_and_new_from_git_refs(tmp_path: Path) -> None:
    repo = GitRepository(name="repo", absolute_path="/repo")
    fake_port = FakeGitPort()
    service = GitService(git_port=fake_port)
    visual_diff = FakeVisualDiff()
    action = OpenVisualFeatureDiffAction(git_service=service, visual_diff=visual_diff)

    old_fcstd = tmp_path / "old_commit.FCStd"
    new_fcstd = tmp_path / "new_commit.FCStd"
    _write_fcstd(old_fcstd, "Pad")
    _write_fcstd(new_fcstd, "Pad")
    fake_port.set_file_bytes("abc~1", "doc.FCStd", old_fcstd.read_bytes())
    fake_port.set_file_bytes("abc", "doc.FCStd", new_fcstd.read_bytes())

    result = action.execute(
        OpenVisualFeatureDiffRequest(
            repo=repo,
            git_path="doc.FCStd",
            node_path="Body/Pad",
            old_commit="abc~1",
            new_commit="abc",
            working_tree_document_path=None,
        )
    )

    assert result.is_success is True
