# Purpose and decisions

Reviewed 2026-10-04. Product decisions below capture the project owner's explicit
requirements and tester feedback from the development conversation. Technical
status must be read with [current state](current-state.md), not inferred from a
requirement alone.

## The problem being solved

Bioinformatics teaching, researchers without access to managed compute, and
workplaces with Windows-only machines need to run established tools locally.
Many users do not have the Linux, shell, container or filesystem-mounting skills
usually assumed by tool documentation. Some settings cannot send analysis data
to an external service. Workplace browser restrictions also make a browser UI
an unsuitable required entry point.

Workbench should let a user choose local files and output folders, understand
the analysis, run a tool or assemble a scientifically compatible pipeline, and
receive interpretable results with reproducible methods and provenance.
Installing optional tools should not require rebuilding the application or
configuring a Linux environment. These users deserve real scientific software,
clear limits and useful errors, not simplified substitute algorithms.

The initial request explored whether Linux could be made into a lightweight
application. The demonstrated approach became **prepared native/portable
computation plus a small local orchestration layer**. It does not boot Linux or
promise to execute arbitrary Linux binaries. No claim of an unprecedented OS
technique or universal speed/memory advantage is established. Docker, WSL and
QEMU remain useful alternatives; avoiding them here is a usability/deployment
choice, not a claim that they inherently repartition or damage a PC.

## Accepted decisions

| ID | Decision and reason | Consequence for future work |
| --- | --- | --- |
| D01 | Local analysis is the default. Data locality is necessary for teaching and restricted workplaces. | Analysis files remain local. Public reference downloads and pack downloads are distinct, explicit operations. No hidden uploads or cloud fallback. |
| D02 | Use real pinned upstream tools with bounded portability adaptations. | Prefer native Windows builds, portable runtimes or a pack-private language runtime according to the tool. Preserve algorithms, record patches and compare scientific outputs. |
| D03 | The supported entry point is a native desktop app. The browser prototype was unsuitable for some workplace policies. | Preserve Win32 UI and private pipe-based backend. A browser or listening HTTP server must not become necessary to launch or run analysis. |
| D04 | Application and packs have independent lifecycles. The starter stays small. | Starter pack IDs are `align` (minimap2), `bam` (SAMtools), `variants` (BCFtools). Optional packs install through the manager or offline ZIP import. One repository with independent tags is sufficient. |
| D05 | A pack represents one tool or a small closely related operation set, such as indexing plus alignment. | New tools declare their own inputs, parameters and outputs. Existing multi-tool packs remain compatible; do not delete or rename published identities to impose the new preference retroactively. |
| D06 | Individual tools and assembled pipelines are both first-class. | Keep one clear library selection path, standalone operations and distinct saved tool settings versus saved pipeline graphs. Do not relabel one tool's settings as a complete pipeline. |
| D07 | Pipelines support branching, fan-out and merging, not just a list. | Draw a layered DAG with shared-output consumers at the same dependency level when dependencies permit. Show each input's producing step/output. Support step removal and validate the remaining graph. |
| D08 | Methods and provenance are part of the result, not an afterthought. | Show a methods preview before running; retain methods, DAG, commands, versions, parameters, input hashes and execution records with outputs. Methods are a reviewable draft, not a guarantee of publication sufficiency. |
| D09 | Reproducibility includes preserving installed versions. | Saved pipelines pin pack version and manifest hash. Updates install alongside old versions and require an explicit pipeline upgrade. Published bytes are immutable. |
| D10 | Trust and integrity must remain explicit. | Verify installed/archive inventories and signed online catalogues. An offline ZIP checksum does not authenticate its publisher. Never silently create a new trust root or bypass signing to make online installation work. |
| D11 | Design is guided by novice-user testing. | Preserve the accepted library/editor direction and readable layouts. Add resource needs, compatible input guidance and actionable errors without exposing unnecessary implementation details. |

## Interaction history worth preserving

The project tried a coloured corner wheel, then a rotating category wheel with a
second tool ring. Testers rejected the double ring and accepted the subsequent
tool-library design. Do not revive the wheel because an old screenshot or source
file still contains it. Modern rounded styling was desired; clarity of selection,
readable descriptions and restrained colours matter more than a decorative
control. Resizing, scrolling, focus outlines and text overlap were actual
reported problems and should be checked in UI work.

Testers also identified missing step removal and ambiguous shared outputs.
The resulting expectation is a Snakemake-style dependency diagram with clear
input sources. This is a layout and graph requirement; it does not imply that
the current scheduler runs independent branches concurrently. A merge requires
compatible ports and real tool support, not merely drawing two arrows into a
node. See [architecture](architecture.md) for the implementation boundaries.

Users want optional reports at meaningful points in a pipeline and public
reference discovery, including Ensembl. Downloaded references must become
explicit local, versioned inputs with provenance. Do not imply every reference
database, report format or downstream analysis is already integrated.

## Scientific and deployment boundaries

An accepted file extension is not sufficient evidence of compatibility. Genome
and transcript references differ; DNA and splice-aware RNA alignments differ;
sorted BAM is not necessarily duplicate-marked or recalibrated BAM. Sample
identity, reference assembly, strandedness and quantitative assumptions should
be checked or made explicit where required.

Do not equate a PASS VCF filter or a small synthetic fixture with diagnostic
validation. The project supports research workflows and teaching. Workplace/NHS
motivation does not establish clinical suitability, organisational approval or
regulatory status. Normal desktop operation needs no administrator account, but
application-control approval can include the private runtime and every tool.

The native tools are trusted code running as the user. The callback ABI,
argument validation and checksums do not create an isolation sandbox. Treat a
new pack publisher as a trust decision. Keep secrets and user datasets out of
public builds, tests and CI logs.

## How to change a decision

State the problem, proposed change, affected saved contracts and validation
needed. Record whether the change is an implementation detail, a new proposal,
or a user-approved product change. Add a dated replacement decision and link the
superseded one; do not erase the reason for the previous approach. Never treat
this record as authorization to publish or alter account settings in a new
session.
