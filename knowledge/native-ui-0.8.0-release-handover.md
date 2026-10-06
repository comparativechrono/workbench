# Native Workbench 0.8.0 release handover

Recorded **2026-10-06**. The user explicitly accepted the latest tested 0.8.0
candidate and authorized publication. This is user-reported acceptance of the
candidate, separate from the automated evidence below. It supersedes the
previous pending tester-confirmation status. **Publication is pending** at this
checkpoint; 0.7.0 remains the published application.

## Accepted source and immutable candidate

Promote the exact archives built from
`b3928ca6a29d22b5f010a303658c2e19c24324da`, validated in
[run 37453380541](https://github.com/comparativechrono/workbench/actions/runs/37453380541).
The [candidate bundle](https://github.com/comparativechrono/workbench/actions/runs/37453380541/artifacts/11408021439)
is artifact **11408021439**, 75,599,305 bytes, SHA-256
`234688eabc01315aceba6fd588094bc7bf2263670766d0bdc9d088f8f0c735c1`.
Its recorded expiry is **2026-11-05T10:59:55Z**; a temporary CI artifact is not a
durable release download.

| Accepted archive | Bytes | SHA-256 |
| --- | ---: | --- |
| `native-workbench-0.8.0-starter-windows.zip` | 16,948,940 | `df001a80033ff8e834045ec683c79672e0efdbd4880fb89fca8bf8c36d830fdc` |
| `native-workbench-0.8.0-update-from-0.6.0.zip` | 12,897,242 | `3dd146267b9a8300ba957c84914bc324ea537c05b09268b48381ae6a4d530e96` |
| `native-workbench-0.8.0-source.zip` | 46,243,835 | `c2590379b45d313acbcd5bbc41344b288aa6ad159804bf06dcbdcc9726adb22f` |

The packaged `NativeWorkbench.exe` SHA-256 is
`e32fc3e5acb42766641a822f01835430b3312b84c3174bd282fe2a50ef6f9d71`.
Candidate recovery verified all three ZIP CRCs, build provenance, 68 core
inventory entries, 143 unchanged starter-pack entries, 15 packaged workspace
source copies and 14 relevant source files. The
[scroll/candidate ledger](evidence/native-workflow-0.8.0-scroll-2026-10-06.json)
retains exact report and capture hashes and earlier failures.

The release workflow is to promote these accepted bytes, not rebuild them.
Later handover and publication records remain separate from the source
companion's creation-time snapshot. Do not replace an archive to make its
historical pending statements appear current. Published 0.7.0 application and
tool-pack bytes remain unchanged.

## What the accepted candidate passed

All five jobs in run 37453380541 passed. Evidence is tied to the accepted
archives, not inferred from the planned release tag:

- **82 source checks** passed in Linux CI with no failures or skips.
- Each ordinary and space-containing Windows path passed **32 workspace checks**
  (8 host, 2 scientific and 22 GUI) and **8 References/update checks**, with no
  failures or skips. Native minimap2-to-SAMtools execution preserved 202 paired
  alignment records and produced sorted BAM. Both paths retain 28 verified
  workspace/References captures.
- The nested-output regression ran the full five-stage starter pipeline with
  long-path policy disabled in disposable CI. All 7 core checks passed; all 20
  pipeline output hashes were independently checked, including 19 paths over
  260 characters, up to 279. The expected homozygous **starter:1351 G>A, GT 1/1**
  result and real BAM were retained. The prior missing-output failure was
  reproduced separately, and the original CI policy was restored.
- Three native panels passed temporal and precision-wheel checks at 96 DPI on
  Windows Server 2022/private Python 3.13.16: 960 sampled desktop frames, zero
  unexpected static-text/background frames, all 300 requested endpoint
  transitions observed, and all 18 precision-wheel cases passed.
- Native updater coverage is **0.6.0 to 0.8.0**. It preserved all 187 existing
  files, repeated idempotently, verified 68 target core files and reopened
  offline. No 0.7.0-to-0.8.0 updater is supplied or claimed.

The user had already confirmed the nested-output pipeline fix. The subsequent
acceptance covers the latest reviewed candidate and authorizes publication;
no additional machine, display model, DPI or physical input-device measurements
are inferred from that acceptance.

## Limits retained after acceptance

The user's visual flashing was **not reproduced in CI**: the prior package also
had zero unexpected frames across the same 960 samples. Six old precision-wheel
cases did fail and now pass; that movement defect is distinct from the visual
flashing report. Sampling at 27.16–31.80 observed frames/second masks edit/button
regions and cannot exclude shorter flashes between samples. Earlier settled
pixel comparisons were not temporal observations.

Native coverage does not establish every physical trackpad, high-DPI or
multiple-monitor configuration, native folder-picker interaction, optional-pack
long path or institutional deployment. It is research/teaching validation, not
clinical validation. Accepted user feedback does not widen those automated
claims. See the [native interface guide](native-ui.md) for the workflow and
input contracts.

## Publication checkpoint

Publication is authorized but not yet recorded as complete. The intended
identity is **app-v0.8.0**, a development prerelease consistent with 0.7.0. A
narrow Actions promotion will recover and verify the pinned accepted bundle,
publish its unchanged archives with matching provenance/evidence and checksums,
and verify the final public downloads.

Record the actual release tag/commit, publication time, final download URLs,
asset sizes/hashes, retained evidence locations and public verification after
publication succeeds. Keep the accepted candidate run distinct from any later
native execution against final release URLs; publication itself is not a new
native test. Update the current-state/index/inventory at the verified completion
level without altering dated reports or historical candidate objects.
