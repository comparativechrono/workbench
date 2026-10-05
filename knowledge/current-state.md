# Current project state

Snapshot: **2026-10-05**. Starting source baseline:
[`8f95caa1f267d19ce72ea3cd7f2396ae66a801c1`](https://github.com/comparativechrono/workbench/tree/8f95caa1f267d19ce72ea3cd7f2396ae66a801c1).
Read this alongside the [machine-readable release inventory](release-inventory.json)
and the repository [README](../README.md). Update the date, source baseline and
evidence when the state changes; do not silently turn a pending item into a claim
of completion.

## Reference-discovery development

The 0.7 source adds a native References finder and offline local library,
initially using release-pinned Ensembl archive datasets. Genome FASTA, GTF,
cDNA, ncRNA and protein files can be explicitly downloaded, checked, expanded
and bound to compatible tool inputs. Receipts and exact file hashes feed into
the frozen plan, methods and results. Reference datasets stay separate from
executable packs. Current reference documentation is in the
[0.7 guide](../docs/reference-discovery-0.7.md).

This section records implementation work, not a completed Windows acceptance
claim. A live 2026-10-05 audit found the published `app-v0.7.0-rc1` diagnostic
candidate, but no final `app-v0.7.0`. Its reference backend and 0.6.0-to-0.7.0
updater CLI passed recorded Windows checks; the overall GUI gate failed. The
details panel overlapped download controls, and tab automation timed out. The
source correction in `b9d0ee7` still needs a newly packaged native gate.
See the [continuation handover](reference-release-handover.md) for recovered
screenshots, exact identities and fresh source checks. The 0.7 packaging also includes AGENTS and
knowledge files in the source companion and supports a preserved-data update
from the exact 0.6.0 starter. The released baseline below remains dated evidence.

## What is available

The native desktop application **0.6.0** and **32 distinct tool packs** are
published as development prereleases. There are 33 published pack versions,
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
| `fastqc` | 1.0.0 | Single/paired FASTQ quality reports |
| `multiqc` | 1.0.0 | Aggregate explicitly selected local QC reports |
| `featurecounts` | 1.0.0 | Single-end RNA read or paired-fragment gene counts |
| `bedtools` | 1.0.0 | BED interval operations and reference sequence extraction |
| `blast` | 1.0.0 | Local nucleotide/protein and translated similarity searches |
| `gatk` | 1.0.0 | GATK 4 germline calling, alignment preparation, gVCF combination/genotyping and VCF operations |
| `snpeff` | [1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-snpeff-v1.0.0) | SnpEff/SnpSift local annotation databases, consequences, INFO annotation and impact selection |
| `deseq2` | [1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-deseq2-v1.0.0) | DESeq2/tximport bulk gene-level differential expression |
| `mosdepth` | [1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-mosdepth-v1.0.0) | Complete-reference and target-region BAM coverage |
| `iqtree` | [1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-iqtree-v1.0.0) | Nucleotide/protein maximum-likelihood tree inference from alignments |
| `kraken2` | [1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-kraken2-v1.0.0) | Register/prepare local databases and classify single or paired FASTQ reads |
| `bracken` | [1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-bracken-v1.0.0) | Estimate taxonomic abundance from a Workbench classification record or explicitly declared external report |

Existing bundled pipeline packs remain available for reproducibility. The
development direction is individually usable tools or small related operations
composed into user-built pipelines. Installing a newer pack does not replace the
version or manifest hash pinned by a saved pipeline.

## What the evidence establishes

The initial 2026-10-04 handover read release metadata and RNA CI records; it did
not repeat every older binary download or scientific run. The later optional-pack
work independently downloaded and rehashed each new public release asset,
retained Linux/source regression evidence, and ran the exact final pack ZIPs
through the released 0.6.0 native Windows bridge. The inventory records these
verification levels separately. Earlier application and pack evidence remains
dated evidence for its original bytes, not a fresh test of every older tool.

| Component | Recorded evidence | Boundary |
| --- | --- | --- |
| App 0.6.0 | 214 automated tests passed, one Windows-only skip; eight starter checks; actual 0.5.4-to-0.6.0 updater migration on Linux; desktop/updater compiled with warnings treated as errors | Scientific execution used the portable Linux reference backend. This is not proof of the current Windows GUI or native long-path behavior. |
| Original 18 independent archives | Preserved original pack IDs, versions, manifests, contents and licence/source materials; archive inventories, sizes, hashes and ZIP CRCs audited | Repackaging did not constitute a new native Windows execution test for every tool. |
| STAR 1.0.0 | Eight Linux scientific tests and six released-app graph/import contracts; exact published archive passed native Windows CI in ordinary and space-containing paths | Five scientific fixtures plus a two-thread, two-pass buffer regression; small synthetic data, not a human-genome benchmark. |
| kallisto 1.0.1 | Ten Linux scientific tests and six released-app graph/import contracts; exact published archive passed native Windows CI in ordinary and space-containing paths | Single/paired fixtures exercise two threads and three bootstrap replicates; not validation of all RNA-seq protocols. |
| FastQC 1.0.0 | Eight Linux source/scientific tests; exact final ZIP passed two native scientific checks in each path | Single plain and synchronized paired gzip FASTQ; counts, bases, GC and Q40 truth; private Java runtime, no GUI acceptance claim. |
| MultiQC 1.0.0 | Ten Linux source/regression tests, including real FastQC output; exact final ZIP passed its multi-input native check in each path | Six explicitly selected reports exercise five parsers; no whole-folder scanning, sample-merging inference or clinical interpretation. |
| featureCounts 1.0.0 | Eight Linux scientific/guard tests; exact final ZIP passed six native checks in each path | Single/paired counting at two threads, all three strand modes and known gene/assignment truth. |
| BEDTools 1.0.0 | Seven Linux regression tests, with all 15 fixture cases compared byte-for-byte to unmodified upstream; exact final ZIP passed 15 native checks in each path | Interval truth, CRLF, valid empty results, 64-bit coordinates and forward/reverse-complement extraction; exposed BED operations only. |
| BLAST 1.0.0 | Linux tests: 10 passed and one deliberately skipped on unmodified upstream; all 11 passed on the patched build. Exact final ZIP passed five scientific checks and six additional regressions in each native path | Four search modes, known coordinates/frames and a legitimate no-hit case; local-only failure regressions are separate from OS network isolation. |
| GATK 1.0.0 | Fourteen Linux scientific/regression tests passed. Exact final native Windows gate passed nine scientific checks and seven graph/archive contracts in each path, with no failures/errors/skips | Nine exposed operations with synthetic variant/genotype, duplicate and recalibration truth; no general Windows GATK support, clinical validation or whole-genome/cohort performance claim. |
| SnpEff 1.0.0 | Exact final ZIP passed four native installation/scientific checks, six graph/archive contracts and 13 additional scientific/failure regressions per path | Independent codon and allele truth, explicit database genetic codes and whole-record impact selection; consequences are not pathogenicity or assembly validation. |
| DESeq2 1.0.0 | Exact final ZIP passed three native installation/scientific checks, six graph/archive contracts and 14 additional scientific/failure regressions per path | Direct upstream matrix and tximport oracles cover 300 genes each. Synthetic bulk-expression/design/import tests do not establish experimental adequacy, FDR calibration or large-cohort performance. |
| mosdepth 1.0.0 | Exact final ZIP passed four native installation/scientific checks, six graph/archive contracts and 11 additional scientific/failure regressions per path | BAM/CIGAR/pair-overlap and full-reference denominator truth, BED targets and malformed-input rejection; no base-quality filtering or RNA expression claim. |
| IQ-TREE 1.0.0 | Exact final ZIP passed four native installation/scientific checks, six graph/archive contracts and 13 additional scientific/failure regressions per path | DNA/protein model and support truth, real MUSCLE-to-IQ-TREE execution, safe taxon restoration and bounded summaries; not species-tree or large-dataset validation. |
| Kraken2 1.0.0 | Exact final ZIP passed 6 native installation/scientific checks, 6 graph/archive contracts and 16 additional scientific/failure regressions per path | Synthetic assignments, paired fragment counts, gzip and local database/path guards; no production database bundled or large-database/clinical validation. |
| Bracken 1.0.0 | Exact final ZIP passed 4 native installation/scientific checks, 7 graph/archive contracts and 17 additional scientific/failure regressions per path | Independent Bayesian arithmetic, exact upstream estimator and real Kraken2-to-Bracken execution; database/model association, read-length approximation and estimated-abundance denominators remain explicit. |

The five-pack October [graph/import report](evidence/popular-pack-graph-contracts-2026-10-04.json)
records **eight tests passed, zero failures/errors/skips** on Linux with the
unchanged released 0.6.0 app and the corrected frozen BLAST guard. It binds the
exact ZIP/manifest hashes of the disposable graph-tested pack copies to FastQC
fan-in reporting, STAR-to-featureCounts branches at a shared DAG level, merged
reporting and BEDTools-to-BLAST nucleotide search. Type/pairing mismatches,
missing strand choices, duplicate connections and changed saved pins are rejected.
It explicitly records that no scientific executable or native importer ran.

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

The added packs' final runs also used the actual native importer and rejected a
duplicate version without replacing the installed manifest:

| Pack | Exact-final Windows run | Scientific checks per path |
| --- | --- | --- |
| FastQC 1.0.0 | [37207251061](https://github.com/comparativechrono/workbench/actions/runs/37207251061) | 2 |
| MultiQC 1.0.0 | [37208730673](https://github.com/comparativechrono/workbench/actions/runs/37208730673) | 1 multi-input case |
| featureCounts 1.0.0 | [37208535793](https://github.com/comparativechrono/workbench/actions/runs/37208535793) | 6 |
| BEDTools 1.0.0 | [37207758617](https://github.com/comparativechrono/workbench/actions/runs/37207758617) | 15 |
| BLAST 1.0.0 | [37210341211](https://github.com/comparativechrono/workbench/actions/runs/37210341211) | 5, plus 6 adapter/local-failure regressions |
| GATK 1.0.0 | [37220420948](https://github.com/comparativechrono/workbench/actions/runs/37220420948) | 9, plus 7 graph/archive contracts |
| mosdepth 1.0.0 | [37228329920](https://github.com/comparativechrono/workbench/actions/runs/37228329920) | 4, plus 6 graph/archive contracts and 11 scientific/failure regressions |
| IQ-TREE 1.0.0 | [37229409061](https://github.com/comparativechrono/workbench/actions/runs/37229409061) | 4, plus 6 graph/archive contracts and 13 scientific/failure regressions |
| SnpEff 1.0.0 | [37229552990](https://github.com/comparativechrono/workbench/actions/runs/37229552990) | 4, plus 6 graph/archive contracts and 13 scientific/failure regressions |
| DESeq2 1.0.0 | [37230943331](https://github.com/comparativechrono/workbench/actions/runs/37230943331) | 3, plus 6 graph/archive contracts and 14 scientific/failure regressions |

The four new exact-final runs used the released 0.6.0 application unchanged in
ordinary and space-containing `windows-2022` paths. mosdepth's helper source was
`102e85e2ce38c750b521c70e532001dd55451509`; IQ-TREE, SnpEff and DESeq2 used
`24c6899aa7c19208ec88ae816879952ed0d8527e`. Their release assets include separate
`native-workbench-<id>-1.0.0-windows-validation.json` reports. Graph contracts use
the released Python engine and a checked publication callback; native installation
checks separately exercise the actual bridge/importer and scientific commands.

DESeq2's [source-build development run 37229593426](https://github.com/comparativechrono/workbench/actions/runs/37229593426)
passed all 14 native scientific/failure regressions at source `24c6899aa7c19208ec88ae816879952ed0d8527e`.
This did not import the final ZIP. The subsequent exact-final
[run 37230943331](https://github.com/comparativechrono/workbench/actions/runs/37230943331)
independently passed three native installation checks, six graph/archive
contracts and 14 scientific regressions in each Windows path, with zero
failures/errors/skips. The [dated validation record](evidence/deseq2-1.0.0-validation-2026-10-04.json)
and [public final report](https://github.com/comparativechrono/workbench/releases/download/pack-deseq2-v1.0.0/native-workbench-deseq2-1.0.0-windows-validation.json)
bind these results to archive SHA-256
`eccffbcaf3adad6ab1da63ea771fe103a807a88722a56f5db82072cf02c1292d`
and manifest SHA-256
`f5a06708651f14f25e89ca3588ed6bf2f91442e43d635a9fc7ab5af066112ee1`.
The pack, source/evidence and R-runtime source ZIPs were independently downloaded
and rehashed against the frozen artifacts.

The exact DESeq2 ZIP's earlier Linux graph attempt preserved one strict failure
after temporary extracted files reappeared following cleanup; five
graph/application tests passed and no installed file changed. Earlier six-test
Linux success applies to a different archive. Both exact-final Windows graph
suites subsequently passed all six cases, including duplicate-import immutability,
without weakening assertions. Preserve the original failed report and separate
source-build evidence; the final native report closes the release gate without
rewriting that history.

The corresponding source/evidence ZIPs are listed with digests in the inventory.
They preserve Linux and candidate-stage evidence, including historical status
at creation. The separate final validation JSON supersedes any pending-final-gate
statement inside those immutable companions; do not rewrite the companions.
Passing a scientific fixture is not clinical validation, a full desktop
acceptance test or proof of performance on arbitrary datasets.

GATK's [dated validation record](evidence/gatk-1.0.0-validation-2026-10-04.json)
links the frozen pack, matching source and distinct test stages. Candidate
[run 37220034835](https://github.com/comparativechrono/workbench/actions/runs/37220034835)
passed nine scientific checks and seven graph/archive contracts in each of the
ordinary and space-containing `windows-2022` paths. The scientific gate used the
released native bridge/importer; the graph/archive suite used the unchanged
released Python engine and a copy callback for folder publication.
The exact final [GATK 1.0.0 release](https://github.com/comparativechrono/workbench/releases/tag/pack-gatk-v1.0.0)
then passed the same nine scientific checks and seven graph/archive contracts
in each path in [run 37220420948](https://github.com/comparativechrono/workbench/actions/runs/37220420948),
at source `eb4a255b69a2eabfb539937218a1d0e57c5776a3`, with no failures/errors/skips.
The [separate final validation report](https://github.com/comparativechrono/workbench/releases/download/pack-gatk-v1.0.0/native-workbench-gatk-1.0.0-windows-validation.json)
binds those results to the released ZIP and manifest hashes.

The Linux graph suite's six graph/application tests passed, but its strict
archive-copy test observed transient files or altered hashes inside disposable
copies. The diagnostic reports are retained; there is no claim of a clean
seven-test Linux pass. Windows candidate and final graph/archive checks passed without
weakening the inventory or duplicate-immutability assertions. The published
source companion retains its creation-time status; the separate final validation
report supersedes pending-final statements without changing its bytes.

## Kraken2 and Bracken exact-final evidence

| Final pack | Native Windows run | Recorded result |
| --- | --- | --- |
| Kraken2 1.0.0 | [37235526518](https://github.com/comparativechrono/workbench/actions/runs/37235526518) | 6 installation, 6 graph/archive, 16 scientific/failure checks per path |
| Bracken 1.0.0 | [37236121810](https://github.com/comparativechrono/workbench/actions/runs/37236121810) | 4 installation, 7 graph/archive, 17 scientific/failure checks per path |

Kraken2's [final validation record](evidence/kraken2-1.0.0-validation-2026-10-04.json) binds the exact ZIP and manifest
to helper source `85ef78b0436417a85d8d70ed685dc2a52c24f7a4`. Its final pack SHA-256 is
`9feb39546f6af9d718629304d7fc6a5d70d8a015839deef7d4a869e7587a0e91`.

Bracken's [final validation record](evidence/bracken-1.0.0-validation-2026-10-04.json) binds the exact ZIP and manifest
to helper source `289c4176561fe6c8bbbfba1e225cd65fbafb126d`. Its final pack SHA-256 is
`bfd5ae2ea3ef3e54f3ae5b97530e58bf1aad8562d66ca1c8e190b87472f1d853`.

The unchanged released 0.6.0 application and ordinary/space-containing
`windows-2022` paths were used. Native installation exercised the actual
importer/bridge; graph/archive tests used the released Python engine with a
checked copy callback. Bracken's full scientific suite also executed actual
Kraken classification followed by the unchanged upstream abundance estimator.
Every final public asset was independently downloaded and rehashed.

The separately retained [shared-resource checks](evidence/metagenomics-resources-2026-10-04.json)
passed 17 source-level tests on Linux for descriptor identities, path/archives,
fragment accounting and failure cleanup. That report explicitly records no
scientific executable, native importer or Windows execution; it is not a native
release gate. It is preserved in Git because the earlier source companions did
not include this report.

These are small synthetic checks, not GUI acceptance, production-scale database
benchmarks or clinical validation. The packs remain optional and independently
usable. Reference indexes and Bracken read-length distributions remain separate
local resources; no reference download occurs during analysis. Registration
hashes database bytes but keeps external database/model association explicitly
user-attested. Bracken's external-report operation likewise retains declared
provenance rather than fabricating a Workbench classification history. Exact
read length is the default; representative-length mode is a recorded
approximation. Paired abundance counts fragments, not twice as many mate reads.

Source/evidence companions retain their creation-time pending-final status.
The separate exact-final reports supersede that status without replacing any
published bytes. Historical candidate/failure records remain preserved and are
excluded from the 32 current pack identities. See the
[pipeline guide](../docs/KRAKEN2-BRACKEN-PIPELINE.md) and
[resource contract](../docs/METAGENOMICS-RESOURCES.md).

## Important current limits

See the [RNA-seq guide](../docs/rna-seq-packs.md),
[kallisto pack guide](../docs/KALLISTO-PACK.md),
[additional pack guide](../docs/popular-packs-2026-10.md), each installed `PACK-README.md`
and its bundled provenance files for detailed supported interfaces.

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
- **FastQC 1.0.0** uses unmodified FastQC 0.13.0 with private Temurin
  8u504-b01. Four-line plain/gzip FASTQ, explicit Phred+33/+64 and synchronized
  mates are supported. ASCII paths must exclude semicolons; filenames beginning
  with lowercase `stdin` are rejected because upstream treats them as streams.
  QC flags require interpretation and do not trim or filter reads.
- **MultiQC 1.0.0** uses MultiQC 1.35 with private Python 3.13.16 and pinned
  Windows wheels. It accepts 1–64 explicitly selected metrics files from five
  supported parsers; kallisto requires its captured quantification log, not
  `run_info.json` or `abundance.tsv`. Input names are namespaced to preserve
  separate rows; no biological sample matching is inferred. Implicit settings,
  version checks, uploads and AI are disabled. Its Python audit hook and report
  CSP are bounded controls, not an OS sandbox. Reports do not launch a browser;
  viewing HTML separately may require an approved viewer. Per-run private wheel
  extraction needs about 1 GiB extra disk space.
- **featureCounts 1.0.0** uses the official unmodified Subread 2.1.1 Windows
  executable. It counts one RNA BAM against matching plain GTF, with explicit
  strandedness. Paired counting requires both aligned ends and excludes chimeras;
  supplementary alignments are rejected, NH multimappers/secondary and ambiguous
  reads excluded, and duplicate-marked reads retained. Results are raw integer
  gene counts, not normalization or differential expression. The guard requires
  exact contig names but does not prove genome/sample identity.
- **BEDTools 1.0.0** exposes nine interval operations using
  `2.31.1-workbench1`. Input is consistent plain BED3–6 with zero-based half-open
  coordinates; released 0.6.0 bounds inputs to one million intervals and rejects
  empty downstream BED inputs even when an upstream no-hit result is legitimate.
  Sequence extraction privately copies and indexes plain FASTA, with individual
  contigs bounded to 2,147,483,647 bases. No BED12/GTF/VCF/BAM semantics are implied.
- **BLAST 1.0.0** uses BLAST+ 2.17.0 built with static MSVC runtime from pinned
  NCBI/SQLite source. It exposes BLASTN, BLASTP, BLASTX and TBLASTN with local,
  uncompressed FASTA queries/subjects. Each run builds a private version-4
  database; reusable database folders, remote search and automatic download are
  not exposed. The guard validates complete FASTA records/identifiers and the
  selected alphabet. Similarity hits do not establish function or orthology;
  translated searches require an appropriate genetic code. Narrow source patches
  retain paths with spaces and remove implicit remote sequence/database fallback;
  the guard disables usage reporting and preserves child diagnostics. Exact
  coordinate/translated-frame and local-failure checks are bounded evidence,
  not a network firewall or validation of all BLAST operations.
- **GATK 1.0.0** exposes nine germline/preparation/VCF operations using unchanged
  GATK 4.7.0.0, its existing Workbench local-path adaptation and private Java 17.
  It requires coordinate-sorted single-sample DNA BAMs with a declared sample
  and a resolvable RG tag on every alignment, the matching plain reference, and
  BED intervals for calling/BQSR. MarkDuplicates retains reads and disables
  optical-duplicate detection; it is not UMI-aware. BQSR learns over selected
  intervals using explicit known sites and applies the model to the full BAM.
  HaplotypeCaller uses pure-Java PairHMM/Smith-Waterman implementations, with
  slower performance possible than native acceleration. CombineGVCFs accepts
  two to 32 distinct-sample inputs. Released 0.6.0 uses labelled generic file
  ports for gVCFs, keeping them incompatible with ordinary VCF ports; the
  adapter validates file roles, NON_REF likelihoods and sample uniqueness.
  Generic file connections alone do not establish gVCF compatibility. Genuine
  empty ordinary VCF results remain valid. Filters are explicit site-annotation
  criteria, not a guaranteed Best Practices protocol. GenomicsDB, Spark, VQSR,
  Python-dependent CNV tools and clinical/whole-genome performance validation
  are outside this scope. See the [pack guide](../docs/GATK-PACK.md).
- Resource demands and portability constraints remain tool-specific. A local
  GUI cannot make a large reference fit into insufficient RAM. Do not promise
  generic Linux binary compatibility, arbitrary Unicode paths or universal
  support for every upstream command.

The [four-pack guide](../docs/ANNOTATION-EXPRESSION-COVERAGE-PHYLOGENETICS.md)
describes the newer limits. SnpEff database resources remain separate local
inputs with explicit assembly/release/codon mappings. DESeq2 accepts independent
bulk samples with condition or additive batch-plus-condition designs; raw count
semantics and actual biological independence cannot be proven by broad metrics
ports. Its private per-run R tree consumes extra disk, and R scratch needs a
space-free path or existing short alias. Mosdepth aggregates all BAM samples,
including uncovered reference contigs in its primary denominator; it applies no
base-quality filter. IQ-TREE consumes aligned nucleotide/protein sequences and
omits detailed JSON bipartitions above 256 taxa while preserving the complete
Newick tree. Small synthetic checks establish neither GUI acceptance nor clinical
or human-genome/cohort performance.

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
describe the original **18-pack split**. They are not the complete later optional-pack
inventory. Preserve their historical meaning and use this snapshot when planning
the next catalogue generation; add validated release mappings deliberately.

The [public RNA candidate release](https://github.com/comparativechrono/workbench/releases/tag/rna-candidates-20261003)
is a diagnostic archive. Its early STAR candidates exposed logging/buffer faults;
later candidates established correspondence with the final packs. Do not present
candidate downloads as current supported analysis versions, remove historical
published bytes, or infer that a successful candidate replaces an exact-final
archive check.

The [October optional-pack candidates](https://github.com/comparativechrono/workbench/releases/tag/popular-candidates-20261004)
retain failed and superseded diagnostics. featureCounts' first candidate counted
correctly but its full-row checks did not accept Windows CRLF; a stale second
candidate was not promoted. MultiQC's first candidate exposed the runner's
precreated output directory behavior. Later candidates and exact-final gates
record the fixes; retain historical bytes and correspondence reports. BLAST
0.0.1 passed five scientific result-file checks per path but lost child diagnostic
output; candidate 0.0.2 uses explicit inherited standard handles and passes the
additional local-failure regressions. Only the separate exact-final gate validates
the published 1.0.0 archive.

Finally, a Git clone alone is not the full third-party build environment. Recover
the explicit [application source companion](https://github.com/comparativechrono/workbench/releases/download/app-v0.6.0/native-workbench-0.6.0-source.zip)
and matching pack source/licence materials as described in
[source recovery](../docs/source-recovery/README.md). Do not depend on a previous
agent's scratch paths, compiler cache, browser session or unpublished credentials.

DESeq2's complete corresponding sources additionally require the separate
`native-workbench-deseq2-1.0.0-r-runtime-sources.zip` release asset: Rtools base
libraries and compiler runtimes, Tcl/Tk extensions, original notices and exact
build recipes/patches. Its runtime-bound lock and SHA-256 are recorded in
`tools/deseq2/`; see [the recovery notes](../tools/deseq2/R-RUNTIME-SOURCES.md).
The smaller source/evidence companion contains tracked source and reports, not
this external-library archive. Installed packs never fetch sources during analysis.
