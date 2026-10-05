# Agent entry point

This repository is **Native Workbench**, a local Windows desktop application for
bioinformatics. Start with [knowledge/README.md](knowledge/README.md), then read
the topic relevant to the task. The knowledge directory is the maintained
handover; older versioned documents describe their historical releases.

## Before changing anything

1. Read [purpose and decisions](knowledge/purpose-and-decisions.md) and
   [current state](knowledge/current-state.md). Check the actual branch, working
   tree and release versions; the dated handover is not a live service registry.
2. Read [architecture](knowledge/architecture.md) and
   [development](knowledge/development.md) for application work, or
   [pack development](knowledge/pack-development.md) for tool work.
3. Identify the supported scientific operation, affected contracts and the
   evidence needed. Read [validation and releases](knowledge/validation-and-releases.md)
   before building or publishing an artifact.

## Project invariants

- Keep analysis local. The normal desktop path must not require a browser,
  HTTP listener, Docker, WSL, administrator privileges or a system Python/Java.
  Institution approval may still cover each bundled executable; do not bypass it.
- Port pinned upstream tools with narrow, documented compatibility changes.
  Preserve the scientific algorithms and test meaningful scientific outputs.
  This is not a general Linux binary emulator or a security sandbox.
- Keep the application small and optional tools independently installable.
  Packs own typed inputs, options, commands, outputs, methods, citations and checks.
  Use the established schema and runner instead of adding per-tool UI branches.
- Preserve pack IDs, published bytes and saved version/manifest pins. Changed
  pack content needs a new pack version. Never silently upgrade saved pipelines.
- Preserve the accepted tool library, individual-tool mode, separate settings
  and pipeline saves, branching/merging DAGs and explicit input provenance.
  The wheel and double-ring selectors were rejected by testers.
- Keep shell-free argument arrays, bounded import validation, checksums and
  catalogue signature verification. Packs execute trusted native code; checksums
  alone do not establish publisher identity or isolate malicious tools.
- Keep reference retrieval explicit and separate from analysis. Preserve archive,
  assembly, resource role and exact-byte provenance; incomplete downloads must
  never appear as ready inputs. See the reference-discovery guide.
- Record exactly what was tested: platform, app and pack versions, artifact
  hashes, inputs and assertions. Linux execution, PE inspection, native Windows
  CLI checks, desktop GUI checks and clinical validation are different claims.
- Preserve the fastp reporting fix and other documented portability regressions.
  Retain matching source, build provenance and third-party licensing materials.

## Completing work

Run the smallest relevant checks that establish the changed behavior. A source
checkout intentionally omits large build inputs; document missing prerequisites
instead of claiming unrun tests passed. Do not commit binaries, private data,
credentials, signing keys or transient build outputs.

Update the relevant knowledge pages when architecture, contracts, decisions,
release status or limitations change. Keep stable decisions separate from dated
release evidence. [knowledge/project.json](knowledge/project.json) is an index;
[knowledge/release-inventory.json](knowledge/release-inventory.json) is a dated
inventory, **not** an installation catalogue or trust file.

Follow the current user's instructions and the permissions of the environment
you are actually using. Historical actions recorded here do not authorize new
publishing, deployment or account access.
