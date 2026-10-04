# File responsibility: History panel facade, cross-column coordination, and native non-canvas view proxy.
"""History panel facade and FreeCAD native view callbacks."""

from ....domain.settings import SettingsRepository
from ....qt import QtCore, QtWidgets
from ...presenters.presentation_models import DiffTreePresentation
from ..document_diff.panel import DocumentDiffTreeWidget
from ..history.models import HistorySelection
from ..history.panel import HistoryPanelWidget
from ..property_diff.tree import PropertyDiffTreeWidget


__all__ = ["HistoryPanelView"]


class HistoryPanelView(QtWidgets.QWidget):
    """3-column diff panel and document-independent FreeCAD native view proxy.

    Provides a horizontal QSplitter with:
    - Left: HistoryPanelWidget for repository info and history list
    - Middle: DocumentDiffTreeWidget for document diffs and staging
    - Right: PropertyDiffTreeWidget for property diffs

    """

    history_selection_changed = QtCore.Signal(object)  # HistorySelection | None

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        QtWidgets.QWidget.__init__(self, parent)
        self._settings_repo = settings_repo
        self._current_selection: HistorySelection | None = None
        self._setup_ui()

    def widget(self) -> QtWidgets.QWidget:
        """Return the History widget for FreeCAD's native MDI view wrapper."""
        return self

    def onHasMsg(self, _message: str) -> bool:
        """Reject canvas capabilities, including panning and automatic overlay hover reveal."""
        return False

    def _setup_ui(self) -> None:
        """Initialize the 3-column layout with child widgets."""
        layout = QtWidgets.QVBoxLayout(self)

        # Create horizontal splitter
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)

        # Column 1: History panel widget
        self._history_panel = HistoryPanelWidget(self)
        self._history_panel.history_selection_changed.connect(self._on_history_panel_selection_changed)
        self._history_panel.history_selection_changed.connect(self.history_selection_changed.emit)

        # Column 2: Document diff tree widget
        self._document_diff_tree = DocumentDiffTreeWidget(self)

        # Column 3: Property diff tree widget
        self._property_diff_tree = PropertyDiffTreeWidget(self, settings_repo=self._settings_repo)

        # Add to splitter
        splitter.addWidget(self._history_panel)
        splitter.addWidget(self._document_diff_tree)
        splitter.addWidget(self._property_diff_tree)

        # Set initial sizes: narrower history, narrower document diff, wider property table
        splitter.setSizes([150, 150, 400])

        # Set minimum size for the panel
        self.setMinimumSize(450, 200)

        layout.addWidget(splitter)

    def _on_history_panel_selection_changed(self, selection: HistorySelection | None) -> None:
        """Handle history panel selection changes to update document widget state."""
        self._current_selection = selection
        self._document_diff_tree.set_current_history_selection(selection)

    @property
    def history_panel(self) -> HistoryPanelWidget:
        """Expose history child facade for presenter-event wiring."""
        return self._history_panel

    @property
    def document_diff_panel(self) -> DocumentDiffTreeWidget:
        """Expose document-diff child facade for presenter-event wiring."""
        return self._document_diff_tree

    @property
    def property_diff_panel(self) -> PropertyDiffTreeWidget:
        """Expose property-diff child widget for narrow collaborator injection."""
        return self._property_diff_tree

    def focus_window(self) -> None:
        """Bring the top-level history panel window to foreground."""
        window = self.window()
        window.show()
        window.raise_()
        window.activateWindow()
        window.setFocus()

    def show_doc_diffs(self, diffs: list[DiffTreePresentation]) -> None:
        """Display multiple diff trees in the tree widget.

        Delegates to DocumentDiffTreeWidget.

        Args:
            diffs: List of DiffTreePresentation objects, each representing
                  a diff tree for one document with its metadata.
        """
        self._document_diff_tree.set_current_history_selection(self._current_selection)
        self._document_diff_tree.show_doc_diffs(diffs)

    def clear_doc_diffs(self) -> None:
        """Clear document diff tree and related controls.

        Also clears property diff panel to avoid stale node/property pairing.
        """
        self._document_diff_tree.clear_doc_diffs()
        self._property_diff_tree.clear_property_diff()
