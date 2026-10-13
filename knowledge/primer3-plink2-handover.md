# Primer3 and PLINK2 optional packs

Date: 2026-10-13. Status: implementation complete; exact Windows validation pending.

The owner requested the next roadmap stage, Primer3 and PLINK2. Development is
on `feature/primer3-plink2-packs`, based on reviewed Kalign delivery
`8c0321d0cf04751a7c921d42098bed13ebb7b11a`, tree
`4c126c5c06fdf554dc02a24af3e3a73347220a3b`. Kalign PR #17 remains draft and
unmerged; this new review will be stacked on `feature/kalign-pack`. PR #16's
existing integration merge is preserved. No additional merge, release or
catalogue publication was requested. Published application 0.16.0 and the
existing 0.16.1 UI candidate remain unchanged.

## Initial supported operations

- Independent `primer3` 1.0.0: `design-pcr`, standard paired PCR primer design
  from one local, uncompressed DNA FASTA template. Expose meaningful product-size,
  primer-size, melting-temperature and chemistry settings. Record primer
  sequences, binding coordinates, product size and actual upstream measurements.
  No whole-genome specificity, in-silico PCR, probe or clinical claim.
- Independent `plink2` 1.0.0: `summarize-vcf`, allele/genotype counts and sample/
  variant missingness for a bounded, validated set of diploid biallelic human
  autosomal SNP hardcalls from uncompressed VCF. Do not silently filter variants,
  convert dosages or invent QC pass thresholds. PCA and association testing are
  later interfaces with additional scientific and dependency contracts.

Use pinned real upstream scientific executables, narrow compatibility changes,
native guards, explicit typed inputs and complete corresponding source/licences.
Primer3 uses unmodified 2.6.1 at `7f9f17d6012f404e83bbf0f931a4d06eb4af465b`;
PLINK2 uses unmodified 2.0.0-a.7.12 at `5c1f185d4144e62fa23087d68760162f712cd2a8`
with the documented no-LAPACK build and pinned zlib 1.3.2. Full source, notices
and byte identities are retained by the recipes. Pack versions are independent
of the unchanged application version. Local Linux suites passed 15 Primer3 and
17 PLINK2 tests, zero skips; Primer3 included three fresh pristine reference
cases. Native Windows cross-compilation and static archive checks passed, but
these are not native execution evidence.

## Validation and delivery

Independent synthetic primer binding/product truth and genotype-count/missingness
truth must support meaningful source and native checks. Execute the exact frozen
pack ZIPs in ordinary and spaced Windows paths, with import/integrity, saved pins,
normal graph runs, Methods/provenance, searchable Results and Starter regressions.
Inspect all native form pages and actual displayed screenshots on the immutable
0.16.1 application. Prior Kalign or application passes do not validate these packs.

Retain raw reports, source and archive hashes, failed attempts and scope limits.
Save a draft review PR with matching download/source/evidence links. No automatic
merge or publication follows. Representative-PC acceptance, scientific Linux
CWL, benchmarking, signing/institutional deployment and release/updater validation
remain separate. Pack-specific JSON measurement tiles require existing parser
support; output files do not imply native summary parsing.
