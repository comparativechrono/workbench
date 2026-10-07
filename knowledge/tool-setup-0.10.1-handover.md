# Tool Setup corrective patch 0.10.1

Snapshot: 2026-10-07. Branch: `fix/tool-setup-0.10.1`, from published-main
`4777f020f0907b4431d0a5be115ef5d9aa776457`. Version 0.10.1 is not released.

Testers reported flashing column headers, unusable package scrolling and the
message “Download failed. Check the connection and whether the approved host
is accessible.” The exact published 0.10.0 archive and its successful prior
Windows reports remain immutable historical evidence. New checks must establish
the behavior missing from that coverage.

## Changes and diagnosis

The native setup list was disabled during refresh or installation, which also
prevented scrolling. The patch keeps navigation enabled and vetoes checkbox
changes while selection is locked. It updates changed row cells in place,
retains selection/focus/scroll position across structural updates, and avoids
repeated radio, text, progress and column updates. The report list is already
double-buffered; the setup window no longer adds top-level compositing around
it. Failed/cancelled/interrupted operation notices retain the pack name.

Header flashing has not yet been independently reproduced. The new gate samples
actual desktop header pixels through sustained idle and live polling, records
observed changes rather than assuming them, and exercises real wheel and scrollbar
navigation. A separate disposable extraction of published 0.10.0 supplies a
negative control. A network failure is a failed prerequisite, not evidence of
the expected UI regression.

The old downloader caught every URLError and OSError with the same message,
including local create/write/flush failures. New diagnostics distinguish bounded
HTTP status, proxy authentication, certificate/TLS, DNS, timeout/refusal/reset,
and permissions/full/locked/missing local storage. Only approved hostnames appear;
raw exceptions, signed URLs and proxy credentials do not. Signing, hashes,
approved-host checks, cancellation and timeout/retry policy remain unchanged.

The exact released downloader matched the inspected pre-patch source. Both old
and new Linux transport probes verified the current 32-pack production catalogue
and the 486,120-byte reads archive with SHA-256
`2dd05fece8deb2b0178d8b1bc2b6830f175b3fbc2f5a4d48f9c9023cbfe6775b`.
The testers' failure has not been reproduced or diagnosed. The improved message
will distinguish the next necessary action on their machine.

The patch also corrects stale bundled README text claiming production trust was
not included. It retains the same owner public key, setup profile and pack bytes.

## Validation before native candidate

- Backend source checks: 68 passed; one native Windows filesystem test skipped.
  These are 46 pack-manager passes plus 15 setup-manager and seven service passes;
  the Windows-only case must be executed by CI, not counted here.
- Seven focused synthetic patch-updater packaging guards passed. They enforce
  the exact published baseline, core-only replacements and unchanged pack,
  production trust and setup-profile bytes.
- UI gate Python syntax and whitespace checks passed. This is not a native UI pass.

The dedicated `native-setup-patch-candidate.yml` builds exact starter, matching
source and 0.10.0 updater archives once. It runs ordinary and space-containing
Windows setup/UI/References/results/upgrade checks and one real production Full
installation. The updater gate includes saved setup selection and queue state
alongside installed tools, settings/pins, references and results. Native results,
archive identities, failures and later release status must be appended after
actual checks. No new Windows pass is asserted in this preparation snapshot.
