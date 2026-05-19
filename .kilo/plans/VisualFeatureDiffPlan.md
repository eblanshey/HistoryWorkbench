# Visual Feature Diff Plan

## Goal

Add a proof of concept that opens a visual old/new comparison for eligible tree nodes by extracting BREP files from FCStd archives.

Scope supports all history modes:

- Working Tree
- Staging
- Commit

## Current Architecture Touchpoints

- `freecad/diff_wb/ui/views/document_diff_tree_widget.py` renders document and node rows with `QTreeWidgetItem`.
- `freecad/diff_wb/ui/presenters/diff_presenter.py` transforms `NodeDiff` into `NodePresentation`, stores `DiffResult` by git path, and handles node selection.
- `freecad/diff_wb/application/actions/create_document_diffs.py` defines working-tree comparison semantics. Current old side uses the git index through `commit=None`.
- `freecad/diff_wb/domain/git/ports.py`, `domain/git/git_service.py`, and `infrastructure/git/git_port_adapter.py` already expose text `git show` for YAML snapshots. FCStd visual diff needs binary-safe materialization.
- `freecad/diff_wb/domain/freecad_ports.py` and `infrastructure/freecad/ports.py` represent low-level FreeCAD Python document operations. Visual BREP comparison should use a dedicated FreeCAD visual diff service instead of adding feature-specific methods to `FreeCadPort`.
- `freecad/diff_wb/ui/translation_strings.py` owns user-facing strings.

## User Flow

1. User selects `Working Tree`, `Staging`, or a specific `Commit`.
2. Diff tree renders changed nodes as usual.
3. Node rows whose `type_id` is visual-eligible get a right-side visual diff icon.
4. User clicks the icon.
5. Workbench creates a temporary visual diff workspace under `/tmp`.
6. Workbench materializes old/new FCStd sides based on selected history mode.
8. Workbench unzips both FCStd copies.
9. Workbench finds `<ObjectName>.Shape.brp` for the clicked node in both extracted archives.
10. Workbench creates a new FreeCAD document.
11. Workbench imports old BREP as `Old` and new BREP as `New`.

## Visual Diff Eligibility

Use presenter-side type rules for icon enablement:

- `Part::*`
- `PartDesign::*`
- exact `Sketcher::SketchObject`

The icon policy is in `DiffPresenter` via `NodePresentation.visual_diff_enabled`.

## UI Plan

Add node action support without changing property diff behavior.

- Extend `NodePresentation` with `visual_diff_enabled: bool = False`.
- Presenter computes `visual_diff_enabled` from node type and current history state.
- In `DocumentDiffTreeWidget`, use a per-node row widget in the same tree column and float the action icon on the right side of the row.
- Add a small icon button for enabled nodes.
- Store both `git_path` and `node_path` on the button callback.
- Keep normal tree item click behavior for property diff selection.

Add a new icon under `freecad/diff_wb/resources/icons/`, for example `VisualDiff.svg`.

Add translation strings for:

- Visual diff tooltip.
- Missing old/new FCStd message.
- Missing BREP message.
- Import failure message.

## Application Plan

Add one application action dedicated to this use case.

Suggested file:

- `freecad/diff_wb/application/actions/open_visual_feature_diff.py`

Suggested request model fields:

- `repo: GitRepository`
- `git_path: str`
- `node_path: str`
- `old_commit: str | None`
- `new_commit: str | None`
- `working_tree_document_path: str | None`
- `property_name: str = "Shape"`

Supported side combinations:

- Working Tree: `old_commit=None`, `new_commit=None`, `working_tree_document_path=<repo/git_path>`
- Staging: `old_commit="HEAD"`, `new_commit=None`, `working_tree_document_path=None`
- Commit: `old_commit="<commit>~1"`, `new_commit="<commit>"`, `working_tree_document_path=None`

Suggested action responsibilities:

1. Resolve object name from `node_path` final segment.
2. Create a temporary directory with `tempfile.mkdtemp(prefix="diffcad_visual_")`.
3. Materialize old FCStd side to `<tmp>/old/Old.FCStd` from git ref/index.
4. Materialize new FCStd side to `<tmp>/new/New.FCStd` from disk (working tree) or git ref/index (staging/commit).
5. Extract both archives into separate folders.
6. Find `<object_name>.Shape.brp` in each extracted folder.
7. Call the FreeCAD port to create a visual diff document from both BREP paths.
8. Return `Result.success(True)` or failure message.

Temporary files can remain for MVP diagnostics. Add cleanup only after visual import no longer needs files on disk.

## Git Plan

Do not reuse `get_file_contents()` for FCStd files because it runs subprocess in text mode and can corrupt binary zip data.

Add binary-safe materialization:

- `GitPort.write_file_from_ref(git_root: str, commit: str | None, git_path: str, destination: str) -> bool`
- `GitService.write_file_from_ref(repo: GitRepository, commit: str | None, git_path: str, destination: str) -> bool`
- `GitPortAdapter.write_file_from_ref(...)`

Implementation details:

- Use `git show :<path>` when `commit is None`.
- Use `git show <commit>:<path>` when commit is provided.
- Run subprocess without `text=True` for this method.
- Stream stdout directly into the destination file or capture bytes and write bytes.
- Keep timeout and logging consistent with existing git adapter methods.

Working-tree old side still uses `commit=None` (index). Staging and commit modes also use `write_file_from_ref` for both sides.

## Archive Plan

Add a small helper inside the visual diff action or a focused application helper module.

Responsibilities:

- Open FCStd with `zipfile.ZipFile`.
- Extract entries safely under the target directory.
- Reject archive entries that escape the target directory.
- Search extracted files for exact filename `<object_name>.Shape.brp`.

For MVP, only `Shape` is searched. Other BREP-backed properties such as `SuppressedShape` and `AddSubShape` are intentionally ignored.

## FreeCAD Visual Diff Service Plan

Do not add visual comparison methods to `FreeCadPort`. `FreeCadPort` should stay a thin representation of common FreeCAD Python document operations.

Add a dedicated class for this feature:

- `freecad/diff_wb/infrastructure/freecad/visual_diff.py`
- `FreeCADVisualDiff`
- `open_brep_visual_diff(old_brep_path: str, new_brep_path: str) -> DocumentLike`

Implementation uses FreeCAD runtime APIs directly through injected `FreeCadContext`:

1. Create a new document with a descriptive generated name.
2. Load each BREP with `Part.Shape().read(path)`.
3. Add two `Part::Feature` objects.
4. Set object names/labels to `Old` and `New`.
5. Assign each loaded shape.
6. Recompute the new document.

This avoids `ImportGui` and keeps feature-specific visual comparison behavior out of the generic FreeCAD port.

## Presenter Wiring

Add constructor dependency to `DiffPresenter`:

- `open_visual_feature_diff_action: OpenVisualFeatureDiffAction`

Wire it in `freecad/diff_wb/application/di/container.py` and `freecad/diff_wb/ui/composer.py`. The container should create `FreeCADVisualDiff(ctx)` and inject it into `OpenVisualFeatureDiffAction`.

Add view protocol method:

- `set_visual_diff_callback(callback: Callable[[str, str], None]) -> None`

Add presenter handler:

- `on_visual_diff_clicked(git_path: str, node_path: str) -> None`

Handler flow:

1. Verify current history selection exists.
2. Verify repo exists.
3. Build `OpenVisualFeatureDiffRequest` based on history mode.
4. Execute action.
5. Log failure through `Log.warning`.

## Testing Plan

Unit tests should cover behavior, not implementation trivia.

- Presenter marks visual diff availability by type policy (`Part::`, `PartDesign::`, `Sketcher::SketchObject`).
- View creates a visual diff button only for eligible node presentations and emits `(git_path, node_path)`.
- Git adapter binary materialization streams `git show` bytes directly to destination file.
- Visual diff action materializes both sides (git/git or git/file), extracts archives, finds matching `.Shape.brp`, and calls FreeCAD port with old/new BREP paths.
- Visual diff action returns failure when either BREP is missing.

Integration coverage can be added later with `tests/freecad/BasicFile.FCStd` if the POC survives first implementation.

Run after implementation:

- `task check`
- `task test`

## MVP Limitations

- Only `Shape` BREP is supported.
- For working tree mode, old side uses git index and new side reads the working-tree file from disk.
- For staging and commit modes, both sides come from git refs/index.
- Working tree visual diff reflects saved file state on disk, not unsaved in-memory edits.
- Temp directories are not cleaned immediately, to keep imported BREP files available for FreeCAD and to aid debugging.

## Acceptance Criteria

- Eligible node type (`Part::`, `PartDesign::`, `Sketcher::SketchObject`) shows a right-side visual diff icon.
- Clicking the icon opens a new FreeCAD document with objects named `Old` and `New`.
- Working tree uses old BREP from `git show :<fcstd path>` and new BREP from disk FCStd.
- Staging and commit views also support icon + visual diff using git refs/index for both sides.
