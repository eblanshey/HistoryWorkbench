---
title: Smoke Testing
description: Checklist of features to verify manually, covering project detection, initialization, git identity, and iteration operations.
---
## Project Detection

- Detect project from open FreeCAD documents on workbench activation
- Refresh project detection and reload iterations
- Display "No project detected" state when no repository found
- Click project label to open repository directory in file browser

## Project Initialization

- Initialize new git repository: choose directory from candidate list based on open documents
- Initialize new git repository: directories already inside a project are disabled with explanation
- Initialize new git repository: success message with initialized path and a new gitignore
- Initialize new git repository: no candidates available when no saved documents open

## Git Identity

- Configure author name and email: save locally for current project only
- Configure author name and email: save globally for all projects
- Configure author name and email: global option disabled when global config file not writable, with explanation
- Configure author name and email: name and email required field validation
- Configure author name and email: pre-populated with existing identity values
- Configure author name and email: cancel dialog aborts flow

## Ignored Files (.gitignore)

- View current gitignore content in editor dialog
- Edit and save gitignore content
- Cancel editor dialog without saving
- Help link to gitignore syntax documentation

## Iteration History

- Display commit list with hash, author, timestamp, and message
- Load more commits on scroll (infinite scroll / pagination)
- Display "No iterations to display" placeholder when commit history is empty
- Right-click commit: restore all files from iteration
- Right-click commit: copy iteration ID (commit hash) to clipboard

## Current Files Area (Working Tree) View

- Select Current Files Area row to show working tree diffs
- Display document diff tree with status indicators (modified, added, deleted)
- Display summary counts: Modified, Deleted, Added
- Display "No changes" state when working tree is clean
- Expand/collapse document nodes in diff tree
- Diff row colors, hover, and selection remain visible with OpenTheme enabled
- Existing diff rows update after switching between light and dark themes
- Each document and node label renders once with OpenTheme enabled
- Right-click Current Files Area: mark all reviewed

## Reviewed Area (Staging) View

- Select Reviewed Area row to show staged diffs
- Display staged document diff tree
- Right-click Reviewed Area: restore reviewed files
- Right-click Reviewed Area: remove all from Reviewed

## Document Staging

- Stage single document: plus icon button per document row with tooltip
- Stage all documents: plus icon button in summary bar with tooltip
- Remove single document from Reviewed: minus icon button per document row with removal tooltip
- Remove all from Reviewed: minus icon button in summary bar with removal tooltip
- Stage button disabled for non-stageable documents
- Stage deleted documents

## Property Diff

- Select node in document diff tree to show property-level differences
- Property diff display with old/new value columns
- Changed property colors remain visible while unchanged rows retain theme styling
- Highlighted property values remain selectable and copyable
- Property diff clears when document diff clears or node changes
- Float precision from settings applied to numeric property display

## Visual Diff (3D Comparison)

- Open 3D comparison for node from Current Files Area view
- Open 3D comparison for node from Reviewed Area view
- Open 3D comparison for node from commit view
- Visual diff button per node row in diff tree

## Restore from History

- Restore single document from Reviewed: confirmation dialog with destructive warning
- Restore single document from commit: confirmation dialog with destructive warning
- Restore all from Reviewed: restore icon button opens scope selection dialog (listed FreeCAD files vs all FreeCAD files)
- Restore all from commit: restore icon button opens scope selection dialog (listed FreeCAD files vs all FreeCAD files)
- Restore confirmation: cancel aborts operation
- Restore all: confirmation dialog after scope selection
- Restore success info message
- Restore failure error display

## Save Iteration (Commit)

- Save iteration: enter iteration notes dialog
- Save iteration: empty notes validation warning
- Save iteration: no reviewed files info message
- Save iteration: missing git identity auto-prompts configure author dialog
- Save iteration: commit success refreshes history list
- Save iteration: commit failure error display
- Save iteration: cancel dialog aborts flow

## Document Management

- Open document for comparison: Open button on closed working-tree file indicator
- Open all documents in repository
- Open all documents in repository: no project warning
- Recompute active document
- Recompute all open documents
- Close all comparison windows (Diff_* documents without saving)

## Panel

- Open History Panel from toolbar or command
- Panel 3-column layout: history, document diff, property diff
- Panel splitter resize between columns
- Panel close and reopen preserves application state (current git repository detection)
- Panel focus after async FreeCAD actions (open document)

## Settings

- Float precision: set decimal places for numeric comparison (range 0-12)
- Excluded object types: use default exclusion list
- Excluded object types: use custom exclusion list with prefill from defaults on first use
- Excluded properties: use default exclusion list
- Excluded properties: use custom exclusion list with prefill from defaults on first use
- Type-specific excluded properties: use default exclusion list
- Type-specific excluded properties: use custom exclusion list with prefill from defaults on first use
- Git executable: leave empty so git runs from the system PATH
- Git executable: enter a path manually (e.g. portable git) and save; commit history loads through the configured binary
- Git executable: Browse button opens a file dialog that fills the path field
- Git executable: clear the field and save to return to PATH lookup
- Git executable: popup "Git Not Found" when git is neither configured nor on PATH, or the configured path is not a readable executable (refresh project, initialize project, save iteration)
- Git executable: no popup when detection simply finds no repository but git works
- Settings save and load persistence
- Settings info text: changes affect comparison only, not saved snapshots
