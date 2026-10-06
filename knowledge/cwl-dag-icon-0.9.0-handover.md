# CWL, DAG and icon candidate handover

**2026-10-06: exact candidate validated and accepted by the user; publication
authorized and in progress.** Work is on `feature/cwl-dag-icon` in
[PR #2](https://github.com/comparativechrono/workbench/pull/2). The user stated,
“Go ahead accept and release, the testers are happy with it.” This supersedes
pending tester review; the [acceptance record](evidence/cwl-dag-icon-0.9.0-acceptance-2026-10-06.json)
keeps user acceptance separate from automated checks. No 0.9.0 release has yet
been recorded. Published 0.8.0 and all tool-pack bytes remain unchanged. The [feature guide](cwl-results.md) describes the export contract and
external execution requirements.

## Exact candidate

Application source is **`beea34ab29f3e7cb9a7e79dbcfa11c89f40ee59d`**, packaged by
[run 37485987457](https://github.com/comparativechrono/workbench/actions/runs/37485987457).
The [candidate bundle](https://github.com/comparativechrono/workbench/actions/runs/37485987457/artifacts/11424165351)
is artifact **11424165351**, 75,880,943 bytes, SHA-256
`26f1f2070de5ffae4cdb219bd22579f22a3af943eab6e93048fa6e38ad041071`.
It was independently downloaded and hash-verified; this is a CI artifact,
not a published application release.

| Archive | Bytes | SHA-256 |
| --- | ---: | --- |
| `native-workbench-0.9.0-starter-windows.zip` | 17,002,821 | `c2661c144e073c4efdd190ffd186bacd9398b6413b81770d7a057c3947eecf02` |
| `native-workbench-0.9.0-source.zip` | 46,423,298 | `7bfc3802cad3b476300ae7075214e2c06ee320d987df66945ff0809cb3218824` |
| `native-workbench-0.9.0-update-from-0.6.0.zip` | 12,951,447 | `eed778882bed560e765c1f2c03d6473b2ea07f2b219e4bd81bff7297e67b177d` |

The [artifact audit](evidence/cwl-dag-icon-0.9.0-artifact-audit-2026-10-06.json)
verified ZIP CRCs, 497 source entries against the exact Git commit, 70 core
entries, 65 update entries and all 19 update blobs. All 143 starter-pack files
match the accepted 0.8.0 starter, and all 17 packaged Python modules match the
source companion. The native executable's nine icon frames match the ICO
regenerated from the exact SVG source. This resource inspection is separate
from native displayed-icon validation.

## Completed checks and retained failures

The [validation ledger](evidence/cwl-dag-icon-0.9.0-validation-2026-10-06.json)
binds the reports to the above archives. Initial run **37485987457 failed
overall**; it must not be described as a completed feature gate.

| Check | Recorded result |
| --- | --- |
| Linux source gate | 125 passed, zero failures/skips; stock `cwltool 3.3.20260925135507` validated and executed the controlled fixture. |
| Existing native workspace, each path | 32 passed. |
| References/update, each path | 9 passed, including nonempty reference-provenance CWL and 0.6.0-to-0.9.0 preservation. |
| Initial native feature gate, each path | 7 science/export/SVG checks passed; 1 GUI fixture check failed; zero skips. |
| Final focused native feature gate, each path | 9 passed, zero failures/skips; `nativeGUIValidated: true`. |
| Long-path native regression | 3 checks passed, zero failures/skips; full five-stage starter pipeline, all 20 output hashes checked with opt-in disabled and original policy restored. |

The ordinary and space-containing native cases use Windows Server 2022 and
private Python 3.13.16. Independently, six exact Windows-produced CWL documents
passed stock schema validation on Linux. Their original Windows paths were
unavailable there and produced location warnings; this is not execution of
those scientific workflows on Linux. Native replay of the embedded runner is
also distinct from invoking a Windows CWL engine.

The initial GUI fixture demanded a canvas width of 560 logical pixels, while
the hosted desktop supplied 457 at 96 DPI. It failed before the new connection
interactions. Validator commit `3352ef7` fitted the fixture to the actual viewport
without changing application bytes. Its focused
[run 37487450679](https://github.com/comparativechrono/workbench/actions/runs/37487450679)
then failed because it checked the wrong selected inspector; the retained
screenshot showed the connection. These are retained failed checks, not passes.

Validator **`a8c939a81ee6bdc0f3bb8f3682d4a415d768d9e8`** explicitly selects each
receiving card before inspecting its connection. Focused
[run 37488239616](https://github.com/comparativechrono/workbench/actions/runs/37488239616)
used the unchanged `beea34a` package and confirmed the intended connections and
native icons. Its normal-to-zoom capture interaction timed out, so the overall
GUI check still failed. Both normal captures were reviewed and showed clear
routes; that partial evidence did not close the full check.

Final validator **`bc972125814c1f24dca86391d0c5f240716a52f3`** passed focused
[run 37489208656](https://github.com/comparativechrono/workbench/actions/runs/37489208656)
against the same `beea34a` archives: **9 checks per path, zero failures/skips**,
both native GUI flags true. The final
[ordinary report](evidence/cwl-dag-icon-0.9.0-final-ordinary-native-results.json)
and [space-containing-path report](evidence/cwl-dag-icon-0.9.0-final-spaces-native-results.json)
retain the checks. All four normal (100%) and zoomed (83%) captures were reviewed
and showed clear cards, routes and arrowheads.

Geometry located the zoom button centre at `(582, 732)`, outside the hosted
work area of `1024 × 728`; that point hit `MSTaskListWClass`, the taskbar.
The final fixture therefore uses the native button's `BM_CLICK` command for
zoom capture only. This is not reported as a new physical-click pass. The
separate 32-check workspace gate already covers physical zoom-button clicks.
Real connection interactions and native icons remain checked in the focused
gate. No application bytes changed to repair these validator fixtures, and all
three earlier failed runs remain failed historical records.

## Remaining scope

User acceptance and release authorization are recorded above. Publication and
independent verification of public downloads remain outstanding. The accepted
candidate includes a tested updater for **0.6.0 only**. A separate 0.8.0-to-0.9.0
updater is being prepared against the unchanged accepted starter; its build and
native preservation checks remain pending. Independent CWL
execution needs a compatible engine, Python 3.10+, matching packs and data;
Windows binaries are not translated to another operating system. Optional
executable replacements and rebound data need their own scientific validation.
No rerun of all optional packs, broad physical-display survey or new temporal
scrolling acceptance is claimed. User acceptance does not broaden those automated
validation claims or establish publication before its completion.
