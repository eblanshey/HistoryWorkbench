# File responsibility: Application action for checking whether the git
# executable can be located from the configured preference or the system PATH.
"""Application action for git executable availability checks."""

from __future__ import annotations

from ....domain.git.git_service import GitService
from ..result_models import Result


class CheckGitAvailabilityAction:
    """Check whether the git executable is available to the workbench."""

    def __init__(self, git_service: GitService) -> None:
        """Initialize with the git service dependency."""
        self._git_service = git_service

    def execute(self) -> Result:
        """Return success with True when git can be located, success with False otherwise."""
        return Result.success(self._git_service.is_git_executable_available())


__all__ = ["CheckGitAvailabilityAction"]
