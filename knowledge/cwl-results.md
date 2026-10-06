# CWL results, dependency routing and application icon

**Development checkpoint: 2026-10-06.** Branch `feature/cwl-dag-icon` targets
**0.9.0**. This is source under development, not a published release or an
exact-package Windows pass. Candidate commit, archive hashes, CI run and final
evidence are **pending**. Published 0.8.0 artifacts, pack versions and their
dated evidence remain unchanged.

## The result's executable workflow

Newly prepared analyses write **`workflow.cwl`** beside `plan.json`, `graph.json`,
`pipeline.svg`, methods and execution records. This is one packed **CWL v1.2
document encoded as JSON**: a `#main` Workflow plus its CommandLineTool processes
in `$graph`. It contains the actual frozen dependencies, named file roles,
parameters and pack operations used by this analysis. It is not a generic
template inferred from tool names or a substitute for the detailed result files.

Shared producers, branches, paired-read roles, scalar inputs and ordered
multi-file inputs remain explicit CWL bindings. Each operation exposes its
declared outputs. Parameter defaults retain the exact CLI strings from the
frozen plan. The exporter preserves command argument arrays, copy operations
and binary pipes rather than guessing a different upstream command interface.

The `nw:` namespace retains Workbench-specific evidence:

| Export information | Meaning |
| --- | --- |
| `nw:planSha256`, `nw:runId`, `nw:created` | Identity of the original frozen plan/run. |
| `nw:operation`, `nw:parameters` | Exact frozen operation declarations, executable versions, pack/manifest pins and parameters. |
| `nw:source`, `nw:port`, `nw:references` | Original file identities/hashes, semantic roles and state, and frozen reference provenance. |
| `nw:execution` | Original status and outcome record; planned, running, failed or cancelled work is not labelled successful. |
| `nw:scheduler` | The original Workbench scheduling policy, recorded as provenance. |

Complex extension values are literal JSON strings so schema loaders do not
reinterpret Workbench fields such as `id`, `type` and `path`. Decode those values
as JSON when inspecting the complete evidence. `nw:execution` keeps a directly
readable status and an opaque `recordJson` with the detailed original outcome.

Preparation binds the export's definition SHA-256 into `plan.json`. Only the
reciprocal plan hash and changing original-run outcome are excluded from that
definition digest. Workbench checks the export against the frozen plan before
native execution. It updates the original outcome when execution starts and
finishes, without rediscovering commands or rereading a changed pack manifest,
and records the resulting CWL file SHA-256 in `run.json`. A later independent
CWL execution does not rewrite the original Workbench run record or turn its
historical outcome into proof of a new successful analysis.

## Running outside Workbench

Each CommandLineTool embeds an independent **Python 3.10+ standard-library
runner**. It imports no Workbench modules. External execution requires a
compatible CWL v1.2 engine, Python 3.10+, the input data, and the matching tool
pack directories. These are requirements for rerunning the exported file
outside the app; normal Native Workbench operation still uses its bundled
private runtime and needs no system Python, CWL engine, browser, Docker or WSL.

For an environment that already supplies those prerequisites, the document's
basic invocation is:

```sh
cwltool --no-container workflow.cwl
```

The workflow input `nw_python` defaults to `python3`; bind it to a different
Python executable when required by the external environment. CWL job JSON/YAML
can rebind the named file, directory and parameter inputs. Their defaults are
the original local `file:` URIs, not embedded datasets. Packs, private tool
runtimes and reference databases are not downloaded or bundled into the CWL
document. Retain the original pack folder layout, or rebind the corresponding
Directory inputs when moving the workflow.

The runner checks the pack manifest, every declared asset and each selected
original executable against its pinned SHA-256. Declared private-runtime assets
are included in those checks. Optional `exe_*` File inputs explicitly allow a
compatible replacement executable; that override deliberately changes executable
identity, so matching scientific behavior needs its own evidence. Manifest and
asset pins still apply. SoftwareRequirement hints describe versions; they do
not install software.

Original input hashes remain historical provenance. They do **not** reject
intentionally rebound data, or prove that the same path still contained the
original bytes before an external rerun. The independent runner hashes its
currently bound inputs and produced outputs and checks that they remain
unchanged during the operation. Keep those distinct from the original run's
hashes. Reference/resource descriptors may point to additional files outside
their own File input; those resources must remain available or be relocated
consistently. CWL cannot discover every dependency inside an arbitrary descriptor.

Windows x86-64 executables and private runtimes do not become Linux/macOS
binaries through CWL export. Use a suitable execution environment or explicitly
bind compatible software. CWL File typing and the embedded command runner do
not reproduce Workbench's biological preflight, reference/header checks,
Windows Job Object ownership, cancellation behavior or scheduler. A CWL engine
may schedule independent branches differently. The tools declare no network
access and no containers, but that declaration is not an operating-system
security sandbox. Tool commands remain trusted native code.

## Diagram and icon changes

The saved `pipeline.svg` and native workflow canvas use orthogonal dependency
routes around padded cards. Routes retain named output/input attachment points,
including skip-rank dependencies and fan-out/fan-in. Crossing/overlap penalties
help distinguish independent edges; true fan-out can share its common trunk.
This changes drawing geometry, not biological compatibility, graph dependencies,
execution order, pack versions or saved pins. It does not promise that arbitrary
manually overlapping cards can always be routed or that every edge crossing
can be eliminated.

For graphs above 64 cards, routes retain card avoidance but omit the extra
cosmetic edge-separation search to bound routing work.

The native canvas routes between left/right typed sockets in user-positioned
cards; the saved SVG uses a separate top-to-bottom rank layout and named port
slots. Saved diagrams do not copy manual canvas positions. An obscured native
socket has no unsafe straight-line fallback: the canvas asks the user to move
overlapping cards apart. Crossings can remain even when no line crosses a card.

The application artwork is the repository SVG
[`desktop/assets/native-workbench.svg`](../desktop/assets/native-workbench.svg).
[`scripts/build_app_icon.py`](../scripts/build_app_icon.py) derives a native ICO
with nine resolutions (16 through 256 pixels) using the standard library and a
bounded renderer for the SVG's supported geometric primitives. Unsupported
artwork fails the build rather than silently changing the rendering. Native
resources use the generated ICO; the app does not require an SVG renderer at
runtime. Native resource loading and displayed large/small icons require their
own packaged Windows check, separate from inspecting the SVG or ICO structure.

## Validation checkpoint

Source tests and exact packaged CI evidence are being assembled. **No new pass
count, native run identity or candidate download is asserted here yet.** The
development gate is intended to distinguish:

- Export/schema contracts and independent `cwltool` validation/execution of
  controlled fixtures on the recorded host platform.
- Native Workbench result creation, frozen outcome/hash binding, native pack
  execution and replay of the exported standalone runner. Runner replay on
  Windows is not execution through a Windows CWL engine.
- SVG/native edge geometry, interaction regressions and actual packaged icon
  resources/class icons.
- Existing workspace, References and data-preserving updater regressions.

Record the exact source commit, candidate archive hashes, platform, validator
version, passed/failed/skipped checks and reviewed native captures after the gate
finishes. Preserve failures, missing-prerequisite skips and original release
evidence. Neither a valid CWL document nor one controlled rerun establishes
every tool's cross-platform equivalence or a changed analysis's scientific
validity.
