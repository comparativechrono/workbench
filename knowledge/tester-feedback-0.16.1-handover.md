# Tester-feedback revision of unpublished 0.16.1

Implementation checkpoint: **2026-10-09**. Work continues on
`fix/native-ui-0.16.1` in [draft PR #15](https://github.com/comparativechrono/workbench/pull/15),
from verified starting head `8cd3457745da52d38b5470c9ae917c8394ca46b0`.
The PR remains stacked on `feature/deployment-acceptance`, base
`f74d90229be6a78d6ad0c0076c54c04bb7e7cae2`, and unmerged draft
[PR #14](https://github.com/comparativechrono/workbench/pull/14).
Published **0.16.0**, `main` and all published assets remain unchanged.

This is a further revision of the unpublished **0.16.1** candidate, not a release.
Implementation is in progress. A new candidate commit, exact archives and their
validation evidence have not yet been recorded. No merge or publication is part
of this work.

## Feedback and intended changes

| Area | Revision contract | Required observations |
| --- | --- | --- |
| Run and polling | Remove redundant redraws during unchanged status polling and address the reported Run flashing. Retain meaningful state updates, mutation guards and command ordering. | Temporal captures around Run and repeated polling, with actual state changes still visible; no inference of zero flicker from a settled screenshot. |
| Tool categories | Preserve the viewport anchor when expanding a category and address the black flash on collapse. | Expansion/collapse at meaningful scroll positions, stable anchor behavior and temporal captures of the visible window. |
| Methods and preflight | Restore Methods as a separate action and remove the primary Readiness button. Keep Run preflight and its actionable validation. Do not add runtime or memory forecasts. | Native control visibility, Methods content, invalid-input blocking and valid Run behavior. |
| Samples | Add native New, Edit and Save as CSV/TSV, with a verified one-row Starter example. | Create/edit/export/reimport through the native controls, cancellation and error cases, and scientific batch use of the resulting table. |

The sample editor must keep file-path columns, base folders and input mapping
explicit. Only columns marked as file paths are resolved for export; metadata
must not be guessed to be paths. Saving elsewhere must preserve the intended
input identities, and Save as must preserve an existing destination file.
The example represents one synthetic sample using the existing Starter inputs;
duplicating its rows must not be presented as independent biological replicates.
Loading or editing a table does not silently choose a workflow or run analysis.

The previous keyboard/focus and narrow-display fixes remain requirements.
Reference management, existing workflows, saved pins, published pack bytes and
scientific known answers must remain intact. Recorded measurements still do not
establish invented QC pass thresholds.

## Evidence boundary

The preceding [UI-patch handover](ui-patch-0.16.1-handover.md) and its receipts are
immutable historical evidence for application source
`8938e709b041106e8a46e1447383e8e9ba3e0cb9` and final validator
`69022689e686b2cacdc98dbdbef728e664941e67`. Its **141 source passes, 84 native
checks per path, 19 repeated patch checks per path, archive audit and settled
96-DPI visual review apply only to those prior archives**. They do not test this
tester-feedback revision. Original failed attempts and the corrected screenshot
interpretation remain in those records.

New application bytes require a new source/archive correspondence audit and
their own source, native, temporal and screenshot results. Record application
and validator commits separately. A repeat of a gate on unchanged archives is a
repeat observation, not additional unique coverage.

## Validation to complete

| Scope | Status at this checkpoint |
| --- | --- |
| Implementation and focused source tests | In progress; no result recorded here. |
| New Starter, matching source companion and core updater | Pending build and exact archive identities. |
| Existing 19-check patch scope and 65 existing native checks per path | Planned on the new exact archives in ordinary and space-containing Windows paths. |
| New tester-feedback native and temporal gate | Planned; must exercise Run/poll redraws, category anchoring/collapse and Methods/preflight. |
| Samples editor and batch regression | Planned; must exercise explicit mapping, CSV/TSV export/reimport and the verified one-row example. |
| Independent archive/source audit | Pending; retain sizes, SHA-256 values, unchanged pack/runtime identities and matching source. |
| Screenshot and temporal review | Pending; retain actual visible captures, frame/timing limits, failures and skips. |
| Draft delivery | Pending implementation and the new evidence above. |

Before delivery, replace pending entries only with observed results and link the
new receipts, runs, exact download artifacts and rejected attempts. Keep earlier
0.16.1 receipt files unchanged. Report unavailable checks explicitly.

## Remaining limits

Representative-PC, high-DPI/transitions, multiple-monitor, physical-trackpad and
managed-machine acceptance remain outstanding. The previous layout evidence was
limited to its hosted 96-DPI sizes; source review identified overlap below 908
logical client pixels for busy Cancel/Results and below 902 for the footer.
Changed controls need fresh layout review, not an inherited fit claim.

Finite temporal sampling does not establish zero flicker or exclude shorter
unsampled transients. Synthetic examples establish their stated known answers,
not biological replication, realistic capacity or clinical fitness.
Executable signing still needs a controlled identity; institutional deployment
requires actual IT approval. Scientific Linux CWL and SDK/build recovery remain
later sets. Benchmarking is handled separately.
