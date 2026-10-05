# Remaining work and suggested next steps

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
