# SPDX-License-Identifier: LGPL-3.0-or-later
"""Domain models for document snapshots.

This module provides models for capturing the state of a FreeCAD document
at a point in time, represented as a tree structure.
"""

from dataclasses import dataclass, field

from .property_value import PropertyValue


@dataclass(frozen=True)
class TreeNode:
    """A node in the document tree.

    Represents an object or sub-object in a FreeCAD document, with its
    properties and children. The tree structure reflects the document's
    hierarchy (objects contain sub-objects via GetSubObjects).

    Attributes:
        name: The name of this node (object name or sub-object name)
        type_id: The FreeCAD TypeID of the object (e.g., "PartDesign::Body")
        label: The user-friendly label of the object
        path: The full path to this node (e.g., "Body/Pad")
        is_root: True if this is a root-level object (not a sub-object)
        properties: Mapping of property name to value
        children: Child nodes (sub-objects)
    """

    name: str
    type_id: str
    label: str
    path: str
    is_root: bool = True
    properties: dict[str, PropertyValue] = field(default_factory=dict)
    children: list["TreeNode"] = field(default_factory=list)

    def __str__(self) -> str:
        return f"TreeNode({self.path} [{self.type_id}])"

    def add_child(self, child: "TreeNode") -> None:
        """Add a child node (creates a new tree with the child added)."""
        # Since the dataclass is frozen, we can't modify children directly
        # This method is for documentation; actual tree building happens outside
        raise NotImplementedError("TreeNode is immutable. Build the tree during construction.")


@dataclass(frozen=True)
class Snapshot:
    """A snapshot of a FreeCAD document at a point in time.

    A snapshot captures the complete state of a document as a tree structure.
    It includes metadata about when the snapshot was taken and provides
    methods for comparing against other snapshots.

    Attributes:
        document_name: Name of the document
        timestamp: Timestamp when the snapshot was taken
        root_nodes: List of root-level tree nodes (top-level objects)
    """

    document_name: str
    timestamp: str
    root_nodes: list[TreeNode] = field(default_factory=list)

    def __str__(self) -> str:
        node_count = sum(1 for node in self.root_nodes for _ in self._count_nodes(node))
        return f"Snapshot({self.document_name}, {len(self.root_nodes)} objects, {node_count} total nodes)"

    def _count_nodes(self, node: TreeNode) -> list[TreeNode]:
        """Helper to count all nodes recursively."""
        result = [node]
        for child in node.children:
            result.extend(self._count_nodes(child))
        return result

    def get_all_nodes(self) -> list[TreeNode]:
        """Get all nodes in the tree (flattened)."""
        all_nodes = []
        for root in self.root_nodes:
            all_nodes.extend(self._collect_nodes(root))
        return all_nodes

    def _collect_nodes(self, node: TreeNode) -> list[TreeNode]:
        """Recursively collect all nodes."""
        nodes = [node]
        for child in node.children:
            nodes.extend(self._collect_nodes(child))
        return nodes

    def find_node_by_path(self, path: str) -> TreeNode | None:
        """Find a node by its path.

        Args:
            path: The path to the node (e.g., "Body/Pad")

        Returns:
            The node if found, None otherwise
        """
        for root in self.root_nodes:
            node = self._find_node_recursive(root, path)
            if node:
                return node
        return None

    def _find_node_recursive(self, node: TreeNode, target_path: str) -> TreeNode | None:
        """Recursively search for a node by path."""
        if node.path == target_path:
            return node
        for child in node.children:
            found = self._find_node_recursive(child, target_path)
            if found:
                return found
        return None
