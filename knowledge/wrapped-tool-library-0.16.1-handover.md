# Wrapped native tool library, unpublished 0.16.1

## Status and scope, 2026-10-10

This follow-up is **in progress** on `fix/native-ui-0.16.1`, starting at
`568f2a74a62c4befb7ffe9c9f26390fe5a8c1d72`. It continues
[draft PR #15](https://github.com/comparativechrono/workbench/pull/15), based on
`feature/deployment-acceptance` at
`f74d90229be6a78d6ad0c0076c54c04bb7e7cae2`. The application version remains
unpublished **0.16.1**. Published **0.16.0** and its assets remain unchanged;
no merge or release is included.

Testers reported that the centre pane obscures long tool labels and that the
hover popup needed to read them is annoying. The requested presentation is a
fully visible, wrapped tool name in **bold**, followed by the complete regular-
weight description. Each row must fit inside the left library pane; reading a
tool's label must not require hovering over it. This is a native presentation
change inspired by the user's description of Galaxy, not an integration with
Galaxy or a change to scientific tool metadata.

The [library contract](expandable-tool-library.md) records the requirements.
Keep the native TreeView category hierarchy, keyboard navigation, selection,
search, compatible-output filtering and workflow dragging. Preserve standalone
forms, workflow pins and saved graphs, Methods, Samples editing, reference
management and the existing Run/category/resize corrections. Pack IDs,
versions, published bytes and scientific execution are outside this change.

## Implementation and validation plan

Implementation and exact-package validation have not yet been completed for
this revision. The dedicated candidate workflow is
`.github/workflows/native-wrapped-library-candidate.yml`. It must bind the new
application build to matching source, Starter and updater archives, then test
the exact Windows package in ordinary and space-containing paths.

Required focused observations include complete wrapped names/descriptions,
bold names and regular descriptions, absence of the library label popup, row
fit at the supported narrower and wider window sizes, and retained category,
keyboard, search, selection and drag behavior. Source checks, existing native
regressions, archive/source correspondence and screenshot review must be
recorded separately with exact identities. Do not infer a new pass from a
previous candidate or count repeated gates as additional unique coverage.

The earlier resize candidate remains documented in the unchanged
[resize handover](resize-redraw-0.16.1-handover.md). Its strict single-transition
negative control was not reproduced and its workflow remains failed; the
bounded concurrent-resize comparison is separately scoped. The new library
candidate does not rerun or reclassify that historical negative control.
Historical resize workflows are manual-only, while the library workflow owns
validation of this new scope.

## Evidence and delivery

New build commit, archive SHA-256 identities, test results, screenshots and
download links are pending. Keep durable focused receipts and original-report
hashes in the repository, excluding opaque tokens and unnecessary runner/input
metadata. Preserve failed attempts and any unavailable checks explicitly.

Delivery remains an unpublished review candidate in draft PR #15.
Representative-PC, high-DPI, multiple-monitor, physical-trackpad and managed-
machine acceptance remain outstanding. Executable signing and institutional
approval, scientific Linux CWL, SDK/build recovery and separately managed
benchmarking are outside this presentation change.
