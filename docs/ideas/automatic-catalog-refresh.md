# Automatic catalog refresh

Status: proposed
Last reviewed: 2026-09-15

## Goal

Keep the Markdown inventory of local and NAS archives current after successful
archive operations, without requiring a separate manual catalog command.

## Current behavior

[archive-hf-model](../../scripts/ai/archive-hf-model) downloads, copies, verifies,
packages, and records conversions. Its `main` function coordinates selected stages.
[catalog-hf-models](../../scripts/ai/catalog-hf-models), exposed through
`bin/model-catalog`, independently scans storage and atomically replaces each
generated catalog. Refresh is manual; no archive completion hook exists.

Catalog scans are offline by default. Upstream checks require the explicit
`--check-upstream` option. Existing output protection rejects overwriting
unrecognized Markdown, and scan errors preserve the previous catalog.
See the [catalog guide](../../scripts/ai/README.md#markdown-download-catalog).

## Proposed changes

The following is a recommended initial design, not an agreed CLI contract:

1. Add an opt-in archive completion option, tentatively `--refresh-catalog`.
   Run the refresh once after all requested archive stages succeed.
2. Reuse the existing catalog implementation. Pass resolved roots and output
   options explicitly, using argument arrays and the running Python interpreter
   if invoking the script as a subprocess. Do not depend on an installed command
   being on PATH or duplicate the scanner.
3. For local-only operations, scan local storage without requiring a NAS.
   When NAS copying succeeds, include local and NAS locations in the catalog.
   Keep independent backup storage outside this initial catalog integration.
4. Keep refresh offline. Online freshness checks remain a separate explicit
   action; do not silently add authentication or network requirements.
5. Report refresh failure separately from successful archival. Preserve verified
   artifacts and existing catalogs. Recommend a nonzero command exit status with
   an explicit message that archival succeeded but catalog refresh failed.
6. Serialize refreshes targeting the same output with a portable mechanism that
   covers scanning and publication, so a stale scan cannot replace a newer one.
   Apply the coordination to manual catalog writers as well.

## Scope

Include successful downloads, NAS copies, packaging, and conversion imports that
affect catalog contents. Retain manual catalog commands. Defer timers, filesystem
watchers, background services, automatic downloads, and upstream polling.

## Constraints

Preserve immutable snapshots, generated-file protections, staging exclusions,
and atomic publication. Do not install a scheduler or assume systemd. Follow
the existing root overrides and XDG defaults. Refresh failure must never remove
an archive or roll back a completed copy. Atomic replacement of individual files
does not make multiple output files a transaction; report partial output success.

## Acceptance criteria

* Without the new option, existing archive behavior remains unchanged.
* Successful opted-in operations produce a catalog containing their published
  artifacts; matching local and NAS copies retain the scanner's grouping behavior.
* Local-only refresh works with no NAS access and no upstream SDK installed.
* Failed archive stages do not trigger a success refresh.
* Scan/write failures leave previous affected catalogs and all archived data safe,
  with an actionable error and the chosen documented exit status.
* Concurrent refreshes cannot publish an older scan over a later completed scan.

## Validation

Extend [archive tests](../../tests/test_archive_hf_model.py) and
[catalog tests](../../tests/test_model_catalog.py) with small temporary archives.
Cover local-only and combined roots, conversion and package publication, stage
failure, missing NAS, protected output, paths containing spaces, and concurrent
writers. Assert offline refresh makes no upstream requests. Exercise multiple
outputs with a failure on one destination and verify the reported outcome.

## Open questions

* Confirm the opt-in option name and whether a future configuration default is useful.
* Should the default write only the local catalog, as the manual command does,
  or also mirror it to NAS? Recommend retaining the existing default and making
  additional output paths explicit.
* Confirm the proposed nonzero exit policy for refresh failure after archival.
* Should verification-only runs refresh? Recommend allowing an explicitly
  requested refresh after successful verification, without making it automatic.

## Implementation outcome

Not implemented. This document records the proposed handoff only.
