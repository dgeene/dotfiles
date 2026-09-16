# AI model archives

`archive-hf-model` preserves commit-pinned Hugging Face snapshots for later use,
plus separate GGUF inference artifacts. The default workflow downloads, checks
against the Hub, seals the local snapshot, copies it to NAS staging, verifies the
copy against the source hashes, then publishes the destination directory and
saves NAS checksums. Snapshots are ordinary uncompressed directories.

Choose the stages you need:

| Invocation | Result |
|---|---|
| No stage flags, or `--all` | Download, verify, copy to NAS, and save checksums. |
| `--download` | Download and seal a local snapshot with local checksums. No NAS copy. |
| `--sync` | Copy an existing local snapshot to NAS, verify it, and save NAS checksums. |
| `--checksum` | Verify an existing NAS snapshot and create missing checksum files. |
| `--verify` | Check an existing snapshot against its saved checksums; NAS is the default target. |
| `--archive` | Package an existing local snapshot as an optional uncompressed `.tar`. Add `--compression zstd` for compression. |

Explicit stage flags can be combined, for example `--download --sync`. `--all`
runs only the standard download/sync/checksum workflow and cannot be combined
with other stage flags. To archive to NAS later, use `--sync`; `--archive` selects
local tar packaging, which is separate from the NAS directory copy.

Original model weights can run on supported GPU runtimes directly. GGUF is a
runtime format, and quantization is a separate precision/size tradeoff. Prefer
the publisher's original released precision as the source for future conversions.
Neither a `.safetensors` extension nor this archive tool certifies original
precision, lineage, or compatibility with a particular converter/runtime.

## Requirements

- Python 3.9+; no additional Python packages required by this script.
- For downloads: `hf` supporting `models info --revision --expand --format json`,
  `download --local-dir --revision`, and
  `cache verify --local-dir --revision --fail-on-missing-files`. Authentication
  uses the CLI's existing login or `HF_TOKEN`; do not put credentials in recipes
  or command arguments.
- For NAS/backup copies: `rsync` (including the older macOS version).
- For `.tar.zst`: `zstd`. Uncompressed `.tar` needs only Python.

The implementation supports Linux/macOS without requiring systemd, GNU tar,
or a particular GPU. NAS paths refer to locally mounted storage, not `host:path`
rsync destinations. The NAS root must already exist for `--sync` (including the
default workflow); `--backup-root` must exist whenever supplied. `--download`
alone needs neither NAS storage nor rsync. Mount the intended storage before
copying; an existing directory alone does not prove a NAS is mounted.

Run examples from `scripts/ai/`, or use the script's path from the checkout root.
Run `./archive-hf-model --help` for all options.
Replace `/mounted/...` and `/storage/...` examples with your actual storage paths,
and `FULL_COMMIT` placeholders with the archived revision's full 40-character SHA.

## Storage and immutability

Local storage defaults to `$XDG_DATA_HOME/hf-model-archives`, falling back to
`~/.local/share/hf-model-archives`. NAS defaults to `/mnt/ai-models`.
Override with `--local-root` / `HF_MODEL_DOWNLOAD_ROOT` and `--nas-root` /
`AI_MODELS_NAS_ROOT`. Choose a persistent disk with enough free space for the
source, staged copies, and any optional tar archive.

```text
<root>/
├── source/huggingface/<owner>/<model>/<full-commit>/
│   ├── config.json, tokenizer files, weights, model card, license, ...
│   └── archive-provenance/
│       ├── request.json
│       ├── download-<id>.json
│       └── snapshot.json
├── inference/gguf/<owner>/<model>/<full-commit>/
│   ├── download/                 # GGUF files downloaded from this repo/commit
│   └── <conversion-name>/        # Local conversion of this source commit
└── metadata/checksums/
    ├── source/huggingface/<owner>/<model>/<commit>.sha256
    └── inference/gguf/<owner>/<model>/<commit>/<artifact>.sha256
```

The same relative paths apply on local, NAS, and backup storage. The owner is
the actual repository owner, including third-party quantization publishers.
Locally converted outputs use the source repository identity and commit.
`download` is reserved and cannot be a local conversion name.

Published snapshots are immutable **to this tool**, not protected by filesystem
permissions: reruns verify and reuse matching snapshots; conflicting files,
selections, or recipes fail without replacement. Old revisions retain their
bytes. Do not edit files inside a published snapshot or run converters there.
Use a separate working/output directory. `--rsync-delete` is retired and rejected.
`--force-download` can refresh an unfinished download, but cannot overwrite a
published snapshot.

A filtered selection occupies its own immutable snapshot. To archive another
selection of the same repository commit, supply a different positional
`model_name`, such as `Qwen3-8B-Q4_K_M` or `Qwen3-8B-Q8_0`. This changes the
`<model>` directory component, not the repository identity. Use the same
`model_name` for later sync, checksum, and verification stages, including when
supplying `--local-model-dir`.

Auto layout routes GGUF-only weights to `inference/gguf`; source weights, mixed
repositories, and unknown selections use `source/huggingface`. `--layout` changes
routing, not filtering. GGUF layout rejects recognized source-format weights.
Offline stages locate existing organized snapshots automatically; specify
`--layout source` or `--layout gguf` if both layouts exist for the same model/revision.

Old flat or mutable owner/model directories are not moved, deleted, or silently
adopted. Download the desired revision into a fresh snapshot to establish its
provenance. `--local-model-dir` can select a new exact download destination, or
an existing **sealed** snapshot for offline operations. Existing unmanaged
folders are rejected; a tar operation cannot reconstruct their original revision.

## Download and source checks

These examples archive complete publisher repositories from
[Qwen](https://huggingface.co/Qwen/Qwen3-8B) and
[Mistral](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3).
Without `--include` / `--exclude`, every repository file is selected, including
any alternative weight formats or duplicate representations the publisher supplies.

```sh
# Source model: download, verify, copy to NAS, and save checksums
./archive-hf-model Qwen/Qwen3-8B --nas-root /mounted/ai-models

# Another publisher's source model, using the same workflow
./archive-hf-model mistralai/Mistral-7B-Instruct-v0.3 --nas-root /mounted/ai-models

# Local snapshot only, resolving a branch/tag or full commit
./archive-hf-model Qwen/Qwen3-8B --revision main --download

# Require the structural source checks to pass without warnings
./archive-hf-model Qwen/Qwen3-8B --download --require-source-complete
```

For GGUF, select the desired quantization instead of downloading every variant.
The examples below use filenames from the
[Qwen GGUF repository](https://huggingface.co/Qwen/Qwen3-8B-GGUF/tree/main) and a
[third-party Mistral GGUF repository](https://huggingface.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF/tree/main):

```sh
# Publisher-provided Q4_K_M GGUF, downloaded and copied to NAS
./archive-hf-model Qwen/Qwen3-8B-GGUF Qwen3-8B-Q4_K_M \
  --include 'Qwen3-8B-Q4_K_M.gguf' --include 'README.md' \
  --include 'LICENSE*' --include 'params' --nas-root /mounted/ai-models

# Third-party Q5_K_M GGUF, with its model card and available conversion metadata
./archive-hf-model bartowski/Mistral-7B-Instruct-v0.3-GGUF Mistral-7B-Instruct-v0.3-Q5_K_M \
  --include 'Mistral-7B-Instruct-v0.3-Q5_K_M.gguf' --include 'README.md' \
  --include 'LICENSE*' --include '*.imatrix' --nas-root /mounted/ai-models
```

Filters are case-sensitive and apply to paths relative to the repository root;
quote patterns so your shell does not expand them. Inspect the repository file
list before choosing a filename. For split GGUFs, include every shard of the
selected variant, plus any required projector/encoder files for multimodal models.
`--include 'LICENSE*'` preserves matching files only when present; review notices
about missing terms. GGUF and filtered snapshots produce assessment notices in
normal mode, so do not use `--require-source-complete` for these examples.
Check that weights were selected: a mistyped weight pattern can still match only
the separately included metadata files and publish a snapshot with warnings.

Each download resolves a full commit before selecting or fetching files. It
records repository URLs, selected files, UTC invocation times, sizes, local
SHA-256 hashes, format labels, and declared model-card lineage. Times refer to
the invocation and may include reuse of cached bytes. Mutable `.cache` metadata
is removed from the tool-owned staging directory before publication.

`hf cache verify` checks downloaded bytes against the pinned Hub revision before
publication. Full-repository selections also require no missing upstream files.
Filtered selections are checked against their selected file list locally and do
not require unselected files. `--skip-upstream-verification` explicitly skips
only this online verification, records that decision, and retains local and
transfer integrity checks.

The sealed `snapshot.json` contains an exact file/hash inventory and a
`source_assessment` report. Checks include:

- Whether filters omitted repository files.
- Whether selected weight indexes reference missing shards (always fatal).
- Presence of recognized weights, root config, tokenizer vocabulary, model card,
  and license files.
- Declared architecture, dtype, quantization configuration, and adapter/base
  dependencies. Missing or uncertain dependencies produce notices.

These are structural checks, not a test load or an inspection of tensor precision.
Full snapshots preserve custom code, chat templates, processors, and vision/audio
components when the repository supplies them, but external dependencies and
architecture-specific requirements still need review. No repository code is run.
`--require-source-complete` makes all assessment warnings fatal, including filtered
selections, GGUF artifacts, and unresolved declared base models. Some valid
repositories will therefore need normal mode and manual review.

For adapters, archive the base model separately and attach its exact identity:

```sh
./archive-hf-model owner/adapter --download \
  --base-model-dir /storage/source/huggingface/owner/base/FULL_BASE_COMMIT
```

Repeat `--base-model-dir` for multiple dependencies. Each supplied snapshot is
verified; its repository, commit, and manifest hash are recorded. A missing or
mismatched declared base is reported. The base weights are not duplicated inside
the adapter snapshot and must be copied/backed up separately. An adapter remains
flagged as non-standalone, even when its base dependency is recorded.

## Verified NAS and independent copies

### Download now, copy to NAS later

The download stage creates a sealed local snapshot and local checksums. It does
not require the NAS to be mounted. This example chooses an explicit local root
and reuses it when copying later:

```sh
# Stage 1: download and verify locally
./archive-hf-model Qwen/Qwen3-8B --download \
  --local-root "$HOME/models/hf-archives"

# Stage 2: after mounting the NAS, copy the already downloaded revision
./archive-hf-model Qwen/Qwen3-8B --sync --revision FULL_COMMIT \
  --local-root "$HOME/models/hf-archives" --nas-root /mounted/ai-models
```

Replace `FULL_COMMIT` with the commit directory in stage 1's final `Local` path,
or read `repository_commit` in that snapshot's
`archive-provenance/snapshot.json`. For this source model, the local path is
`$HOME/models/hf-archives/source/huggingface/Qwen/Qwen3-8B/FULL_COMMIT`.
`--sync` performs no Hub lookup or download: it verifies the snapshot, copies it,
and writes NAS checksums. A separate `--checksum` flag is unnecessary. The local
snapshot remains in place.

Alternatively, provide the exact sealed directory printed by stage 1; the tool
reads the revision and layout from its manifest:

```sh
./archive-hf-model Qwen/Qwen3-8B --sync \
  --local-model-dir "$HOME/models/hf-archives/source/huggingface/Qwen/Qwen3-8B/FULL_COMMIT" \
  --nas-root /mounted/ai-models
```

The same two stages work for a selected GGUF. Preserve the custom `model_name`
when copying later; download filters do not need to be repeated for `--sync`:

```sh
# Stage 1: local GGUF snapshot only
./archive-hf-model Qwen/Qwen3-8B-GGUF Qwen3-8B-Q4_K_M --download \
  --include 'Qwen3-8B-Q4_K_M.gguf' --include 'README.md' \
  --include 'LICENSE*' --include 'params' --local-root "$HOME/models/hf-archives"

# Stage 2: use this GGUF repository's commit, not the source model's commit
./archive-hf-model Qwen/Qwen3-8B-GGUF Qwen3-8B-Q4_K_M --sync \
  --revision FULL_GGUF_COMMIT --local-root "$HOME/models/hf-archives" \
  --nas-root /mounted/ai-models
```

The GGUF snapshot is under
`inference/gguf/Qwen/Qwen3-8B-Q4_K_M/FULL_GGUF_COMMIT/download/` on both roots.
Its commit appears immediately before `/download/` in the final `Local` path.
For sync/checksum/verification stages, `--revision` must be the **full commit SHA**
unless supplied via a sealed `--local-model-dir`; these stages never resolve
`main` online. Continue using your selected roots on subsequent commands, or set
`HF_MODEL_DOWNLOAD_ROOT` and `AI_MODELS_NAS_ROOT` as machine-local defaults.

### Independent copies and verification

The following examples use the configured/default local and NAS roots:

```sh
# Also preserve an independent directory copy
./archive-hf-model Qwen/Qwen3-8B --revision FULL_COMMIT \
  --sync --backup-root /mounted/second-storage

# Copy from an existing NAS snapshot when local storage is unavailable
./archive-hf-model Qwen/Qwen3-8B --revision FULL_COMMIT \
  --checksum --backup-root /mounted/second-storage
```

`--backup-root` adds a verified copy when combined with download, conversion,
sync, checksum, or archive stages. With no stage flags it adds to the default
workflow. Roots must be separate and non-overlapping; the tool cannot establish
whether two paths are on physically independent devices. Choose independent
storage and retain it according to your backup policy. Directory copies and tar
packaging do not automatically provide offsite protection or NAS snapshots.

Transfers verify the source snapshot, copy into a hidden sibling directory, and
compare the destination's exact file set and hashes against the source before a
same-filesystem rename publishes it. Saved checksum files also cover the embedded
manifest. Existing destinations must match; corruption never becomes a new baseline.
`--checksum` verifies the sealed NAS snapshot and creates missing checksums, but
never replaces an existing checksum baseline.

Interrupted downloads and copies remain in hidden `.*.download-partial` or
`.*.copy-partial` directories. Rerun with the same full revision, model name,
roots, and download selection/options to resume; `main` may have moved since the
interruption. For an unfinished download, the pinned commit is recorded in the
staging directory's `archive-provenance/request.json` under `commit`. Publication
locks prevent concurrent writers; after a killed process, remove an empty stale
`.lock` directory only after confirming no writer is running. Conflicting staging
requests must be reviewed and moved aside manually. Published data is never
removed automatically. Directory publication is atomic, but this is not a
power-loss durability guarantee for every filesystem or NAS implementation.

Periodically verify saved copies, including the external checksum baseline:

```sh
./archive-hf-model Qwen/Qwen3-8B --revision FULL_COMMIT --verify
./archive-hf-model Qwen/Qwen3-8B --revision FULL_COMMIT --verify --verify-target local
./archive-hf-model Qwen/Qwen3-8B --revision FULL_COMMIT --verify \
  --verify-target backup --backup-root /mounted/second-storage
```

Verification-only operations do not create missing baselines or copy data.
Checksums detect changes; they are not signatures against an attacker who can
replace both data and manifests. Hashing and verification read large files in
full, potentially several times; budget disk/NAS bandwidth accordingly.

## Record a local GGUF conversion

Run conversion/quantization in a separate workspace with a converter that supports
the architecture. Preserve the original source snapshot. Keep dependency locks,
converter commit, commands, environment versions, and any calibration data or
importance matrix used. Multimodal outputs may need separate projector/encoder
files; include all runtime artifacts in the output directory.

Create a local JSON recipe, replacing the descriptive placeholders with actual
paths, versions, commits, and commands:

```json
{
  "name": "q4-k-m",
  "source_directory": "/storage/source/huggingface/Qwen/Qwen3-8B/FULL_SOURCE_COMMIT",
  "converter": {
    "repository": "https://github.com/ggml-org/llama.cpp",
    "commit": "FULL_40_CHARACTER_CONVERTER_COMMIT"
  },
  "commands": [
    ["python", "convert_hf_to_gguf.py", "source", "--outfile", "work/model-bf16.gguf", "--outtype", "bf16"],
    ["build/bin/llama-quantize", "work/model-bf16.gguf", "outputs/model-Q4_K_M.gguf", "Q4_K_M"]
  ],
  "environment": {"python": "ACTUAL_VERSION", "platform": "ACTUAL_OS_AND_ARCHITECTURE"},
  "dependency_files": ["requirements-lock.txt"],
  "calibration_files": []
}
```

`source_directory`, `dependency_files`, and `calibration_files` paths are relative
to the recipe file unless absolute. Entries in `commands` are recorded verbatim;
include the original working directory in `environment` when it matters. The recipe
must contain exactly the top-level keys shown. The converter commit must be a
full lowercase SHA. `dependency_files` must be nonempty; use
`calibration_files: []` when no calibration was used. Otherwise list the data and
importance-matrix files to preserve. Only include non-secret files and commands.

```sh
./archive-hf-model Qwen/Qwen3-8B \
  --record-conversion /work/recipe.json --local-model-dir /work/outputs --sync

./archive-hf-model Qwen/Qwen3-8B --revision FULL_SOURCE_COMMIT \
  --conversion-name q4-k-m --verify
```

`--record-conversion` alone imports locally; the example also adds `--sync` to copy
the result to NAS. The input `--local-model-dir` is the converter's output directory;
the imported snapshot is published under `--local-root` in the GGUF layout.

Import verifies the source snapshot, copies the existing GGUF outputs, bundles
and hashes dependency/calibration files and the source manifest, then seals a
separate conversion snapshot. It records commands and environment as
**user-reported**, never executes them, and does not attest that the reported
commands produced the outputs. Use a new conversion name if any output, recipe,
or input changes. Downloaded third-party GGUF provenance records its publisher's
revision; it does not invent a conversion recipe.

## Markdown download catalog

`model-catalog` scans local and NAS storage offline and creates or updates a
Markdown catalog. It needs only Python 3.9+ and does not modify model snapshots.
Run it from the repository root:

```sh
# Scan both roots; write LOCAL_ROOT/MODEL-CATALOG.md
./bin/model-catalog --local-root /storage/hf-model-archives --nas-root /mounted/ai-models

# Scan just local storage using the archiver's existing defaults/environment
./bin/model-catalog --local-only

# Save a combined catalog on both storage systems
./bin/model-catalog --local-root /storage/hf-model-archives --nas-root /mounted/ai-models \
  --output /storage/hf-model-archives/MODEL-CATALOG.md \
  --output /mounted/ai-models/MODEL-CATALOG.md

# Read-only preview; --nas-only similarly limits scanning to the NAS
./bin/model-catalog --local-only --stdout
```

The implementation is `scripts/ai/catalog-hf-models`; `bin/model-catalog` is a
symlink to it. Both entry points accept the same flags. Roots use the same
`HF_MODEL_DOWNLOAD_ROOT`, `AI_MODELS_NAS_ROOT`, and XDG defaults as the archiver.
With `--nas-only`, the default output is `NAS_ROOT/MODEL-CATALOG.md`.
For remote storage, run the command on that machine or use a locally mounted
path; roots are filesystem paths, not SSH URLs.

The index includes a model overview and a section per revision/artifact with:

- A short excerpt from the archived model card, with a metadata-based fallback.
- Repository/revision links, source versus GGUF artifacts, formats, and filename
  quantization labels. Identical snapshot manifests share an entry listing both
  local and NAS copies; different revisions, selections, and recipes stay separate.
- Declared architecture/dtype, base model, task, language, license, recorded
  conversion tool, download timestamps, and readiness warnings where available.
- Each copy's directory, file count, total file size, and weight-file size.
  Sizes are logical file sizes, not disk allocation or runtime memory estimates.
- A separate filename/size list for `.tar` and `.tar.zst` packages.

The scan covers `source/huggingface` and `inference/gguf`, plus packages under
`archives`. Older weight/config directories within these layouts are listed as
**unsealed**, with unknown revisions and path-inferred repository names. Arbitrary
flat directories and the Hugging Face Hub cache are not cataloged. Hidden staging
directories and nested directory symlinks are skipped; a symlink for the storage
root itself is supported. Model cards/configs are read in bounded amounts;
weights are only statted, and tar packages are never decompressed.

This is a catalog, not checksum verification: sealed entries have a manifest,
but the scan does not prove their bytes match. Missing/extra recorded files are
flagged. Model-card prose and metadata are publisher declarations, not independently
verified capabilities or hardware requirements. Simple scalar/list card fields
are supported without requiring a YAML library; complex YAML remains unknown.

Rerun the command to refresh the catalog after downloads, copies, or removals.
Each output is replaced atomically only after a successful scan. Missing roots,
unreadable files, or malformed metadata cause failure and preserve the previous
catalog. Use `--local-only` when the NAS is unavailable instead of publishing an
incomplete combined catalog. Ensure the NAS is actually mounted: an existing
empty mount directory cannot be distinguished from an intentionally empty archive.

Outputs must end in `.md` and stay outside model directories. The command only
replaces files bearing its generated-file marker, protecting unrelated Markdown
documents. Generated catalogs should live on storage outside this repository;
keep personal notes in a separate file because refresh replaces generated content.

## Hardware requirements for inference

An archived model needs both a compatible runtime/GPU and enough memory to run.
The archive tool preserves metadata but does not calculate hardware requirements
or test runtime compatibility.

1. Inspect the snapshot's `README.md` for the publisher's usage instructions and
   dependencies. Check `config.json` for architecture, `dtype` / `torch_dtype`,
   and `quantization_config`. The `source_assessment` in
   `archive-provenance/snapshot.json` summarizes declared values and warnings;
   these declarations are not verified tensor precision. Identify the exact GGUF
   variant or complete set of weight shards you intend to load, including any
   required base model or multimodal components.
2. Estimate weight memory as `total parameters × bits per parameter ÷ 8` bytes.
   For an 8-billion-parameter model, theoretical weights alone require:

   | Precision | Approximate weight memory (decimal GB) |
   |---|---:|
   | FP32 | 32 GB |
   | FP16 / BF16 | 16 GB |
   | 8-bit | 8 GB |
   | 4-bit | 4 GB |

   These are not total VRAM requirements. Quantization metadata, runtime working
   memory, and the KV cache add overhead. Longer context and more simultaneous
   requests can substantially increase memory use. Use actual selected weight
   sizes to refine the estimate, allowing for the runtime's loaded precision;
   compressed tar size does not estimate runtime memory. For mixture-of-experts
   models, use total parameters for weight storage, not just active parameters.
   See the [Hugging Face cache documentation](https://huggingface.co/docs/transformers/main/en/kv_cache).
3. Check that your runtime version supports the exact model architecture,
   quantization, GPU, drivers, and operating system. For example,
   [llama.cpp](https://github.com/ggml-org/llama.cpp) runs supported GGUF models
   using backends such as NVIDIA CUDA and Apple Metal, and supports CPU execution
   and mixed CPU/GPU loading. Offloading requires sufficient system RAM and can
   reduce speed. On Apple silicon, budget available unified memory shared with
   the OS and other applications. Enough memory alone does not prove compatibility.
4. Test the exact artifact at your intended context length and concurrency.
   Record peak memory and generation speed; loading successfully does not prove
   the model is fast enough for your use. These estimates concern inference;
   training and fine-tuning have different memory requirements.

Keep a test record outside the sealed snapshot, such as under
`$XDG_STATE_HOME/hf-model-archives` (default `~/.local/state/hf-model-archives`).
Record the model revision and artifact, quantization, runtime/version, OS/driver,
GPU and VRAM (or Mac/unified memory), system RAM, context length, concurrency,
offloading settings, peak memory, and measured speed. Do not edit the published
snapshot to add hardware notes.

## Optional packaging and restore checks

Ordinary uncompressed directories remain the default storage format; the standard
workflow does not create a tar archive. `--archive` optionally packages a snapshot
as an uncompressed `.tar`. Compression is not required for preservation, checksums,
or verification. Enable zstd only when its storage/transfer savings justify the
extra compression/decompression work; measure savings on your actual artifacts.

```sh
# Optional uncompressed tar (no zstd dependency)
./archive-hf-model Qwen/Qwen3-8B --revision FULL_COMMIT --archive

# Opt in to zstd compression
./archive-hf-model Qwen/Qwen3-8B --revision FULL_COMMIT --archive --compression zstd
```

Archives default beside the local snapshot, named
`<model>-<commit>[-<artifact>].tar`, or `.tar.zst` with `--compression zstd`.
`--archive-dir` / `--archive-path`
choose another location outside the snapshot; explicit filenames must end in
`.tar` or `.tar.zst`, which determines their compression even when `--compression`
is supplied. An explicit `.tar.zst` path also opts into compression. Existing archives are
verified and reused, never overwritten. Archive publication requires filesystem
hard-link support for the temporary and final archive in the same directory.

Creation reads back every archived file and compares it with the source inventory
before publishing. By default it also creates `<archive>.sha256`.
`--no-archive-checksum` explicitly omits that sidecar. `--archive-checksum` validates
an existing archive internally before initializing a missing sidecar; it cannot
establish the historical authenticity of an archive whose baseline was lost.

Copy the archive and its sidecar together, then verify both the archive hash and
all embedded file hashes, without extracting:

```sh
./archive-hf-model Qwen/Qwen3-8B --verify-archive \
  --archive-path /mounted/second-storage/Qwen3-8B-FULL_COMMIT.tar
```

For a restore drill, extract the verified archive into a fresh empty directory:

```sh
mkdir /storage/restore-check
tar -xf /mounted/second-storage/Qwen3-8B-FULL_COMMIT.tar -C /storage/restore-check
```

For an optionally compressed archive, verify its `.tar.zst` path above, then
extract into a fresh empty directory:

```sh
mkdir /storage/restore-check-zstd
zstd -dc /mounted/second-storage/Qwen3-8B-FULL_COMMIT.tar.zst \
  | tar -xf - -C /storage/restore-check-zstd
```

Source archives contain a top-level commit directory; GGUF archives contain the
artifact directory (`download` or the conversion name). Preserve the external
checksum tree too. From the restored snapshot directory, `sha256sum -c` with the
saved snapshot `.sha256` validates the restored files (macOS: `shasum -a 256 -c`).
Test loading/converting a restored model with its intended runtime as a separate
compatibility check. Keep the original and an independent verified copy until
your restore and retention requirements are satisfied; the tool never deletes them.

## Development checks

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
```

Run from the repository root. Tests use small temporary fixtures and mocked Hub
calls; rsync transfers and tar/zstd restore checks run locally when available.
