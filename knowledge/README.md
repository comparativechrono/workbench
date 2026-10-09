# Native Workbench knowledge base

**Active development, 2026-10-08:** the owner accepted the
[feature roadmap](roadmap.md). Unpublished **0.12.0** begins with
[readiness, performance records and diagnostic export](readiness-performance.md)
on `feature/readiness-performance`. Published 0.11.0 remains the baseline;
the first implementation tranche has passed its recorded exact-candidate checks
and screenshot review in [draft PR #7](https://github.com/comparativechrono/workbench/pull/7).
Representative-machine acceptance, benchmarking and release work remain separate.

This is the durable handover for people and agents continuing Native Workbench.
It records why the project exists, how it works, how to extend it, and which
claims the evidence supports. It is stored as plain UTF-8 Markdown and JSON:
open, diffable files with no proprietary reader or external memory service.
"Knowledge base" describes this directory; it does not claim compliance with a
separate standard called Open Knowledge Format.

**Reviewed:** 2026-10-07. **Starting source baseline:**
[`8f95caa1f267d19ce72ea3cd7f2396ae66a801c1`](https://github.com/comparativechrono/workbench/commit/8f95caa1f267d19ce72ea3cd7f2396ae66a801c1).
This handover includes the 0.7 reference-discovery implementation and
Kraken2/Bracken metagenomics after the annotation,
expression, coverage and phylogenetics expansion. SnpEff, DESeq2, mosdepth and IQ-TREE have successful
exact-final Windows installation, graph and scientific gates. Evidence for
each release retains its own date and tested bytes. Re-check the current tree
and releases before treating this snapshot as current.

The [0.8.0 native interface](native-ui.md) was published as a development
prerelease after user acceptance; [PR #1](https://github.com/comparativechrono/workbench/pull/1)
is merged. The release promotes the exact tested candidate bytes without a
rebuild. All nine public assets were independently downloaded and hash-verified;
see the
[0.8.0 release handover](native-ui-0.8.0-release-handover.md). Testers
accepted its layout and reported workflow/input, scrolling and navigation
issues. The 2026-10-06 revision adds explicit reusable workflow inputs and
navigation controls, fixes native repaint/first-open errors and clarifies
scientific tool names. The first feedback candidate's **75 source checks passed**, followed by **32
workspace checks and 8 References/update checks in each Windows path**, with
zero failures or skips. These include native workflow pointer interactions,
scroll repaint comparison and a 202-record minimap2 SAM-to-sorted-BAM run. The
[feedback record](evidence/native-workflow-0.8.0-feedback-2026-10-06.json)
retains an earlier scientific-assertion failure and keeps the revised candidate
separate from the
[successful 2026-10-05 candidate](evidence/native-ui-0.8.0-development-2026-10-05.json).
The guide retains tested candidate identities and identifies untested physical
trackpad/display scenarios. A later user report exposed a separate ordinary-path
I/O failure on a 269-character pipeline output. The corrected candidate passed
**82 CI source checks**, the repeated **32+8 native checks per path**, and a new
long-path regression that reproduces the old error and passes the full corrected
starter pipeline with machine long-path policy disabled. All 20 pipeline output
hashes were checked, including the expected variant-call truth. The fix preserves
ordinary provenance identities and uses extended paths at filesystem boundaries.
See the
[sanitized long-path record](evidence/native-workflow-0.8.0-long-path-2026-10-06.json).
Earlier native passes did not establish this deep-output-path behavior.
The user subsequently confirmed that the pipeline fix worked, while reporting
that text still flashes during scrolling. That pipeline confirmation is user
acceptance of the reported fix, not a new automated run or acceptance of all
display behavior. The earlier scroll check compared settled images and did not
observe intermediate frames. The further revision at `b3928ca` adds composited
form panels, suppresses redundant redraws and accumulates small wheel deltas.
Its [exact-package native run](https://github.com/comparativechrono/workbench/actions/runs/37453380541)
passed all five jobs. Across three panels, 960 sampled desktop frames showed
no unexpected text/background image and all 300 requested endpoint transitions
were observed; all 18 precision-wheel cases passed. The old package also showed
no unexpected frames, so the tester's visual flashing was **not reproduced in
CI**. Six old precision-wheel cases did fail and now pass; that is a separately
reproduced movement defect. The [scroll record](evidence/native-workflow-0.8.0-scroll-2026-10-06.json)
retains these limits and the verified candidate download. The user's subsequent
acceptance supersedes the pending tester-confirmation status; it is user-reported
acceptance, not a new CI observation or broader display-coverage claim.
Version 0.8.0 was published at **2026-10-06T13:12:15Z** as
[app-v0.8.0](https://github.com/comparativechrono/workbench/releases/tag/app-v0.8.0).
Published 0.7.0 and its evidence remain unchanged.

The **0.9.0** CWL export, routed DAG and SVG-derived icon release is now
[published](https://github.com/comparativechrono/workbench/releases/tag/app-v0.9.0)
after exact-package checks and user acceptance. The release promotes application
source `beea34a` unchanged; PR #2 and tag point to `1ee61f1`. Its separate updater
from 0.8.0 passed 13 native checks per path, and the publication workflow verified
all 12 public assets by anonymous download. A separate independent audit also
verified all 12 assets, five ZIP CRCs and three checksum manifests. See the
[0.9.0 handover](cwl-dag-icon-0.9.0-handover.md) and [CWL feature guide](cwl-results.md).

- [Tool Setup 0.10.1 patch handover](tool-setup-0.10.1-handover.md) — scrolling/repaint regression, download diagnostics and exact-candidate evidence; publication status is recorded there.
- [Expandable tool library](expandable-tool-library.md) — 0.11.0 development candidate with native category browsing; validation and release status are recorded separately from 0.10.1.

## Reading order

| File | Question it answers |
| --- | --- |
| [Purpose and decisions](purpose-and-decisions.md) | Who is this for, what approach was chosen, and what must not be lost? |
| [Current state](current-state.md) | What is released, tested, limited or unfinished? |
| [Architecture](architecture.md) | Where does each responsibility live, and how does a run work? |
| [Native UI development](native-ui.md) | How do the three panes, standalone tools and workflow canvas work, and what remains to validate? |
| [0.9.0 handover](cwl-dag-icon-0.9.0-handover.md) | Which CWL/DAG/icon bytes were accepted and published, and what passed? |
| [Tool setup](tool-setup.md) | How do Full, Starter and Custom installation work, and what remains before official deployment? |
| [0.10.0 setup handover](tool-setup-0.10.0-handover.md) | Which exact 0.10.0 files were published, and what did their Windows and public-download checks establish? |
| [CWL results](cwl-results.md) | What does an exported workflow contain and what does external execution require? |
| [0.8.0 release handover](native-ui-0.8.0-release-handover.md) | Which exact native-interface bytes were accepted and published? |
| [Starter tool semantics](starter-tool-semantics.md) | Which program does each starter operation run, how does SAM become BAM, and what does faidx mean? |
| [Reference discovery](../docs/reference-discovery-0.7.md) | How are references found, downloaded, reused offline and recorded in runs? |
| [Development](development.md) | How do I recover inputs, build, test and resume work? |
| [Pack development](pack-development.md) | How do I add a real tool without rebuilding the app? |
| [Validation and releases](validation-and-releases.md) | What establishes correctness, and how are artifacts published and trusted? |
| [Catalogue signing](../publishing/catalogue-signing.md) | How does the protected official publisher work, and which one-time owner settings remain necessary? |
| [Roadmap](roadmap.md) | What should be addressed next, and what would count as completion? |
| [Readiness and performance development](readiness-performance.md) | What does the first accepted roadmap milestone implement, and which measurements/privacy/validation limits apply? |
| [Project index](project.json) | Machine-readable entry points and stable constraints. |
| [Release inventory](release-inventory.json) | Dated public versions, download assets, checksums and evidence pointers. |

The repository-root [AGENTS.md](../AGENTS.md) is the short onboarding entry point.
For a new pack, read the pack guide and validation guide together. For a UI or
engine change, start with architecture and development, then check the accepted
interaction decisions.

## Evidence and authority

- Product requirements and design history come from the project owner's
  development conversation, captured explicitly in the decision record. They
  are requirements, not proof that every feature is fully implemented.
- Each dated topic identifies its reviewed source or validation checkpoint;
  newer development is separate from the starting baseline above. Source links
  are repository-relative so they work in a clone and on GitHub.
- Release facts come from published release metadata, accompanying reports and
  named CI runs. A historical pass applies to the tested bytes and environment.
- Proposed next work is labelled as such. Missing evidence is kept visible.

If a page disagrees with current code, reproduce or inspect the behavior and
update the page. Do not change a scientific result or loosen validation merely
to make documentation appear true. Do not let implementation drift silently
override an explicit product requirement: explain the conflict first.

Older documents remain useful for source recovery and release-specific details.
In particular, [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) describes the first
experimental computation module, not the complete current application.
[docs/pack-development-0.6.md](../docs/pack-development-0.6.md) originally
recommended two repositories; its guidance is now corrected to this one
repository with independent application and pack tags. The 18-pack lists under `publishing/`
describe the original 0.6 split, before STAR, kallisto and the later optional
packs. Do not mistake these historical inventories for the latest complete list.

The GATK 1.0.0 source/evidence companion includes a complete `knowledge/` snapshot
and root `AGENTS.md`. Its creation-time pending-final-gate statements remain
historical; use the separate final validation record for completed evidence.
The 0.7 application source packager now includes root `AGENTS.md`, this complete
handover, recursive documentation and workflow definitions in its hashed source
inventory. The older 0.6 source companion remains unchanged.

For the four newer packs, start with the
[connection and installation overview](../docs/ANNOTATION-EXPRESSION-COVERAGE-PHYLOGENETICS.md),
then the individual guides. Preserve each release's source/evidence snapshot and
separate final validation report. DESeq2's R-runtime corresponding sources are a
second release asset, with their own file lock and runtime-bound hash; the small
source/evidence ZIP does not contain those third-party archives. See
[source recovery details](../tools/deseq2/R-RUNTIME-SOURCES.md) and the maintained
pack-development and validation pages before rebuilding.

The [Kraken2/Bracken pipeline guide](../docs/KRAKEN2-BRACKEN-PIPELINE.md) and
[shared resource specification](../docs/METAGENOMICS-RESOURCES.md) describe local
database preparation, descriptor identities, fragment/read semantics and
explicit external-model declarations. Both exact-final packs have successful
Windows installation, graph and scientific evidence. Preserve their full
source/evidence companions and separate final validation records; large
scientific databases are user-selected inputs and are not included in the packs.

## Maintaining the handover

Keep facts close to their source rather than duplicating full specifications.
After a change, update the affected topic and its evidence link. Refresh the
dated current-state/inventory snapshot after a release; do not rewrite an old
successful result to refer to newly built bytes. Preserve superseded versions
and the reason a decision changed.

Before handing work to another agent, record:

1. The task, branch/commit, changed files and whether changes are published.
2. Decisions made and compatibility or scientific behavior affected.
3. Exact verification commands, environment, results, skips and artifact hashes.
4. Remaining work, blockers and the smallest next action.
5. Durable source/evidence locations; avoid relying on a temporary workspace,
   an active browser session or a previous agent's private memory.

Never add patient data, credentials, private keys, account tokens or temporary
session details to this public directory. Synthetic scientific fixtures and
publicly redistributable source/evidence are suitable.
