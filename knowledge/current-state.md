# Current project state

Snapshot: **2026-10-04**. Source baseline:
[`9368c22058a3fe3cd434e7185fcaf5ff3fd6ce22`](https://github.com/comparativechrono/workbench/tree/9368c22058a3fe3cd434e7185fcaf5ff3fd6ce22).
Read this alongside the [machine-readable release inventory](release-inventory.json)
and the repository [README](../README.md). Update the date, source baseline and
evidence when the state changes; do not silently turn a pending item into a claim
of completion.

## What is available

The native desktop application **0.6.0** and **20 distinct tool packs** are
published as development prereleases. There are 21 published pack versions,
because kallisto 1.0.0 is retained after being superseded by 1.0.1. Historical
candidate releases are additional diagnostics, not current analysis packs.

The Windows starter contains only the `align`, `bam` and `variants` packs
(minimap2, SAMtools and BCFtools). Users extract the starter and run
`NativeWorkbench.exe`; no Docker, WSL, browser launch or system Python is required.
Additional packs install through **Manage tools > Import pack ZIP**, including on
offline computers. The [0.6.0 application release](https://github.com/comparativechrono/workbench/releases/tag/app-v0.6.0)
also supplies a separate updater for an existing **0.5.4** installation, an SDK,
the explicit source companion, checksums and a verification report. The starter
is 16,871,065 bytes; individual tool packs can be much larger.

The current published pack identities are below. The JSON inventory records
their exact release URLs, archive filenames, sizes and GitHub-reported digests.
These are **pack versions**, which differ from upstream tool versions.

| Pack ID | Current pack version | Purpose |
| --- | --- | --- |
| `align` | 0.4.0 | minimap2 read alignment; starter |
| `bam` | 0.4.0 | SAMtools alignment-file operations; starter |
| `variants` | 0.4.0 | BCFtools variant operations; starter |
| `reads` | 0.4.0 | Read quality |
| `trimming` | 0.4.0 | Read trimming |
| `fastp` | 0.4.1 | Read preprocessing and reports; retain the report fix |
| `bwa` | 0.4.0 | BWA alignment |
| `bowtie2` | 0.5.3 | Bowtie 2 DNA alignment |
| `hisat2` | 0.5.3 | HISAT2 DNA and RNA alignment |
| `freebayes` | 0.4.0 | FreeBayes variant calling |
| `lofreq` | 0.5.3 | LoFreq variant calling |
| `vardict` | 0.5.3 | VarDictJava targeted variants |
| `mutect2` | 0.5.4 | GATK Mutect2 somatic variants |
| `variant-pipeline` | 0.4.0 | Existing bundled variant pipeline |
| `research-variants` | 0.4.1 | Existing research variant workflows |
| `seqkit` | 0.5.2 | Sequence utilities |
| `muscle` | 0.5.2 | Multiple sequence alignment |
| `vsearch` | 0.5.2 | Amplicon operations |
| `star` | 1.0.0 | Bulk RNA alignment and optional annotated gene counts |
| `kallisto` | 1.0.1 | Bulk RNA transcript quantification |

Existing bundled pipeline packs remain available for reproducibility. The
development direction is individually usable tools or small related operations
composed into user-built pipelines. Installing a newer pack does not replace the
version or manifest hash pinned by a saved pipeline.

## What the evidence establishes

This documentation update read public GitHub release metadata, release notes,
the baseline README and the two final RNA workflow-run records. It **did not**
rehash all binary downloads or rerun scientific tests. The inventory's digests
are GitHub asset metadata; older release notes additionally record checks made
during publication. Keep those verification levels distinct.

| Component | Recorded evidence | Boundary |
| --- | --- | --- |
| App 0.6.0 | 214 automated tests passed, one Windows-only skip; eight starter checks; actual 0.5.4-to-0.6.0 updater migration on Linux; desktop/updater compiled with warnings treated as errors | Scientific execution used the portable Linux reference backend. This is not proof of the current Windows GUI or native long-path behavior. |
| Original 18 independent archives | Preserved original pack IDs, versions, manifests, contents and licence/source materials; archive inventories, sizes, hashes and ZIP CRCs audited | Repackaging did not constitute a new native Windows execution test for every tool. |
| STAR 1.0.0 | Eight Linux scientific tests and six released-app graph/import contracts; exact published archive passed native Windows CI in ordinary and space-containing paths | Five scientific fixtures plus a two-thread, two-pass buffer regression; small synthetic data, not a human-genome benchmark. |
| kallisto 1.0.1 | Ten Linux scientific tests and six released-app graph/import contracts; exact published archive passed native Windows CI in ordinary and space-containing paths | Single/paired fixtures exercise two threads and three bootstrap replicates; not validation of all RNA-seq protocols. |

The RNA graph/import contract tests used a Python copy callback in place of
native folder publication. The separate Windows jobs exercised the released
0.6.0 app's actual native bridge, pack import and duplicate-version rejection.
Do not describe the former as equivalent to the latter.

Final native Windows records:

- [STAR run 37149903110](https://github.com/comparativechrono/workbench/actions/runs/37149903110)
  completed successfully at source `1b87d7506898d49e339e547e02aed53ed7a9b167`.
  All five checks passed in each location. The additional buffer regression
  produced 400 SAM records from 200 read pairs with expected gene counts and
  identical ordinary/recycled-buffer results; installed pack files were unchanged.
  [Final validation JSON](https://github.com/comparativechrono/workbench/releases/download/pack-star-v1.0.0/native-workbench-star-1.0.0-windows-validation.json).
- [kallisto run 37150386848](https://github.com/comparativechrono/workbench/actions/runs/37150386848)
  completed successfully at source `a3a14f015c375fc318f4b0114b785667c6f26472`.
  Single-end and paired-end checks both passed at two threads and three
  bootstrap replicates in each location, including gzip reads.
  [Final validation JSON](https://github.com/comparativechrono/workbench/releases/download/pack-kallisto-v1.0.1/native-workbench-kallisto-1.0.1-windows-validation.json).

The corresponding source/evidence ZIPs are listed with digests in the inventory.
They preserve Linux and candidate-stage evidence, including historical status
at creation. The separate final validation JSON supersedes any pending-final-gate
statement inside those immutable companions; do not rewrite the companions.
Passing a scientific fixture is not clinical validation, a full desktop
acceptance test or proof of performance on arbitrary datasets.

## Important current limits

See the [RNA-seq guide](../docs/rna-seq-packs.md),
[kallisto pack guide](../docs/KALLISTO-PACK.md), each installed `PACK-README.md`
and its `licenses/provenance.json` for detailed supported interfaces.

- **STAR 1.0.0** uses STAR `2.7.11b-workbench1`. It builds a private index on
  every run because the 0.6.0 graph cannot expose reusable directory-valued
  products. Inputs are uncompressed genomic FASTA and Phred+33 FASTQ; annotated
  operations require a matching GTF. Paths must be ASCII and contain no commas;
  spaces are supported. Human-scale work generally needs tens of GB of RAM and
  substantial storage; the SAMtools sorting-memory setting does not limit STAR
  RAM. STARsolo, shared-memory indexes, external decompression and CRAM are not
  exposed. RNA alignments are deliberately incompatible with the existing DNA
  calling/preparation operations. Gene counts contain three strand columns;
  users select the column appropriate to the library downstream.
- **kallisto 1.0.1** uses `0.52.0-workbench2`. It needs a transcript/cDNA FASTA
  or compatible version-13 kallisto index, accepts plain/gzip inputs, and requires
  ASCII paths (spaces work). Single-end quantification requires an appropriate
  fragment-length mean and SD in whole bases, not guessed read-length defaults.
  Library strandedness is explicit. Outputs are transcript estimated counts,
  TPM and optional plaintext bootstrap estimates. Differential expression,
  transcript-to-gene aggregation, single-cell BUS, long reads, bias correction,
  BAM and HDF5 are outside this interface. The generic graph index type cannot
  identify every index format; the adapter validates the kallisto version.
- **kallisto 1.0.0** had an upstream conditional-compilation defect in this
  no-HDF5 build: multithread plaintext bootstrap dispatch was skipped. The
  adapter failed on missing outputs; this was not a general failure of zero-
  bootstrap quantification. Its earlier passing checks used one thread.
  Version 1.0.1 fixes dispatch to the existing upstream worker without changing
  its sampling or estimation algorithms. Keep 1.0.0 bytes and pipeline pins
  unchanged; explicitly select 1.0.1 for new/updated pipelines.
- Resource demands and portability constraints remain tool-specific. A local
  GUI cannot make a large reference fit into insufficient RAM. Do not promise
  generic Linux binary compatibility, arbitrary Unicode paths or universal
  support for every upstream command.

## Unfinished work and safe starting points

1. **Signed catalogue publication and clean installation test.** Pack downloads
   exist, but no signed online catalogue or `source.json` trust file is published
   or configured. The starter has an empty default source list. Follow
   [catalogue publishing](../docs/catalogue-publishing-0.6.md) and
   [the repository publication guide](../docs/github-publication.md). A
   maintainer-controlled external signing key and independently checked public
   fingerprint are required. An unsigned preview, GitHub credentials or this
   inventory cannot substitute for that trust configuration.
2. **Native desktop acceptance and long paths.** Validate the current 0.6.0 GUI,
   updater and long-path behavior on Windows, then record the exact app/pack
   versions and environment. Run **File > Check installation** on target
   machines. Native command-line pack CI does not close these outstanding items.
3. **Broader scientific and usability coverage.** Expand native checks for packs
   without equivalent current evidence, resource guidance and representative
   datasets. Preserve tool defaults in validation cases and exercise optional
   features explicitly. Keep patient/private data out of public fixtures and
   release diagnostics.
4. **Future schema improvements.** Reusable STAR indexes need a designed,
   versioned directory-product contract; tool-specific index typing is also a
   useful extension. These are proposals, not implemented 0.6.0 features.

The older `publishing/releases-0.6.0.json`,
`publishing/publication-layout-0.6.0.json` and parts of the publication guide
describe the original **18-pack split**. They are not the complete later RNA
inventory. Preserve their historical meaning and use this snapshot when planning
the next catalogue generation; add validated release mappings deliberately.

The [public RNA candidate release](https://github.com/comparativechrono/workbench/releases/tag/rna-candidates-20261003)
is a diagnostic archive. Its early STAR candidates exposed logging/buffer faults;
later candidates established correspondence with the final packs. Do not present
candidate downloads as current supported analysis versions, remove historical
published bytes, or infer that a successful candidate replaces an exact-final
archive check.

Finally, a Git clone alone is not the full third-party build environment. Recover
the explicit [application source companion](https://github.com/comparativechrono/workbench/releases/download/app-v0.6.0/native-workbench-0.6.0-source.zip)
and matching pack source/licence materials as described in
[source recovery](../docs/source-recovery/README.md). Do not depend on a previous
agent's scratch paths, compiler cache, browser session or unpublished credentials.
