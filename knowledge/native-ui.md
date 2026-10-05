# Native interface development

**Status recorded: 2026-10-05.** The Galaxy-inspired interface is development
work for application **0.8.0**, on `ui/galaxy-native-workspace`, starting from
`7c6f2437842788daf9918ac2194ef859b153092c`. It is **unreleased** at this checkpoint.
The published 0.7.0 release and its reference-validation evidence remain
unchanged. Native Windows validation of this new interface is **pending**;
source checks below do not establish packaged desktop behavior.

## User-approved direction

Testers requested familiar Galaxy-style tool discovery and workflow editing.
The user approved a three-pane native interface, with general settings in the
right pane during standalone use and selected-step options there during
workflow editing. This replaces the earlier arrangement of a small graph,
step list and editor in the central area. It preserves the accepted searchable
tool library and does not revive the rejected wheel selectors.

Official design references are the Galaxy Training Network's
[interface introduction](https://training.galaxyproject.org/training-material/topics/introduction/tutorials/galaxy-intro-short/tutorial.html)
and [workflow editor guide](https://training.galaxyproject.org/training-material/topics/galaxy-interface/tutorials/workflow-editor/tutorial.html).
Galaxy is copyrighted open-source software; its
[current licence](https://github.com/galaxyproject/galaxy/blob/dev/LICENSE.txt)
describes the applicable terms. Workbench uses its own branding, controls and
Win32/GDI+ drawing. No Galaxy code, icons or screenshots are incorporated into
the application. The left panel is labelled **Tools**: Galaxy's separate Tool
Shed marketplace should not imply a newly implemented Workbench marketplace.

## Layout and operation

| Area | Tools mode | Workflow mode |
| --- | --- | --- |
| Header | Tools and Workflow buttons; Native Workbench identity | The same mode buttons |
| Left pane | Searchable installed tool library, category filter, Manage tools | The same library; drag a tool to the canvas or use Add to workflow |
| Central pane | Selected tool's description, explicit file inputs and run parameters | Workflow canvas with named input/output ports and tool cards |
| Right pane | General settings: analysis name, input browsing folder, output folder, References | Selected step's options; General settings remains accessible |
| Run action | Run tool | Run workflow |
| Save action | Save settings | Save workflow |

Selecting a tool in Tools mode opens that tool's standalone form. Switching
tools does not append hidden workflow steps. In Workflow mode, selecting a
canvas tool opens its options in the right pane. Dragging an output to an input
requests an explicit graph connection. Compatible targets depend on declared
semantic types, required state, capacity and cycle rules. The named-source
picker remains an alternative to pointer dragging.

The input folder is a browsing starting point for native file pickers. Selecting
it does not bind every file in that folder or infer paired reads. Tool inputs
remain individually selected named fields. The output folder is the parent for
new run directories, which retain methods, files, checksums and logs. References
opens the existing native finder/local library; download and binding remain
explicit operations. Results access remains available without introducing a
Galaxy dataset-history pane or dataset-history semantics.

The app remains native Win32 with a private Python host over anonymous pipes.
It requires no browser, HTTP listener, Docker, WSL or system Python. Tool
metadata continues to generate fields and determine scientific compatibility;
the layout adds no per-tool execution implementations.

## Session and save contracts

`DesktopHost` owns one workflow model and an independent cached `DesktopModel`
for each opened standalone tool. Mode changes preserve current parameters,
file bindings, selection and undo state **within the running process**. They do
not create automatic saved analyses or promise recovery of unsaved edits after
closing the application. Opening the same tool again preserves its edits;
reopening a deliberately cleared tool starts a new single-tool model.

Canonical persistence remains the existing separate contracts:

- Saved tool settings are presets, with an exact pack pin and reusable
  parameters; file/sample bindings are excluded.
- Saved workflows are connected, typed pipeline graphs. They retain exact
  pack pins and exclude local file bindings. A saved workflow still requires
  at least two connected tools.
- Loading a pipeline or the example selects Workflow mode. Loading a preset
  applies it to the active selected tool after compatibility validation.
- Reference targets, review and run preparation use the active model.
  Switching modes/tools is blocked during active runs and pack/reference
  operations. Frozen run evidence remains independent of later edits.
- A catalogue refresh updates all editing sessions while preserving their
  existing pack-version and manifest pins.

Explicitly injected host models remain the active workflow session for existing
embedders/tests. Normal native startup begins with an empty Tools session.

## Native host and canvas boundary

| Private RPC | Request | Response |
| --- | --- | --- |
| `workspace/mode` | `{"mode":"tool"}` or `{"mode":"workflow"}` | Active snapshot including `mode` |
| `workspace/tool` | `{"toolId":"bam/reference-index"}` | Preserved standalone tool snapshot, `mode: "tool"` |
| `workspace/connection-targets` | `{"ref":"step-1::sorted"}` | `{"ref":"step-1::sorted","targets":[{"nodeId":"step-2","portId":"alignment"}]}` |

Connection previews are read-only and concern one dragged source at a time.
They traverse the producer's ancestors to exclude cyclic targets, then apply
the same semantic/state rules used by connection validation. A single-source
port can be replaced; multiple-source ports must have room for the added
source. Existing connections are not duplicated. The actual `connect` action
remains authoritative and atomically rejects invalid edges.

Do not add every port's full source-choice list to every node snapshot. That
would make large graphs quadratic in response size and violate the private
host's 8 MiB frame limit. Ordinary node inputs stay compact; the selected
inspector retains its source picker choices. Preview targets have only
`nodeId` and `portId`. Canvas positions are presentation state and do not change
dependency order, pack pins or scientific graph semantics.

## Verification checkpoint

These source checks were performed during this development session on **Linux
x86-64 with Python 3.12.14**, against the modified working tree:

| Command | Result |
| --- | --- |
| `python3 workspace/tests/test_desktop_modes.py` | 11 passed, 0 failures, 0 skips |
| `python3 workspace/tests/test_desktop_host.py` | 12 passed, 0 failures, 0 skips |
| `python3 workspace/tests/test_reference_service.py` | 10 passed, 0 failures, 0 skips |

The new suite checks independent session edits/undo, strict requests, active
reference binding/review/run selection, busy-state exclusion, pipeline/preset
loading, catalogue refresh with unchanged pins, and connection type/state/cycle
and capacity rules. A synthetic 512-node graph remains below the 8 MiB snapshot
limit; its 511-target preview remains below 64 KiB. These fixtures do not execute
scientific tools or native Windows controls.

The exact packaged Windows gate is being developed in
[`scripts/check_workspace_ui_windows.py`](../scripts/check_workspace_ui_windows.py).
It must establish actual pane placement, tool selection, scrolling/resizing,
drag/drop connections, mode preservation, References access and native control
behavior using the packaged executable and bundled host. Preserve captures,
control bounds, source/artifact hashes, environment and failed attempts. The
existing reference gate must also be applied where this UI changes its access
or binding path. Do not transfer 0.7.0's native passes to the new executable.

Before a release, replace this pending checkpoint with links to the exact
successful candidate/final evidence and public artifact verification. Retain
any excluded DPI, multi-monitor, accessibility or picker scenarios explicitly;
an unavailable check is not a pass.
