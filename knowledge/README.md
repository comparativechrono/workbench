# Native Workbench knowledge base

This is the durable handover for people and agents continuing Native Workbench.
It records why the project exists, how it works, how to extend it, and which
claims the evidence supports. It is stored as plain UTF-8 Markdown and JSON:
open, diffable files with no proprietary reader or external memory service.
"Knowledge base" describes this directory; it does not claim compliance with a
separate standard called Open Knowledge Format.

**Reviewed:** 2026-10-04. **Source baseline:**
[`9368c22058a3fe3cd434e7185fcaf5ff3fd6ce22`](https://github.com/comparativechrono/workbench/commit/9368c22058a3fe3cd434e7185fcaf5ff3fd6ce22).
The initial handover is documentation added after that baseline. Re-check the
current tree and releases before treating its version snapshot as current.

## Reading order

| File | Question it answers |
| --- | --- |
| [Purpose and decisions](purpose-and-decisions.md) | Who is this for, what approach was chosen, and what must not be lost? |
| [Current state](current-state.md) | What is released, tested, limited or unfinished? |
| [Architecture](architecture.md) | Where does each responsibility live, and how does a run work? |
| [Development](development.md) | How do I recover inputs, build, test and resume work? |
| [Pack development](pack-development.md) | How do I add a real tool without rebuilding the app? |
| [Validation and releases](validation-and-releases.md) | What establishes correctness, and how are artifacts published and trusted? |
| [Roadmap](roadmap.md) | What should be addressed next, and what would count as completion? |
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
- Current behavior is checked against source at the baseline above. Source links
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
describe the original 0.6 split, before STAR and kallisto. Do not mistake these
historical inventories for the latest complete list.

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
