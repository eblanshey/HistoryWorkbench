# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for InMemorySnapshotRepository including store creation,
# snapshot addition/retrieval/deletion, metadata listing, and nested children handling.
"""Unit tests for InMemorySnapshotRepository."""

from datetime import datetime

from freecad.diff_wb.domain import Property, Snapshot, TreeNode
from freecad.diff_wb.domain.snapshots.repository import InMemorySnapshotRepository


def _make_snapshot(name: str, nodes: list[TreeNode]) -> Snapshot:
    """Helper to create a Snapshot with current timestamp."""
    return Snapshot(snapshot_id="", document_name=name, timestamp=datetime.now(), nodes=nodes)


class TestInMemorySnapshotRepository:
    """Tests for InMemorySnapshotRepository class."""

    def test_store_creation_and_initialization(self) -> None:
        """Test that store can be created and starts empty."""
        store = InMemorySnapshotRepository()
        assert store.list_snapshots() == []

    def test_add_snapshot_returns_snapshot_id(self) -> None:
        """Test that add_snapshot returns a unique snapshot_id."""
        store = InMemorySnapshotRepository()
        nodes = [
            TreeNode(
                id=1,
                name="TestObject",
                type_id="PartDesign::Body",
                label="Test Body",
                path="TestObject",
                properties={},
            )
        ]
        snapshot = _make_snapshot("test_snapshot", nodes)
        snapshot_id = store.add_snapshot(snapshot)

        assert snapshot_id is not None
        assert isinstance(snapshot_id, str)

    def test_get_snapshot_returns_snapshot(self) -> None:
        """Test that get_snapshot returns the stored snapshot."""
        store = InMemorySnapshotRepository()
        nodes = [
            TreeNode(
                id=2,
                name="TestObject",
                type_id="PartDesign::Body",
                label="Test Body",
                path="TestObject",
                properties={"Label": Property.from_freecad("Test Body", {}, "Base")},
            )
        ]
        snapshot = _make_snapshot("test_snapshot_2", nodes)
        snapshot_id = store.add_snapshot(snapshot)

        retrieved = store.get_snapshot(snapshot_id)
        assert retrieved is not None
        assert retrieved.document_name == "test_snapshot_2"
        assert len(retrieved.nodes) == 1
        assert retrieved.nodes[0].label == "Test Body"

    def test_delete_snapshot_removes_snapshot(self) -> None:
        """Test that delete_snapshot removes the snapshot from the store."""
        store = InMemorySnapshotRepository()
        nodes = [
            TreeNode(
                id=3,
                name="TestObject",
                type_id="PartDesign::Body",
                label="Test Body",
                path="TestObject",
                properties={},
            )
        ]
        snapshot = _make_snapshot("test_snapshot_3", nodes)
        snapshot_id = store.add_snapshot(snapshot)

        store.delete_snapshot(snapshot_id)
        retrieved = store.get_snapshot(snapshot_id)
        assert retrieved is None

    def test_list_snapshots_returns_all(self) -> None:
        """Test that list_snapshots returns all stored snapshots."""
        store = InMemorySnapshotRepository()
        for i in range(3):
            nodes = [
                TreeNode(
                    id=i + 1,
                    name=f"TestObject{i}",
                    type_id="PartDesign::Body",
                    label=f"Test Body {i}",
                    path=f"TestObject{i}",
                    properties={},
                )
            ]
            store.add_snapshot(_make_snapshot(f"test_snapshot_{i}", nodes))

        snapshots = store.list_snapshots()
        assert len(snapshots) == 3

    def test_get_nonexistent_snapshot_returns_none(self) -> None:
        """Test that get_snapshot returns None for non-existent snapshot."""
        store = InMemorySnapshotRepository()
        retrieved = store.get_snapshot("nonexistent-id")
        assert retrieved is None
