# Model storage capacity checks

Status: proposed
Last reviewed: 2026-09-15

## Goal

Identify likely disk-space shortages before expensive model downloads, NAS or
backup copies, conversion imports, and archive packaging begin.

## Current behavior

[archive-hf-model](../../scripts/ai/archive-hf-model) uses staging directories,
checksums, and immutable publication. NAS and backup roots must already exist,
but there is no disk-capacity preflight. A root's existence does not prove that
the expected filesystem is mounted or has enough free space.

Relevant implementation areas are `model_info`, `selected_repo_files`,
`publish_download`, `copy_snapshot`, `create_local_archive`, and
`record_conversion`. Model selection is pinned to a resolved revision.
See the [model archive guide](../../scripts/ai/README.md) for storage layout,
independent copies, and optional packaging. Catalog sizes describe logical file
sizes, not necessarily physical allocation or available storage.

## Proposed changes

These are design recommendations to refine before implementation:

1. Build a per-stage estimate of additional space, using the selected files at
   the pinned upstream revision for downloads and local file sizes for copies
   and conversion imports. Retrieve upstream size metadata only when the selected
   operation already needs it; keep local copy and packaging checks offline.
2. Query available space with Python's standard-library `shutil.disk_usage` on
   the destination or its nearest existing parent. Resolve storage-root symlinks
   and identify shared filesystems where practical on Linux and macOS.
3. Account for files that coexist during staging and publication, including
   existing snapshots, partial downloads, and temporary tar files. Estimate
   additional bytes rather than counting existing allocation twice. Do not
   assume compression savings; include archive overhead and a documented margin.
4. Check before each writing stage, considering shared destination filesystems
   and actual execution order. Report the destination, estimated additional
   requirement, available bytes, margin, and any unknown inputs.
5. Recommend failing before a stage when a known shortage exists. Clearly label
   incomplete estimates; decide the unknown-estimate policy before implementation.
   Preserve existing handling for runtime write failures because free space can
   change after a successful preflight.

## Scope

Cover archive-managed writes to local, NAS, and configured backup storage.
This is a storage-capacity feature, not a model placement or retention manager.
Defer automatic cleanup, moving archives between tiers, mounting storage,
filesystem provisioning, and GPU/VRAM inference sizing.

## Constraints

Use existing dependencies and portable capability checks. Never delete caches,
partial downloads, or older snapshots to make room. Do not read model contents
just to estimate their size. Keep machine-specific roots in existing configuration.

Available-space reports and estimates cannot guarantee success: quotas, sparse
files, copy-on-write, concurrent writers, and remote storage can affect actual
allocation. Distinct paths need not represent independent capacity, and local
filesystem identifiers may not reveal shared NAS pools. Document these limits
without claiming a successful preflight proves sufficient storage or a valid mount.

## Acceptance criteria

* A known shortage stops the affected stage before it writes model data, with
  useful required/available-space information.
* Estimates reflect include/exclude selections at the resolved revision.
* Local copies, packaging, and conversion imports can be checked offline.
* Shared filesystems and source/staging/archive coexistence are accounted for
  conservatively; existing files are not blindly counted as new allocation.
* Unknown sizes or failed capacity queries are reported explicitly using the
  documented policy, never presented as a successful capacity check.
* No preflight failure deletes or modifies existing model artifacts.

## Validation

Extend [archive tests](../../tests/test_archive_hf_model.py) with mocked capacity
and upstream metadata and small filesystem fixtures. Cover sufficient and
insufficient space, unknown file sizes, filtered selections, shared filesystems,
symlinked roots, existing partial downloads, independent copies, compressed and
uncompressed packaging, and capacity-query failures. Assert shortage checks
precede writes. Exercise a runtime disk-full failure after a successful check
to verify existing data stays safe. Do not download large models for testing.

## Open questions

* Should preflight be enabled by default or initially opt-in? Recommend default
  checks once estimates cover every writing stage reliably.
* What reserve margin should apply, and how should users configure it?
* Should incomplete estimates warn and continue or require an explicit override?
  Recommend a clearly documented strict mode if continuing is the default.
* Is a separate estimate-only command worthwhile? Any proposed flags need a CLI
  review; none are implemented by this handoff.
* Should expected-mount identity checking be a separate future idea? Recommend
  keeping it separate from capacity calculations.

## Implementation outcome

Not implemented. This document records the proposed handoff only.
