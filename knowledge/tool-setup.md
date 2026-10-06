# Tool setup: Full, Starter and Custom

**Development target: 0.10.0. Not released.** The user approved this direction on
2026-10-06. Published 0.9.0 and all existing pack releases remain unchanged.
Official online setup is pending a maintainer-controlled signing key, reviewed
source configuration and the exact native release gates described below.

## Installing tools

Open **Tool setup** from the native application. A new installation offers it at
first launch; an existing installation can open it when the user chooses. Merely
opening the application or this window does not download anything.

| Choice | What it does |
| --- | --- |
| **Full — recommended** | Selects all 32 packs in this application's reviewed setup profile. Already installed exact versions are retained. |
| **Starter** | Keeps the three bundled packs: minimap2 alignment, SAMtools and BCFtools. No pack download is needed. |
| **Custom** | Keeps Starter and downloads the selected additional tools. |

Refresh the official catalogue to verify the available versions, review the
missing tools and download size, then choose Install. The setup window shows
progress for the current pack and the complete selection. Downloaded archives
must pass the existing pack manager's signed-catalogue, SHA-256, safe-path,
manifest, complete-file-inventory and compatibility checks before publication.

Cancel stops the current cancellable transfer; a short final publication step
must finish first. Completed packs remain installed. Failed, cancelled or
interrupted selections can be retried, including after reopening Workbench.
Retry retains the chosen versions, archive hashes, manifest hashes and publisher
key. The unfinished pack may need to download again; this is completed-pack
reuse, not byte-range resume of a partial archive. An error does not remove
working tools or silently change the selection to a newer pack.

Graceful cancellation removes the current temporary download/extraction. An
abrupt process termination can leave temporary installation directories; retry
does not treat those files as installed tools or delete directories whose live
ownership it cannot establish.

Installed tools remain available offline. **Manage tools** and offline pack
import remain available for future official packs and packs written by other
developers. Full is a convenient selection of independent packs, not a closed
list of what Workbench can run. References and scientific databases are still
separate, explicitly selected resources.

## Download and disk space

The [measured 32-pack assessment](full-bundle-sizing-2026-10-06.md) found a
**3.81 GB total download and 4.67 GB initial extracted files** including the
published 0.9.0 Starter. The new setup interface adds a small core change; its
exact packaged size must be measured from its own candidate.

A fresh Starter already contains three of the selected packs. The remaining 29
published archives total **3,795,572,848 bytes**. Setup's download estimate counts
only the missing selection. These numbers exclude reference databases, results,
filesystem allocation overhead, extraction working space and per-run expansion
of private runtimes. They are not a guarantee of sufficient storage or memory
for a particular analysis. Each existing pack keeps its licence and source trees;
no repacking or shared-runtime deduplication changes its scientific identity.

## Trust and deployment status

`workspace/setup-profile.json` contains reviewed pack identities, names and byte
sizes. `publishing/setup-assets.json` additionally locks the immutable release
URLs. Neither file authenticates a publisher. The official source must be a
reviewed entry in the application's `workspace/catalog-sources.json`, with ID
`native-workbench-official`; a user-imported source merely using the same ID is
insufficient to become the recommended setup source.

The production source list currently remains **empty**. No real catalogue key or
reviewed signed source document was available during this implementation.
Starter and offline imports work without it; Full and Custom cannot fetch
missing packs until the official source is deployed. A fixture catalogue can
exercise the mechanism, but cannot establish official production trust.

Follow [catalogue preparation](../publishing/setup-catalogue.md) to retrieve and
fully verify the immutable archives, prepare a release map, use the established
publisher with the maintainer's external RSA key, publish the signed documents,
review the public fingerprint and bundle the reviewed source. Private keys must
stay outside the checkout and public outputs. The application must then be
rebuilt and validated against those exact production trust bytes before release.
Existing independent pack/source releases remain the download authorities.

## Implementation and preservation

`workspace/setup_manager.py` owns profile selection, exact queues, per-pack
progress and persisted retry state at `user-data/tool-setup.json`. It uses the
existing `PackManager` downloader and native importer. `service.py` owns the
background worker and prevents conflicting tool/reference/check/setup jobs;
`desktop_host.py` exposes bounded `setup/*` calls through the private pipe.
`desktop/desktop_workspace.cpp` implements the native controls. This adds no
browser, listening HTTP server, administrator requirement or system Python.

`package_split.py` includes the setup module and profile in the core inventory.
It still bundles exactly the same three Starter packs, outside core ownership.
The source companion includes the setup code, knowledge pages, workflows and
only the curated public setup metadata from `publishing/`; that directory is
not swept for local signing/staging material.

`scripts/build_update_0100.py` creates the app-only 0.9.0-to-0.10.0 updater from
one exact starter ZIP and native updater launcher. The published baseline is
pinned to SHA-256
`c2661c144e073c4efdd190ffd186bacd9398b6413b81770d7a057c3947eecf02`.
It checks both core inventories, unchanged Starter pack bytes and the new setup
components, then verifies every replacement against the candidate. It performs
no network request or native execution. Existing packs and exact saved workflow
pins, user source configuration, setup queue, references and results remain
outside the core transaction. The application and updater versions advance to
0.10.0; pack API and pack versions do not change.

## Validation and remaining gates

The combined Linux source gate passed **136 tests**, with **one native-Windows
long-path check skipped** and no failures. It covers setup profiles, exact queue
and signing identities, cancellation/retry, state-write failures, private host
integration, pack import, catalogue publication and core packaging/upgrades.
The [source record](evidence/tool-setup-source-2026-10-06.json) pins the tested
files and lists every suite. The packaging checks below are included in that
total, not additional passes. The native desktop, bridge and updater also
cross-compiled using the pinned LLVM-MinGW with warnings as errors; compilation
does not establish native Windows execution.

The local Linux packaging/update checks performed during this implementation
passed **28 tests, zero failures or skips**:

```sh
python3 -m unittest discover -s tests -p 'test_setup_release.py' -v
python3 -m unittest discover -s tests -p 'test_split_release.py' -v
python3 -m unittest discover -s tests -p 'test_core_update.py' -v
```

Those tests establish synthetic archive/inventory and update-transaction
properties. They do not establish Windows behavior. Backend/UI/trust tests and
exact candidate results must retain their own dated evidence.

Before promoting a release, validate the exact packaged application in ordinary
and space-containing Windows paths: native Full/Starter/Custom interactions,
explicit refresh/install, signed downloads, cancellation, integrity failures,
restart/retry, offline operation, tool-catalogue refresh and mutual exclusion.
An all-32-pack coexistence check must retain every published pin and observe
startup/tool discovery without claiming every tool's scientific operations were
rerun. Existing scientific/UI/References/CWL gates remain separate.

`scripts/check_update_0100_windows.py` additionally checks the exact published
0.9.0 baseline and candidate updater, an existing optional pack, saved settings
and connected pinned workflow, actual reference results and receipts, every
preserved file hash, idempotent repeat update, and new offline scientific/CWL
execution. It uses the updater's private interpreter and does not claim native
updater folder-picker interaction or a live reference download. Its Windows
run is a required release gate, not a pass implied by the script existing.

The candidate workflow must retain input/output hashes, source commit, failures,
screenshots and native reports. After the production signed catalogue is
available, repeat a fresh online setup against that exact deployed trust and
verify public release downloads. No release, official catalogue availability or
unavailable native check is asserted by this guide.
