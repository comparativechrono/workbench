# Validation, releases and publisher trust

Status: maintained handover, audited against repository commit
`1b537869e9d88e493078e1a1f241d16013273f44` on 2026-10-04.
This is an operational procedure, not a claim that every historical pack has
passed every gate. See [the knowledge index](README.md) for current status and
[pack development](pack-development.md) for authoring contracts.

## Separate the kinds of evidence

| Evidence | What it establishes | What it does not establish |
| --- | --- | --- |
| Archive/static validation | Schema, inventories, identity, declared hashes and safe paths | Scientific correctness or executable startup |
| Core unit/contract tests | Parser, graph, trust, transaction and reporting behavior covered by those tests | Operation of every optional tool |
| Linux scientific execution | Known-answer/upstream agreement for the identified Linux binaries | Native Windows execution |
| Native Windows pack gate | Real execution through a released app's native bridge, import and fixture checks | Full GUI behavior, every path, large datasets or clinical validity |
| Manual Windows deployment/UI check | The recorded interactions on that machine and policy configuration | Approval in other institutions or unrestricted platform support |
| Real-data benchmark | Specified dataset, truth, versions, parameters and resources | General accuracy or all protocols |

Always record failed and skipped checks, substituted backends and exact tested
versions. A suite that silently skips because compiled fixtures are absent is
not evidence of a working release. The historical app test count is a dated
observation, not a permanent release target.

## Scientific verification method

Use small, public/synthetic fixtures with independent expected answers. Include
the actual biological properties relevant to the tool: sequences, mapping
positions/CIGAR/flags, splice junctions, alleles/genotypes, abundance estimates,
or expected absence of calls. Avoid producing expected results solely by running
the same implementation. A pinned upstream implementation is useful as a second
comparison, alongside known truth.

Exercise the normal graph engine and actual UI defaults. Include paired/single
operations, relevant compression and strand modes, malformed or incompatible
inputs, empty valid outcomes, optional features and meaningful concurrency.
Validate that failure does not yield apparently complete successful results.
Use tolerances only with a scientific reason; retain exact outputs/hashes where
determinism permits. A seed can be reproducible within a build without ensuring
identical draws across different standard-library implementations.

`workbench-checks.json` uses bounded assertions and pinned fixture assets, not
embedded commands or Python expressions. The ordinary installed backend runs
them through **Check installation**. Add richer regression cases in `tests/`
where fixture assertions cannot express the required property. Relevant code:
[pack checks](../workspace/pack_checks.py),
[scientific metadata](../workspace/PACK-METADATA.md), and
[independent FASTQ oracle notes](../tests/README.md).

For source changes, run focused tests covering the affected contract and any
required release gate. Core application tests should use artificial packs and
not require every optional scientific tool. Optional packs get independent
validation. Do not repeatedly run a broad suite simply to increase a count.

## Released-app compatibility

Test against the oldest declared supported app and the current app. Loading a
new pack into edited checkout code does not prove compatibility with a shipped
application. Keep the released app and starter packs unchanged, verify their
hashes, and use a disposable extraction for each test.

The RNA contract suite checks the released 0.6.0 Python graph/archive contracts
without running scientific executables. Run it in a fresh Python process, with
both exact RNA pack versions present in the disposable released app and their
ZIPs available. Explicitly set the kallisto version: the suite's historical
default is 1.0.0, while the current version is 1.0.1.

```sh
NW_RNASEQ_APP_ROOT=/path/to/disposable/native-workbench \
NW_RNASEQ_ARCHIVE_DIR=/path/to/rna-pack-zips \
NW_RNASEQ_STARTER_ZIP=/path/to/native-workbench-0.6.0-starter-windows.zip \
NW_RNASEQ_STAR_VERSION=1.0.0 \
NW_RNASEQ_KALLISTO_VERSION=1.0.1 \
python3 tests/test_rnaseq_pipeline.py --report /path/to/evidence/rna-contracts.json
```

The app tree must be assembled beforehand with the exact packs; this command
does not fetch or assemble it. Its archive import test substitutes a copy
callback for native folder publication and explicitly reports that no native
importer or scientific executable ran. Do not describe this as the Windows gate.

The October pack contract suite additionally checks FastQC fan-in to MultiQC,
STAR RNA BAM fan-out to featureCounts branches, merged reporting, BEDTools FASTA
to BLAST, rejection of DNA/RNA and protein/nucleotide mismatches, explicit strand
choices and saved pins. It also compares every selected pack folder with its
exact ZIP payload. Like the RNA contract suite, its archive publication uses a
Python copy callback and runs no scientific executables or native importer.

```sh
NW_POPULAR_STARTER_ZIP=/path/to/native-workbench-0.6.0-starter-windows.zip \
NW_POPULAR_PACK_DIR=/path/to/prepared-packs \
NW_POPULAR_ARCHIVE_DIR=/path/to/exact-final-zips \
NW_POPULAR_STAR_ARCHIVE=/path/to/native-workbench-pack-star-1.0.0.zip \
NW_POPULAR_TEMP_DIR=/path/to/disposable-applications \
python3 tests/test_popular_pipeline.py --report /path/to/evidence/popular-contracts.json
```

The [2026-10-04 report](evidence/popular-pack-graph-contracts-2026-10-04.json) records
8/8 passing tests with no failures, errors or skips on Linux/Python 3.12.14.
Its SHA-256 is
`5c4d53d4067070b09af5d3e7698b3fbb06fcba92e4a454ff7d70c4fd7ae4f0ad`.
The first attempt failed the strict immutability assertion when an unexplained
transient Java source file disappeared from a prepared pack. A fresh run passed
without changing pack bytes, weakening assertions or replacing the failed record.
Its diagnostic record remains separate from this successful final report.
The [earlier successful proposal report](evidence/popular-pack-graph-contracts-before-blast-diagnostics-2026-10-04.json)
is also retained with its original hashes. Its old BLAST guard later failed
native error-output checks, so the suite was rerun against the corrected final
archive. The current suite compares the archive against the actual disposable
graph-tested pack copy, avoiding races with another build's preparation folder.

All five packs and STAR are required. Per-pack `NW_POPULAR_<ID>_PACK_DIR` and
`NW_POPULAR_<ID>_ARCHIVE` overrides select isolated frozen builds. A missing-pack
skip is not a passing compatibility check. See current release evidence for the
recorded run rather than assuming the command has been run on a fresh checkout.

## Native Windows pack gate

Package once, freeze the archive, and calculate its SHA-256. On Windows, use a
fresh extraction of a SHA-verified released application. From a developer
checkout, using the released application's bundled Python:

```powershell
& C:/ci/app/native-workbench/runtime/python/python.exe -I scripts/check_pack_release_windows.py --app-root C:/ci/app/native-workbench --archive C:/releases/native-workbench-pack-example-1.0.0.zip --report C:/ci/evidence/native-pack.json
```

The [gate](../scripts/check_pack_release_windows.py) refuses Linux, imports the
archive through the released app, executes the pack's declared checks using
`WorkbenchBridge.exe`, requires nonzero successful checks, and verifies
duplicate-version rejection without manifest replacement. It performs no
network requests. It modifies the disposable app; do not point it at a user's
working installation. Retain the JSON evidence and check
`nativeWindowsHost`, `nativeWindowsExecuted`, exact pack identity, check results,
duplicate rejection and success rather than quoting only the process exit code.

The repository's manually dispatched
[Native Windows pack check workflow](../.github/workflows/native-pack-check.yml)
takes `release_tag`, exact `asset_name` and `asset_sha256`. It runs on
`windows-2022` in two paths, `ordinary` and `path with spaces`. It verifies the
candidate archive and the released starter, then downloads the check helper
from the workflow's exact source commit. The pinned starter is:

- Release: [app-v0.6.0](https://github.com/comparativechrono/workbench/releases/tag/app-v0.6.0)
- Asset: `native-workbench-0.6.0-starter-windows.zip`
- SHA-256: `16fa802304c734b5721d838ff38b7e90ed36ccfc185a22239859cc3762af695a`

The workflow uses `contents: read`, has no catalogue key and publishes nothing.
Its release lookup currently examines the first 100 releases. Older releases
outside that page need a reviewed lookup improvement. Despite the input label
mentioning drafts, the read-only workflow token did not see draft candidates in
the RNA release work. Use separately versioned, clearly labelled public
prerelease candidates when needed; do not broaden token privileges simply to
make a draft visible.

Extra regressions have deliberately narrow scope:

- `check_star_chunks_windows.py` runs for the exact STAR 1.0.0 asset and checks
  repeated input/output chunks using real paired alignments and gene counts.
- `check_kallisto_defaults_windows.py` runs only for the old kallisto 1.0.0 asset,
  whose original fixture used one thread. kallisto 1.0.1's own installation checks
  now use two threads and three bootstraps. Do not apply the old helper's
  one-thread-fixture assumption to 1.0.1.
- `tools/blast/check_offline.py` runs for BLAST pack assets. It checks installed
  hashes, known alignment coordinates in a directory with spaces, missing local
  database failures, malformed FASTA and rejection of remote arguments. Its
  explicit `osNetworkBlocked: false` records that CI did not disable networking;
  the regression is code-path evidence, not a firewall test.

The matrix alone does not prove Unicode/long-path support, offline network
blocking, cancellation, interactive GUI behavior or institutional deployment.
Record those separately, including expected rejection for a pack's declared
path limitations. Test upgrades beside old versions, saved graph pins, unchanged
inputs, failed subprocess cleanup and methods/provenance. Test real offline
behavior with networking disabled after obtaining approved installers.

## Freeze, publish and verify

1. Assign the stable pack ID and a new numeric pack version. Finalize executable,
   metadata, README, fixtures and license/source contents before packaging.
2. Run `scripts/package_split.py pack` and
   `scripts/validate_pack_release.py`; retain the reported archive/manifest
   hashes and inventory. Review the actual ZIP contents, not only local build
   folders. Test the exact candidate on native Windows.
3. Retain matching source, build/patch provenance, dependency notices and test
   evidence. If candidate and final versions differ, record the exact allowed
   differences and compare executable/command/schema/fixture bytes. A successful
   candidate does not excuse checking the exact final archive.
4. Publish independent tags `pack-<id>-v<version>` in this repository, with the
   installable ZIP and matching source/evidence assets. Application releases use
   `app-v<version>`. Preserve older tags/assets for saved pins. A failed published
   version receives a new version with a clear explanation, never replacement
   bytes under the old identity.
5. Download every final public asset independently and compare its size and
   SHA-256 with the frozen local artifact. Verify committed source bytes too.
   Run the native gate on the **exact final archive**, retain its run URL/report,
   and update release notes to describe actual results and remaining limits.
6. Once publisher trust is provisioned, publish a newly signed catalogue only
   after all its immutable asset URLs/hashes have been verified. Complete a
   clean-client refresh/download/install test before announcing online availability.

Testing a final archive may require publishing it first for the read-only CI
workflow to fetch it. Keep its status clearly identified as under validation
until that gate passes. Publication is not evidence of validation. Likewise, do
not promote a historical candidate or stale draft simply because its asset name
resembles the final release.

Build-time provenance may correctly say `windowsExecuted: false` because the
builder performed no Windows execution. Keep that record intact and attach
subsequent native evidence to the exact archive hash. Editing the archive to
change the flag would invalidate the artifact that was tested.

## Known exact-final release evidence

These records provide concrete examples of the method. They are small scientific
regressions, not human-scale performance benchmarks or clinical validation.

| Final pack | Exact final native run | Recorded scope |
| --- | --- | --- |
| [STAR 1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-star-v1.0.0) | [37149903110](https://github.com/comparativechrono/workbench/actions/runs/37149903110) | Five scientific checks per path, plus repeated-chunk paired alignment/count regression at two threads |
| [kallisto 1.0.1](https://github.com/comparativechrono/workbench/releases/tag/pack-kallisto-v1.0.1) | [37150386848](https://github.com/comparativechrono/workbench/actions/runs/37150386848) | Single/paired gzipped-read truth at two threads and three bootstraps in both paths |
| [FastQC 1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-fastqc-v1.0.0) | [37207251061](https://github.com/comparativechrono/workbench/actions/runs/37207251061) | Two checks per path: plain single/gzip paired reads, bases, GC, Q40 and report truth |
| [MultiQC 1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-multiqc-v1.0.0) | [37208730673](https://github.com/comparativechrono/workbench/actions/runs/37208730673) | One aggregation case per path with six selected reports and all five supported parsers |
| [featureCounts 1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-featurecounts-v1.0.0) | [37208535793](https://github.com/comparativechrono/workbench/actions/runs/37208535793) | Six checks per path, single/paired counts, three strand modes and two threads |
| [BEDTools 1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-bedtools-v1.0.0) | [37207758617](https://github.com/comparativechrono/workbench/actions/runs/37207758617) | Fifteen checks per path, including CRLF, empty outputs, 64-bit coordinates and strand extraction |
| [BLAST 1.0.0](https://github.com/comparativechrono/workbench/releases/tag/pack-blast-v1.0.0) | [37210341211](https://github.com/comparativechrono/workbench/actions/runs/37210341211) | Five scientific checks plus six adapter/local-failure regressions per path; four search modes, coordinates/frames, no hits, spaces, missing databases and invalid/remote arguments |

STAR final ZIP SHA-256:
`edbeefff1c1149b632407f50a8a28847989a34eaa004752b43680fb6e29e4877`.
kallisto final ZIP SHA-256:
`641cd1f2b05e0951b1f8a58f45d6308ca6206bf86bf90fb74d0daa2860f5eecd`.
The releases carry `native-workbench-star-1.0.0-windows-validation.json` and
`native-workbench-kallisto-1.0.1-windows-validation.json`, respectively, and
matching source/evidence companions. Historical candidate reports inside a
companion are not a substitute for the final archive's validation report.

Exact new archive hashes, final Windows evidence assets and matching source
companions are recorded in [the inventory](release-inventory.json). Every gate
also imports through the native bridge and verifies duplicate-version rejection.
The source/evidence ZIPs retain their creation-time status; separate final JSON
records supersede historical pending-final statements. BEDTools' source companion
contains an empty static-validation log; its separate final JSON supplies a fresh
complete static inventory/schema/hash verification. Preserve the published ZIP
and this explicit correction rather than silently replacing it.

`scripts/make_pack_validation_candidate.py` creates a separate numeric candidate
and a correspondence report from a frozen proposed final pack. Only the pack
version and permitted README prefix change; executable, commands, metadata,
fixtures and source must remain byte-identical. Candidate releases retain failures
and superseded trials for diagnosis, not as user installation recommendations.

The failures drove useful regression coverage: STAR could exit successfully
while producing no expected alignments because of the libc++ buffer behavior;
kallisto 1.0.0 omitted requested multithreaded plaintext bootstraps. The latter
remains available unchanged and is superseded by 1.0.1. Zero-bootstrap or
single-thread 1.0.0 behavior was not the failing case.

## Catalogue trust is a separate unfinished deployment step

As of the audit date, **the signed online catalogue and public `source.json`
trust file are not published/configured**. The released 0.6.0 app contains an
empty `workspace/catalog-sources.json`. Offline **Manage tools → Import pack ZIP**
works and verifies the inventory, but reports that the publisher has not been
authenticated. Do not turn a checksum list, unsigned preview, arbitrary GitHub
search result or test key into trusted production discovery.

[Catalogue publication](../docs/catalogue-publishing-0.6.md) defines the actual
mechanism: an externally provisioned maintainer RSA key (2048–4096 bits, exponent
65537), an explicit public source definition, approved HTTPS/redirect hosts, and
RSASSA-PKCS1-v1_5/SHA-256 signatures over exact payload bytes. The private key
stays outside the repository, archives and output directory; it is not generated
or uploaded by the publisher. GitHub credentials and catalogue signing keys have
different purposes. Never include either in handover documents or examples.

For a local unsigned inspection using a release map:

```sh
python3 scripts/publish_pack_catalog.py \
  --release-map /path/to/reviewed-release-map.json \
  --unsigned-preview \
  --output /path/to/new-preview-directory
```

The map must point to actual local archives and their verified immutable HTTPS
release URLs. `publishing/releases-0.6.0.json` is the historical map of the first
18 packs, not a complete current optional-pack map. Create/review an updated map
before a future catalogue publication. The script validates archives and emits
`catalogue-preview.UNSIGNED.json`; it does not upload or verify live URLs.

Once a maintainer supplies the intended external key, follow the signing command
in [GitHub publication](../docs/github-publication.md), using the updated map and
the final catalogue URL. Use a new output directory for each attempt. Review the
source-key fingerprint through a trusted channel, keep publication timestamps
increasing, and retain old signed catalogues. Key replacement requires explicit
source trust replacement. A catalogue signature does not authenticate a source
file obtained from an unknown party.

To make a reviewed source preinstalled later, create a **new application version**
with that source object in `workspace/catalog-sources.json`; do not modify the
already checksummed 0.6.0 release. Offline deployment and institutional mirrors
remain supported distribution approaches without uploading sample data.

## Evidence to leave for the next maintainer

For each release, leave a discoverable record of source commit, tag, app/pack/tool
versions, input archive and patch hashes, compiler/dependency identity, final
asset names/sizes/hashes, manifest hash, test commands/environment, passed/failed/
skipped results, native Windows run/report links, known limitations and matching
license/source companion contents. Distinguish proposed work from completed
checks. Keep synthetic fixture provenance and scientific expected answers with
the recipe. Never make a future maintainer depend on an ephemeral workspace,
private browser state or an unrecorded local compiler installation.
