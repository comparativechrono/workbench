# Reference release continuation

Reviewed 2026-10-05 from remote `main`
`5338853ba3b69438fc36c1b9dcd3ad89d6bbcde4`, on branch
`finish-reference-release`. This record distinguishes recovered evidence from
checks performed during the continuation. It is not a release acceptance claim.

## Recovered state

The live release audit found `app-v0.7.0-rc1` at source
`8ad25c71ec13d2c06a670b59a2cc13ca84a50ac9` and no final `app-v0.7.0` release.
RC1 remains an immutable diagnostic candidate. Its starter SHA-256 is
`8314887d482184afac1b196f4a19d023d5abf2584dba6cedcb63a2283ce5e705`.
It must not be promoted because it lacks the committed interface correction.

The missing interface finding was recovered from the retained native captures
and measured control bounds in
[Windows run 37295599791](https://github.com/comparativechrono/workbench/actions/runs/37295599791).
The References details panel overlapped the destination/download controls by
15 logical pixels at normal and minimum size. At normal size its bottom was
616, while the destination controls began at 601. The ordinary-path evidence
artifact (ID `11337734019`) was independently downloaded and checked against
SHA-256 `e76880d280ea002c3457f942c1ff5bb66eb2c5f2af5eefdd1d38e137a81f0692`;
both screenshots were inspected during this continuation.

The same run also exposed a separate GUI harness timeout: synchronously sending
`WM_KEYDOWN/VK_RIGHT` to the tab returned WinError 1460. Existing source commit
`b9d0ee7f16f675d0c42d77d7a093530ca052d09b` reserves a 12-pixel gap on each side
of the details panel, queues tab key input and asserts observed control geometry.
No Windows run after that correction existed at the audit. Source inspection is
not proof that the rebuilt executable passes.

The [retained RC1 report](evidence/reference-candidate-rc1-gui-diagnostic-2026-10-05.json)
records seven successful checks before its GUI failure: five live yeast products
and their compressed/expanded identities, cancellation cleanup, socket-denied
reuse and input binding, frozen methods, native SAMtools indexing of 17 contigs,
installation integrity and preserved-data migration. Both Windows paths failed
the overall GUI gate. These are historical results for RC1, not new executions.

The interrupted phrase "0.6.0 update" means **0.6.0 to 0.7.0**, using the exact
published 0.6.0 starter and RC1 updater
`49b50acbb8c89a706fb99963f63f1fc87c008dcc162b82c86f44976739116496`.
Its native CLI/private-interpreter test verified 68 target core files, preserved
187 existing files, repeated idempotently and reopened the preserved library
offline. Only the expected one-byte session lock was added. It did not exercise
the updater's native folder picker. This is separate from the older
0.5.4-to-0.6.0 Linux migration evidence.

## Checks performed during continuation

The [fresh source report](evidence/reference-source-contracts-resumed-2026-10-05.json)
records 139 passed, zero failures/errors/skips on Linux x86-64 / Python 3.12.14
at `5338853ba3b69438fc36c1b9dcd3ad89d6bbcde4`. All 15 runtime module hashes match
the earlier source evidence and remained unchanged during the run. It covers
reference provider/manager/service/provenance, host, pack contracts, packaging,
updater transactions and two explicit frontend network boundaries. Synthetic
source checks establish neither live downloads nor native Windows GUI behavior.

The exact 0.6.0 starter, source companion and pinned LLVM-MinGW 20260922 UCRT
toolchain were downloaded and SHA-256 checked against the development runbook.
Rebuild, new immutable candidate, exact Windows acceptance and final public
download verification remain separate gates. Published RC1 assets are unchanged.

All three native executables compiled successfully with the pinned toolchain and
the project's `-Werror` settings during continuation. PE inspection identifies
Windows x86-64 outputs; this is cross-compilation evidence only. The native gate
has been expanded to exercise actual search/discovery, checkboxes, cancellation,
downloads and compatible input assignment, in addition to measured geometry.
The measured geometry check rejected the original RC1 capture's -15-pixel gap.
The expanded GUI interactions require a new native execution before acceptance.

The first local candidate build at `7e928100dd243cdbb9809941f98dfa80a2e0ac02`
completed compilation and packaging, but failed publication readiness: an
unexpected, incomplete starter `.zip.partial` remained in the output directory
and was included by a permissive checksum glob. No assets were published from
that directory. The release driver now requires the exact intended output and
checksum sets, archive identities and CRCs before any upload. Retain the failed
local output as diagnostic evidence; do not silently remove the unexpected file
and call that original release set successful. The
[independent package audit](evidence/reference-local-package-readiness-failure-2026-10-05.json)
records the failed output set separately from the three valid intended ZIPs:
412 source files matched that commit, 143 starter-pack and 39 runtime files were
unchanged, and the updater's 13 operations exactly matched the core differences.

## Completion boundary

### Later live audit: independently published RC2

During this continuation, another writer created
`release/reference-0.7.0-completion` and published `app-v0.7.0-rc2` at
13:17:50Z from `19444e0f2a9c9981d87f033bd3b2b17f79878add`. That branch then
advanced to `456d1dbc17254ec9e6ccf0408525a9c6c4955357` to retain GUI failure
captures. These writes were not made by this continuation or its delegated
agents. Our `finish-reference-release` workflow
[37316644535](https://github.com/comparativechrono/workbench/actions/runs/37316644535)
refused to replace the existing RC2 before building or publishing; its Windows
job was skipped, not passed. It published no assets.

The independent RC2 runs
[37315901362](https://github.com/comparativechrono/workbench/actions/runs/37315901362)
and [37317100708](https://github.com/comparativechrono/workbench/actions/runs/37317100708)
both failed the GUI gate in ordinary and space paths. We downloaded, rehashed
and inspected the later diagnostic artifact `11348119558`, SHA-256
`c2c38a3c59a108469f0752bd1b6217763ef3232cab722b8b1e2cd76445b9ab94`.
The normal capture measures the corrected +12-pixel gap. It also records a
blocking modal, **Expected a JSON array**, with no populated library rows.
The [exact RC2 report](evidence/reference-rc2-windows-report-2026-10-05.json)
retains seven passing backend/native updater checks; the overall result is
failure. These new remote runs were inspected here, not launched by this turn.

Source diagnosis identifies two empty-state defects. Before requesting
`references/list`, `show_references()` refreshes controls; `reference_enabled()`
reads an absent `species` value as an array even though no row is selected.
Separately, a later successful species search clears discovery to null, while
the UI unconditionally iterates `discovery.files`. This branch now guards both
cases and adds a repeat-search assertion to the expanded native gate. The
desktop cross-compiles with the pinned toolchain and `-Werror`; this corrected
executable has **not** been packaged or executed on Windows. The original
RC1 tab timeout's cause remains unproved; queued input alone cannot establish
that an underlying modal was absent.

All five new publication-readiness regression tests pass. The
[live audit record](evidence/reference-concurrent-release-audit-2026-10-05.json)
keeps hashes, scope and remaining gates. Publication is paused pending
coordination with the independent remote writer. Preserve both branches and
immutable candidates; do not automatically overwrite RC2 or compete to publish
the next tag. No final `app-v0.7.0` existed at the latest audit.

The reference feature is not released as final 0.7.0 until a package containing
the layout correction passes its exact native gate in ordinary and space paths,
the captures and results are reviewed, and every final public asset is downloaded
and verified. Preserve final reports separately from source companions whose
creation-time status is pending. Record any unavailable GUI, folder-picker,
high-DPI, Unicode/long-path or institutional-network check explicitly.

### Latest coordination checkpoint

After preserving the RC2 diagnosis, the independent writer published
[RC3](https://github.com/comparativechrono/workbench/releases/tag/app-v0.7.0-rc3)
from `57d635370a1cd34dd1549aff95a2feba7faeeb74` at 13:37:17Z. Its release notes
claim both empty-state fixes; this continuation has not independently verified
those new package bytes. Native run
[37318450359](https://github.com/comparativechrono/workbench/actions/runs/37318450359)
was queued at inspection. It is pending, not passed. The
[metadata checkpoint](evidence/reference-rc3-coordination-checkpoint-2026-10-05.json)
records exact advertised identities. Further publication requires coordination
with that active writer; our corrections and expanded gate remain on
`finish-reference-release`. No completed final 0.7.0 is claimed.
