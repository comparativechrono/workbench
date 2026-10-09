# Curated workflows and results: 0.16.0 handover

Status on 2026-10-09: **implementation and validation in progress; unpublished**.
Do not infer completion from prior candidate evidence.

The verified base is `feature/reference-management` at
`f45622f8915a3fa80c0904fcd97c216e0b5980f3`, in
[draft PR #10](https://github.com/comparativechrono/workbench/pull/10).
The preceding recovery work remains in
[draft PR #9](https://github.com/comparativechrono/workbench/pull/9).
Both were open, draft and unmerged when this set began. The remote branches and
clean checkout contained no persisted curated-workflows/results implementation.
Personal-context retrieval was unavailable, so the repository and supplied
handover are the retained sources of prior intent.

The current set is saved in [draft PR #11](https://github.com/comparativechrono/workbench/pull/11).
The first exact candidate, `1226947256e8d31124a45227d22933c5d4a6b08e`, was
rejected in [run 37938879718](https://github.com/comparativechrono/workbench/actions/runs/37938879718).
Its [source record](evidence/curated-workflows-results-0.16.0-initial-source-2026-10-09.json)
contains 469 CI source passes and four explicit skips. The
[independent audit](evidence/curated-workflows-results-0.16.0-initial-archive-audit-2026-10-09.json)
verified 728 exact-commit source files, 87 core files, 33 runtime modules and
unchanged published pack/private-runtime/profile/trust bytes. It retains a
rejected incomplete local transport download before the successful redownload.

Both [Windows paths](evidence/curated-workflows-results-0.16.0-initial-windows-2026-10-09.json)
failed the new summaries: the reader compared Windows path-stat creation time
against handle-fstat change time and misclassified unchanged files. The fix
retains device/inode/size/modification-time cross-checks and compares creation/
change times only within the same API before and after reading. Five new
regressions include stable timestamp divergence and actual concurrent content
mutation; 26 summary and six service checks pass locally after the correction.

The live-reference validator also rejected the new version because its allowlist
ended at 0.15.0; that narrow validator correction does not itself establish a
live-reference pass. Other configured native gates passed, but the Windows source
step stopped at the failed summary suite and the new GUI gate was not reached.
The next candidate must rebuild and rerun the exact Windows package, retain failed
attempts, audit its archives and review its new captures. Earlier successes do
not apply to the changed package.

Work is on `feature/curated-workflows-results`. No version decision for this set
was saved; **0.16.0** distinguishes the new implementation from the frozen
reference-management 0.15.0 package. Published **0.11.0** remains unchanged.
See the [feature contract](curated-workflows-results.md) for scope and interfaces.

## Second attempted candidate

`23cf175cd03baededcc5a97ea597f55f68d5c9ae`, built in
[run 37940096315](https://github.com/comparativechrono/workbench/actions/runs/37940096315),
passed 474 CI source tests with four Windows-only skips. Both Windows paths passed
the two curated scientific workflows, known answers, measured summaries, search,
persistence, changed-output rejection, missing dependencies and actual input-failure
guidance. Native catalogue initialization still threw `Expected a JSON array`
before a catalogue reply arrived; this candidate is also rejected. The native
fix must tolerate absent rows during loading and empty selections in both dialogs.
The [second independent archive audit](evidence/curated-workflows-results-0.16.0-second-archive-audit-2026-10-09.json) passed.

## Evidence to complete before delivery

- Exact tested source commit and corresponding source/Starter archive hashes.
- Relevant source checks, with failed attempts and skips retained.
- Packaged Windows scientific, native UI and regression gates in ordinary and
  space-containing paths; review the new screenshots.
- Independent downloaded archive/source correspondence and preserved pack,
  private-runtime, production catalogue/profile/trust identities.
- Draft PR and temporary review download links.

Representative-PC/high-DPI acceptance, scientific Linux CWL validation,
realistic Windows–Linux benchmarks, signing/institutional deployment and
release/updater validation remain separate outstanding work. No merge or release
is authorized by this request.
