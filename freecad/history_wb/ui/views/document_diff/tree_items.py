"""File responsibility: Build document diff QTreeWidgetItem hierarchies from presentation models."""

from __future__ import annotations

from ....qt import QtCore, QtWidgets
from ....utils import translate
from ...presenters.presentation_models import NodePresentation
from ..widgets.styles import TREE_ITEM_HEIGHT


__all__ = ["build_document_root_item", "build_node_item"]


def build_document_root_item(
    display_text: str,
    git_path: str,
) -> QtWidgets.QTreeWidgetItem:
    """Create one top-level structural document item."""
    root_item = QtWidgets.QTreeWidgetItem([display_text or translate("History", "Unnamed Document")])
    root_item.setSizeHint(0, QtCore.QSize(0, TREE_ITEM_HEIGHT))
    root_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, git_path or display_text)

    return root_item


def build_node_item(node: NodePresentation) -> QtWidgets.QTreeWidgetItem:
    """Recursively build one structural node subtree."""
    name = node.path.split("/")[-1] if node.path else ""
    text = node.label if node.label == name else f"{node.label} ({name})"

    item = QtWidgets.QTreeWidgetItem([text])
    item.setSizeHint(0, QtCore.QSize(0, TREE_ITEM_HEIGHT))
    item.setToolTip(0, node.type_id)
    item.setData(0, QtCore.Qt.ItemDataRole.UserRole, node.path)
    item.setData(0, QtCore.Qt.ItemDataRole.UserRole + 1, node.has_changes)
    for child in node.children:
        item.addChild(build_node_item(child))

    return item
