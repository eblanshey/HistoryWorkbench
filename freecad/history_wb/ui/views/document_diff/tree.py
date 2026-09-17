"""File responsibility: Document diff tree rendering, interaction routing, and node-row wiring."""

from __future__ import annotations

from collections.abc import Callable

from ....domain.diff.models import DiffState
from ....qt import QtCore, QtGui, QtWidgets
from ....resources import get_icon_path
from ....utils import translate
from ...presenters.presentation_models import DiffTreePresentation, NodePresentation
from ..theme.diff import colors_for_diff_state, palette_with_resolved_text
from ..widgets.buttons import make_icon_tool_button, make_tool_button
from ..widgets.styles import (
    DIFF_ROW_CONTAINER_OBJECT_NAME,
    DIFF_ROW_LABEL_OBJECT_NAME,
    TREE_ITEM_HEIGHT,
    TREE_ITEM_ICON_SIZE,
    VISUAL_DIFF_ICON_BUTTON_STYLE,
)
from .diff_row import DiffTreeRowWidget
from .tree_items import build_document_root_item, build_node_item


__all__ = ["DocumentDiffTree"]


class DocumentDiffTree(QtWidgets.QWidget):
    """Render document diff trees and emit node-level user actions."""

    node_selected = QtCore.Signal(str, str)  # git_path, node_path
    visual_diff_requested = QtCore.Signal(str, str)  # git_path, node_path

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._refreshing_style = False
        self._setup_ui()

    def clear(self) -> None:
        """Clear all rendered document and node items."""
        self._tree_widget.clear()

    def show_doc_diffs(
        self,
        diffs: list[DiffTreePresentation],
        create_document_row_widget: Callable[[DiffTreePresentation, str], DiffTreeRowWidget],
    ) -> None:
        """Render multiple document trees and install custom document-row widgets."""
        updates_enabled = self._tree_widget.updatesEnabled()

        # Defer repaints while installing many items and row widgets to avoid repeated layout and style work.
        self._tree_widget.setUpdatesEnabled(False)
        try:
            self.clear()

            # Empty document lists mean caller wants cleared middle column only.
            if not diffs:
                return

            for diff in diffs:
                display_text = diff.git_path or translate("History", "Unnamed Document")
                root_item = build_document_root_item(
                    display_text,
                    diff.git_path,
                )
                document_row = create_document_row_widget(diff, display_text)

                self._tree_widget.addTopLevelItem(root_item)
                document_row.set_diff_state(diff.document_state)
                root_item.setText(0, "")
                self._tree_widget.setItemWidget(root_item, 0, document_row)

                for node in diff.nodes:
                    self._add_node_subtree(root_item, node, diff.git_path)

                self._expand_nodes_with_changes(root_item)
        finally:
            self._tree_widget.setUpdatesEnabled(updates_enabled)

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
        self._theme_probe = QtWidgets.QLabel(self._tree_widget)
        self._theme_probe.hide()
        self._tree_widget.header().hide()
        self._tree_widget.setColumnCount(1)
        self._tree_widget.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._tree_widget.itemClicked.connect(self._on_tree_item_clicked)
        self._tree_widget.currentItemChanged.connect(self._on_current_item_changed)
        self._tree_widget.installEventFilter(self)
        self._refresh_diff_stylesheet()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(tree_header)
        layout.addWidget(self._tree_widget)

    def _refresh_diff_stylesheet(self) -> None:
        """Apply one shared stylesheet for every highlighted document-tree row."""
        if self._refreshing_style:
            return

        # Stylesheet themes such as OpenTheme add item margins, borders, and
        # rounded corners. Widget-backed rows paint a separate rectangle, so
        # normalize the native item box to keep both layers aligned without seams.
        item_selector = "QTreeWidget#documentDiffTree::item"
        container_selector = f"QTreeWidget#documentDiffTree QWidget#{DIFF_ROW_CONTAINER_OBJECT_NAME}"
        unchanged_selector = f'{container_selector}[diffState="{DiffState.UNCHANGED.name}"]'
        rules = [
            f"{item_selector} {{ margin: 0px; padding: 0px; border: none; border-radius: 0px; }}",
            f"{item_selector}:selected {{ border: none; border-radius: 0px; }}",
            f"{item_selector}:hover {{ border: none; border-radius: 0px; }}",
            f"{container_selector} {{ border-radius: 0px; }}",
            f"{unchanged_selector} {{ background-color: transparent; }}",
            f"{unchanged_selector} QLabel#{DIFF_ROW_LABEL_OBJECT_NAME} {{ background-color: transparent; }}",
        ]
        palette = self._effective_diff_palette()
        for state in (DiffState.ADDED, DiffState.DELETED, DiffState.MODIFIED):
            colors = colors_for_diff_state(state, palette)
            if colors.normal_background is None:
                raise RuntimeError("Changed document state requires a background color")
            selector = (
                f'QTreeWidget#documentDiffTree QWidget#{DIFF_ROW_CONTAINER_OBJECT_NAME}[diffState="{state.name}"]'
            )
            label_selector = f"{selector} QLabel#{DIFF_ROW_LABEL_OBJECT_NAME}"
            rules.extend(
                [
                    f"{selector} {{ background-color: {colors.normal_background.name()}; "
                    f"color: {colors.normal_foreground.name()}; }}",
                    f"{label_selector} {{ background-color: transparent; color: {colors.normal_foreground.name()}; }}",
                    f"{selector}:hover {{ background-color: {colors.hover_background.name()}; "
                    f"color: {colors.hover_foreground.name()}; }}",
                    f"{selector}:hover QLabel#{DIFF_ROW_LABEL_OBJECT_NAME} {{ "
                    f"color: {colors.hover_foreground.name()}; }}",
                    f'{selector}[rowSelected="true"] {{ background-color: {colors.selected_background.name()}; '
                    f"color: {colors.selected_foreground.name()}; }}",
                    f'{selector}[rowSelected="true"] QLabel#{DIFF_ROW_LABEL_OBJECT_NAME} {{ '
                    f"color: {colors.selected_foreground.name()}; }}",
                ]
            )

        # setStyleSheet emits StyleChange synchronously, which can trigger another theme refresh.
        self._refreshing_style = True
        try:
            self._tree_widget.setStyleSheet(" ".join(rules))
        finally:
            self._refreshing_style = False

    def _effective_diff_palette(self) -> QtGui.QPalette:
        """Resolve visible text color from application QSS into tree palette.

        Stylesheet themes can paint label text without updating the tree's Text
        palette role. A polished QLabel exposes effective WindowText while
        preserving theme-owned surface roles.
        """
        self._theme_probe.ensurePolished()
        return palette_with_resolved_text(
            self._tree_widget.palette(),
            self._theme_probe.palette().color(QtGui.QPalette.ColorRole.WindowText),
        )

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:  # noqa: N802
        """Refresh shared colors from theme events delivered to the inner tree."""
        if watched is self._tree_widget and event.type() in {
            QtCore.QEvent.Type.ApplicationPaletteChange,
            QtCore.QEvent.Type.PaletteChange,
            QtCore.QEvent.Type.StyleChange,
        }:
            self._refresh_diff_stylesheet()
        return super().eventFilter(watched, event)

    def _add_node_subtree(self, parent_item: QtWidgets.QTreeWidgetItem, node: NodePresentation, git_path: str) -> None:
        """Build one node subtree, attach it, then install widget-backed rows."""
        item = build_node_item(node)
        parent_item.addChild(item)
        self._install_node_row_widgets(item, node, git_path)

    def _install_node_row_widgets(
        self,
        item: QtWidgets.QTreeWidgetItem,
        node: NodePresentation,
        git_path: str,
    ) -> None:
        """Install one node-row widget, then recurse through children."""
        text = item.text(0)

        row_widget = DiffTreeRowWidget(text, tooltip=node.type_id, parent=self._tree_widget)
        row_widget.set_diff_state(node.state)
        item.setText(0, "")

        if node.visual_diff_enabled:
            row_widget.add_trailing_widget(self._create_visual_diff_button(item, git_path, node.path))

        self._tree_widget.setItemWidget(item, 0, row_widget)

        for index, child_node in enumerate(node.children):
            child_item = item.child(index)

            # Tree-item builder and presentation model recursion must stay aligned.
            if child_item is None:
                raise RuntimeError("Node child item missing during document diff tree wiring")

            self._install_node_row_widgets(child_item, child_node, git_path)

    def _create_visual_diff_button(
        self,
        item: QtWidgets.QTreeWidgetItem,
        git_path: str,
        node_path: str,
    ) -> QtWidgets.QToolButton:
        """Create visual comparison action for one node row."""
        button = make_tool_button(
            tooltip=translate("History", "Open 3D comparison"),
            icon=QtGui.QIcon(str(get_icon_path("VisualDiff.svg"))),
            width=TREE_ITEM_HEIGHT,
            height=TREE_ITEM_HEIGHT,
            style=VISUAL_DIFF_ICON_BUTTON_STYLE,
            auto_raise=True,
            icon_size=QtCore.QSize(TREE_ITEM_ICON_SIZE, TREE_ITEM_ICON_SIZE),
            tool_button_style=QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly,
        )
        button.clicked.connect(
            lambda checked=False: self._on_node_visual_diff_requested(item, git_path, node_path)
        )
        return button

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

    def _on_current_item_changed(
        self,
        current: QtWidgets.QTreeWidgetItem | None,
        previous: QtWidgets.QTreeWidgetItem | None,
    ) -> None:
        """Refresh selected styling on previous and current widget-backed rows."""
        for item, selected in ((previous, False), (current, True)):
            if item is None:
                continue
            row_widget = self._tree_widget.itemWidget(item, 0)
            if isinstance(row_widget, DiffTreeRowWidget):
                row_widget.set_selected(selected)

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
