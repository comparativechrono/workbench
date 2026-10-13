# Kalign optional pack

Date: 2026-10-13. Status: implementation complete; exact Windows candidate validation pending.

The owner requested merging the completed Prodigal/FastTree batch and proceeding
to Kalign. PR #16 is merged into its existing integration branch; the new
`feature/kalign-pack` branch starts at `8addaa1278c535e4931eb0b2b85b8f47b51ddd66`.
Published application **0.16.0** and the existing **0.16.1** UI candidate remain
unchanged. No release or catalogue publication is included.

## Bounded first interface

Independent pack identity `kalign` **1.0.0**, with separate nucleotide and
protein multiple-sequence alignment operations. Typed unaligned FASTA inputs
produce typed MSA FASTA outputs, retaining selected identifiers, order and
ungapped residues. Biological homology is a user input requirement, not inferred
by file type. The first interface uses one CPU and the ordinary upstream
alignment mode; ensembles, custom penalties and refinement are outside this set.

The native build uses upstream Kalign **3.5.1**, commit
`3e6de1df29d111c5fa5beb4c4294ef681978fd23`, source archive SHA-256
`01bacb2205e7b6792c570b163b5ccc0713284737ba862ca3b500a96a8a4d1bd9`.
Source inspection identified Windows POSIX I/O/time compatibility and explicit
alphabet selection as portability boundaries. The adapted tool version
is **3.5.1-workbench1**, preserving the alignment algorithms. The default-only
CLI alphabet patch and Windows compatibility header are retained in the pack.
The local 18-test Linux suite passed with no skips, including fresh pristine
reference execution; this does not establish native Windows execution.

## Validation and delivery work

Native Linux/reference comparisons and independent synthetic indel truth must
verify real alignments, not just successful process exit. Exact frozen Windows
archives will be imported into unchanged 0.16.0 in ordinary and spaced paths,
with real Kalign-to-FastTree nucleotide/protein DAGs, exact pins, provenance,
failures and Starter regressions. The FastTree dependency is the merged but
unpublished **1.0.0** candidate, not a published release.

Native forms/results will use the unchanged 0.16.1 UI candidate, including all
form pages from the true top, actual display screenshots and exact output hashes.
Pack JSON measurements remain result files unless a supported native summary
parser is present; do not claim new summary tiles without evidence. Source,
archive/static, native scientific and GUI observations remain separate.

A draft review PR and exact archive/source/evidence links will be saved after
validation. No validation result for Prodigal/FastTree establishes that Kalign
passes. Representative PCs, scientific Linux CWL, signing/deployment,
release/updater work and realistic benchmarking remain separate.
