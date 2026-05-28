# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Restore FreeCAD documents from commit/index into
# working tree and recover FreeCAD open-document state.
"""Application action for destructive document restore from history sources."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum

from ...domain.freecad_ports import FreeCadPort
from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from .result_models import Result


class RestoreSource(Enum):
    """Source used for restore."""

    COMMIT = "commit"
    INDEX = "index"


class RestoreScope(Enum):
    """Scope used for restore."""

    SINGLE_PATH = "single_path"
    LISTED_FCSTD = "listed_fcstd"
    ALL_FCSTD = "all_fcstd"


@dataclass(frozen=True)
class RestoreDocumentsRequest:
    """Restore request payload."""

    repo: GitRepository
    source: RestoreSource
    scope: RestoreScope
    commit_hash: str | None = None
    paths: list[str] | None = None


@dataclass(frozen=True)
class RestoreDocumentsSummary:
    """Restore outcome metadata."""

    restored_paths: list[str]
    reopened_count: int


@dataclass(frozen=True)
class _OpenDocState:
    name: str
    file_name: str
    is_active: bool


class RestoreDocumentsAction:
    """Restore FreeCAD files from commit/index and reopen project documents."""

    def __init__(self, git_service: GitService, freecad_port: FreeCadPort) -> None:
        self._git_service = git_service
        self._freecad_port = freecad_port

    def execute(self, request: RestoreDocumentsRequest) -> Result:
        """Execute destructive restore and recover open-document state."""
        validation_error = self._validate_request(request)
        if validation_error is not None:
            return Result.failure(validation_error)

        commit_or_none = request.commit_hash if request.source == RestoreSource.COMMIT else None
        restore_paths = self._resolve_paths(request, commit_or_none)
        if not restore_paths:
            return Result.failure("No files available to restore from selected source")

        filter_error, filtered_paths = self._filter_existing_source_paths(
            request,
            commit_or_none,
            restore_paths,
        )
        if filter_error is not None:
            return Result.failure(filter_error)
        restore_paths = filtered_paths

        open_project_docs = self._collect_open_project_docs(request.repo)

        restore_success = False
        try:
            for state in open_project_docs:
                self._freecad_port.close_document(state.name)
            restore_success = self._git_service.restore_paths_from_ref(request.repo, commit_or_none, restore_paths)
        finally:
            reopened = self._reopen_documents(open_project_docs)

        if not restore_success:
            return Result.failure("Failed to restore selected files")

        return Result.success(RestoreDocumentsSummary(restored_paths=restore_paths, reopened_count=reopened))

    def _resolve_paths(self, request: RestoreDocumentsRequest, commit_or_none: str | None) -> list[str]:
        """Resolve concrete restore path set for selected restore scope.

        For single/listed scope, returns provided path list.
        For all-FCStd scope, returns union of source FCStd paths and
        current saved FCStd paths so source-missing historical files can
        be removed by git restore.
        """
        if request.scope in (RestoreScope.SINGLE_PATH, RestoreScope.LISTED_FCSTD):
            return list(request.paths or [])

        source_paths = set(self._git_service.get_all_fcstd_paths(request.repo, commit_or_none))
        current_saved = set(self._git_service.get_current_saved_fcstd_paths(request.repo))
        return sorted(source_paths | current_saved)

    def _validate_request(self, request: RestoreDocumentsRequest) -> str | None:
        """Validate required source/scope fields before restore."""
        if request.source == RestoreSource.COMMIT and not request.commit_hash:
            return "Missing commit hash for commit restore"
        if request.scope in (RestoreScope.SINGLE_PATH, RestoreScope.LISTED_FCSTD) and not request.paths:
            return "No files selected for restore"
        return None

    def _filter_existing_source_paths(
        self,
        request: RestoreDocumentsRequest,
        commit_or_none: str | None,
        restore_paths: list[str],
    ) -> tuple[str | None, list[str]]:
        """Filter restore paths to files that exist in selected source.

        Applied only to single/listed scopes to avoid unintended deletions when
        selected row represents source-side deletion.
        """
        if request.scope not in (RestoreScope.SINGLE_PATH, RestoreScope.LISTED_FCSTD):
            return None, restore_paths
        existing_source_paths = [
            path for path in restore_paths if self._git_service.file_exists(request.repo, commit_or_none, path)
        ]
        if not existing_source_paths:
            return "Selected file is not available in source", []
        return None, existing_source_paths

    def _collect_open_project_docs(self, repo: GitRepository) -> list[_OpenDocState]:
        """Capture open project document state for close/reopen cycle."""
        active = self._freecad_port.get_active_document()
        active_name = getattr(active, "Name", "") if active is not None else ""
        docs = self._freecad_port.get_all_open_documents()
        eligible = self._git_service.get_eligible_docs(repo, docs)
        return [
            _OpenDocState(
                name=getattr(doc, "Name", ""),
                file_name=getattr(doc, "FileName", ""),
                is_active=getattr(doc, "Name", "") == active_name,
            )
            for doc in eligible
            if getattr(doc, "Name", "") and getattr(doc, "FileName", "")
        ]

    def _reopen_documents(self, docs: list[_OpenDocState]) -> int:
        """Best-effort reopen of previously open documents still present on disk."""
        reopened = 0
        active_name: str | None = None
        for doc in docs:
            if not os.path.exists(doc.file_name):
                continue
            self._freecad_port.open_document(doc.file_name)
            reopened += 1
            if doc.is_active:
                active_name = doc.name
        if active_name:
            self._freecad_port.set_active_document(active_name)
        return reopened
