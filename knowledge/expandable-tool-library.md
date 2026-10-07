# Expandable native tool library

Development started **2026-10-07** from published 0.10.1 documentation baseline
`3a6e06f8fa05a8ceebed4584bd3433e07f08df52`, on
`feature/expandable-tool-library`. The next development candidate is **0.11.0**.
Published 0.10.1 and its independent tool packs remain unchanged. This page is
a development handover, not release acceptance or evidence of a Windows pass.

## Requested interaction

Testers asked to replace the category dropdown and flat scrolling tool list
with visible category headings that expand to show their tools, as in Galaxy.
The official Galaxy Training Network
[interface tutorial](https://training.galaxyproject.org/training-material/topics/introduction/tutorials/galaxy-intro-short/tutorial.html)
(last modified 2026-09-23) and its
[interface image](https://training.galaxyproject.org/training-material/topics/introduction/images/galaxy_interface.png)
were inspected on 2026-10-07. The image itself shows a 2025 event banner; its
page's modification date is not evidence that the screenshot was captured in
2026. The design reference is search above browsable tool sections. Workbench
retains its own native controls, styling, branding and general-settings pane.
No Galaxy images, code or other assets are included in the application.

## Native implementation

`desktop/desktop_workspace.cpp` uses a Windows TreeView for tool library control
104. Category headings come from the installed catalogue and contain tool
children with the existing scientific display names. Categories are navigation
items, never executable tools or workflow inputs. Multiple categories may be
open at once. The category dropdown is removed, giving the library more space.

Single-click a heading to expand or collapse it. Native arrow-key navigation
and Enter/Space on a heading provide keyboard access. Selecting a tool opens
its standalone form in Tools mode. In Workflow mode, Add to workflow,
double-click and dragging a tool onto the canvas keep their existing meanings.
Expanding a heading must never add a step or replace the current form.

Search includes category names and existing tool search metadata. Search and
the existing compatible-output filter reveal matching tools inside their
categories. Clearing a filter restores the ordinary browsing expansion state.
Expansion, selection and viewport are session presentation state, separate from
saved scientific workflows and exact pack pins. Routine model refreshes should
not rebuild an unchanged tree or reset the user's browsing position. Installing
a pack supplies new tool/category metadata without an application rebuild.

## Validation and candidate status

The native implementation is complete and has passed a strict-warning
cross-build with the pinned LLVM-MinGW 20260922 UCRT compiler. The Linux source
gate passed **70 tests, no failures or skips** across desktop host (12), modes
(11), workflow inputs (11), pack service (6), setup manager (15), setup service
(7) and split packaging (8). Independent review found and corrected a Win32
expansion-notification issue: repeated toggles can omit notifications after
`TVIS_EXPANDEDONCE`, so the view now records actual expansion state directly.
These are source/build findings, not a Windows GUI pass. Exact packaged native
validation remains pending. No tester acceptance, public release or updater is
claimed yet.

The candidate workflow is `.github/workflows/native-tool-library-candidate.yml`.
It builds a standalone Windows starter and matching source once, then tests
those exact bytes in ordinary and space-containing installation paths. Existing
workspace checks retain their real starter analysis and workflow interactions;
the focused library gate covers category navigation and filtering. Gate code
must read control 104 as a TreeView without changing unrelated ListView tests.

Live Full downloads, Ensembl downloads and upgrades are outside this layout
change's candidate gate. Prior passes for those features apply only to their
recorded artifacts. This UI work does not resolve the separate tester-machine
bridge/security investigation or establish managed-PC approval.
