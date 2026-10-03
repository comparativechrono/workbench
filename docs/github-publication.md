# Publication plan: comparativechrono/workbench

This document describes publication of the existing 0.6.0 files for
`https://github.com/comparativechrono/workbench`. Nothing here has been uploaded,
and no production signing key or trusted source file has been created. The URLs
below are proposed publication locations; their live availability is unverified.

One repository is sufficient. Separate tags and release assets give the app and
packs independent lifecycles; a second repository is not required. This layout
supersedes the SDK documentation's earlier suggestion to use two repositories.

| Component | Tag or branch | Contents |
| --- | --- | --- |
| Application | release tag `app-v0.6.0` | Starter, 0.5.4 updater, SDK, full source companion, README, checksums and verification report |
| Each pack | release tag `pack-<id>-v<version>` | Its existing independently installable ZIP; release notes link the corresponding source companion |
| Catalogue | branch `catalogue` | Signed `catalogue.json`, public `source.json`, publication report and retained catalogue history |

`publishing/publication-layout-0.6.0.json` lists every exact proposed URL and all 18 pack release
tags. Existing pack IDs and versions are preserved, including `align`, `bam`,
`variants` and `fastp` 0.4.1. A future app release uses another app tag; a future
tool release uses another pack tag. Neither requires rebuilding the other.
Never replace a published pack ZIP under an existing pack/version identity.

The stable catalogue URL will be:

`https://raw.githubusercontent.com/comparativechrono/workbench/catalogue/catalogue.json`

The public source/trust file will be:

`https://raw.githubusercontent.com/comparativechrono/workbench/catalogue/source.json`

The current source companion's planned location is:

`https://github.com/comparativechrono/workbench/releases/download/app-v0.6.0/native-workbench-0.6.0-source.zip`

Each pack already retains its own licence/source materials. Preserve this full
source companion too: it includes application source and recovery references to
the exact companion pack archives. Future pack releases need their own matching
source/provenance records; do not point a changed pack to unrelated old sources.

## Prepared files and generation commands

`publishing/releases-0.6.0.json` maps all 18 existing pack ZIPs to their independent release
URLs. Relative local paths resolve against the `publishing/` directory. Place the unchanged application and pack assets in an ignored `release-assets/` directory at the repository root, preserving its `packs/` subdirectory. The unsigned preview
was produced by the real publisher, which re-reads archives and validates hashes,
inventories, manifest identities and metadata. It is not an application-trusted
catalogue.

From the repository root, the preview command is:

```bash
python3 scripts/publish_pack_catalog.py \
  --release-map publishing/releases-0.6.0.json \
  --unsigned-preview \
  --output release-assets/catalogue-preview-001
```

A preview was validated during preparation. Use a new output directory for each generation; the publisher deliberately refuses to overwrite output.

Once the publisher's external private key is available, generate the signed
catalogue and actual source file with this command. Replace the example private
key path with its real protected location outside the source checkout and output
directory; this command has not been run:

```bash
python3 scripts/publish_pack_catalog.py \
  --release-map publishing/releases-0.6.0.json \
  --private-key /protected-release-keys/workbench-catalogue.pem \
  --source-id comparativechrono-workbench \
  --source-name "Comparative Chrono Workbench tools" \
  --catalog-url https://raw.githubusercontent.com/comparativechrono/workbench/catalogue/catalogue.json \
  --output release-assets/signed-001
```

The publisher derives public-key material from the supplied RSA key, signs the
catalogue and verifies it through the application validator. It emits
`catalogue.json`, `source.json` and `publication-report.json`. The resulting
source permits the exact hosts `github.com`, `raw.githubusercontent.com` and
`release-assets.githubusercontent.com`. It performs no uploads. Do not manually
invent a public key or publish the unsigned preview in place of a signed wrapper.

## Publication sequence

1. Review the source snapshot, release evidence and actual Windows checks. Keep
   the existing archives byte-for-byte intact and match `SHA256SUMS.txt`.
2. Publish the `app-v0.6.0` development prerelease and its seven listed assets. Publish the 18
   pack releases using the exact tags/assets in `publishing/publication-layout-0.6.0.json`.
3. Download the published assets through their final URLs and verify their
   hashes. Keep older tags/assets available for saved pipelines.
4. Generate the signed documents. Commit them to the `catalogue` branch only
   after the referenced assets are downloadable. Preserve previous signed
   catalogues under dated history paths and keep publication timestamps increasing.
5. Verify the public-key fingerprint independently, import the real `source.json`
   into a clean app, refresh and install a small pack. Run a native Windows
   scientific check and an offline check before announcing availability.

The unchanged 0.6.0 archives contain an empty default source list. Users can
import the published `source.json` once. To remove that setup step in a later
app build, include the reviewed source object in
`workspace/catalog-sources.json` and produce a new versioned app release; do not
silently modify the already checksummed 0.6.0 archives.

## Still required

- GitHub authorization with permission to create the chosen releases, upload
  their assets and update the catalogue branch in this repository.
- A publisher-controlled RSA signing key: 2048–4096 bits, exponent 65537. The
  current CLI consumes an externally provisioned unencrypted PEM; it never
  creates or uploads the key. No key has been supplied or generated here.
- A recorded source-key fingerprint and confirmation of the desired public
  release timing after publication/download and native Windows checks.

GitHub credentials and the catalogue signing key serve different purposes.
Neither belongs in the repository, pack ZIPs, source archive or public catalogue.
