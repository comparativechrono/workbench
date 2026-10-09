# Development roadmap

## Accepted programme, 2026-10-08

The owner accepted the feature programme below with “Great. We should do all
of these. Lets start working through them.” Development starts with a bounded
measurement/readiness milestone on `feature/readiness-performance`, based on
`82729febfcfab1c43bd9c9798d03c80f595545cb`, targeting **0.12.0**. This is
development authorization, not evidence that the features or a release are
complete. Published **0.11.0** and all published pack bytes remain unchanged.
See the [first-tranche feature guide](readiness-performance.md) and
[current state](current-state.md) for implementation and validation status.

The owner subsequently requested the next tranche. Milestone 2 now targets
unpublished **0.13.0** on `feature/batch-queue-indexes`, stacked on the unmerged
0.12.0 branch. Its first concrete index contract is minimap2 short-read `.mmi`;
its combined-analysis mode initially covers explicitly selected multi-input
metrics/text reports. Neither implies generic cohort pooling or reusable indexes
for every aligner. See [batch workflows](batch-workflows.md) and
[reference indexes](reference-indexes.md) for exact limits and evidence.
Its implementation and recorded hosted Windows gates are complete in
[draft PR #8](https://github.com/comparativechrono/workbench/pull/8); see the
[candidate handover](batch-queue-indexes-0.13.0-handover.md). Representative-machine
acceptance and release/update validation remain separate from that result.

The owner has now requested the final implementation tranche, milestone 3.
It targets unpublished **0.14.0** on `feature/recovery-projects`, starting from
`9f5cd4c88634b4cab04cec66b9e43e93e1db0e17` on the unmerged 0.13.0 branch.
See [recovery, resources and portable projects](recovery-projects.md).
Implementation and the exact hosted Windows candidate gates are complete in
[draft PR #9](https://github.com/comparativechrono/workbench/pull/9); the
[handover](recovery-projects-0.14.0-handover.md) records final downloads,
independent archive verification, failed prior attempts and remaining acceptance
and release work. Milestones 1–3 are implemented on stacked review branches,
not published releases or completed representative-machine acceptance.
This does not declare the further accepted work or benchmark programme complete.

The owner then requested the remaining groups one at a time. The first is
**reference management**, targeting unpublished 0.15.0 on
`feature/reference-management` from `38917349449ce56a45d3e0f4f41b7d2a38621c6d`.
It covers resumable downloads, reviewed local import, verified library relocation
and a bounded NCBI RefSeq accession provider. See the
[feature contract](reference-management.md) and
[handover](reference-management-0.15.0-handover.md). The original three
implementation tranches were not the entire accepted suggestion list; each
remaining group retains its own completion and validation evidence. The reference
group is now implemented and hosted-Windows validated in draft PR #10;
representative-machine acceptance and publication remain separate.

| Milestone | Accepted scope | Completion evidence |
| --- | --- | --- |
| 1 — Measurement and readiness | Local performance records, an understandable readiness report, reviewable diagnostic export and representative-machine validation. | Exact packaged Windows evidence for successful, failed and cancelled work; preserved scientific output; documented timing/counter scope and unavailable values; reviewed JSON equals exported JSON; private-data canaries absent; installation, readiness and scientific execution clearly distinguished. A separate matched Windows–Linux benchmark protocol records hardware, versions, parameters and data identities. |
| 2 — Routine multi-sample work | A sample table, general batch workflows, a durable run queue and reusable reference indexes. | Previewed sample/read-pair mapping; independent per-sample and explicitly combined analyses; exact frozen queued plans surviving restart while the next workflow remains editable; index identity and completeness verified before reuse. Saved pins and existing results survive migration. |
| 3 — Recovery and efficient execution | Verified restart at completed-step boundaries, resource-budgeted parallel execution and portable project bundles. | Fault-injected interruption/restart preserves scientific outcomes, reuses only verified completed products and invalidates changed dependencies; scheduler respects declared budgets/cancellation; project import reports missing or incompatible dependencies without silent substitution. |

High-DPI displays, keyboard navigation, physical trackpads and managed Windows
machines are acceptance work across **every** milestone. Hosted 96-DPI checks
remain useful evidence for their recorded environment; they do not establish
all of these deployment scenarios. No endpoint-security control should be
disabled to obtain a pass.

### Accepted feature contracts

| Feature | Intended behaviour and boundaries |
| --- | --- |
| Sample table and batch workflows | Import CSV/TSV sample names, paired reads, conditions, replicates and references. Preview pairing and reject ambiguity. Preserve sample identity and distinguish independent sample runs from deliberate pooling or cohort analysis. Existing pack-specific sample sheets do not establish a general application batch model. |
| Safe restart | Reuse only completed steps whose inputs, parameters, exact tool/manifest pin, reference identities and declared outputs still match. Begin at step boundaries; resuming within a scientific executable requires that tool's own supported checkpoint contract. |
| Durable queue | Queue immutable analyses with exact settings and software versions, monitor/cancel individual jobs, and edit the next workflow while one runs. Preserve queued state across reopen; never silently repin a saved or queued workflow. |
| Resource controls | Start with a total CPU budget, selected temporary-storage location, free-space checks and honest memory/storage guidance. Add bounded concurrency only after reliable measurements and admission rules exist. Unknown requirements must remain unknown. |
| Reusable reference indexes | Build once and register reference hash, indexing tool, version, options and a complete output inventory. Reject incompatible or incomplete indexes. Typed directory products and changed pack commands need explicit versioned contracts and migration tests. |
| Readiness report | Make graph/input checks, selected pack definitions, output access/storage, deferred integrity/scientific checks and actual tool execution distinct. “Check installation” passing must not imply the user's analysis can run. |
| Performance and diagnostics | Retain measurements locally with their scopes, versions and missing values. Separate preparation/hashing/orchestration from native command stages. Diagnostic sharing is an explicit review-and-save action, with no automatic upload or broad log/data collection. |
| Curated workflows and results | Supply tested workflows with small redistributable example datasets, explanations and expected answers. Add native sample-level QC summaries, searchable results and useful failure explanations with links to raw outputs and methods. Preserve exact tool pins. |

### Further accepted work

- **Reference management:** resumable large downloads, importing existing local
  references, safe library relocation and additional providers. Retain explicit
  retrieval, complete-file integrity and assembly/annotation compatibility.
- **Portable projects:** bundles containing workflows, sample metadata, exact
  pack/reference requirements and optionally data. Provide a guided missing-file
  resolution process and tested Linux execution profiles for exported CWL.
  Existing CWL export is not blanket proof of Linux scientific equivalence.
- **Institutional deployment:** executable signing, bundled executable/dependency
  inventories, offline deployment packages and IT approval documentation. Signing
  does not guarantee acceptance by endpoint-security software.
- **Pack developer toolkit:** templates, metadata/schema validation, scientific
  fixture checks, packaging checks and documented Windows–Linux comparisons.
  Third-party contributions retain independent versions, trust and licensing.

### Benchmark programme

Use direct matched-tool comparisons and complete workflow comparisons to
separate upstream execution from application overhead. Pin versions, datasets,
references, parameters and threads; use the same physical hardware with separate
Windows/Linux installations where practical. Record hardware/storage and OS
configuration. Measure first-use installation/downloads separately from offline
analysis, repeat cold/warm runs, and evaluate meaningful scientific outputs with
predeclared equivalence criteria. Document memory-counter differences rather
than comparing Windows committed-memory peaks directly to Linux maximum RSS.
Preserve failed, cancelled and unavailable measurements. Small installation
fixtures do not establish realistic cohort capacity or performance parity.

## Historical backlog, 2026-10-05

The original dated planning record follows unchanged. Its proposed catalogue
publication was subsequently completed; the signed 32-pack catalogue and
application 0.11.0 are already published. Items here describe their original
date, not current release blockers. Resolve current implementation questions
against the active milestone and maintained state above.

Snapshot: 2026-10-05. These are proposed priorities derived from the current
gaps, not a promise of functionality or authorization for external actions.
Check [current state](current-state.md) before starting; newer work may have
closed a gap. STAR, kallisto, FastQC, MultiQC, featureCounts, BEDTools, BLAST,
GATK, SnpEff, DESeq2, mosdepth and IQ-TREE packs have already been published;
adding their first versions is no longer an outstanding task. The four newest
packs passed exact-final native Windows installation, graph and scientific gates;
this does not close desktop acceptance or catalogue deployment. The 0.7 source
now implements Ensembl archive reference discovery/download and frozen run
provenance; see current-state for its separately recorded release evidence.

| Priority | Work | Completion evidence |
| --- | --- | --- |
| 1 | Validate the current native desktop experience on representative Windows machines. | Named app/pack hashes, Windows versions and reports for launch, library selection, standalone tools, settings/pipeline saves, step removal, branched/merged DAGs, provenance, resizing/scrolling, cancellation and pack management. Separate ordinary, spaced, Unicode and long-path behavior. Check declared path-policy rejections as rejections, not successful analysis. |
| 1 | Complete signed online catalogue publication when the maintainer supplies a controlled signing key. | Public signed catalogue and independently verified source fingerprint; import into a clean app, refresh/install/check a small pack; retain offline operation. Existing 0.6 archives remain unchanged. See the publishing guide for the pending trust setup. |
| 1 | Bring the future catalogue release map up to the actual public inventory. | Include the RNA, October optional, GATK, SnpEff, DESeq2, mosdepth and IQ-TREE packs with source/evidence metadata, including DESeq2's separate R-runtime source companion; explicitly handle superseded kallisto 1.0.0 while retaining it for saved pins. Revalidate all archives before signing. The old 18-pack map is not an up-to-date feed. |
| 2 | Make clean-checkout build recovery less dependent on historical source companions. | Document and verify pinned prerequisites for each supported build; retain corresponding source and licences; remove accidental dependence on a previous agent's temporary paths. Demonstrate a selected pack rebuild from the documented inputs. |
| 2 | Extend native Windows scientific coverage across the older packs. | A per-pack evidence matrix with exact archive/app hashes, supported operations, actual defaults, failure checks and scientific assertions. Do not extrapolate the newer packs' native CI passes to older tools. |
| 2 | Benchmark realistic workloads and resources. | Redistributable or explicitly authorised data, fixed versions/parameters, independent reference results, timing/RAM/disk measurements, hardware and OS details. Keep synthetic installation tests separate. Human-scale performance remains unestablished by the synthetic fixtures. |
| 3 | Improve reusable index contracts, especially STAR. | Versioned directory-valued products or another explicit model, atomic completeness checks, reference/tool/index identity, graph compatibility and migration tests. Current STAR and BLAST operations deliberately rebuild private indexes per run. |
| 3 | Design a dedicated gVCF graph type if expanding cohort workflows. | Versioned core/schema support, static separation from ordinary VCF and unrelated generic files, preserved old pipeline pins and adapter-level format/reference/sample checks. GATK 1.0.0 deliberately uses labelled generic file ports on released 0.6.0; its two-to-32-input CombineGVCFs operation does not establish GenomicsDB or large-cohort support. |
| 3 | Broaden the reference providers and large-download experience. | The initial provider supports Ensembl archive 100–116, local reuse and frozen provenance. Consider new-platform Ensembl once its download layout is stable, NCBI/RefSeq, explicit known-site bundles, resumable transfers and reference relocation. Each needs provider-specific identity, checksum, cancellation and compatibility evidence. Keep Kraken/Bracken databases and SnpEff codon mappings separate from executable packs. |
| 3 | Extend differential-expression designs only when a concrete need is established. | DESeq2 now supplies bulk gene-level differential expression and kallisto transcript-to-gene import for condition or additive batch-plus-condition designs. Paired/repeated measures, continuous covariates, interactions and single-cell analyses remain outside that interface. Any extension needs explicit experiment-design contracts, independent upstream/known-answer tests and a new pack version; broad metrics ports alone cannot establish valid raw counts or biological replication. |

Do not combine all of these into an uncontrolled redesign. Choose one concrete
gap, inspect the current code, define acceptance evidence, and make a bounded
change. Keep the app/pack boundary intact.

## Questions to resolve when the relevant task starts

- Who controls catalogue signing, where is its public fingerprint recorded, and
  how are key rotation and recovery handled? The private key must not be stored
  in this repository or supplied through a public document.
- Which Windows versions, hardware limits and institutional application-control
  configurations are supported? Current source/CI evidence is not a support
  matrix for every managed PC.
- Which RNA-seq workloads and reference sizes should drive reusable-index and
  resource design? Small synthetic checks cannot answer capacity questions.
- What reference providers, reporting outputs and additional tools do actual
  users need next? The Galaxy Tool Shed can inform tool selection, but a Galaxy
  wrapper is not by itself a Windows port, licence audit or scientific contract.

Keep resolved answers in the decision record and the relevant technical page.
