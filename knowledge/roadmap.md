# Remaining work and suggested next steps

Snapshot: 2026-10-04. These are proposed priorities derived from the current
gaps, not a promise of functionality or authorization for external actions.
Check [current state](current-state.md) before starting; newer work may have
closed a gap. STAR and kallisto packs have already been published, so adding
their first versions is no longer an outstanding task.

| Priority | Work | Completion evidence |
| --- | --- | --- |
| 1 | Validate the current native desktop experience on representative Windows machines. | Named app/pack hashes, Windows versions and reports for launch, library selection, standalone tools, settings/pipeline saves, step removal, branched/merged DAGs, provenance, resizing/scrolling, cancellation and pack management. Separate ordinary, spaced, Unicode and long-path behavior. Check declared path-policy rejections as rejections, not successful analysis. |
| 1 | Complete signed online catalogue publication when the maintainer supplies a controlled signing key. | Public signed catalogue and independently verified source fingerprint; import into a clean app, refresh/install/check a small pack; retain offline operation. Existing 0.6 archives remain unchanged. See the publishing guide for the pending trust setup. |
| 1 | Bring the future catalogue release map up to the actual public inventory. | Include STAR 1.0.0 and kallisto 1.0.1 with source/evidence metadata; explicitly handle superseded kallisto 1.0.0 while retaining it for saved pins. Revalidate all archives before signing. The old 18-pack map is not an up-to-date feed. |
| 2 | Make clean-checkout build recovery less dependent on historical source companions. | Document and verify pinned prerequisites for each supported build; retain corresponding source and licences; remove accidental dependence on a previous agent's temporary paths. Demonstrate a selected pack rebuild from the documented inputs. |
| 2 | Include this handover in the next source companion. | Extend the fixed source selection in `scripts/package_split.py:build_sources` to include `knowledge/` and root `AGENTS.md`, and inspect the newly versioned source ZIP. This documentation change does not alter existing release archives or the current packager. |
| 2 | Extend native Windows scientific coverage across the older packs. | A per-pack evidence matrix with exact archive/app hashes, supported operations, actual defaults, failure checks and scientific assertions. Do not extrapolate STAR/kallisto CI passes to all tools. |
| 2 | Benchmark realistic workloads and resources. | Redistributable or explicitly authorised data, fixed versions/parameters, independent reference results, timing/RAM/disk measurements, hardware and OS details. Keep synthetic installation tests separate. Human-scale performance remains unestablished by the RNA fixtures. |
| 3 | Improve reusable index contracts, especially STAR. | Versioned directory-valued products or another explicit model, atomic completeness checks, reference/tool/index identity, graph compatibility and migration tests. Current STAR deliberately rebuilds a private index per run. |
| 3 | Broaden reference acquisition and reporting according to user needs. | Explicit assembly/annotation release selection, hashes/provenance, correct genome versus transcript input types, offline reuse, failure cleanup and reports tied to the originating step. Audit existing Ensembl/report support before implementing another path. |
| 3 | Extend RNA analysis beyond alignment and transcript quantification when requested. | Independently versioned packs with scientifically sound contracts, experiment-design inputs, citations and known-answer checks. Differential expression and transcript-to-gene aggregation are not supplied by STAR/kallisto alone. |

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
