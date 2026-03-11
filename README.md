# FreeCAD Diff Workbench

This workbench provides the ability to view changes between the current document and an older "snapshot" of the same document. The diff view is rendered in two columns, each containing a feature and property tree that is colored to highlight differences.

This functionality is especially powerful when combined with git to version control your FreeCAD files. Git functionality is not integrated here.

Note that the diff view is only intended to verify that your changes didn't cause unintentional parametric downstream mistakes. Just because a diff doesn't show any changes doesn't mean the FreeCAD file itself is unchanged. FreeCAD updates metadata such as timestamps, "touched" attributes, and view orientation every time a file is saved, which may not be displayed in the diff view. The intention with this workbench is more to answer questions like "Did changing this variable from 2mm to 3mm cause any unintended features/properties to change?"

## Suggested Workflow

1. Start with a clean git working tree (everything is committed)
2. Start FreeCAD and open your part files
3. Open the Diff Workbench. The Diff window is opened.
4. Click the "Take Snapshot" command in the toolbar. The list of snapshots on the left side of the window is updated to include the new snapshot, which is named "Snapshot YYYY-MM-DD HH:MM:SS".
5. Start working on your part files.
6. When you are done with your changes, switch back to Diff workbench.
7. Click the "Take Snapshot and Compare" button.
8. Compare changes. If everything looks good, go to File → Save All.
9. Commit all changes to git.
10. Return to step 5 to keep working.

## Diff View

The Diff Window features columns on the left and right. The earlier snapshot is rendered as a tree view on the left, and current snapshot on the right. Scrolling is synchronized within both windows.

Most objects have two expansion icons: one displays children objects, the other displays the properties.

- New objects are colored in green on the right side, and crossed out on the left
- Deleted objects are crossed out on the right side, and green on the left
- Modified objects are blue on both sides

When an object's properties are expanded, both their current values and their expressions, if available, are displayed. A change in either will be highlighted in the diff.

The name of each snapshot is displayed above both columns in a dropdown box. Click the dropdown box to select another snapshot to compare against. A button in between them on the top allows you to switch columns.

For now snapshots are stored in memory and are lost when FreeCAD is closed, but in the future they can be saved to files.

## Configuration

The FreeCAD Preferences dialog has a Diff Workbench panel with the following options:

- Excluded Types: a textarea with types, one on each line to exclude from the diff view. Objects of this type, and all its children are removed from the tree. By default, "App::Origin" is excluded because it never changes.
- Excluded Properties: a textarea with property names to exclude from the diff view. Exclude properties that create too much noise for a diff view, such as properties with timestamps.