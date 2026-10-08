# Native Workbench

Run bioinformatics tools locally on Windows through a native desktop application.
Choose files and folders, run a tool, or connect compatible tools into a branching
pipeline. Analysis data stays on the machine.

The small starter distribution includes **minimap2, SAMtools and BCFtools**.
Native **Tool setup** offers all 32 current packs through **Full**, or a smaller
**Custom** selection. Packs stay independently versioned; **Manage tools** also
supports approved signed catalogues and offline ZIP import.
The application does not require Docker, WSL or a system Python installation.

## Release status

**0.11.0 is validated and authorized for publication.** It adds expandable
native tool categories, preserves search and workflow interaction, and includes
a validated updater from 0.10.1. Public promotion/download verification is still
pending; use the published baseline below until the release record is updated.
See the [0.11.0 release notes](docs/releases/0.11.0.md) and
[handover](knowledge/expandable-tool-library.md).


[**0.10.1 is published as a development prerelease**](https://github.com/comparativechrono/workbench/releases/tag/app-v0.10.1).
It fixes Tool Setup scrolling and repeated header redraws, preserves navigation
while packs install, and replaces generic download errors with specific network
or local-storage diagnostics. The testers' original download failure has not
been reproduced on their machine; the new message identifies the next action.

The official signed catalogue and **Full, Starter and Custom** setup remain.
The Starter ZIP is **17.03 MB**; a fresh Full selection downloads another
**3.80 GB** for 29 additional packs. All 32 packs stay independently versioned.
Installed tools work offline; references, databases and results are separate.

The [exact-package Windows run](https://github.com/comparativechrono/workbench/actions/runs/37634723095)
passed setup, workspace, References, results/CWL/DAG/icon and 0.10.0 upgrade
checks in ordinary and space-containing paths. The old package reproduced
navigation defects and variable header pixels; the patch retained 391 stable
header samples with working scrolling. Each upgrade preserved 204 existing
files and verified 72 core files. Real production Full installed all 32 pins and
passed offline 202-record alignment/BAM and BED input checks. This covers
installation/coexistence and starter science, not every optional pack operation.

The [publication workflow](https://github.com/comparativechrono/workbench/actions/runs/37638350825)
promoted the validated archives without rebuilding and verified all ten public
assets by anonymous download and SHA-256. An independent second download also
verified all assets, four ZIP CRCs and both checksum manifests. See the [0.10.1 release notes](docs/releases/0.10.1.md)
and [handover](knowledge/tool-setup-0.10.1-handover.md) for exact scope and limits.

The release retains `workflow.cwl` in analysis results, routed dependency diagrams,
an SVG-derived Windows icon, the native Tools/Workflow interface and Ensembl
archive References with offline reuse and provenance. Earlier application
releases and all published tool-pack assets remain unchanged; their historical
evidence is retained in the [knowledge base](knowledge/README.md).

To execute exported CWL separately, provide a CWL engine, Python 3.10+, matching
tool-pack files and input data; Windows binaries remain Windows binaries. This
adds no dependency to normal Workbench operation. The
[CWL guide](knowledge/cwl-results.md) describes the export contract and limits.

## Using the application

Download the [0.10.1 Windows Starter ZIP](https://github.com/comparativechrono/workbench/releases/download/app-v0.10.1/native-workbench-0.10.1-starter-windows.zip),
extract it and run `NativeWorkbench.exe`. At first launch choose **Full**,
**Starter** or **Custom**. For Full or Custom, choose **Refresh catalogue**, review
the tools and download size, then choose **Install selection**. Starter works
without pack downloads. Use **File > Check installation** to check the target
machine. See the [tool setup guide](knowledge/tool-setup.md) for cancellation,
retry and offline use.

Use **Tools** for one operation, or switch to **Workflow** to add reusable input
cards and connect compatible tool ports. Input cards own the selected files;
tool cards own their options and connections. See the
[native interface guide](knowledge/native-ui.md).

Open **References** to search the **Ensembl archive**, choose a numbered release
and species/assembly, find files and explicitly download the required products.
On **Downloaded**, select a reference and a compatible input, then choose
**Use for input**. The local library works offline; loading or running an
analysis does not start downloads. cDNA and ncRNA remain distinct products.
See the [reference guide](docs/reference-discovery-0.7.md).

To add more tools later, reopen **Tool setup** through **Manage tools**, or use
the manager's catalogue selection. For offline import, download the tool's
`native-workbench-pack-…zip` asset from the
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

### Updating an existing installation

For version **0.10.0**, use the
[0.10.1 updater](https://github.com/comparativechrono/workbench/releases/download/app-v0.10.1/native-workbench-0.10.1-update-from-0.10.0.zip).
Close Workbench, extract the updater outside the application folder, run
`UpdateWorkbench.exe`, and choose the existing `native-workbench` folder.
Installed packs, saved settings/workflow pins, setup state, results and reference
files are retained. Native CLI preservation passed in both Windows paths;
the folder-picker interaction was not part of that automated gate.

This updater supports **0.10.0 only**. From 0.9.0, first use the
[0.10.0 updater](https://github.com/comparativechrono/workbench/releases/download/app-v0.10.0/native-workbench-0.10.0-update-from-0.9.0.zip).
Earlier 0.6.0 and 0.8.0 installations have updaters to 0.9.0 in the
[earlier release](docs/releases/0.9.0.md). There is no updater for 0.7.0:
retain that installation and extract the 0.10.1 Starter into a separate folder.
Extraction does not migrate data automatically.

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
