# SPDX-License-Identifier: LGPL-3.0-or-later
"""Domain models for diff results.

This module provides models for representing the differences between two
document snapshots, including property-level and node-level comparisons.
"""

from dataclasses import dataclass, field
from enum import Enum, auto

from .property_value import PropertyValue


class DiffState(Enum):
    """The state of a node or property in a diff comparison.

    This is used for UI rendering to highlight changes:
    - ADDED: Node/property exists only in the new snapshot
    - DELETED: Node/property exists only in the old snapshot
    - MODIFIED: Node/property exists in both but has different values
    - UNCHANGED: Node/property is identical in both snapshots
    """

    ADDED = auto()
    DELETED = auto()
    MODIFIED = auto()
    UNCHANGED = auto()


@dataclass(frozen=True)
class PropertyDiff:
    """The difference between two property values.

    Attributes:
        property_name: Name of the property
        old_value: Value in the old snapshot (None if added)
        new_value: Value in the new snapshot (None if deleted)
        state: The diff state (ADDED, DELETED, MODIFIED, UNCHANGED)
    """

    property_name: str
    old_value: PropertyValue | None
    new_value: PropertyValue | None
    state: DiffState

    def __str__(self) -> str:
        if self.state == DiffState.ADDED:
            return f"{self.property_name}: +{self.new_value}"
        elif self.state == DiffState.DELETED:
            return f"{self.property_name}: -{self.old_value}"
        elif self.state == DiffState.MODIFIED:
            return f"{self.property_name}: {self.old_value} -> {self.new_value}"
        return f"{self.property_name}: {self.old_value}"


@dataclass(frozen=True)
class NodeDiff:
    """The difference between two tree nodes.

    Represents the diff result for a single node in the document tree,
    including its properties and children.

    Attributes:
        path: The path to this node
        type_id: The TypeID of the node
        state: The overall state of this node
        property_diffs: List of property-level differences
        children: List of child node diffs
    """

    path: str
    type_id: str
    state: DiffState
    property_diffs: list[PropertyDiff] = field(default_factory=list)
    children: list["NodeDiff"] = field(default_factory=list)

    def __str__(self) -> str:
        state_str = self.state.name
        prop_count = len(self.property_diffs)
        child_count = len(self.children)
        return f"NodeDiff({self.path}, {state_str}, {prop_count} props, {child_count} children)"

    @property
    def has_changes(self) -> bool:
        """Check if this node or any children have changes."""
        if self.state != DiffState.UNCHANGED:
            return True
        if self.property_diffs:
            return True
        return any(child.has_changes for child in self.children)

    @property
    def changed_properties(self) -> list[PropertyDiff]:
        """Get only the properties that actually changed."""
        return [p for p in self.property_diffs if p.state != DiffState.UNCHANGED]


@dataclass(frozen=True)
class DiffSummary:
    """A summary of changes in a diff result.

    Provides quick statistics about the scope of changes:
    - Total nodes compared
    - Nodes added, deleted, modified, unchanged
    - Total properties changed
    """

    total_nodes: int = 0
    added_nodes: int = 0
    deleted_nodes: int = 0
    modified_nodes: int = 0
    unchanged_nodes: int = 0
    total_property_changes: int = 0

    def __str__(self) -> str:
        return (
            f"DiffSummary: {self.added_nodes} added, "
            f"{self.deleted_nodes} deleted, "
            f"{self.modified_nodes} modified, "
            f"{self.unchanged_nodes} unchanged"
        )

    @classmethod
    def compute(cls, diff_result: "DiffResult") -> "DiffSummary":
        """Compute a summary from a diff result.

        Args:
            diff_result: The diff result to summarize

        Returns:
            A DiffSummary with computed statistics
        """
        total_nodes = 0
        added_nodes = 0
        deleted_nodes = 0
        modified_nodes = 0
        unchanged_nodes = 0
        total_property_changes = 0

        for node_diff in diff_result.node_diffs:
            total_nodes += 1
            counts = cls._count_node(node_diff)
            added_nodes += counts["added"]
            deleted_nodes += counts["deleted"]
            modified_nodes += counts["modified"]
            unchanged_nodes += counts["unchanged"]
            total_property_changes += counts["property_changes"]

        return cls(
            total_nodes=total_nodes,
            added_nodes=added_nodes,
            deleted_nodes=deleted_nodes,
            modified_nodes=modified_nodes,
            unchanged_nodes=unchanged_nodes,
            total_property_changes=total_property_changes,
        )

    @staticmethod
    def _count_node(node: NodeDiff) -> dict[str, int]:
        """Recursively count node states and property changes.

        Returns:
            A dict with counts for 'added', 'deleted', 'modified', 'unchanged', 'property_changes'
        """
        # Count this node
        if node.state == DiffState.ADDED:
            added = 1
            deleted = 0
            modified = 0
            unchanged = 0
        elif node.state == DiffState.DELETED:
            added = 0
            deleted = 1
            modified = 0
            unchanged = 0
        elif node.state == DiffState.MODIFIED:
            added = 0
            deleted = 0
            modified = 1
            unchanged = 0
        else:
            added = 0
            deleted = 0
            modified = 0
            unchanged = 1

        # Count property changes
        property_changes = sum(1 for prop_diff in node.property_diffs if prop_diff.state != DiffState.UNCHANGED)

        # Recurse into children
        for child in node.children:
            child_counts = DiffSummary._count_node(child)
            added += child_counts["added"]
            deleted += child_counts["deleted"]
            modified += child_counts["modified"]
            unchanged += child_counts["unchanged"]
            property_changes += child_counts["property_changes"]

        return {
            "added": added,
            "deleted": deleted,
            "modified": modified,
            "unchanged": unchanged,
            "property_changes": property_changes,
        }


@dataclass(frozen=True)
class DiffResult:
    """The complete result of comparing two snapshots.

    Represents all differences between an old and new snapshot, organized
    as a tree structure that mirrors the original document hierarchy.

    Attributes:
        old_snapshot_name: Name/identifier of the old snapshot
        new_snapshot_name: Name/identifier of the new snapshot
        node_diffs: List of root-level node diffs
    """

    old_snapshot_name: str
    new_snapshot_name: str
    node_diffs: list[NodeDiff] = field(default_factory=list)

    def __str__(self) -> str:
        summary = DiffSummary.compute(self)
        return f"DiffResult({self.old_snapshot_name} vs {self.new_snapshot_name}): {summary}"

    @property
    def summary(self) -> DiffSummary:
        """Get a summary of this diff result."""
        return DiffSummary.compute(self)

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes in this diff."""
        return (
            self.summary.total_property_changes > 0
            or self.summary.added_nodes > 0
            or self.summary.deleted_nodes > 0
            or self.summary.modified_nodes > 0
        )

    def get_all_changed_paths(self) -> list[str]:
        """Get all paths that have changes (for UI highlighting)."""
        changed_paths: list[str] = []
        for node_diff in self.node_diffs:
            self._collect_changed_paths(node_diff, changed_paths)
        return changed_paths

    def _collect_changed_paths(self, node: NodeDiff, result: list[str]) -> None:
        """Recursively collect paths with changes."""
        if node.has_changes:
            result.append(node.path)
        for child in node.children:
            self._collect_changed_paths(child, result)
