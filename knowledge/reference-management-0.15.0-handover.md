# Reference management: 0.15.0 handover

Status on 2026-10-08: **implementation complete; exact Windows validation pending; unpublished**.

The owner asked to implement the remaining accepted groups one at a time.
This first group covers resumable reference downloads, importing local references,
safe library relocation and an additional provider. See the
[feature contract](reference-management.md). The previous conditional release
request was not satisfied: the broader roadmap is not yet complete. This new
request authorizes development, not publication.

Work is on `feature/reference-management`, based on
`38917349449ce56a45d3e0f4f41b7d2a38621c6d` from the unmerged 0.14.0 review
branch. App version 0.15.0 separates this work from that frozen candidate.
Published 0.11.0, immutable pack bytes and production catalogue/profile/trust
remain unchanged. No merge, release or updater has been performed.

The [local source record](evidence/reference-management-0.15.0-local-source-2026-10-08.json)
has **422 passed, six skipped** across 28 suites. Four skips are Windows-only;
two need the external stock CWL runner, which the candidate workflow installs.
An initial local harness applied isolated mode to seven historical suites whose
helper imports require ordinary invocation; their import failures and successful
documented invocations are retained separately. No application change was used
to conceal those harness failures.

An independent critical audit reran 82 overlapping source checks, all passing.
It exposed and verified fixes for orphan checkpoint files, publication-before-
registration crash recovery, malformed pending IDs, cancellation boundaries and
NCBI annotation wording. Existing reference tests also exposed a run-startup
error path introduced by earlier resource-policy work; lifecycle checks now run
before graph interpretation and a missing graph gets a clear validation error.
The native desktop compiled with the pinned toolchain and strict warnings.
Final UI review also fixed stale import confirmation returning after form edits
and a server-list refresh; the native gate exercises edit, close/reopen and a
fresh explicit preview. One local strict-build attempt failed on an unknown
temporary object-file type; its identical retry passed. The cause was not
established, and the clean CI build remains required.

[Live Linux NCBI checks](evidence/reference-management-0.15.0-ncbi-linux-2026-10-08.json)
discovered and downloaded yeast `GCF_000146045.2` genome, GTF and protein files,
independently verifying upstream MD5, gzip integrity and compressed/expanded
SHA-256. The observed annotation was SGD R64-5-1, dated 2026-07-10. This is a
retrieved annotation snapshot, not an immutable assembly annotation release.

Exact packaged Windows execution and native screenshot review remain pending.
Existing 0.14.0 passes apply only to its named artifacts. Source tests, strict
cross-compilation and live Linux provider checks are not packaged Windows passes.

Remaining groups after this set include curated workflows/results improvements,
executable signing and institutional deployment, scientific Linux CWL profiles,
realistic Windows–Linux benchmarks and representative-machine acceptance.
Existing SDK templates, validators, signed catalogues and offline pack imports
are already present. Do not describe that entire developer toolkit as absent.
