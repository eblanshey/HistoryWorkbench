---
title: Configuration
description: Reference for History Workbench configuration options.
---

FreeCAD's Preferences dialog includes a **History** panel.

![Preferences Panel](./preferences.png)

## Exclusion Lists

Exclusion lists hide noisy generated data from tree comparison views.

Each exclusion list supports two modes:

- **Use default exclusion list:** Use History Workbench's built-in defaults.
- **Use custom exclusion list:** Provide your own exclusions.

Default values are defined in [`freecad/history_wb/domain/config.py`](https://github.com/eblanshey/HistoryWorkbench/blob/master/freecad/history_wb/domain/config.py).

### Excluded Object Types

Enter one FreeCAD `TypeId` per line, such as `App::Origin`. Objects of these types and their children are removed from comparison views. You can see an object's type by hovering your mouse over it in the History's tree panel.

### Excluded Properties

Enter one property name per line, such as `TimeStamp`. These properties are excluded across all object types.

### Type-Specific Excluded Properties

Enter one mapping per line in the format `TypeId -> PropertyName`. This excludes one property for one object type while keeping it visible elsewhere.

```text
TechDraw::DrawSVGTemplate -> PageResult
```

## Numeric Comparison

### Float Precision

Set the number of decimal places used for floating-point comparison and display. The supported range is `0` to `12`; the default is `2`.

## Git Executable

Point the workbench at a specific git binary instead of relying on the one found on the system `PATH`. This is useful for portable git installations, such as PortableGit on Windows.

- **Empty (default):** git is located on the system `PATH`, matching typical command-line behavior.
- **Set:** the given path is used for every git command the workbench runs. Enter a full path to the git binary, or use **Browse...** to pick one:
  - Windows: e.g. `C:\PortableGit\bin\git.exe`
  - macOS: e.g. `/opt/homebrew/bin/git`
  - Linux: e.g. `/usr/bin/git` or `/opt/git/bin/git`

A leading `~` is expanded to your home directory. The setting takes effect for subsequent git operations immediately after saving; no restart is required.

