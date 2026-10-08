# Readiness, performance records and diagnostic export

Development snapshot: **2026-10-08**. Target application **0.12.0**, unpublished,
on `feature/readiness-performance`, based on
`82729febfcfab1c43bd9c9798d03c80f595545cb`. Published 0.11.0 and its accepted
archives remain unchanged. The owner accepted the broader
[development programme](roadmap.md); this is the first bounded milestone.
No packaged Windows evidence is recorded for this milestone at this snapshot.
Add exact build/run identities and results when available; do not transfer the
0.11.0 passes to changed application bytes.

## Purpose and scope

Users previously reported an installation check passing while a selected
analysis failed. The new readiness review explains which checks have actually
run and which remain necessary. Local measurements provide a foundation for
the proposed Windows–Linux research programme. An explicit diagnostic preview
and ZIP export allow users to share bounded deployment/run information without
Workbench gathering logs or scientific data.

This milestone does not implement batch samples, a durable queue, restart,
index reuse or parallel scheduling. Independent graph branches still execute
sequentially. These are accepted later work with separate contracts and gates.
The current measurements are not a completed realistic-workload benchmark or
a performance-parity claim.

## Readiness and planned methods

`workspace/readiness.py` extends the existing engine review through
`Workbench.review(graph, output_folder)`. Legacy graph validation, errors,
warnings, methods and validity remain available; newly discovered readiness
failures also block the existing Run path. The native review dialog shows
readiness checks before planned methods and explains that installation success
does not guarantee analysis success.

The structured `readiness` record has schema 1, a status, a summary, individual
checks, selected-output measurements and resource requirements. Check codes are
fixed application identifiers; labels/messages may contain local context and
are **not** diagnostic-export fields.

| Check | What is established at review time |
| --- | --- |
| `graph_inputs` | Existing connection, parameter, installed-pin and initial input-signature validation. |
| `pack_manifests` | Selected manifest/schema identities are checked; this is not a full executable inventory check or a successful tool launch. |
| `output_location` | An existing absolute output folder is selected without symlink/junction traversal. Review does not create it. |
| `output_write` | A unique temporary probe is created, written, flushed and removed. Existing outputs are untouched. |
| `output_space` | Available storage is measured when possible. Positive free space does not prove the analysis will fit. |
| `output_path_policy` | The destination and declared output paths meet the selected tools' recorded path rules. |
| `resource_requirements` | Memory, temporary-storage and output-size requirements remain unknown; no estimate is invented. |
| `input_integrity` | Full dataset/reference hashing and runner executable checks are deferred to preparation/execution. |
| `scientific_preflight` | Detailed tool-specific biological/file compatibility remains required before relevant steps. |
| `tool_execution` | No scientific executable is launched by readiness review; successful execution is not claimed. |

Check statuses are `passed`, `failed`, `warning`, `not_checked` and `deferred`.
Overall status is `blocked`, `incomplete` or `ready_for_preparation`.
`ready_for_preparation` deliberately means that preparation may proceed; it is
not a certificate of scientific validity or sufficient resources. Omitting the
output folder leaves readiness incomplete. The engine continues to recheck
integrity and scientific compatibility at its existing boundaries.

## Local performance record

`workspace/performance.py` and `workspace/engine.py` write `performance.json`
inside the run result folder. Its schema-1 kind is
`native-workbench-performance`. The record binds application version, run/plan
identity, selected tool/pack pins, numeric thread settings, system configuration
and input sizes/hashes to explicitly scoped measurements. It is a local result
artifact; it is not automatically attached to diagnostics or uploaded.

The final `run.json` records the performance file's SHA-256. Performance is
updated during execution, including partial measurements when a phase fails
or is cancelled. Missing counters and unrun phases are distinguishable from
measured zero. Preparation and execution use a monotonic clock.

| Measurement | Interpretation |
| --- | --- |
| Preparation | Validation, freezing, input hashing, reference provenance and definition/export phases. The declared total excludes later frozen-plan/result companion writes. |
| Step phases | Input verification, scientific preflight, backend invocation, output validation and hashing. |
| Backend invocation | Includes the bridge, native checks, command stages and result collection; it is not pure scientific-compute time. |
| Native command stages | Command/pipeline wall time, user/kernel CPU, process counts and peak Windows Job Object committed memory when available. Copy and built-in operations do not invent process counters. |
| Execution total | Inclusive engine execution through methods/CWL finalization; excludes the final performance and run-record writes. Inclusive totals overlap phase measurements and must not be added to them. |

Native measurements come from the already-owned Windows Job Object. The
snapshot is taken before the job closes; live descendants or unavailable
counters produce explicit partial/unavailable coverage. Instrumentation must
preserve existing launch, cancellation and cleanup behaviour. The resource
contract does not add a second execution backend or alter tool algorithms.

`peak_job_memory_bytes` measures **committed memory**, not working set or Linux
resident-set size. Do not sum peaks across stages or present unlike counters as
equivalent Windows–Linux measurements. Disk I/O bytes, peak temporary-storage
usage, system load and actual thread utilisation are not measured in this
milestone. Hardware model, storage configuration, external workload control,
repeats and matched scientific truth remain part of the later benchmark protocol.

## Reviewable local diagnostic export

The native **View → Review diagnostics…** action opens a read-only report.
The user may save it to the selected output folder with **Save diagnostic ZIP**.
The host does not upload or send anything. Reviewing a historical run does not
attach the unrelated last workspace-readiness review. For the workspace, counts
describe its most recent readiness review and may precede later edits; exporting
diagnostics does not rerun readiness or certify the currently edited graph.

`workspace/diagnostics.py` exposes:

```python
report = build_report(app_root, catalog, run=None, readiness=None)
text = preview_text(report)
archive_path = export_report(report, destination_parent)
```

`build_report` reads only the supplied structured objects and a small general
system inventory; it does not enumerate `app_root`, user folders or results.
The report allows application/pack versions, manifest identities, a fixed
public pack-ID vocabulary, broad OS/architecture/CPU/RAM information, run/step
status and readiness status counts. Other pack identifiers become `third-party`.
These labels and identities do not authenticate a publisher or prove installation
integrity. Unknown values remain unknown.

Excluded fields include scientific-file contents and hashes, sample/workflow
names, arbitrary identifiers or labels, filenames/paths, logs, commands,
parameters, settings, raw exceptions, environment variables, network addresses,
usernames and hostnames. Counts and record arrays are bounded; omissions are
reported. This is intentionally not a complete troubleshooting dump, and its
system/software inventory still deserves review before sharing.

`Workbench.review_diagnostics` keeps an immutable report snapshot behind an
opaque token. It retains at most four previews and expires them after 15 minutes.
`save_diagnostics` accepts the previously issued token, saves that exact snapshot
and consumes the token after success. Reopening the dialog creates a new review;
unrelated subsequent application changes cannot silently alter approved bytes.

The uniquely named `native-workbench-diagnostics-<random-id>.zip` contains:

- `report.json`: exact canonical UTF-8 JSON shown for review, with a trailing
  newline;
- `README.txt`: static inclusion/exclusion and interpretation limits;
- `SHA256SUMS.txt`: SHA-256 of the other two members, not a signature.

Export validates the full allowlisted schema, uses fixed internal names and
never overwrites an existing file. The selected destination must already exist
and be absolute. Export rejects symlink/junction destinations and
pins directory traversal while creating the archive. Windows I/O uses the
existing extended-path boundary helpers while displayed paths stay ordinary.
Failed writes remove the newly created partial archive. No encryption is added.

## Source map and validation handover

| Files | Responsibility |
| --- | --- |
| `workspace/readiness.py` | Bounded review-time preparation checks and explicit deferred checks. |
| `workspace/performance.py`, `workspace/engine.py` | Scoped monotonic measurements and hash-bound local performance sidecar. |
| `desktop/process_performance.h`, runner/pipeline/workflow sources | Native Job Object counters without changing process ownership. |
| `workspace/diagnostics.py` | Privacy projection, canonical preview and safe local ZIP creation. |
| `workspace/service.py`, `workspace/desktop_host.py` | Readiness integration and explicit diagnostic snapshot/token lifecycle. |
| `desktop/desktop_workspace.cpp` | Native readiness/methods review and diagnostic review/save interaction. |

Focused source checks include:

```sh
python3 workspace/tests/test_readiness.py
python3 workspace/tests/test_performance.py
python3 workspace/tests/test_diagnostics.py
python3 workspace/tests/test_readiness_service.py
```

The diagnostics source check initially passed eight Linux cases with two
explicitly unrun Windows cases (junction rejection and a destination longer
than 300 characters). The Windows suite has a separately skipped POSIX symlink
case. These are platform distinctions, not interchangeable passes. An independent
review identified an ordinary-path Windows I/O regression risk; export was
corrected to use the established extended-path helpers before packaging.
Subsequent validation should record its exact source and current test counts.

The native resource fixture is `tests/windows_performance.cpp`, built with
`tests/build_windows_performance.sh`. Its execution on Windows, packaged
application checks and native dialog interactions require separate evidence.
Cross-compilation alone is not a native pass. Root release/build records should
retain failures, unavailable counters and all ordinary/spaced-path results.

Before a release, validate the exact candidate's successful scientific workflow,
blocked readiness, failed/cancelled stages, resource coverage and result/CWL
preservation; demonstrate diagnostic privacy, exact preview/export matching,
token handling and safe destinations through the native/host path. Reuse valid
historical evidence only for unchanged artefacts and explicitly stated scopes.
Representative physical-machine, high-DPI, keyboard, trackpad and institutional
acceptance remains separate from hosted Windows checks.

## Current source evidence, 2026-10-08

The consolidated [source record](evidence/readiness-performance-0.12.0-source-2026-10-08.json) contains **151 passed, three skipped, no failed suites** across 15 focused/regression suites. Two skips require Windows diagnostic paths; one requires optional independent `cwltool`. The desktop, bridge and 14-case process-accounting helper passed strict pinned cross-compilation. These are not Windows execution passes. Native candidate workflow execution remains pending.

Native stage wall time uses the existing `GetTickCount64` clock (typically 10–16 ms resolution), covering launch through the pre-cleanup snapshot. It excludes later hashing/reporting and remaining cleanup. CPU counter units of 100 ns do not promise that measurement accuracy.
