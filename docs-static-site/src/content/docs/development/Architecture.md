---
title: Architecture
description: Layered architecture with domain-driven and ports-and-adapters patterns for the History Workbench project.
sidebar:
    order: 2
---
History Workbench uses a layered architecture with domain-driven and ports-and-adapters patterns. The goal is to keep FreeCAD, Qt, git, and filesystem details at the edges while core CAD-history behavior remains understandable and testable.

## Design Principles

- Dependencies point inward where practical: entry points and UI call application actions; application actions coordinate domain services; infrastructure adapts external systems.
- Domain concepts are explicit: snapshots, diffs, settings, tree paths, and git state have dedicated models and services.
- Application actions are small desktop use cases. They coordinate dependencies and return result objects rather than directly updating Qt views or dialogs.
- UI state stays in the UI layer. The application container does not own presenter state or view state.
- External systems are represented through ports. Real FreeCAD, git, YAML, and filesystem implementations live in infrastructure; tests usually use fakes.
- FreeCAD startup work stays minimal. The workbench registers commands first, then creates the diff panel when activated or opened.

## Desktop Call Flow

History Workbench is a desktop FreeCAD workbench hosted inside another application. These flows show how host callbacks move through project layers; use the layer names below when deciding where code belongs.

```text
FreeCAD command/workbench callback -> entry point -> WorkbenchCommandPresenter or application action
Qt widget event                    -> presenter   -> application action
Handler                            -> application action
Application action                 -> domain service/model -> infrastructure adapter
Infrastructure adapter             -> FreeCAD / git / filesystem / YAML
```

FreeCAD commands are entry points. They expose `GetResources()`, answer `IsActive()`, and translate `Activated()` callbacks into presenter or application calls. They are not presenters, although small command-specific dialogs may still live there until they are worth extracting into UI code.

UI code owns Qt widgets, presenters, dialog flow, display feedback, translated display text, and UI session state. Application actions own workbench use cases such as stage, commit, diff, save-before-diff, and open visual comparison. Domain owns CAD-history models, rules, and algorithms. Infrastructure owns concrete FreeCAD, git, filesystem, YAML, and FreeCAD preference calls.

FreeCAD document changes often update the visible desktop UI as a side effect. Visibility is not the layer boundary. Opening, saving, recomputing, staging, and creating comparison documents belong in application use cases when they are part of a workbench operation and are performed through ports.

## Runtime Flow

```text
FreeCAD loads init_gui.py
        |
        v
Workbench.Initialize()
        |
        |-- register FreeCAD commands
        |-- register toolbar and menu
        v
First Workbench.Activated()
        |
        |-- create FreeCAD runtime context
        |-- create ApplicationContainer
        |-- configure Log with FreeCADLogger
        |-- create and register ApplicationState
        |-- create and register WorkbenchCommandPresenter
        |-- configure and register preferences page
        v
Workbench.Activated() or Open Diff Window command after activation
        |
        v
compose_and_register_panel(container, application_state, focus_history_window_callback)
        |
        |-- create HistoryPanelView
        |-- create presenters (consume application_state)
        |-- register presenters in UIRegistry
        |-- detect active git repository
        v
FreeCAD main window addWindow(HistoryPanelView)
        |
        |-- register document-independent native MDI view
        |-- activate History with non-canvas overlay capabilities
        v
Presenter executes application actions
        |
        v
Domain services and infrastructure adapters perform work
```

## Layer Responsibilities

### Entry Points

Location: `freecad/history_wb/entrypoints/`

Entry points integrate with FreeCAD's workbench and command APIs. They are driving adapters from the host desktop application into History Workbench.

- `workbench.py` defines `HistoryWorkbench`, registers toolbars/menus, lazily creates the application container, registers preferences, and opens the diff panel.
- History is registered through the main window's native `addWindow()` API as a document-independent view. Native activation lets FreeCAD apply its non-canvas overlay policy without changing dock preferences or the active document. FreeCAD/Qt manage window geometry and maximized state. Panel cleanup follows native view destruction, including across MDI shell replacement during detach/redock.
- `commands.py` defines FreeCAD command classes and delegates work to `WorkbenchCommandPresenter` or application actions.
- Entry points may access the global container through `freecad/history_wb/_container.py`.
- Entry points should stay thin. They translate FreeCAD callbacks into application or UI calls.
- Command classes should stay thin. They translate FreeCAD callbacks into handler or application calls, instantiating handlers with container actions and dialog callbacks.

### UI Layer

Location: `freecad/history_wb/ui/`

The UI layer owns presenter state, Qt views, dialog flow, display feedback, signal wiring, and UI-only session state.

- `composer.py` composes app-scoped command presenters and panel-scoped views/presenters, consuming a pre-created `ApplicationState`.
- `wiring.py` binds public widget/component signals to presenter listener methods.
- `state.py` stores application-scoped `ApplicationState` such as detected `GitRepository`. Survives panel close and is accessible to commands even when the panel is closed.
- `registry.py` stores globally reachable `ApplicationState`, app-scoped `WorkbenchCommandPresenter`, and nullable panel-scoped presenters.
- `presenters/` coordinates application actions, owns UI session flow, and maps domain/application results into presentation models.
- `views/` contains Qt widgets, child view components, dialog helpers, theme helpers, and preferences UI.
- `HistoryPanelView` supplies `widget()` and `onHasMsg()` callbacks for FreeCAD's native MDI wrapper. It does not advertise canvas capabilities such as `CanPan` or `AllowsOverlayOnHover`, matching Start-style overlay behavior. Overlay auto-hide still follows FreeCAD's non-3D-view preference, and explicit overlay hint clicks remain available.
- User-facing UI text is translated at display sites with literal `translate("History", "...")` calls, or defined with `QT_TRANSLATE_NOOP` when deferred.

Presenter responsibilities are split by kind:

- `DiffPresenter` is top-level diff coordinator. Owns current history selection, triggers load/stage/restore/open flows, and updates document/property views.
- `GitRepositoryPresenter` owns repository detection, commit loading, and panel-specific rendering. Delegates shared command flows to `WorkbenchCommandPresenter`.
- `WorkbenchCommandPresenter` is app-scoped. Owns single instances of `AuthorConfigurationHandler`, `CommitIterationHandler`, `InitializeRepositoryHandler`, and `GitIgnoreHandler`. Creates temporary `DialogView` instances parented to the FreeCAD main window at call time, avoiding stale Qt references from panel widgets.
- `presenters/document_diff/` contains focused helpers for diff loading, staging, restore, visual diff, cached results, document/node mapping, status indicators, and summary-button state.
- `presenters/git_repository/` contains focused handlers for repository initialization, gitignore editing, author configuration, and commit iteration.
- `presenters/property_diff/` contains property presentation mapping and nested property-path tree helpers.

Presenters receive only the specific view objects and action objects they need from the UI composer, not sibling child widgets or Qt gesture details. Views render Qt widgets and perform translation. Presenters pass raw data and intent, not translated UI strings. Dialogs and message boxes stay in view layer even when launched from FreeCAD command entry points.

Presenters must never import Qt or call message helpers directly. They depend on `DialogView` or equivalent message protocol methods for all modal UI. `DialogView` implements those protocol methods by delegating to `views/diff_panel/messages.py`. Extracted presenter collaborators (handlers, loaders) receive the narrow dialog/message protocol, not concrete view modules. This keeps modal UI in the view layer and keeps presenter tests Qt-free.

Handlers are focused, stateless workflow classes inside presenter subdirectories. They own multi-step dialog flows and action orchestration for a single use case. They are owned by `WorkbenchCommandPresenter` for command-accessible flows. Panel presenters delegate shared command flows to `WorkbenchCommandPresenter` instead of constructing handlers directly.

### Application Layer

Location: `freecad/history_wb/application/`

The application layer exposes workbench use cases as small action classes. Actions coordinate desktop side effects through ports without owning Qt presentation behavior.

- `actions/` contains use cases organized by domain: `git_repo/` (repository lifecycle), `git_history/` (read history), `git_workflow/` (staging, commit, restore), `git_config/` (identity and gitignore), `documents/` (FreeCAD document ops), `snapshots/` (snapshot creation), `diffs/` (diff computation and visual comparison), and `settings/` (preferences).
- `actions/result_models.py` contains reusable result types.
- `container.py` wires application actions, domain services, and infrastructure adapters.

Actions should be stateless after construction. They receive dependencies through constructors, execute one operation, and return a result. They may save FreeCAD documents, open comparison documents, write snapshot files, or stage git paths when those effects are part of the use case and are performed through ports or domain services.

### Domain Layer

Location: `freecad/history_wb/domain/`

The domain layer contains core CAD-history concepts, rules, models, algorithms, and contracts.

- `diff/` contains diff models, comparison algorithms, and `DiffEngine`.
- `git/` contains git models, git port protocols, and `GitService`.
- `settings/` contains settings models, text codec helpers, persistence state, and `SettingsRepository`.
- `snapshots/` contains snapshot models, snapshot serialization helpers, snapshot repository contracts, and `SnapshotExtractor`.
- `tree/` contains tree nodes, property models, and data-path wrappers.
- `config.py` contains default diff settings such as exclusions and float precision.
- `freecad_ports.py` defines minimal FreeCAD-facing protocols used by domain/application code.

Most domain code is pure Python. `domain/snapshots/gui_extractor.py` extracts FreeCAD's visual tree through `claimChildren()` using injected `GuiLike` from `FreeCadContext`, so domain services avoid direct `FreeCADGui` imports while still matching runtime GUI behavior. Concrete FreeCAD runtime imports and document mutation belong in infrastructure adapters.

### Infrastructure Layer

Location: `freecad/history_wb/infrastructure/`

Infrastructure adapts external systems to project protocols. It is still required even for systems central to the workbench, because FreeCAD runtime modules, git CLI, YAML libraries, and filesystem IO are concrete integration details.

- `freecad/ports.py` adapts the runtime FreeCAD API to `FreeCadPort` and `AppPort`.
- `freecad/freecad_visual_diff_creator.py` creates visual comparison documents through FreeCAD and Part APIs.
- `freecad/freecad_file_manager.py` materializes and extracts FreeCAD document revisions for visual diffing.
- `freecad/settings_repo.py` persists diff settings through FreeCAD preferences.
- `freecad/logger.py` sends `Log` output to the FreeCAD console.
- `git/git_port_adapter.py` implements git operations by calling the git CLI.
- `persistence/snapshot_yaml.py` writes snapshot YAML.
- `persistence/snapshot_yaml_deserializer.py` reads snapshot YAML.

Infrastructure can depend on domain and application types. Domain and application code should not depend on infrastructure implementations directly except where dependencies are wired in the container.

## Current Source Layout

```text
freecad/history_wb/
├── _container.py
├── init_gui.py
├── resources.py
├── utils.py
├── version.py
├── application/
│   ├── container.py
│   ├── actions/
│   │   ├── diffs/
│   │   ├── documents/
│   │   ├── git_config/
│   │   ├── git_history/
│   │   ├── git_repo/
│   │   ├── git_workflow/
│   │   ├── settings/
│   │   └── snapshots/
├── domain/
│   ├── config.py
│   ├── freecad_ports.py
│   ├── diff/
│   ├── git/
│   ├── settings/
│   ├── snapshots/
│   └── tree/
├── entrypoints/
│   ├── commands.py
│   └── workbench.py
├── infrastructure/
│   ├── freecad/
│   ├── git/
│   └── persistence/
├── resources/
│   ├── icons/
│   ├── translations/
│   └── ui/
└── ui/
    ├── composer.py
    ├── registry.py
    ├── state.py
    ├── wiring.py
    ├── presenters/
    │   ├── document_diff/
    │   ├── git_repository/
    │   ├── property_diff/
    │   ├── git_repository_presenter.py
    │   └── workbench_command_presenter.py
    └── views/
```

## Dependency Rules

```text
Entry Points
    |
    v
UI Layer --------------+
    |                  |
    v                  |
Application Layer      |
    |                  |
    v                  |
Domain Layer <---------+
    ^
    |
Infrastructure Layer
```

- Entry points may call UI registries, presenters, commands, and application container accessors.
- UI may call application actions and use domain models for display state.
- Handlers depend on application actions, `ApplicationState`, and the dialog/message protocol, not on presenters, concrete widgets, or Qt.
- Application may use domain services, domain models, and domain ports.
- Application actions may coordinate desktop side effects through ports, but should not import Qt widgets or concrete FreeCAD/git/filesystem implementations.
- Domain should not import UI or application modules.
- Infrastructure implements ports and can call external APIs.
- The container is a composition mechanism, not application state.
- `ApplicationState` is shared state reachable from entry points and UI, but not owned by application actions.

## Placement Rules

Use these rules when deciding where code belongs:

| Code mentions or does | Layer |
| --- | --- |
| FreeCAD command registration, `Activated()`, `GetResources()`, workbench lifecycle | Entry point |
| Qt widget, dialog, message box, translated display text, view state | UI |
| Multi-step user operation such as stage, commit, diff, save before diff, open comparison | Application |
| Snapshot/diff/tree/settings/git rule that can be expressed without concrete runtime APIs | Domain |
| `FreeCAD`, `FreeCADGui`, `Part`, git CLI, YAML library, direct filesystem IO, zip extraction | Infrastructure |
| Concrete object creation and dependency wiring | Composition root/container |

Opening a FreeCAD document, saving a modified document, recomputing, or creating a comparison document can visibly change the desktop UI. The deciding factor is not visibility. The deciding factor is ownership: presentation code decides what the user sees and asks for; application code decides what the workbench operation does; infrastructure code performs concrete runtime calls.

## Composition Roots

History Workbench has two composition roots.

### Application Composition

On first `workbench.Activated()`, `_initialize_container()` creates the FreeCAD runtime context and calls `create_application_container(ctx)`. The container wires:

- FreeCAD adapters
- git adapter and git service
- settings repository
- snapshot extractor
- diff engine
- application actions

The container is stored through `set_container()` so FreeCAD command instances can access it at execution time. `workbench.Initialize()` stays lightweight: it registers commands, toolbar, and menu only.

### UI Composition

`compose_and_register_panel(container, application_state, focus_history_window_callback)` creates:

- `HistoryPanelView`
- `DiffPresenter`
- `GitRepositoryPresenter`

`ApplicationState` and `WorkbenchCommandPresenter` are created during first activation before panel composition. The command presenter is registered in the UI registry before composition, and the composer fetches it to pass into `GitRepositoryPresenter`. This keeps both state and command flows alive across panel open/close cycles.

It then registers UI objects in `ui_registry` for command access. UI composition happens when the diff panel is created, not during initial FreeCAD module import.

## UI Composition Rules

Composite Qt views may be split into focused child widgets, but event flow stays explicit and top-down.

- Composer wires presenters to public top-level view/component signals.
- `wiring.py` is single place for presenter event binding tables.
- Top-level views act as facades for composed child widgets.
- Child widgets do not import, instantiate, or call sibling child widgets.
- Child widgets emit signals upward. Facades coordinate cross-widget state such as history-selection propagation into document diff state.
- Presenters listen with intent/use-case method names such as `save_iteration`, `select_history_item`, `stage_document`, `restore_all_from_history`, and `open_visual_diff`.
- Widget/component signals use event or state names such as `refresh_requested`, `history_selection_changed`, `node_selection_requested`, and `visual_diff_requested`.
- Avoid widget-gesture names such as `on_*_clicked` in public presenter-facing API.
- Cross-widget coordination is tested at facade level; child rendering and mapping behavior is tested at owning component/helper level.

Example: `HistoryPanelView` composes `HistoryPanelWidget`, `DocumentDiffTreeWidget`, and `PropertyDiffTreeWidget`. Selecting history in `HistoryPanelWidget` does not directly mutate `PropertyDiffTreeWidget`; facade state and presenter listeners coordinate the resulting document/property updates.

## Snapshot And Diff Pipeline

History Workbench stores textual snapshots next to `.FCStd` files so git can compare CAD model state.

```text
FreeCAD document
        |
        v
SnapshotExtractor
        |
        v
Snapshot model
        |
        |-- working tree snapshot from open document
        |-- commit snapshot from YAML deserializer
        v
DiffEngine
        |
        v
DiffResult
        |
        v
DiffPresenter
        |
        v
HistoryPanelView
```

Snapshots contain normalized object payloads and occurrence paths. This allows repeated or linked objects to be represented separately from object data. Diff comparison uses settings for exclusions and numeric precision.

Spreadsheet cells retain evaluated values and store raw cell contents in the root path's `expression` field, including literal inputs and formulas. Cell aliases use an `Alias` sub-path. This preserves source-input changes even when evaluated values remain equal and uses the existing expression comparison and display.

## Git Workflow Integration

Git support is implemented as domain service plus infrastructure adapter.

- `GitService` owns repository-level workflow rules.
- `GitPort` defines git operations.
- `GitPortAdapter` calls the git CLI.
- Application actions use `GitService` to find repositories, list commits, stage files, detect staged/committed paths, and commit staged changes.
- The UI stores the active `GitRepository` in `ApplicationState` because repository selection is application-scoped state that survives panel close.

History Workbench supplements normal git clients. It focuses on CAD-specific staging, snapshot generation, and review.

## Settings And Preferences

Default settings live in `domain/config.py`. Runtime settings are read and written through `SettingsRepository`, implemented by `FreeCADSettingsRepository` with FreeCAD preferences.

Settings affect diff computation and display. They do not affect snapshot generation.

## Public APIs

Module `__init__.py` files define public module APIs with `__all__` where useful. Importing from package-level modules is preferred when a symbol is exported there.

```python
from freecad.history_wb.domain.diff import DiffEngine
from freecad.history_wb.domain.snapshots import Snapshot
from freecad.history_wb.domain.tree import Property
```

Direct file imports are acceptable when a symbol is not part of a package API or when tests need focused access to implementation details.

## Known Tradeoffs

- `SnapshotExtractor` uses injected `GuiLike` to access GUI documents and `claimChildren()` behavior. This keeps extraction aligned with FreeCAD's visual tree without domain-level `FreeCADGui` imports.
- `ApplicationContainer` exposes small `log()` and `translate()` helpers for entry points. Core code should prefer `Log` and view-level translation patterns.
- Some FreeCAD APIs are difficult to type precisely. Protocols in `domain/freecad_ports.py` intentionally model only the behavior History Workbench uses.

## Glossary

| Term | Meaning |
| --- | --- |
| Action | Application-layer use case object with an `execute()` method. |
| Adapter | Infrastructure implementation of a port, such as `GitPortAdapter`. |
| Application Container | Object that wires actions, services, repositories, and adapters. |
| Composition Root | Place where dependencies are created and connected. |
| Domain | Core model and behavior independent from presentation details. |
| Port | Protocol that describes an external dependency. |
| Presenter | UI coordinator that turns application results into view updates. |
| Snapshot | Text-friendly representation of a FreeCAD document's model state. |
| ApplicationState | Application-scoped UI state, such as detected repository, shared across entry points and UI. Survives panel close. |
| Handler | Focused workflow class inside presenter subdirectories. Owns multi-step dialog flows and action orchestration for a single use case. |
