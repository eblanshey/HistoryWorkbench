# File responsibility: Diff result presenter for UI.
#
# Coordinates diff loading, action handling, and view updates.
# Delegates pure presentation mapping to focused presenter helper modules.
"""Diff result presenter for UI.

This module provides the DiffPresenter class that transforms domain-level
diff results into UI-friendly presentation models.
"""

from collections.abc import Callable
from pathlib import Path

from ...application.actions.diffs.create_document_diffs import CreateDocumentDiffsAction
from ...application.actions.diffs.open_visual_diff import OpenVisualDiffAction
from ...application.actions.documents.get_open_eligible_documents import GetOpenEligibleDocumentsAction
from ...application.actions.documents.open_document import OpenDocumentAction
from ...application.actions.git_history.get_committed_file_paths import GetCommittedFilePathsAction
from ...application.actions.git_history.get_staged_file_paths import GetStagedFilePathsAction
from ...application.actions.git_workflow.restore_documents import RestoreDocumentsAction
from ...application.actions.git_workflow.stage_documents import StageDocumentsAction
from ...application.actions.git_workflow.unstage_documents import UnstageDocumentsAction
from ...application.actions.result_models import (
    DocumentDiffResult,
)
from ...domain.settings import SettingsRepository
from ...utils import Log
from ..state import ApplicationState
from ..views.diff_panel.dialog_view import DialogView
from ..views.document_diff.panel import DocumentDiffTreeWidget
from ..views.document_diff.summary_state import (
    SummaryButtonState,
)
from ..views.history.models import HistorySelection
from ..views.property_diff.tree import PropertyDiffTreeWidget
from .document_diff.diff_loader import DocumentDiffLoader
from .document_diff.document_mapper import build_document_presentations
from .document_diff.restore_handler import DocumentDiffRestoreHandler
from .document_diff.result_store import DocumentDiffResultStore
from .document_diff.staging_handler import DocumentDiffStagingHandler, StagingDisplayState
from .document_diff.summary_state import (
    build_summary_button_state,
    count_summary_counts,
)
from .document_diff.visual_diff_handler import DocumentVisualDiffHandler
from .property_diff.property_mapper import transform_property_diffs


class DiffPresenter:
    """Transform DiffResult into presentation models and call view methods.

    This presenter transforms domain-level diff results into UI-friendly
    presentation models, then calls concrete view collaborators to trigger
    the actual UI rendering.

    Dependencies are injected for testability.
    """

    def __init__(
        self,
        document_view: DocumentDiffTreeWidget,
        property_view: PropertyDiffTreeWidget,
        dialog_view: DialogView,
        application_state: ApplicationState,
        get_eligible_docs_action: GetOpenEligibleDocumentsAction,
        create_document_diffs_action: CreateDocumentDiffsAction,
        stage_documents_action: StageDocumentsAction,
        unstage_documents_action: UnstageDocumentsAction,
        get_staged_file_paths_action: GetStagedFilePathsAction,
        get_committed_file_paths_action: GetCommittedFilePathsAction,
        open_visual_feature_diff_action: OpenVisualDiffAction,
        open_document_action: OpenDocumentAction,
        restore_documents_action: RestoreDocumentsAction,
        focus_history_window_callback: Callable[[], None],
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        """Initialize with required dependencies.

        Args:
            document_view: Document-diff view collaborator
            property_view: Property-diff view collaborator
            dialog_view: Modal dialog and message collaborator
            application_state: Application-scoped state holder containing git repository info
            get_eligible_docs_action: Action to get eligible open documents
            create_document_diffs_action: Action to orchestrate document diffs by mode
            stage_documents_action: Action to stage documents to git
            settings_repo: Settings repository for runtime precision (optional, uses default if None)
        """
        from ...domain.config import FLOAT_PRECISION as DEFAULT_FLOAT_PRECISION

        self._document_view = document_view
        self._property_view = property_view
        self._dialog_view = dialog_view
        self._application_state = application_state
        self._open_document = open_document_action
        self._settings_repo = settings_repo
        self._default_precision = DEFAULT_FLOAT_PRECISION
        self._result_store = DocumentDiffResultStore()
        self._diff_loader = DocumentDiffLoader(get_eligible_docs_action, create_document_diffs_action)
        self._staging_handler = DocumentDiffStagingHandler(
            self._result_store,
            stage_documents_action,
            unstage_documents_action,
        )
        self._restore_handler = DocumentDiffRestoreHandler(
            restore_documents_action,
            get_committed_file_paths_action,
            get_staged_file_paths_action,
            self._dialog_view.show_restore_file_confirmation_dialog,
            self._dialog_view.show_restore_scope_dialog,
            self._dialog_view.show_info_message,
            self._dialog_view.show_error_message,
        )
        self._visual_diff_handler = DocumentVisualDiffHandler(open_visual_feature_diff_action)
        self._current_history_selection: HistorySelection | None = None
        self._focus_history_window_callback = focus_history_window_callback

    def track_history_selection(self, selection: HistorySelection | None) -> None:
        """Track effective history selection state for non-click refresh paths."""
        self._current_history_selection = selection

    def open_document_for_comparison(self, git_path: str) -> None:
        """Open missing working-tree document in FreeCAD, then recompute Current Files Area diff."""
        repo = self._application_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            return
        document_path = str(Path(repo.absolute_path) / git_path)
        result = self._open_document.execute(document_path)
        if not result.is_success:
            if result.message:
                Log.warning(result.message)
            return
        self._on_working_tree_selected()
        self._focus_history_window_callback()

    def _get_precision(self) -> int:
        """Get the current float precision from settings or use default.

        Returns:
            The float precision value (decimal places) from settings,
            or the default if settings repo is not available.
        """
        if self._settings_repo is not None:
            try:
                settings = self._settings_repo.get_settings()
                return settings.float_precision
            except (AttributeError, RuntimeError):
                # If settings retrieval fails, fall back to default
                pass
        return self._default_precision

    def select_history_item(self, selection: HistorySelection) -> None:
        """Handle single item selection from history list.

        Args:
            selection: HistorySelection containing item_kind and optional commit_hash
        """
        self._current_history_selection = selection
        if selection.item_kind == "WORKING_TREE":
            self._on_working_tree_selected()
        elif selection.item_kind == "STAGING":
            self._on_staging_selected()
        elif selection.item_kind == "COMMIT":
            self._on_commit_selected(selection.commit_hash)

    def clear_doc_diff(self) -> None:
        """Clear document diff data and document/property diff panels."""
        self._result_store.clear()
        self._document_view.clear_doc_diffs()

        # Property panel belongs to selected document tree node and must clear with the tree.
        self._property_view.clear_property_diff()

    def _on_working_tree_selected(self) -> None:
        """Handle Working Tree item selection.

        For each candidate path:
        1. Include every eligible open document
        2. Include every dirty FCStd path from git, including deleted files
        3. Display status-only rows when no snapshot diff can be computed
        """
        repo = self._application_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            self.clear_doc_diff()
            return

        document_results = self._diff_loader.load_working_tree(repo)
        self._result_store.store_results(document_results)

        if document_results:
            self.present_diffs(document_results)
        else:
            Log.debug("No diff results to display")
            self.clear_doc_diff()

    def _on_staging_selected(self) -> None:
        """Handle Staging item selection.

        For each staged FCStd file:
        1. Get staged snapshot from index (commit=None)
        2. Get snapshot from HEAD
        3. Create diff between HEAD and index

        Displays resulting diffs. For paths where index snapshot is missing,
        creates flat warning items (no tree below).
        """
        repo = self._application_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            self.clear_doc_diff()
            return

        document_results = self._diff_loader.load_staging(repo)
        self._result_store.store_results(document_results)

        if document_results:
            self.present_diffs(document_results)
        else:
            Log.debug("No diff results to display for staging")
            self.clear_doc_diff()

    def _on_commit_selected(self, commit_hash: str | None) -> None:
        """Handle commit item selection.

        Requests document-level commit diffs via CreateDocumentDiffsAction,
        then stores results and presents them to the view.
        """
        if commit_hash is None:
            Log.warning("Commit selection received without commit hash")
            self.clear_doc_diff()
            return

        repo = self._application_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            self.clear_doc_diff()
            return

        document_results = self._diff_loader.load_commit(repo, commit_hash)
        self._result_store.store_results(document_results)

        if document_results:
            self.present_diffs(document_results)
        else:
            Log.debug(f"No FCStd files changed in commit {commit_hash}")
            self.clear_doc_diff()

    def stage_document(self, git_path: str) -> None:
        """Handle '+ Stage' button click for staging.

        For deleted documents, stages the deletion with no snapshots.
        For other documents, stages the new snapshot from the diff result.
        """
        repo = self._application_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            return

        self._apply_staging_display_state(self._staging_handler.stage_document(repo, git_path))

    def stage_all_documents(self) -> None:
        """Handle 'Stage All' button click.

        Collects snapshots for non-deleted stage-able documents and deleted paths
        for stage-able deleted documents, then stages everything in one call.
        """
        repo = self._application_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            return

        self._apply_staging_display_state(self._staging_handler.stage_all(repo))

    def remove_document_from_reviewed(self, git_path: str) -> None:
        """Unstage one reviewed document unit (FCStd + snapshot yaml)."""
        repo = self._application_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            return

        self._apply_staging_display_state(self._staging_handler.remove_document_from_reviewed(repo, git_path))

    def remove_all_from_reviewed(self) -> None:
        """Unstage all reviewed staged paths from index."""
        repo = self._application_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            return

        self._apply_staging_display_state(
            self._staging_handler.remove_all_from_reviewed(repo, self._current_history_selection)
        )

    def restore_document(self, git_path: str) -> None:
        """Restore one document from index or selected commit."""
        current = self._current_history_selection
        repo = self._application_state.git_repository

        if current is None or repo is None:
            return

        if current.item_kind not in ("WORKING_TREE", "STAGING", "COMMIT"):
            return

        restore_success = self._restore_handler.restore_document(repo, current, git_path)
        self._property_view.clear_property_diff()

        if restore_success:
            self._focus_history_window_callback()

        if (
            restore_success
            and self._current_history_selection is not None
            and self._current_history_selection.item_kind == "WORKING_TREE"
        ):
            self._on_working_tree_selected()

    def restore_all_documents(self) -> None:
        """Restore listed/all files for current staging/commit source."""
        current = self._current_history_selection
        if current is None:
            return
        self.restore_all_from_history(current)

    def restore_all_from_history(self, selection: HistorySelection) -> None:
        """Restore from history context selection without changing selected row."""
        repo = self._application_state.git_repository

        if repo is None:
            return

        if selection.item_kind not in ("STAGING", "COMMIT"):
            return

        restore_success = self._restore_handler.restore_all(repo, selection)

        self._property_view.clear_property_diff()

        if restore_success:
            self._focus_history_window_callback()

        if (
            restore_success
            and self._current_history_selection is not None
            and self._current_history_selection.item_kind == "WORKING_TREE"
        ):
            self._on_working_tree_selected()

    def present_diffs(
        self,
        document_results: list[DocumentDiffResult],
    ) -> None:
        """Transform multiple DiffResults into presentation models and display.

        Args:
            document_results: Action-level document diff results.
        """
        if not document_results:
            self.clear_doc_diff()
            return

        self._property_view.clear_property_diff()

        is_working_tree = (
            self._current_history_selection is not None and self._current_history_selection.item_kind == "WORKING_TREE"
        )

        presentations = build_document_presentations(document_results, is_working_tree)

        presentations.sort(key=lambda p: p.git_path)

        self._document_view.show_doc_diffs(presentations)
        state: SummaryButtonState = build_summary_button_state(self._current_history_selection, presentations)
        self._document_view.set_button_states(state)

        counts = count_summary_counts(document_results)
        self._document_view.set_summary_counts(counts)

    def open_visual_diff(self, git_path: str, node_path: str) -> None:
        """Open visual diff for one node in current history mode."""
        current_selection = self._current_history_selection
        if current_selection is None:
            return

        repo = self._application_state.git_repository
        if repo is None:
            Log.warning("No git repository detected")
            return

        self._visual_diff_handler.open_visual_diff(current_selection, repo, git_path, node_path)

    def select_node(self, git_path: str, node_path: str) -> None:
        """Handle tree node selection to display property diffs.

        Called by view when user clicks a node in the diff tree.
        Looks up the property diffs for that path and displays them.

        Args:
            git_path: The document path used by cached diff results
            node_path: The path of the selected node within that document
        """
        # Guard: No diff results stored
        if not self._result_store.has_diff_results():
            self._property_view.clear_property_diff()
            return

        # Stale tree selections can arrive after refresh; clear instead of raising.
        diff_result = self._result_store.get_diff_result(git_path)
        if diff_result is None:
            Log.debug(f"[PRESENTER] No DiffResult found for git_path: {git_path}")
            self._property_view.clear_property_diff()
            return

        # Find NodeDiff by path within this document's hierarchy
        node_diff = diff_result.hierarchy.find_by_path(node_path)

        # If not found, clear properties
        if node_diff is None:
            Log.debug(f"[PRESENTER] NodeDiff not found for path: {node_path} in document {git_path}")
            self._property_view.clear_property_diff()
            return

        # Transform property diffs to presentations
        properties = transform_property_diffs(node_diff, self._get_precision())
        Log.debug(f"[PRESENTER] Transformed to {len(properties)} PropertyPresentation")
        self._property_view.show_property_diff(properties)

    def _apply_staging_display_state(self, state: StagingDisplayState) -> None:
        """Apply handler-produced staging display updates to view and selection flows."""
        if state.clear_doc_diff:
            self.clear_doc_diff()

        if state.clear_property_diff:
            self._property_view.clear_property_diff()

        # Cached working-tree remainder can be re-presented without reloading actions.
        if state.remaining_document_results is not None:
            self.present_diffs(state.remaining_document_results)

        if state.refresh_mode == "working_tree":
            self._on_working_tree_selected()
        elif state.refresh_mode == "staging":
            self._on_staging_selected()
