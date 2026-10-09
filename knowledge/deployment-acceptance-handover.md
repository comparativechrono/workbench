# Deployment and Windows acceptance companion

Status on 2026-10-09: implementation and exact-kit validation in progress.
Branch: `feature/deployment-acceptance`, based on published main
`9ac6f906e3acd88e743ed87c76cbf99c9087636d`. This is an unpublished companion
tooling candidate for application 0.16.0, not a new application release.

The owner approved the next bounded set with “okay, lets do that” after reviewing
the Windows acceptance/deployment proposal. Benchmarking is being handled
separately. Scientific Linux CWL profiles, SDK/build recovery and other scientific
extensions remain later work. This set does not sign executables, change endpoint
security policy or claim institutional approval.

## Implementation contract

- Build a verified offline Starter/tester bundle from the four exact published
  archives locked in `packaging/deployment-0.16.0-lock.json`. Preserve application,
  updater, source and pack bytes; record separate application and toolkit commits.
- Produce machine-readable and readable inventories covering files, components,
  executable formats, declared PE imports and actual licence/source notices.
  Unknown metadata, dynamic dependencies and signature trust remain explicit.
- Verify the complete immutable kit before preparing fresh external test copies.
  Keep reports and user state outside the kit. Never package an existing user's
  installation or overwrite an existing test/report directory.
- Offer structured manual acceptance and actual Windows signature observations,
  plus explicit import of separately bound automated observations. Manual checks
  start untested and cannot be completed by importing hosted results.
- Exercise the published updater through its actual folder picker and check
  cancellation, invalid selection, successful update, preservation and repeat use.
  Add bounded native keyboard/resize checks and retain screenshots and failures.

See the [tester guide](../docs/deployment-acceptance.md),
[IT review guide](../docs/institutional-deployment.md), and
[candidate workflow](../.github/workflows/deployment-acceptance-candidate.yml).

## Fixed application inputs

| Role | Version | SHA-256 |
| --- | --- | --- |
| Starter | 0.16.0 | `f96e03e43cac92ba8ca9a0a3807eb671f9924d5e624cadbba94d1a5ca1309073` |
| Updater | published 0.11.0 to 0.16.0 | `d75d5129e9b9feaef70faa62d5ea91049c0162df8c7bdc74c7bc81d1933eec8f` |
| Application source | 0.16.0, `e855dc4396e0c16ae35f4e840eb9cc734adb4441` | `f746f00a82675c2cf52364a3b4d040721c6d06ac5605488efbdc0376ef5b7e44` |
| Disposable update baseline | 0.11.0 | `e816e2f7cd5efe98af752fbf072fab00344ebaa2b6963795c2fbf4a86b5fa81c` |

These archives have been freshly downloaded and rehashed for this set. That
inspection alone is not a native Windows pass. The original published 0.16.0
validation remains in its [release handover](curated-workflows-0.16.0-release-handover.md).

## Evidence to complete before review delivery

Record the exact toolkit commit, unit-test results, generated ZIP/provenance and
manifest hashes, source correspondence, ordinary/spaced native run identities,
signature observations, manual-untested assertions, curated regressions and
visual review. Retain any failed attempts with their actual scope. No new native
or representative-machine pass is claimed by this implementation checkpoint.

## Remaining external acceptance

High-DPI, multiple monitors, physical trackpads, institution-managed machines,
actual application-control decisions and executable-signing identity remain
external observations or prerequisites. The kit makes those checks repeatable
and recordable; it cannot complete them by generating a blank report. An initial
signature inventory may legitimately contain unsigned or unavailable statuses.
