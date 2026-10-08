# Recovery, resources and portable projects: 0.14.0 handover

Status on 2026-10-08: **implementation complete; exact Windows validation in progress; unpublished**.
The owner requested the final accepted implementation tranche. This is not
authorization to merge or publish a release.

Development branch: `feature/recovery-projects`, based on
`9f5cd4c88634b4cab04cec66b9e43e93e1db0e17` from the unmerged 0.13.0 review
branch. Published 0.11.0 and production packs/profile/trust remain unchanged.
The [feature guide](recovery-projects.md) records contracts and scope.

[Draft PR #9](https://github.com/comparativechrono/workbench/pull/9) is stacked
on #8. The **initial** frozen application source is
`cd0ed848fd9d9c8728b0d83991511a348c13719e`, tree
`af1eda87edb7c91f19fbeff0d3ed95972fa712e9`, built in
[run 37840523641](https://github.com/comparativechrono/workbench/actions/runs/37840523641).

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Starter | 17,769,934 | `f5b347a1e379f48bd5b72950bc331f25be39a9764f6342ab066f5cb62bfe1837` |
| Matching source | 47,431,453 | `7f4394c485532815954cbebcb51f0902522af1521a2e48f04c32cb092f78bfc8` |
| Existing align 0.4.1 candidate pack | 575,862 | `3a08cf061f0b62c5502d1420115db3fcae2b04bf695ad3cfd1c3063de0fafa02` |

The [source gate](evidence/recovery-projects-0.14.0-source-2026-10-08.json)
passed **287 checks with four Windows-only skips**. This includes actual stock
`cwltool` replay of a relocated report-only project after deleting its original
inputs. It does not establish Linux scientific parity. Strict pinned native
compilation passed. The [archive audit](evidence/recovery-projects-0.14.0-archive-audit-2026-10-08.json)
verified 684 source files, 82 core files, 28 runtime Python modules and unchanged
143 published pack files, 39 private runtime files and production profile/trust.
Two incomplete local transport copies were rejected; new retrievals matched
complete official sizes/hashes and ZIP CRCs. Their cause is not established.

The [initial Windows record](evidence/recovery-projects-0.14.0-initial-windows-2026-10-08.json)
retains a **failed** run. In each path, existing workspace 32, library seven,
batch/index 11, readiness five and resource-accounting 14 checks passed, as did
independent pack import/science and three separately instrumented transport
checks. The new recovery gate stopped before a check passed: its validator
expected three steps instead of the Starter's four native steps plus a report.
The real review correctly offered four reuse decisions and report regeneration.
The isolated Windows source gate also stopped at a missing test-helper import.

Only validators and test imports are being corrected. The
[frozen recheck workflow](../.github/workflows/native-recovery-recheck.yml)
pins the same Starter and both executable hashes, refuses application/build
changes and records its separate validator commit. The corrected exact-native gate passed **12 checks per path** in
[run 37841697478](https://github.com/comparativechrono/workbench/actions/runs/37841697478).
A source-only follow-up confirmed physical scratch ownership but exposed
Windows short/long-path alias defects in portable metadata and one further
lexical-path test assumption. Independent screenshot reviews also found a
clipped export confirmation label and a queue capture taken before UI polling
showed completion. The [recheck record](evidence/recovery-projects-0.14.0-rechecks-2026-10-08.json)
retains these failed runs and separates the passing native feature gate.

The portable exporter now canonicalizes explicit file identities while retaining
raw graph aliases for metadata tokens; duplicate aliases and wrong hashes are
rejected. Two new regressions cover this. The native caption is shortened, and
the validator now waits for displayed queue completion and tests actual Windows
short-path project export. **These application changes require a new build and
exact-package validation; earlier passes are not transferred to changed bytes.**
The old frozen recheck workflow remains pinned to its historical archive and
must not be used to imply a pass for the rebuilt candidate.

Representative Windows machines, high-DPI/physical trackpad observations,
institutional approval, realistic Windows–Linux benchmarks and release/update
validation remain separate work. The accepted roadmap's further features are
not declared complete by this milestone.
