# Translations

This directory contains translation sources and compiled binaries for the Project History workbench.

## Files

- `ProjectHistory.ts`: base template extracted from source code.
- `ProjectHistory_<locale>.ts`: locale translation source files, for example `ProjectHistory_de.ts`.
- `ProjectHistory_<locale>.qm`: compiled locale binaries generated from locale `.ts` files.

## Update Translation Template

Use Taskfile task:

```bash
task translations:update
```

Equivalent direct command:

```bash
lupdate -extensions py freecad/diff_wb -ts freecad/diff_wb/resources/translations/ProjectHistory.ts
```

## Compile Locale Files

Use Taskfile task:

```bash
task translations:compile
```

Equivalent direct command for specific locales:

```bash
lrelease freecad/diff_wb/resources/translations/ProjectHistory_de.ts
```

`translations:compile` skips cleanly when no locale files exist.

## Update Locale Sources

Use Taskfile task:

```bash
task translations:update-locales
```

Equivalent direct command for one locale file:

```bash
lupdate -extensions py freecad/diff_wb -ts freecad/diff_wb/resources/translations/ProjectHistory_de.ts
```

Run this after changing user-facing strings so locale `.ts` files receive new and obsolete entries.

## Refresh All

Use Taskfile task:

```bash
task translations:refresh
```

This updates `ProjectHistory.ts`, merges new strings into locale `.ts` files, and compiles locale `.ts` files.

## Repository Policy

Commit `ProjectHistory.ts` and locale `.ts` files.
Commit locale `.qm` files when locale translations exist.
