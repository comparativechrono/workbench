# bustools 1.0.0 — a matched BUS bundle to measured gene counts

This independent Windows x64 pack exposes `bustools/count-bus` using real
bustools **0.45.1-workbench1**. It corrects assay barcodes, sorts BUS records and
counts unambiguous exact-UMI molecules into a **barcode-by-gene** Matrix Market
matrix. It does not call cells, normalize counts, test differential expression,
or assign QC pass thresholds. It does not generate BUS from FASTQ. The existing
kallisto pack supplies bulk quantification; it is not a BUS-producing predecessor.

Select five coherent local, uncompressed files together:

- `output.bus`, `matrix.ec` and `transcripts.txt` from the **same kallisto bus
  run/index**, preserving transcript order. BUS v1 little-endian only.
- A complete transcript-to-gene mapping from that index's annotation: transcript
  ID and gene ID in two tab-separated columns. An optional third gene-name column
  is ignored. Every transcript must map exactly once. IDs contain 1–128 ASCII
  letters, digits, dots, underscores or hyphens.
- The assay/chemistry's reviewed barcode allowlist, one unique uppercase A/C/G/T
  sequence per line. Obtain the original sequence-only list; compressed files and
  sample suffixes such as `-1` are rejected and never silently stripped.

Input limits are 2,000,000 BUS records / 64 MiB; barcodes 1–16 bases and UMIs 1–31;
250,000 transcripts; 500,000 ECs and 5,000,000 transcript memberships; 4,000,000
allowlist entries / 128 MiB. Nonzero BUS flags, padding and extra high barcode/UMI
bits (including pooled/split metadata) are rejected. Total BUS multiplicity must
fit an unsigned 32-bit integer. These are bounded interface limits, not promises
about workload time or total memory. ASCII installation/input/output paths are
required; spaces are supported. CRLF text inputs are normalized to LF in private
run copies. Inputs and installed pack files are never changed.

The guard checks structure, indices, complete mappings and output dimensions.
The run records exact input hashes and commands. These checks cannot establish
that separately selected files have a common biological origin: review their
provenance before running. A different sample's EC mapping may have plausible
indices and still be scientifically wrong.

## Scientific behavior

The unchanged upstream algorithms run as separate shell-free processes:
`correct -w allowlist`, `sort -t 1 -m 64M`, then `count --genecounts`. The 64 MiB
sort buffer is not a whole-process memory cap. Barcode correction keeps exact
allowlist matches; unique Hamming-distance-1 candidates are corrected; ambiguous
or uncorrectable barcodes are discarded. Correction log record counts differ
from read multiplicity sums.

Counting groups identical barcode-plus-UMI values and intersects gene sets across
their ECs. Exactly one surviving gene contributes one molecule, regardless of
read multiplicity. Multiple-gene intersections and disjoint-gene UMI collisions
contribute no count. No `--umi-gene` collision rescue, UMI edit-distance correction,
multimapping/fractional allocation or multiplicity-counting mode is requested.

`counts.mtx` rows correspond to `counts.barcodes.txt`; columns correspond to
`counts.genes.txt`. Retained barcode rows can have zero counts and are **not called
cells**. `summary.json` records input/retained record counts, read multiplicities,
barcode rows, genes, nonzero entries and counted molecules. A header-only BUS,
all barcodes discarded, or all groups ambiguous can validly yield zero counts.
Upstream sort omits the BUS header for zero records; the adapter restores only
the exact corrected BUS header before counting and records this in settings. No
records are added. Review assay/mapping choices and stage logs; zero is not a QC pass or evidence of
no expression. Corrected/sorted BUS, settings and stage logs are retained.
Native Results provides existing status/search/provenance; the JSON measurements
are output files, not new native Results tiles.

## Synthetic check and failure guidance

The included synthetic BUS bundle is constructed directly from documented binary
records; it is not biological data or proof of FASTQ/index preparation. Its 14
records carry 24 reads of multiplicity. Twelve records / 19 read multiplicities
survive barcode correction; sorted duplicates collapse to 11 records. Expected
matrix: `AAAA/geneA=3`, `CCCC/geneB=1`, `CCCC/geneC=1`; `TTTT` is a zero row. There
are 3 barcode rows, 3 genes, 3 nonzero entries and 5 counted molecules. This covers
exact/unique/ambiguous/unmatched barcodes, repeated observations, within-gene
transcript ambiguity, resolving EC intersections and disjoint-gene collisions.

Missing files/executables give reinstall or selection guidance. Truncated BUS,
invalid ECs, partial mappings, assay-length mismatches, unsupported metadata,
non-ASCII paths and pre-existing outputs fail explicitly. If a stage fails,
inspect its named log and check disk space, allowlist choice and bundle provenance.
Do not rename gzip/BUSZ or arbitrary data to `.bus`.

## Source and licensing

Upstream 0.45.1 commit `d4d7a283dbe9d34d2106e9ba31e2566413be6a70`:
<https://github.com/BUStools/bustools/tree/d4d7a283dbe9d34d2106e9ba31e2566413be6a70>.
Exact source archive SHA-256:
`b014317ea4501c3314ac358eb074dbbe3a10ed6daec53587f17a897e670e40df`.
The only source patch marks the version and makes bundled Roaring inline linkage
private for COFF. Scientific code and algorithms are unchanged. Native builds
use pinned LLVM/MinGW, baseline x86-64 (no AVX/AVX2), static zlib 1.3.2 and an
8 MiB stack reservation. Complete upstream/zlib sources, patch, build commands,
binary hashes and compiler/runtime notices are included in `licenses/`.

bustools is BSD-2-Clause; CRoaring 0.2.65 is Apache-2.0; Eigen 3.3.7 is primarily
MPL-2.0 with all bundled notices retained; LBFGSpp/CppNumericalSolvers have MIT
notices. The Workbench guard is MIT. See the complete individual notices.

Citation: Melsted, Ntranos and Pachter (2019), *The barcode, UMI, set format and
BUStools*, <https://doi.org/10.1093/bioinformatics/btz279>.

Build with `scripts/build_bustools_native.py --fetch` and prepare with
`scripts/prepare_bustools_pack.py`; `--linux` builds the same adapted source for
local scientific tests, and `--linux --upstream` builds a pristine reference.
Linux execution and PE inspection are separate from exact packaged Windows
acceptance. Representative PCs, real datasets and benchmarking remain separate
validation work; the dated handover identifies actual tested artifacts.
