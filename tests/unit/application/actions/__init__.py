"""Module responsibility: Application action tests.

These tests verify the complete workflow of application actions (TakeSnapshotAction,
CompareSnapshotsAction) by integrating real domain services (SnapshotExtractor, DiffEngine)
with faked infrastructure ports (FakeFreeCadPort, InMemorySnapshotRepository).

What These Tests Cover:
- Real domain logic: Uses actual SnapshotExtractor and DiffEngine implementations
- Faked infrastructure: Replaces FreeCAD port and repositories with test doubles
- End-to-end workflows: Tests complete action execution from start to finish
- Domain service integration: Verifies how domain services work together

What These Tests Don't Cover:
- FreeCAD runtime: No FreeCAD document manipulation or GUI interaction
- Actual FreeCAD API: Uses FakeFreeCadPort instead of real FreeCAD objects
- UI components: No Qt widgets or presenters tested here

Running Tests:
    uv run pytest tests/unit/application/actions/ -v

Test Files:
- test_take_snapshot.py: Tests for TakeSnapshotAction workflow
- test_compare_snapshots.py: Tests for CompareSnapshotsAction workflow

Dependencies Under Test:
- application/actions/commands/take_snapshot.py
- application/actions/commands/compare_snapshots.py
- domain/snapshots/extractor.py
- domain/diff/engine.py
- domain/diff/models.py

With fakes from:
- tests/fakes/fake_freecad_port.py
- tests/fakes/fake_logger.py
- domain/snapshots/repository.py (InMemorySnapshotRepository)
- domain/settings/repository.py (fake implementation)
"""
