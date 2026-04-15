
# Task: Phase 3 - Working Tree and Staging Items

## Goal
Add "Working Tree" and "Staging" selectable, centered items to the top of the commit history list.

## Context
As part of the MVP implementation, the history list needs to allow users to compare the current working tree and the git index (staging area) against a selected commit. These two states are not commits themselves but must be available as selection options at the top of the history list.

## Decisions Made
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Use `TextAlignmentRole` | Allows the custom delegate to render text centered for special items while keeping commits left-aligned | Hardcoding indices in the delegate (too fragile) |
| Use specific strings in `UserRole` | Provides a clear way for the presenter to distinguish special items from actual `GitCommit` hashes during selection | Using negative indices or a separate list (more complex state management) |

## Architecture Impact
- `freecad/diff_wb/ui/views/diff_panel_view.py`:
    - Modify `_SnapshotListItemDelegate.paint` to respect alignment roles.
    - Modify `DiffPanelView.show_commits` to prepend special items.

## FreeCAD Dependency
- [x] No FreeCAD required (pure code/Qt logic)
- [ ] FreeCAD required (follow exploration phase)

## Implementation Plan

### Phase 1: Update UI Delegate for Alignment
- [x] Write unit tests for `_SnapshotListItemDelegate` to verify that it respects `Qt.ItemDataRole.TextAlignmentRole` when painting selected items.
- [x] Update `_SnapshotListItemDelegate.paint` to retrieve the alignment from `index.data(Qt.ItemDataRole.TextAlignmentRole)` and use it instead of the hardcoded `Qt.AlignmentFlag.AlignLeft`.

### Phase 2: Update History List Population
- [x] Write tests to verify that "Working Tree" and "Staging" items are always present at the top of the list, even if no commits are provided.
- [x] Modify `DiffPanelView.show_commits`:
    - Move the `if not commits: return` guard to *after* adding the special items.
    - Create and add "Working Tree" item with text "Working Tree", alignment `Qt.AlignmentFlag.AlignCenter`, and UserRole `"WORKING_TREE"`.
    - Create and add "Staging" item with text "Staging", alignment `Qt.AlignmentFlag.AlignCenter`, and UserRole `"STAGING"`.
    - Append the actual git commits as before.

## Test Strategy
- **Unit tests**: Use PySide6 tests to verify `QListWidgetItem` data (UserRole and TextAlignmentRole) and delegate painting logic.
- **Integration tests**: Verify the list population via `GitRepositoryPresenter` in a simulated environment.

## Manual Test Cases
Proposed manual test cases grouped by file location:

### docs/manual-testing/git-history.md
- **History List Layout**: Verify that "Working Tree" and "Staging" are the first two items in the list, their text is centered, they are selectable, and they are followed by the git commits in DESC order.

## Findings & Notes
- The `_SnapshotListItemDelegate` currently overrides the paint method for selected items, which is why the `TextAlignmentRole` must be explicitly handled there to avoid the default left-alignment.

