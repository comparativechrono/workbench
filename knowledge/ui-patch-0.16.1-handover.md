# Native keyboard and narrow-display patch, 0.16.1

Development snapshot: **2026-10-09**, branch `fix/native-ui-0.16.1`, based on
`f74d90229be6a78d6ad0c0076c54c04bb7e7cae2` and its open draft deployment companion
[PR #14](https://github.com/comparativechrono/workbench/pull/14). The user approved
continuation after reviewing the two observed desktop defects. This is an
unpublished application patch candidate; published 0.16.0 and the companion's
original failure evidence remain unchanged. No merge or release is authorized.

## Changes and contracts

- Results moves focus to its available query before disabling a focused action.
  Asynchronous replies do not take focus back from another control. Opening
  Results places focus in the query. Keyboard Search must retain focus and allow
  immediate Escape, for empty and populated results on fresh and upgraded apps.
- The main window uses monitor work-area bounds for initial placement and minimum
  size. The logical minimum is 960×680; narrow layouts retain three panes with a
  compact library and unchanged option-editor width. Shared geometry keeps
  controls and painted separators aligned. This targets the observed 1024-pixel
  desktop; high-DPI and representative-machine acceptance remain separate.
- Application and three native resource versions become **0.16.1**. Scientific
  operations, saved pins, all four published pack trees, private runtime, setup
  profile and catalogue trust remain unchanged.
- A new candidate builder derives one Starter, matching Git/source companion and
  core-only 0.16.0→0.16.1 updater from exact published 0.16.0 inputs. The existing
  deployment workflow/lock still describe their original frozen application.

## Required evidence before delivery

The new [candidate workflow](../.github/workflows/native-ui-patch-candidate.yml)
builds once, validates source correspondence and runs separate exact Windows
installations in ordinary and spaced paths: updater picker/state preservation,
keyboard/layout, curated scientific/results, workspace, reference management,
results/replay/DAG/icon and scrolling scopes. Initial bounds must be observed
before the driver resizes the window. Native focus checks use actual keyboard
input with no pointer workaround after Results opens.

Source tests have been exercised locally, but native execution and exact package
validation are **pending at this implementation checkpoint**. Before delivering,
record exact tested commit/archive hashes, source/test results and explicit skips,
all native failures and final observations, screenshot review and working draft
review/download links. Do not transfer the older release's passes to these bytes.

Representative-PC, high-DPI/transitions, multiple monitors, physical trackpads,
managed-machine policy and IT approval remain outstanding. Signing requires a
controlled identity. Scientific Linux CWL and SDK/build recovery remain later
sets; benchmarking is handled separately.
