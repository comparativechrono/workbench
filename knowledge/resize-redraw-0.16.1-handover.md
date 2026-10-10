# Tools resize correction for unpublished 0.16.1

Started **2026-10-10**, following the owner's request: “Okay. Let's fix that.”
The defect is visible while resizing in Tools mode: some controls briefly display
their previous layout, clipping content at the right or bottom even after their
native bounds have changed. This is a bounded follow-up to the completed tester-feedback candidate.

## Starting state and scope

- Repository: [comparativechrono/workbench](https://github.com/comparativechrono/workbench).
- Branch: `fix/native-ui-0.16.1`; starting head
  `93c0a6b1189781fb8df960b025a512ed73461240`.
- Review: [draft PR #15](https://github.com/comparativechrono/workbench/pull/15),
  based on `feature/deployment-acceptance` at
  `f74d90229be6a78d6ad0c0076c54c04bb7e7cae2` and unmerged draft PR #14.
- Version: remains unpublished **0.16.1**. Published **0.16.0**, `main` at
  `9ac6f906e3acd88e743ed87c76cbf99c9087636d`, and published assets are unchanged.
- Delivery: implementation, exact-candidate validation and updated draft review;
  no merge or release.

Fix the existing layout/repaint behavior without weakening the Run/category
redraw corrections, separate Methods, Run preflight, native Samples editing,
reference management or existing workflows. Preserve saved pins, pack bytes,
scientific answers and recorded-measurement semantics. No new features, QC pass
thresholds or runtime/memory forecasts are in this follow-up.

## Prior evidence and negative control

The [tester-feedback handover](tester-feedback-0.16.1-handover.md) and all of its
receipts remain historical and unchanged. Its exact application source is
`73778e00461e2b83c07b9ea97df2b9c5d4b6317d`; the prior Starter ZIP has SHA-256
`1291f93b5ece3c4da34eb2f2e29fccc83b6d87ec5fb73abf28bfd9cc8f155b75`
(17,879,604 bytes), from
[build run 37997370988](https://github.com/comparativechrono/workbench/actions/runs/37997370988).
That is the old-package comparison identity, not the new candidate identity.

Old immediate Tools resize captures retained old geometry and right/bottom
clipping, although native bounds were already correct. The visible image was
corrected by the first later sample, about 0.30–0.32 seconds after resize; the observation does not measure the precise defect duration.
Workflow samples were stable. The old 220 source passes, 113 native checks per
path and settled visual review do not validate a rebuilt application.

## Implementation and validation status

**In progress.** No new frozen application-source commit, archive hashes or
passing new-candidate Windows results are recorded yet. Do not distribute the
old Starter as though it contains this correction.

Required validation:

1. Review the resize message/layout/repaint path and verify relevant source
   checks and strict native builds.
2. Build one exact Starter, matching source companion and supported 0.16.0 core
   updater; independently verify archive hashes and source correspondence.
3. Compare the old and corrected packages using passive visible-frame sampling
   during resize. Use the old package on a fresh ordinary-path installation as
   the negative control; test the corrected package on fresh and upgraded
   installations in ordinary paths and paths containing spaces. Keep capture
   timing and any forced repaint separate.
4. Exercise the existing native regression scopes on the new archives, including
   Run/category temporal behavior, Methods, Samples, results/keyboard behavior,
   references, workflow execution and updater preservation.
5. Review screenshots for layout/clipping, save focused sanitized evidence and
   original-report hashes, and update draft PR #15 with exact download links.

Record failures, unavailable checks and an unreproduced negative control
explicitly. A later settled screenshot cannot establish that intermediate frames
were correct, and finite frame samples cannot establish universal zero flicker.
Original report hashes preserve identity, not continued access to expiring
Actions content. Exclude session/review tokens and unnecessary runner/input
metadata from repository evidence.

Representative-PC, high-DPI/multiple-monitor/physical-trackpad and managed-machine
acceptance remain separate. Executable signing/IT approval, scientific Linux
CWL, SDK/build recovery and the separately managed benchmarking programme are
not completed by this resize correction.
