# Reference discovery release handover

Resume audit: **2026-10-05**. Target: **Native Workbench 0.7.0**. Status at this
checkpoint: existing source fixes are present; a rebuilt candidate, native
Windows acceptance and the final release remain pending. This record does not
claim that packaging or cross-compilation establishes Windows execution.

## Recovered repository and release state

The repository is [comparativechrono/workbench](https://github.com/comparativechrono/workbench).
The resumed checkout was clean `main` at
`5338853ba3b69438fc36c1b9dcd3ad89d6bbcde4`. Work continues on
`release/reference-0.7.0-completion`.

| Record | Recovered identity/status |
| --- | --- |
| Published application baseline | [app-v0.6.0](https://github.com/comparativechrono/workbench/releases/tag/app-v0.6.0); its dated evidence and the 32-pack inventory remain unchanged |
| Existing candidate | [app-v0.7.0-rc1](https://github.com/comparativechrono/workbench/releases/tag/app-v0.7.0-rc1), commit `8ad25c71ec13d2c06a670b59a2cc13ca84a50ac9` |
| Candidate starter SHA-256 | `8314887d482184afac1b196f4a19d023d5abf2584dba6cedcb63a2283ce5e705` |
| Candidate 0.6.0-to-0.7.0 updater SHA-256 | `49b50acbb8c89a706fb99963f63f1fc87c008dcc162b82c86f44976739116496` |
| Final release lookup | [Exact app-v0.7.0 API lookup](https://api.github.com/repos/comparativechrono/workbench/releases/tags/app-v0.7.0) returned 404 during the resume audit |
| Last historical Windows run | [37295599791](https://github.com/comparativechrono/workbench/actions/runs/37295599791), workflow source `9543ae5030ee0ec42e404d251b67b6b1e1af4de6`, failed GUI gate |
| Existing source corrections | `b9d0ee7f16f675d0c42d77d7a093530ca052d09b` changes layout and tab automation; `5338853ba3b69438fc36c1b9dcd3ad89d6bbcde4` clarifies validation scope |

The candidate predates those corrections. No workflow run for either corrected
commit was found at the resume audit. Preserve rc1 bytes and its failed reports;
the next candidate needs its own immutable release identity.

## Missing interface finding recovered

The retained rc1 artifact's `gui-events.jsonl` records the References details
control ending at screen y=616, while the destination field, Choose folder and
Download selected controls begin at y=601. The **15-pixel overlap** is a measured
native layout defect. The [retained diagnosis](evidence/reference-resume-ui-diagnosis-2026-10-05.json)
contains the selected control bounds, source-file hash and originating artifact
identity (artifact 11337734019 from run 37295599791).

That same historical run then timed out on `SendMessageTimeoutW` while sending
`WM_KEYDOWN`/right-arrow to the native tab control (`winerror=1460`). This is an
observed automation failure; it alone does not prove the same failure occurs
for a person clicking the tab. The [original diagnostic report](evidence/reference-candidate-rc1-gui-diagnostic-2026-10-05.json)
retains its failure, traceback and exact candidate hashes.

Existing commit `b9d0ee7` reserves the details-panel height and gaps before sizing
the online lists. Its gate waits for the local library, posts tab keys to the UI
thread, and checks independently observed control geometry at normal/minimum
sizes and on the Downloaded tab. `5338853` states the measured scope. These are
source corrections awaiting a new packaged native run, not completed acceptance.

## What historical Windows evidence actually establishes

Run 37295599791 completed seven backend/native CLI checks in each ordinary and
space-containing path before the GUI failure:

1. Live release-pinned yeast discovery found genome, GTF, cDNA, ncRNA and protein.
2. Cancellation after transferred bytes removed its partial download and
   published no ready reference.
3. All five downloads were expanded atomically and their compressed/expanded
   hashes matched independently pinned identities and receipts.
4. A separate socket-denied host reopened the local library, bound a compatible
   input and generated reference-aware methods.
5. Offline native SAMtools indexed all 17 yeast contigs while preserving the
   reference, frozen identity and completed methods.
6. Application and starter-pack integrity checks passed after reference use.
7. The native updater CLI upgraded the exact 0.6.0 starter to the 0.7.0 candidate,
   then accepted an idempotent repeat and reopened preserved data offline.

The truncated phrase “0.6.0 update” therefore referred to **upgrading from 0.6.0
to 0.7.0**. The updater ran with its private interpreter. Its report records 187
existing preserved files, no changed files, and only the expected
`user-data/session.lock` addition. Installed optional packs and exact saved pins,
reference files/library and results were retained. The updater's native folder
picker was **not** exercised by that CLI check.

These are recovered prior results tied to rc1 bytes. The overall Windows gate
failed, so they must not be counted as full application or GUI acceptance.

## Checks performed during this resume

The [fresh source report](evidence/reference-resume-source-checks-2026-10-05.json)
and [unchanged test log](evidence/reference-resume-source-checks-2026-10-05.txt)
record Linux/Python 3.12.14 checks at source
`5338853ba3b69438fc36c1b9dcd3ad89d6bbcde4`:

| Suite | Passed |
| --- | ---: |
| Reference provider | 17 |
| Reference manager | 25 |
| Reference provenance | 5 |
| Reference service | 10 |
| Desktop host | 12 |
| Split packaging | 8 |
| Core updater | 16 |
| **Total** | **93** |

The current geometry regression gate also rejected the independently captured
rc1 bounds with the expected negative 15-pixel gap; that confirms it detects
the original defect, without claiming corrected native layout success. The
[build record](evidence/reference-resume-build-2026-10-05.json) retains the three
successful strict cross-builds and output hashes; native execution remains pending.

There were zero failures, errors or skips in the 93 source tests. These are deterministic source
contracts, with no fresh live-network, native Windows GUI or scientific
execution claim. The report also compared all 15 runtime hashes in the
[historical 139-test report](evidence/reference-source-contracts-2026-10-05.json)
against the resumed source; all match. The 139 tests remain historical evidence,
not an additional 139 tests rerun in this session.

The [fresh build record](evidence/reference-resume-build-2026-10-05.json)
records verified baseline/compiler downloads, all 65 baseline core files, and
three successful strict native cross-builds. The current geometry regression
gate also rejects the recovered rc1 bounds with the expected 15-pixel overlap.
These are build/static and regression-sensitivity checks, not new Windows
execution.

## Remaining release gates

1. Build and package the corrected desktop, bridge, updater and matching source
   companion from a recorded source commit, preserving the exact 0.6.0 baseline
   and starter-pack bytes. Record compiler/input/output hashes.
2. Publish a new diagnostic candidate without replacing rc1. Dispatch
   `native-reference-check.yml` against its exact starter and updater hashes.
3. Inspect both ordinary and space-containing Windows reports and captures.
   Require download/cancellation/integrity, typed offline reuse/provenance,
   migration preservation and the corrected References layout/tab gate to pass.
   Preserve failures and fix only the implicated behavior if another issue is
   found. Do not treat unavailable native checks as passes.
4. Freeze/publish the final `app-v0.7.0` assets through the established workflow,
   independently download/re-hash them, run the exact-final native gate, and
   attach separate final evidence. Update the current-state and inventory only
   to the completion level those checks establish.

The gate's limits remain explicit: automated Win32 interactions and captured
geometry do not establish broad human usability, all high-DPI/multi-monitor
setups, Unicode/long paths, institutional proxies or human-genome performance.
Scope stays on reference discovery/download; the signed pack catalogue is a
separate project item.
