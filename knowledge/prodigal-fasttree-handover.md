# Prodigal and FastTree pack batch

Date: 2026-10-13. Status: implementation and validation in progress; no pack
release or catalogue change has been published.

## Source and scope

Branch: `feature/prodigal-fasttree-packs`, based on
`fix/native-ui-0.16.1` at `2b2e97aa15970f0e7fb3a5428e8ab7dad6acada2`.
The existing wrapped toolshed and all other application changes are preserved.
Published application **0.16.0** and the unpublished **0.16.1** application
candidate are unchanged. The new pack identities are `prodigal` **1.0.0** and
`fasttree` **1.0.0**; these are independent of upstream tool versions.

- Prodigal: separate prokaryotic genome and metagenome prediction operations,
  explicit genome genetic-code settings, upstream metagenome model selection,
  GFF annotations and predicted protein/CDS FASTA products.
- FastTree: separate nucleotide and protein alignment operations, explicit
  substitution model, rate treatment, seed and optional SH-like local support.
  Outputs remain unrooted approximate maximum-likelihood trees; local support
  is not a conventional bootstrap or a posterior probability.

Both packs use pinned real upstream sources and private native executables.
Adapters validate file roles and preserve scientific results. No system Python,
WSL, Docker, online analysis or application-specific UI branch is introduced.

## Validation plan and current evidence

1. Build pinned upstream tools and native boundary adapters; retain full source,
   compiler identity, flags, licences, dependency imports and binary hashes.
2. Verify meaningful independent scientific fixtures and malformed-input
   failures on the host; host execution is not Windows evidence.
3. Freeze the exact installable ZIPs and matching source companion, then check
   import, known answers, provenance and graph contracts on Windows in ordinary
   paths and paths containing spaces.
4. Exercise native forms/results against the unchanged wrapped-library
   candidate, review actual screenshots and record their limitations.
5. Independently audit downloaded archives against tested commits and save the
   resulting evidence with the draft review PR.

Initial unchanged-core host checks: `tests/test_pack_manager.py` ran 47 tests
with one Windows-only skip; `tests/test_pack_checks.py` passed 14 tests and
`tests/test_pack_inventory_budget.py` passed four tests. These do not validate
the new packs. Pack-specific and native results will be recorded after execution.

Representative Windows PCs, broader display/CPU acceptance and realistic
workload benchmarking remain outside this batch. No synthetic fixture establishes
biological QC thresholds, clinical suitability or resource forecasts.
