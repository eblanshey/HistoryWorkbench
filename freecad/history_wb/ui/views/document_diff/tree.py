"""File responsibility: Document diff tree container with click routing, collapse actions, and node-row wiring."""

from __future__ import annotations

from collections.abc import Callable

from ....domain.diff.models import DiffState
from ....qt import QtCore, QtWidgets
from ....utils import translate
from ...presenters.presentation_models import DiffTreePresentation, NodePresentation
from ..theme.diff import DiffItemDelegate, apply_diff_state_to_widget
from ..widgets.buttons import make_icon_tool_button
from ..widgets.styles import DIFF_ROW_CONTAINER_OBJECT_NAME, DIFF_ROW_LABEL_OBJECT_NAME, TREE_ITEM_HEIGHT
from .node_row import NodeDiffRowWidget
from .tree_items import build_document_root_item, build_node_item


__all__ = ["DocumentDiffTree"]


class DocumentDiffTree(QtWidgets.QWidget):
    """Render document diff trees and emit node-level user actions."""

    node_selected = QtCore.Signal(str, str)  # git_path, node_path
    visual_diff_requested = QtCore.Signal(str, str)  # git_path, node_path

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def clear(self) -> None:
        """Clear all rendered document and node items."""
        self._tree_widget.clear()

    def show_doc_diffs(
        self,
        diffs: list[DiffTreePresentation],
        create_document_row_widget: Callable[[DiffTreePresentation, str], QtWidgets.QWidget],
    ) -> None:
        """Render multiple document trees and install custom document-row widgets."""
        self.clear()

        # Empty document lists mean caller wants cleared middle column only.
        if not diffs:
            return

        for diff in diffs:
            display_text = diff.git_path or translate("History", "Unnamed Document")
            root_item = build_document_root_item(
                display_text,
                diff.git_path,
                self._tree_widget.palette(),
                document_state=diff.document_state,
            )
            document_row = create_document_row_widget(diff, display_text)
            self._apply_diff_state_to_widget(document_row, diff.document_state)

            self._tree_widget.addTopLevelItem(root_item)
            self._tree_widget.setItemWidget(root_item, 0, document_row)

            for node in diff.nodes:
                self._add_node_subtree(root_item, node, diff.git_path)

            self._expand_nodes_with_changes(root_item)

        self._tree_widget.show()

    def collapse_all_tree_items(self) -> None:
        """Collapse every root and descendant item in tree widget."""
        self._tree_widget.collapseAll()

    def collapse_tree_item(self, git_path: str) -> None:
        """Collapse one root tree item identified by stored git path."""
        for index in range(self._tree_widget.topLevelItemCount()):
            item = self._tree_widget.topLevelItem(index)
            item_git_path = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if item_git_path == git_path:
                item.setExpanded(False)
                return

    def _setup_ui(self) -> None:
        tree_header = QtWidgets.QWidget(self)
        tree_header_layout = QtWidgets.QHBoxLayout(tree_header)
        tree_header_layout.setContentsMargins(4, 2, 4, 2)
        tree_header_layout.setSpacing(4)
        tree_header_layout.addWidget(QtWidgets.QLabel(translate("History", "Tree")))
        tree_header_layout.addStretch()

        collapse_all_button = make_icon_tool_button(
            icon_name="Collapse.svg",
            tooltip=translate("History", "Collapse All"),
            accessible_name=translate("History", "Collapse All"),
            size=TREE_ITEM_HEIGHT,
        )
        collapse_all_button.clicked.connect(self.collapse_all_tree_items)
        tree_header_layout.addWidget(collapse_all_button)

        self._tree_widget = QtWidgets.QTreeWidget(self)
        self._tree_widget.setObjectName("documentDiffTree")
        self._tree_widget.header().hide()
        self._tree_widget.setColumnCount(1)
        self._tree_widget.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._tree_widget.setItemDelegate(DiffItemDelegate(self._tree_widget))
        self._tree_widget.itemClicked.connect(self._on_tree_item_clicked)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(tree_header)
        layout.addWidget(self._tree_widget)

    def _add_node_subtree(self, parent_item: QtWidgets.QTreeWidgetItem, node: NodePresentation, git_path: str) -> None:
        """Build one node subtree, attach it, then install optional visual-diff row widgets."""
        item = build_node_item(node, self._tree_widget.palette())
        parent_item.addChild(item)
        self._install_node_row_widgets(item, node, git_path)

    def _install_node_row_widgets(
        self,
        item: QtWidgets.QTreeWidgetItem,
        node: NodePresentation,
        git_path: str,
    ) -> None:
        """Install node-row widget for visual-diff nodes, then recurse through children."""
        if node.visual_diff_enabled:
            text = item.text(0)
            row_widget = NodeDiffRowWidget(text, node.type_id, git_path, node.path, self._tree_widget)

            # Row widget owns visible text; retaining item text lets delegate paint a duplicate label behind it.
            item.setText(0, "")

            row_widget.visual_diff_requested.connect(
                lambda emitted_git_path, emitted_node_path, item=item: self._on_node_visual_diff_requested(
                    item,
                    emitted_git_path,
                    emitted_node_path,
                )
            )
            self._apply_diff_state_to_widget(row_widget, node.state)
            self._tree_widget.setItemWidget(item, 0, row_widget)

        for index, child_node in enumerate(node.children):
            child_item = item.child(index)

            # Tree-item builder and presentation model recursion must stay aligned.
            if child_item is None:
                raise RuntimeError("Node child item missing during document diff tree wiring")

            self._install_node_row_widgets(child_item, child_node, git_path)

    def _expand_nodes_with_changes(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Expand ancestor branches that lead to changed descendants."""
        has_changed_descendants = False

        for index in range(item.childCount()):
            child = item.child(index)
            if child.data(0, QtCore.Qt.ItemDataRole.UserRole + 1):
                has_changed_descendants = True
            self._expand_nodes_with_changes(child)

        # Expand only branches that lead to changed content below current row.
        if has_changed_descendants:
            item.setExpanded(True)

    def _on_tree_item_clicked(self, item: QtWidgets.QTreeWidgetItem, column: int) -> None:
        """Emit selected node coordinates for property-diff routing."""
        del column
        self._emit_node_selected(item)

    def _emit_node_selected(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Compute git path and node path from clicked item and emit when item is a node."""

        # Top-level document rows carry git_path in UserRole for lookup, not node-path semantics.
        if item.parent() is None:
            return

        node_path = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        root = item

        while root.parent() is not None:
            root = root.parent()

        git_path = root.data(0, QtCore.Qt.ItemDataRole.UserRole)

        # Child rows represent actual document nodes and can drive property selection routing.
        if git_path and node_path:
            self.node_selected.emit(git_path, node_path)

    def _on_node_visual_diff_requested(self, item: QtWidgets.QTreeWidgetItem, git_path: str, node_path: str) -> None:
        """Select node row, emit normal selection, then emit visual-diff request."""
        self._tree_widget.setCurrentItem(item)
        self._emit_node_selected(item)
        self.visual_diff_requested.emit(git_path, node_path)

    def _apply_diff_state_to_widget(self, widget: QtWidgets.QWidget, state: DiffState) -> None:
        """Apply diff-state colors to document and visual-diff row widgets."""
        apply_diff_state_to_widget(
            widget,
            state,
            self._tree_widget.palette(),
            container_object_name=DIFF_ROW_CONTAINER_OBJECT_NAME,
            label_object_name=DIFF_ROW_LABEL_OBJECT_NAME,
        )
