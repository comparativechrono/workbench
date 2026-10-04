# Native Workbench

Run bioinformatics tools locally on Windows through a native desktop application.
Choose files and folders, run a tool, or connect compatible tools into a branching
pipeline. Analysis data stays on the machine.

The small starter distribution includes **minimap2, SAMtools and BCFtools**.
Additional tools are installed as independently versioned packs through
**Manage tools**, either from an approved signed catalogue or an offline ZIP.
The application does not require Docker, WSL or a system Python installation.

## Release status

Version **0.6.0 is a development prerelease**. The
[application release](https://github.com/comparativechrono/workbench/releases/tag/app-v0.6.0)
and **20 independently versioned tool packs** are published on GitHub. Their public
downloads have been checked against the original sizes and SHA-256 checksums.

The signed online catalogue and its `source.json` trust file are **not published
or configured**. They require a maintainer-controlled signing key. Use the offline
pack import described below until the signed feed is available.

The build passed 214 automated tests with one Windows-only skip, the eight
starter installation/scientific checks, and an actual 0.5.4-to-0.6.0 updater
migration on Linux. Scientific execution used the portable Linux reference
backend. The new Windows GUI and native Windows long-path behavior still need
validation on Windows.

## Using the application

Download the starter ZIP from the
[0.6.0 application release](https://github.com/comparativechrono/workbench/releases/tag/app-v0.6.0),
extract it and run `NativeWorkbench.exe`. Use **File > Check installation** to
check the target machine.

For another tool, download its `native-workbench-pack-…zip` asset from the
[pack releases](https://github.com/comparativechrono/workbench/releases). In
Workbench, open **Manage tools**, choose **Import pack ZIP**, and select that ZIP.
The ZIP can be copied to an offline machine before importing; running the tool
does not require a network connection. The starter already includes the `align`,
`bam` and `variants` packs.

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


The separate updater requires an existing **0.5.4** installation. Close Workbench,
extract the updater outside the application folder, run `UpdateWorkbench.exe`,
and choose the existing `native-workbench` folder. Installed packs, saved settings
and results are retained.

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
