# bustools and StringTie optional packs

Date: 2026-10-13. Status: implementation complete; local source/science and native cross-build
checks pass. Exact packaged Windows execution and visual review remain pending. No release or merge is authorized for this set.

The owner requested the next roadmap stage after merging all completed PRs.
The clean verified base is `main` at
`9435fd65636917dab30e2c6b393549d1f371ac3d`, tree
`9c93246c76ef9f5f75eb50ce4e4fcee77f76da37`. Work is on
`feature/bustools-stringtie-packs`. Published application **0.16.0**, frozen
**0.16.1** application bytes and all earlier packs remain unchanged. The intended
new independent pack versions are **1.0.0**; the repository has no earlier
bustools or StringTie pack implementation.

## Bounded initial interfaces

- **bustools:** correction against an explicit assay barcode allowlist, sorting
  and gene-level UMI counting from one coherent uncompressed BUS dataset. The
  grouped input includes BUS, equivalence classes, transcript ordering,
  transcript-to-gene mapping and allowlist. Exact hashes and structural/index
  checks establish file identity and consistency, not proof of a common external
  origin; users must select files from the same pseudoalignment run and matching
  annotation/assay. Retain Matrix Market counts and exact gene/barcode labels,
  measured summaries, settings and logs. No cell calling, automatically inferred
  chemistry, differential expression or QC pass threshold. FASTQ-to-BUS generation
  is outside this first interface; the existing kallisto pack provides bulk
  quantification only.
- **StringTie:** guided short-read transcript assembly and a distinct annotation-
  only expression-estimation operation, each taking coordinate-sorted RNA BAM
  plus matching GTF and explicit library strandedness. Validate actual alignment
  order and splice-strand requirements, not only a header label. Guidance can
  yield novel structures; reference-only estimation must not. Retain GTF,
  abundance tables, measured summaries, settings and logs. No long-read/mixed/
  nascent modes, merge, Ballgown, raw-count or differential-expression claim.
  Contig names/bounds can reject mismatches but cannot establish the exact genome
  and annotation source without reviewed provenance.

Use pinned real upstream executables and narrowly documented portability fixes;
retain complete corresponding source, dependencies, licences, build identities
and algorithm-preserving patches. Consequential scientific settings and failure
recovery must be visible. Existing registered input types and metadata should
provide the integration without per-tool application branches.

## Required validation and delivery

Use independent known-answer synthetic fixtures plus pristine upstream Linux
comparisons where meaningful. Preserve zero-output biological cases and verify
count units, barcode correction/UMI ambiguity, transcript structures and expression
interpretation. Prove native build feasibility before elaborate wrappers.

Freeze the exact Windows pack ZIPs, bind source/recipes/binaries/dependencies,
then run ordinary and spaced application/input/results paths. Native import,
scientific/failure tests, saved pins, Methods, CWL export, searchable Results and
Starter regressions must refer to those exact bytes. Exercise a real HISAT2 RNA
alignment → StringTie graph; the successful HISAT2 contract does not establish
all other aligners' compatibility. Review all new native form pages and actual
BitBlt display screenshots on the unchanged 0.16.1 application.

Save source/archive/native/visual evidence, failed attempts and limits, then an
unpublished draft PR against `main`. Native Results does not automatically parse
new pack-specific measurement JSON. Representative-PC/broader display acceptance,
benchmarking, signing/institutional deployment, scientific Linux CWL and release/
updater validation remain separate. Existing passes do not validate this set.

## Implementation freeze

The initial interfaces are implemented as separate packs: bustools
`count-bus` using upstream **0.45.1-workbench1**, and StringTie
`assemble-guided` / `estimate-reference` using **3.0.3-workbench1** with the
reviewed native CLI changes described below. The assembly and estimation
algorithms remain upstream 3.0.3.
The frozen application and all existing pack code remain unchanged.

Local Linux checks include independent known-answer fixtures, fresh pinned
upstream comparisons, valid zero outcomes and malformed-input failures. Native
x64 builds and static pack checks pass; these do not establish Windows execution.
The new hosted workflow will build from the committed tree and preserve exact
pack/source archives, build records, native reports and actual-display captures.

The bustools guard narrowly preserves a genuine zero-record corrected BUS header
when upstream sort succeeds but creates an empty file. Nonzero input, invalid
headers and sort failure cannot use that correction. No records or molecules
are synthesized. StringTie keeps XS-tag precedence over library options and
requires explicit library selection; fixtures separately test untagged strand
behavior. BUS and BAM binary fixtures are generated deterministically from
committed factories.

## First hosted attempt and correction

Draft review: https://github.com/comparativechrono/workbench/pull/19.
Initial source `2044235fb0abff02c8d8259e12abf41df9647bd4`, run
https://github.com/comparativechrono/workbench/actions/runs/38412546344.
The build and downloaded archive/source audit passed. Both Windows paths failed
before full validation: the bustools test accidentally converted native CRLF to
CR-CR-LF, and the generic isolated-pack checker hid Starter's existing SAMtools
from StringTie alignment preflight. The test now verifies exact LF/CRLF bytes
and deliberate malformed-CR rejection. The batch gate must retain the exact
bundled `bam` 0.4.0 / SAMtools 1.24 helper while selecting target self-checks.
StringTie setup guidance describes that existing application prerequisite;
scientific executables and alignment preflight are unchanged. The failed attempt
is preserved in the evidence directory and does not count as a successful
Windows result. Corrected exact candidate validation remains pending.

## Second Windows attempt: CLI portability correction

Source `69a9ec0d09ef94076fbe4ba0f59fd89d2a604bd4`, run
https://github.com/comparativechrono/workbench/actions/runs/38413969992,
rebuilt successfully and passed all hosted source suites plus downloaded exact
archive/source correspondence. Both native scientific jobs then stalled; no
completed native or GUI pass is established for these bytes.

Independent pinned-source inspection identified a native CLI portability defect:
StringTie splits output paths only on `/`, while the guard supplied native
backslash paths. A resulting file-open failure can enter upstream Windows
`GError`, which blocks in `MessageBox` before returning failure. This is a
source-supported diagnosis; no retained native error report yet confirms the
specific triggering message in the stalled jobs. The correction normalizes
child argv paths and makes fatal/warning diagnostics console-only with valid
variadic handling. The tool is explicitly marked **3.0.3-workbench1**, with
retained patches and no assembly/estimation algorithm changes. Exact new Windows
validation is required. The checker also gains a bounded cancellation deadline
and retains partial plans, child logs and check reports on failure.
