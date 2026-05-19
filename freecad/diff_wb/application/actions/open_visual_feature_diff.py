# File responsibility: Open visual old/new BREP comparison from FCStd snapshots in git/index.

"""Open visual old/new BREP comparison from FCStd snapshots in git/index."""

from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from ...ui.translation_strings import (
    VISUAL_DIFF_IMPORT_FAILURE_MESSAGE,
    VISUAL_DIFF_MISSING_BREP_MESSAGE,
    VISUAL_DIFF_MISSING_FCSTD_MESSAGE,
)
from ...utils import Log
from .result_models import Result


@dataclass(frozen=True)
class OpenVisualFeatureDiffRequest:
    """Request payload for opening one visual feature diff.

    Supported side combinations:
    - Working Tree: old from index (old_commit=None), new from disk
      (working_tree_document_path set, new_commit ignored).
    - Staging: old from HEAD, new from index (new_commit=None,
      working_tree_document_path None).
    - Commit: old from commit parent (<commit>~1), new from commit
      (both old_commit/new_commit set, working_tree_document_path None).
    """

    repo: GitRepository
    git_path: str
    node_path: str
    old_commit: str | None
    new_commit: str | None
    working_tree_document_path: str | None = None
    property_name: str = "Shape"


class FreeCADVisualDiffPort(Protocol):
    """Protocol-like runtime dependency for visual BREP import."""

    def open_brep_visual_diff(self, old_brep_path: str | None, new_brep_path: str | None) -> object: ...


class OpenVisualFeatureDiffAction:
    """Create temp workspace, extract BREP files, open visual comparison."""

    def __init__(self, git_service: GitService, visual_diff: FreeCADVisualDiffPort) -> None:
        self._git_service = git_service
        self._visual_diff = visual_diff

    def execute(self, request: OpenVisualFeatureDiffRequest) -> Result:
        """Open a visual diff for one feature shape from requested repository state."""
        object_name = request.node_path.rsplit("/", 1)[-1]
        workspace = Path(tempfile.mkdtemp(prefix="diffcad_visual_"))
        old_fcstd = workspace / "old" / "Old.FCStd"
        new_fcstd = workspace / "new" / "New.FCStd"
        old_extract = workspace / "old_extracted"
        new_extract = workspace / "new_extracted"

        old_fcstd.parent.mkdir(parents=True, exist_ok=True)
        new_fcstd.parent.mkdir(parents=True, exist_ok=True)

        if not self._materialize_old_side(request, old_fcstd):
            return Result.failure(VISUAL_DIFF_MISSING_FCSTD_MESSAGE)
        if not self._materialize_new_side(request, new_fcstd):
            return Result.failure(VISUAL_DIFF_MISSING_FCSTD_MESSAGE)

        try:
            self._extract_fcstd_safely(old_fcstd, old_extract)
            self._extract_fcstd_safely(new_fcstd, new_extract)
        except (OSError, zipfile.BadZipFile, ValueError) as err:
            Log.warning(f"Failed to extract FCStd for visual diff: {err}")
            return Result.failure(VISUAL_DIFF_IMPORT_FAILURE_MESSAGE)

        brep_name = f"{object_name}.{request.property_name}.brp"
        old_brep = self._find_file_by_name(old_extract, brep_name)
        new_brep = self._find_file_by_name(new_extract, brep_name)
        if old_brep is None and new_brep is None:
            return Result.failure(VISUAL_DIFF_MISSING_BREP_MESSAGE)

        try:
            self._visual_diff.open_brep_visual_diff(
                str(old_brep) if old_brep is not None else None,
                str(new_brep) if new_brep is not None else None,
            )
        except Exception as err:  # noqa: BLE001
            Log.warning(f"Failed to open visual diff document: {err}")
            return Result.failure(VISUAL_DIFF_IMPORT_FAILURE_MESSAGE)

        return Result.success(True)

    def _materialize_old_side(self, request: OpenVisualFeatureDiffRequest, destination: Path) -> bool:
        """Write old-side FCStd from git ref/index."""
        return self._git_service.write_file_from_ref(
            request.repo,
            request.old_commit,
            request.git_path,
            str(destination),
        )

    def _materialize_new_side(self, request: OpenVisualFeatureDiffRequest, destination: Path) -> bool:
        """Write new-side FCStd from working tree file or git ref/index."""
        if request.working_tree_document_path:
            try:
                shutil.copy2(request.working_tree_document_path, destination)
            except OSError as err:
                Log.warning(f"Failed to copy new FCStd: {err}")
                return False
            return True
        return self._git_service.write_file_from_ref(
            request.repo,
            request.new_commit,
            request.git_path,
            str(destination),
        )

    def _extract_fcstd_safely(self, archive_path: Path, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path, "r") as archive:
            for member in archive.infolist():
                self._validate_member_path(destination, member.filename)
            archive.extractall(destination)

    def _validate_member_path(self, destination: Path, member_name: str) -> None:
        # Zip entries can contain ../ segments or absolute paths.
        # Resolve final target and enforce it stays inside extraction root.
        # This blocks zip-slip writes outside destination.
        target = destination / member_name
        destination_resolved = destination.resolve()
        target_resolved = target.resolve()
        if os.path.commonpath([str(destination_resolved), str(target_resolved)]) != str(destination_resolved):
            raise ValueError(f"Unsafe archive path: {member_name}")

    def _find_file_by_name(self, root: Path, target_name: str) -> Path | None:
        for path in root.rglob(target_name):
            if path.name == target_name:
                return path
        return None
