# StringTie pack 1.0.0

This optional native Windows x64 pack uses pinned **StringTie 3.0.3-workbench1** (upstream 3.0.3).
Two operations accept one coordinate-sorted short-read RNA BAM and a matching
uncompressed transcript GTF:

- **Assemble guided transcripts** (`assemble-guided`, `-G`) can assemble expressed
  reference and novel models.
- **Estimate reference expression** (`estimate-reference`, `-e -G`) estimates only
  supplied models. It does not discover novel transcripts.

Workbench also needs an installed **SAMtools** pack for its alignment-header
preflight. Starter includes this helper. If it is missing, install **Alignment
files** (pack ID `bam`) from the Toolshed, then rerun the checks. The published
`bam` **0.4.0** pack supplies **SAMtools 1.24** and is the candidate validation
configuration. Workbench records the exact selected helper pack, manifest and
executable in the saved plan. SAMtools is an application validation prerequisite;
the bundled StringTie executable does not invoke it. The StringTie guard still
checks every BAM record after the application's header preflight.

Choose library strandedness explicitly: unstranded, first-strand/read1 opposes
transcript (`--rf`), or second-strand/read1 follows transcript (`--fr`). For
single-end libraries this refers to the sequenced read. The program cannot infer
library preparation. Existing XS tags take priority over these library options; they do not override contradictory alignment tags. Minimum transcript length, coverage, junction coverage,
isoform fraction, single-exon coverage and maximum multimap fraction are recorded
selection settings. They are not QC pass thresholds.

The BAM must really be sorted by genomic coordinates, not merely have a sorted
header. Every mapped alignment requires positive integer `NH`; every spliced
alignment requires `XS:A:+` or `XS:A:-`. HISAT2 `--dta` produces suitable tags.
STAR needs `--outSAMstrandField intronMotif`; a `bam-rna` label alone does not
establish this. Keep one biological sample per BAM. Multiple RG sample names
are rejected; absent RG sample metadata relies on the user's sample selection.
No BAM index is needed. Secondary multimapping alignments use upstream NH
weighting; duplicate-marked reads are retained. Supplementary records and mixed
single/paired flags are rejected.

The GTF must describe the same genome assembly. The guard verifies exact contig
names, lengths and exon bounds, quoted gene_id/transcript_id, consistent gene,
strand and chromosome within a transcript, and nonoverlapping exons. These checks
cannot identify the reference genome sequence or establish experimental fitness.
GFF3, gzipped GTF and generic annotation files are outside this contract.

Bounds: BAM 4 GiB and 10 million alignment records; mapped read length 1–1000
bases; GTF 256 MiB, 100000 transcripts, one million exons, 64 KiB per line.
Use local ASCII paths; spaces are supported. These bounds are input limits,
not a promise about runtime or memory. One StringTie processing thread is used;
there is no whole-process memory cap.

Outputs include `transcripts.gtf` (one-based inclusive coordinates),
`gene-abundance.tsv`, measured JSON summary, exact settings/arguments, and log.
Coverage, FPKM and TPM are expression **estimates**, not integer read counts.
No differential-expression or DESeq2-ready count matrix is produced. Zero
expression and an empty guided assembly are legitimate biological outcomes.
Native Results shows status, searchable outputs and exact provenance; it does
not currently parse this JSON into dedicated measurement tiles.

Long-read, mixed-read, nascent-aware, merge, Ballgown and prepDE workflows are
not exposed. End trimming, 10-base junction anchors, 50-base bundle gap,
STRG label and NH multimap correction remain enabled; other unexposed upstream
defaults are retained. The maximum multimap default is 1 in pinned 3.0.3.

## Synthetic examples and failure guidance

The bundled `spliced.bam` contains 123 constructed reads across two opposite-strand
500-base transcripts: 41 and 82 reads, with independent input mean aligned-base
coverage 8.2 and 16.4. A third guide transcript is unexpressed. These fixtures
establish exact exon topology and a 1:2 abundance relationship; they do not
represent a realistic dataset or benchmark. `empty.bam` tests zero expression.

The `hisat-*` FASTA/paired FASTQ/GTF training set corresponds to the existing
HISAT2 splice fixture repeated with 12 unique pair names. Set minimum transcript
length to 100 for this 180-base guide. Its 60-base internal coverage gap means it
exercises reference expression, not complete de novo transcript reconstruction.

If Workbench reports "Install a SAMtools pack to check alignment prerequisites",
install or restore the Alignment files pack and rerun. For missing XS/NH tags, realign with the indicated RNA settings. For sorting
errors, coordinate-sort the BAM. For contig/coordinate failures, select the
annotation from the same assembly instead of renaming contigs blindly. For
unexpectedly empty results, review library strandedness, guide compatibility,
coverage and selected parameters. On upstream failure inspect `stringtie.log`;
insufficient memory is possible and cannot be predicted from these checks.

## Rebuilding and validation

```sh
python scripts/build_stringtie_native.py --fetch --jobs 2
python scripts/prepare_stringtie_pack.py --destination build/stringtie-pack
python scripts/build_stringtie_native.py --linux --jobs 2
python scripts/build_stringtie_native.py --linux --upstream --jobs 2
python tests/test_stringtie_pack.py --reference-binary build/stringtie-reference-linux/stringtie --report build/stringtie-source-tests.json
```

Build source is commit `3436ad6dfd0ffc806a94086cf747ac6ff2b0dc19`; SHA-pinned
StringTie, zlib 1.3.2 and TRE 0.9.0 archives, build scripts, generated configuration,
compiler/runtime notices and full constituent source are retained. Scientific algorithms are unchanged. The retained `workbench1.patch` replaces
Windows fatal-error modal dialogs with stderr reporting and the same exit status 1,
makes both GError and GMessage consume diagnostic arguments once, and identifies
the modified build in its version banner. The native adapter
passes forward-slash paths to the upstream CLI so output directories are parsed
correctly on Windows. Native Windows uses upstream GThreads/HTSlib Windows
paths, an explicit standard stdint include and TRE POSIXregex symbols. Only
zlib/BAM is exposed; remote plugins and optional non-zlib CRAM codecs are disabled.
The executable is baseline x64 with an 8 MiB stack and system/UCRT dependencies.
Linux science/reference comparison and PE inspection do not establish native
Windows execution. Exact Windows package/path, pipeline and visual evidence
is recorded separately in the maintained project handover.

Primary sources: [StringTie repository](https://github.com/gpertea/stringtie),
[manual](https://ccb.jhu.edu/software/stringtie/index.shtml?t=manual),
[TRE](https://github.com/laurikari/tre), [zlib](https://zlib.net/).
