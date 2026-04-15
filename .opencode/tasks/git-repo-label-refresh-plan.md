# Task: Git Repository Label Reorder and Refresh Button

## Goal
1. Move the repository label to appear ABOVE the "Snapshots" label in the view
2. Add a Refresh button aligned to the right of the repository label, using `FreeCADGui.getIcon("view-refresh.svg")`
3. Hook up the refresh button to the presenter to re-detect the git repository

## Context
Phase 1 implemented the git repository detection and display. The repository label currently appears BELOW the "Snapshots" label. The user wants it ABOVE with a refresh button to re-run the detection.

## Decisions Made

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Use callback pattern for refresh | View doesn't need to know about presenter; presenter registers a callback | Could use signals/slots but callback is simpler for MVP |
| Refresh button in repository header row | Keeps label and button visually grouped | Could put button elsewhere but less intuitive |
| Presenter wires itself to view | Presenter already has view reference, so it can register its own callback; keeps workbench simpler | Could have workbench wire them, but that mixes concerns layer wiring with business logic |

## Architecture Impact

### Files Modified
- `freecad/diff_wb/ui/views/diff_panel_view.py` - Add refresh button, reorder layout
- `freecad/diff_wb/ui/presenters/git_repository_presenter.py` - Add refresh handler method and self-wire to view
- `freecad/diff_wb/ui/protocols/diff_view.py` - Add `set_refresh_callback` to protocol

### New Files
- None

## FreeCAD Dependency
- [x] No new FreeCAD dependency (uses existing FreeCADGui.getIcon)

## Implementation Plan

### Phase 1: Add Refresh Callback Infrastructure

- [x] Write tests for `set_refresh_callback` in view mock
- [x] Update `DiffView` protocol in `ui/protocols/diff_view.py`:
  ```python
  def set_refresh_callback(self, callback: Callable[[], None]) -> None:
      """Set the callback to invoke when refresh button is clicked.

      Args:
          callback: A no-argument callable to invoke on refresh.
      """
  ```

### Phase 2: Update DiffPanelView

- [x] Write tests for refresh button functionality with mocked callback
- [x] In `diff_panel_view.py` `_setup_ui()`:
  - Import `QPushButton`
  - Create `self._refresh_button = QPushButton()`
  - Set icon using: `import FreeCADGui as Gui; self._refresh_button.setIcon(Gui.getIcon("view-refresh.svg"))`
  - Create header layout: `repository_header_layout = QHBoxLayout()`
  - Add `_repository_label` to header layout (left)
  - Add stretch spacer to header layout
  - Add `_refresh_button` to header layout (right)
  - Create `repository_header_container = QWidget()` and set its layout
  - Reorder `snapshot_layout.addWidget()` calls:
    1. `repository_header_container` (FIRST - above snapshots)
    2. `snapshot_placeholder`
    3. `snapshot_list`

- [x] Add `set_refresh_callback(callback)` method to `DiffPanelView`:
  ```python
  def set_refresh_callback(self, callback: Callable[[], None]) -> None:
      """Set the callback to invoke when refresh button is clicked."""
      self._on_refresh_callback = callback
      self._refresh_button.clicked.connect(callback)
  ```

### Phase 3: Update GitRepositoryPresenter

- [x] Write tests for `on_refresh_clicked` method
- [x] In `git_repository_presenter.py`, add method:
  ```python
  def on_refresh_clicked(self) -> None:
      """Re-detect and display git repository when refresh is clicked."""
      result = self._find_git_repo_action.execute()

      if result.is_success:
          repo = result.data
          self._application_state.git_repository = repo
          self._view.show_repository(repo)
      else:
          self._application_state.git_repository = None
          self._view.show_repository(None)
          Log.warning(f"Git detection failed: {result.message}")
  ```
- [x] In `git_repository_presenter.py` `__init__`, after storing `_view`:
  - Call `self._view.set_refresh_callback(self.on_refresh_clicked)`

### Phase 4: Update Manual Test Cases

- [x] Update `docs/manual-testing/git_repository_detection.md`:
  1. In Test Case 3 and 4: Add step to verify the repository info appears **above** the "Snapshots" label (not below)
  2. Add verification step that a refresh button (circular arrow icon) appears to the right of the repository info
  3. After switching workbenches in any test case, optionally click the refresh button to re-trigger detection and verify the same result

## Test Strategy

### Unit Tests (No FreeCAD)
- View `set_refresh_callback` stores callback and connects to button clicked signal
- View refresh button has correct icon (mocked)
- Presenter `on_refresh_clicked` calls action and updates view
- Presenter `on_refresh_clicked` updates application state

### Integration Tests
- None required - manual verification sufficient

## Manual Test Cases

**Existing test cases to update in `docs/manual-testing/git_repository_detection.md`:**

1. **Test Case 3 and 4**: Add verification step that the repository info appears ABOVE the "Snapshots" label
2. **All test cases**: Add optional step after workbench switch to click the refresh button and confirm the same result
3. **All test cases**: Add verification that a refresh button (circular arrow icon) appears to the right of the repository info

## Findings & Notes

### Icon Loading
The icon is loaded using `FreeCADGui.getIcon("view-refresh.svg")` directly on the button. This is a standard FreeCAD icon that should be available in all FreeCAD installations.

### Callback Pattern
Using a simple callback (no signals/slots) keeps the implementation straightforward for MVP. The presenter registers its own method as the callback, keeping the view passive.
