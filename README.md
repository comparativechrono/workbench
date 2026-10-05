# Native Workbench

Run bioinformatics tools locally on Windows through a native desktop application.
Choose files and folders, run a tool, or connect compatible tools into a branching
pipeline. Analysis data stays on the machine.

The small starter distribution includes **minimap2, SAMtools and BCFtools**.
Additional tools are installed as independently versioned packs through
**Manage tools**, either from an approved signed catalogue or an offline ZIP.
The application does not require Docker, WSL or a system Python installation.

## Release status

Version **0.7.0 is a development prerelease**. The
[application release](https://github.com/comparativechrono/workbench/releases/tag/app-v0.7.0)
and **32 independently versioned tool packs** are published on GitHub. This
application update adds a native **References** finder and reusable offline
library for release-pinned Ensembl archive genome FASTA, GTF, cDNA, ncRNA and
protein files, with hashes and provenance retained in analysis results.

The exact published 0.7.0 starter and updater passed the expanded native Windows
[gate](https://github.com/comparativechrono/workbench/actions/runs/37339280407):
eight checks in each ordinary and space-containing path, with no failures or
skips. Checks cover live reference discovery/downloads, cancellation, offline
reuse, provenance, preserved-data updating, References layout and actual
**Use for input** selection. The post-release concurrency audit also exercised
native file checkboxes, a typed destination, **Download selected**, **Cancel
operation**, and binding the newly downloaded genome. All eight original public
assets were freshly downloaded and rehashed; the application bytes are unchanged.
Folder pickers and wider desktop/path acceptance remain outside this automated gate.
See the [release handover](knowledge/reference-release-handover.md) and
[release inventory](knowledge/release-inventory.json) for exact hashes and scope.

The signed online catalogue and its `source.json` trust file are **not published
or configured**. They require a maintainer-controlled signing key. Use the offline
pack import described below until the signed feed is available.

Earlier application and optional-pack evidence retains its original scope.
The 0.6.0 baseline's 214 automated passes, one Windows-only skip and Linux
scientific/updater checks are historical results. Separate native Windows pack
gates validate the published STAR, kallisto, FastQC, MultiQC, featureCounts,
BEDTools, BLAST, GATK, SnpEff, DESeq2, mosdepth, IQ-TREE, Kraken2 and Bracken
archives through the released 0.6.0 bridge; this application update does not
replace those pack versions or rerun every pack's scientific suite.

## Using the application

Download the starter ZIP from the
[0.7.0 application release](https://github.com/comparativechrono/workbench/releases/tag/app-v0.7.0),
extract it and run `NativeWorkbench.exe`. Use **File > Check installation** to
check the target machine.

Open **References** to search the **Ensembl archive**, choose a numbered release
and species/assembly, find files and explicitly download the required products.
On **Downloaded**, select a reference and a compatible input, then choose
**Use for input**. The local library works offline; loading or running an
analysis does not start downloads. cDNA and ncRNA remain distinct products.
See the [reference guide](docs/reference-discovery-0.7.md).

For another tool, download its `native-workbench-pack-…zip` asset from the
[pack releases](https://github.com/comparativechrono/workbench/releases). In
Workbench, open **Manage tools**, choose **Import pack ZIP**, and select that ZIP.
The ZIP can be copied to an offline machine before importing; running the tool
does not require a network connection. The starter already includes the `align`,
`bam` and `variants` packs.

### More optional tools

These additions cover widely used QC, counting, interval and similarity-search
operations. They are independent downloads; the starter distribution is
unchanged. Installed packs use additional disk space.

| Pack | What it adds |
| --- | --- |
| [FastQC 1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-fastqc-v1.0.0) | Single/paired FASTQ quality reports, including gzip inputs |
| [MultiQC 1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-multiqc-v1.0.0) | Combine explicitly selected local FastQC, fastp, STAR, featureCounts and kallisto reports |
| [featureCounts 1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-featurecounts-v1.0.0) | Count reads or paired fragments from an RNA BAM against matching GTF genes |
| [BEDTools 1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-bedtools-v1.0.0) | Intersect, subtract, cover, sort/merge intervals and extract reference sequences |
| [NCBI BLAST+ 1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-blast-v1.0.0) | Local BLASTN, BLASTP, BLASTX and TBLASTN searches against your own FASTA sequences |

Use [the pack guide](docs/popular-packs-2026-10.md) for supported inputs,
scientific choices, pipeline branches and resource requirements. Reports are
created locally; viewing an HTML report separately may require an approved
viewer. The desktop app does not launch a browser to run these tools.

### Annotation, expression, coverage and phylogenetics

These optional packs connect to existing tools without changing the 0.6.0
application or its three-tool starter:

| Pack | What it adds |
| --- | --- |
| [SnpEff + SnpSift 1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-snpeff-v1.0.0) | Local database construction, variant consequences, local VCF annotations and impact selection |
| [DESeq2 + tximport 1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-deseq2-v1.0.0) | Bulk differential expression from raw counts, featureCounts or kallisto sample outputs |
| [mosdepth 1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-mosdepth-v1.0.0) | Whole-reference and target-region BAM depth and breadth |
| [IQ-TREE 1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-iqtree-v1.0.0) | Nucleotide/protein tree inference from alignments such as MUSCLE output |

All four passed their exact-final native Windows installation, graph and
scientific regressions in ordinary and space-containing paths. See the
[four-pack guide](docs/ANNOTATION-EXPRESSION-COVERAGE-PHYLOGENETICS.md) for compatible
connections, sample sheets, separate database resources and material limits.
Private runtimes are included. Matching source/evidence assets accompany the
releases; DESeq2 additionally requires its separate R-runtime source companion
when redistributing the complete corresponding sources.

### Metagenomic classification and abundance

| Pack | What it adds |
| --- | --- |
| [Kraken2 1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-kraken2-v1.0.0) | Prepare/register a local database, then classify single or paired FASTQ reads |
| [Bracken 1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-bracken-v1.0.0) | Reestimate taxonomic abundance from a Workbench classification record or explicitly declared external report |

Both exact-final archives passed native Windows installation, graph and
scientific gates in ordinary and space-containing paths, including a real
Kraken2-to-Bracken chain. Large databases are separate local resources: select an
existing database or prepare an already downloaded archive. The packs do not
download reference data during analysis. Bracken requires a model matching the
database and selected read length; paired report counts remain fragments.
See the [pipeline guide](docs/KRAKEN2-BRACKEN-PIPELINE.md) for setup, model
declarations, supported inputs and evidence limits.

### RNA-seq tools

Install [STAR 1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-star-v1.0.0)
for splice-aware alignment and optional annotated gene counts, or
[kallisto 1.0.1](https://github.com/comparativechrono/workbench/releases/tag/pack-kallisto-v1.0.1)
for transcript quantification. Download the pack ZIP from its release and use
**Manage tools → Import pack ZIP**.

STAR needs a genomic FASTA, with a matching GTF for gene counts; kallisto needs
a transcript/cDNA FASTA or a reusable kallisto index. STAR requires uncompressed
inputs and rebuilds its index per run; kallisto accepts gzip inputs. See the
[RNA-seq guide](docs/rna-seq-packs.md) for compatible pipeline branches, resource
limits and interpretation of counts. Use kallisto 1.0.1 for the corrected
multithread bootstrap support; existing saved pipelines keep their original
pack version until explicitly updated.

### GATK germline tools

Install [GATK 1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-gatk-v1.0.0)
for GATK **4.7.0.0** with its own Java 17 runtime. Its nine operations cover
duplicate marking, base-quality recalibration, HaplotypeCaller VCF/gVCF calling,
CombineGVCFs, GenotypeGVCFs, variant selection, filtering and validation. Run them
individually or connect sample branches into a joint-genotyping pipeline.

See the [GATK pack guide](docs/GATK-PACK.md) for inputs, scientific choices and
validation status. The exact final archive passed nine native scientific checks
and seven graph/archive contracts in both ordinary and space-containing Windows
paths. The existing Mutect2 pack remains the somatic calling interface.
GenomicsDB, Spark, VQSR and Python-dependent GATK tools
are outside this pack, and human whole-genome performance is not yet established.


The [0.7.0 updater](https://github.com/comparativechrono/workbench/releases/download/app-v0.7.0/native-workbench-0.7.0-update-from-0.6.0.zip)
requires an existing **0.6.0** installation. Close Workbench,
extract the updater outside the application folder, run `UpdateWorkbench.exe`,
and choose the existing `native-workbench` folder. Installed packs, saved settings,
results and downloaded references are retained. The native updater CLI and
preservation were tested; its folder-picker interaction was not part of the
automated gate.

Saved pipelines retain exact pack versions and manifest hashes. Installing a
newer pack does not silently change an existing pipeline. Methods descriptions,
pipeline diagrams and execution records accompany results.

## Development and independent packs

Start with the [project knowledge base](knowledge/README.md) for the approach,
architecture, development methods, decisions, validation evidence and next steps.
Agents should first read [AGENTS.md](AGENTS.md).

This repository contains application source and pack development tools. Large
executables, private runtimes, third-party source archives and pack ZIPs belong
in release assets, not Git history. Application and pack tags can be released
independently in this repository; a second repository is not required.

- [Pack development](docs/pack-development-0.6.md)
- [Signed catalogue publishing](docs/catalogue-publishing-0.6.md)
- [Repository-specific publishing plan](docs/github-publication.md)
- [Source recovery](docs/source-recovery/README.md)

Some build and scientific test paths require the separately distributed runtime
and source companions. This checkout alone is not the complete third-party
build environment. Keep the matching source companions available alongside
binary releases.

The application license is in [LICENSE](LICENSE). Third-party tools and runtimes
retain their respective licenses and notices.
