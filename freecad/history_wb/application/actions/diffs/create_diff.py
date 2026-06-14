"""File responsibility: Application action for computing diff between snapshots."""

from ....domain.diff.engine import DiffEngine
from ....domain.snapshots.models import Snapshot
from ....utils import Log
from ..result_models import Result


__all__ = ["CreateDiffAction"]


class CreateDiffAction:
    """Compute diff between two snapshots using DiffEngine."""

    def __init__(self, diff_engine: DiffEngine) -> None:
        self._diff_engine = diff_engine

    def execute(self, old_snapshot: Snapshot | None, new_snapshot: Snapshot) -> Result:
        """Compute diff between two snapshots.

        Args:
            old_snapshot: The older snapshot to compare from (can be None for working tree).
            new_snapshot: The newer snapshot to compare to.

        Returns:
            Result containing DiffResult on success, or failure message on error.
        """
        try:
            diff_result = self._diff_engine.compute_diff(old_snapshot, new_snapshot)
            return Result.success(diff_result)
        except (RuntimeError, ValueError, TypeError, AttributeError, LookupError) as e:
            Log.exception(f"Failed to compute diff for '{new_snapshot.document_name}': {e}")
            return Result.failure(f"Failed to compute diff for '{new_snapshot.document_name}': {e}")
