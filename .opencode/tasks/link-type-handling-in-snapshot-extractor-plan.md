# Task: Handle Link-Type Children in Snapshot Extraction (Keep AssemblyLink Structure)

## Goal
Prevent duplicate-parent warnings and noisy tree expansion caused by link wrappers (`App::Link`, `App::LinkElement`, link-group mode), while preserving meaningful `Assembly::AssemblyLink` structure (including synchronized components and flexible-joint contents) in snapshots.

## Context
Current extractor builds parent-child claims from every object’s `ViewProvider.claimChildren()`. In assemblies with many links, multiple wrappers claim identical child names (`Origin`, `Body`, `Body001`, etc.), producing duplicate-parent warnings and unstable parent ownership semantics.

Research and source findings:
- `App::Link` forwards child claims from linked target (`Gui::ViewProviderLink::claimChildren()`), which can recursively expose linked internals.
- `App::LinkElement` is a link-like per-element wrapper used by link group/array behavior.
- `App::LinkGroup` exists as a class; in assembly workflows, link-group behavior is commonly represented as `App::Link` with `ElementCount > 0`.
- Assembly “Insert Component” creates:
  - `Assembly::AssemblyLink` when inserting an assembly
  - `App::Link` for non-assembly components.
- `Assembly::AssemblyLink` is not a thin pointer: it synchronizes local mirrored contents into its own `Group` (`App::Link` children and nested `Assembly::AssemblyLink`), and for flexible mode (`Rigid=False`) also synchronizes joints via a local joint group.

Planning note:
- `docs/PLAN.md` was requested by process but does not exist in repo at this path. Planning used `docs/Architecture.md` and existing task-plan conventions.

## Decisions Made
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Skip `claimChildren()` expansion for link wrappers (`isLink()` true, plus link-group mode) | Avoid duplicate claims from forwarded linked internals; preserve wrapper node/properties without exploding subtree | Keep existing behavior and only mute warning (rejected: noisy + confusing parent ownership remains) |
| Keep `Assembly::AssemblyLink` children | Its `Group` contains meaningful synchronized local assembly structure and optional flexible-joint data | Skip all AssemblyLink children (rejected: loses assembly-internal state visibility) |
| Update duplicate-parent log wording to “duplicate claim ignored, first parent retained” | Current wording says “Overwriting” but map keeps first parent | Keep current message (rejected: misleading diagnostics) |
| Add runtime type guard helper for skip policy | Centralized, testable logic; easier future extension | Inline ad-hoc checks in map builder (rejected: brittle, less testable) |
| Add focused unit tests with fakes for extraction map behavior | Validate deterministic behavior without FreeCAD runtime in CI | Rely only on manual FreeCAD check (rejected: weak regression protection) |

## Architecture Impact
- **Primary module:** `freecad/diff_wb/domain/snapshots/gui_extractor.py`
  - Add helper to detect link wrappers to skip child-claim expansion
  - Apply helper in `_build_parent_to_child_map()` before calling `claimChildren()`
  - Adjust duplicate-claim logging text
- **Tests:** `tests/unit/domain/snapshots/test_extractor.py`
  - Add/adjust tests around parent-child map construction and duplicate claim handling semantics
- **No UI contract changes required** (tree/render logic remains unchanged)

## FreeCAD Dependency
- [ ] No FreeCAD required (pure code)
- [x] FreeCAD required (follow exploration phase)

## Implementation Plan
**IMPORTANT:** For each phase, test steps come before implementation steps.

### Phase 1: FreeCAD API/Type Confirmation (research lock-in)
- [ ] Write/prepare expected-behavior notes as executable acceptance bullets (what must be skipped vs kept)
- [ ] Verify source-backed type semantics for:
  - `App::Link`
  - `App::LinkElement`
  - link-group mode (`App::Link` with `ElementCount > 0`)
  - `Assembly::AssemblyLink` synchronization behavior (components + flexible joints)
- [ ] Implement/update plan findings section with exact skip/keep policy

Detailed approach snippet:
```python
# policy target
# skip child-claim expansion: App::Link wrappers (including LinkElement / link-group semantics)
# keep child-claim expansion: Assembly::AssemblyLink
```

### Phase 2: TDD for extraction policy (unit with fakes)
- [ ] Write tests first:
  - [ ] Link wrapper parent is skipped for claimChildren expansion
  - [ ] AssemblyLink parent is not skipped
  - [ ] Duplicate child claims keep first parent and do not mutate map
  - [ ] Logging text reflects “ignored duplicate” semantics
- [ ] Implement helper(s) and parent-map integration:
  - [ ] Add `_should_skip_claim_children_parent(obj)` (private)
  - [ ] Use robust detection order:
    1. `isDerivedFrom("Assembly::AssemblyLink")` => **False** (do not skip)
    2. `isLink()` / `isDerivedFrom("App::Link")` / `isDerivedFrom("App::LinkElement")` / link-group mode => **True**
  - [ ] Apply skip before `_get_view_provider(...).claimChildren()`
  - [ ] Update warning message text at duplicate-claim site

Detailed approach snippet:
```python
def _should_skip_claim_children_parent(obj: object) -> bool:
    if _is_assembly_link(obj):
        return False
    return _is_link_wrapper(obj)  # App::Link/App::LinkElement/link-group mode
```

### Phase 3: FreeCAD runtime verification (manual integration)
- [ ] Write verification checklist first:
  - [ ] Snapshot extraction on linked assembly no longer emits duplicate-parent warnings from link wrappers
  - [ ] AssemblyLink nodes still show meaningful synchronized children
  - [ ] Flexible sub-assembly case still exposes joint-related structure where present
- [ ] Execute manual validation with real assembly files and record findings
- [ ] Adjust policy only if runtime reveals mismatch (e.g., additional link-like types needing skip)

Detailed runtime probe ideas:
```bash
./run_with_freecad.sh python -c "import FreeCAD; ..."
# Inspect TypeId/isLink/isDerivedFrom signals for candidate objects found in test assemblies
```

### Phase 4: Final cleanup and regression hardening
- [ ] Write final regression assertions first (map stability + deterministic parent ownership)
- [ ] Ensure helper remains private and extractor public API unchanged
- [ ] Document rationale in code comments near skip policy and duplicate-claim handling

## Test Strategy
- **Unit tests:**
  - `tests/unit/domain/snapshots/test_extractor.py` with fake objects/view providers
  - Positive behavioral tests only (skip link wrappers, keep AssemblyLink, retain first parent)
- **Manual FreeCAD integration checks:**
  - Real assembly with external links
  - Real assembly with `Assembly::AssemblyLink` (rigid and flexible modes)
  - Confirm warning reduction and expected tree structure

## Findings & Notes
1. Duplicate warnings currently come from global child-name parent mapping where first parent wins; log text currently implies overwrite but map does not overwrite.
2. Missing children under specific link nodes in UI is consistent with global first-parent/visited behavior: children may be attached elsewhere or skipped after first visit.
3. `Assembly::AssemblyLink` should remain expanded because it stores synchronized local assembly representation, not only a thin external pointer.
4. Keep policy extensible: if additional link-like classes appear, add them in helper without altering traversal architecture.
