# AI model archives

`archive-hf-model` preserves commit-pinned Hugging Face snapshots for later use,
plus separate GGUF inference artifacts. The default workflow downloads, checks
against the Hub, seals the local snapshot, copies it to NAS staging, verifies the
copy against the source hashes, then publishes the destination directory.

Original model weights can run on supported GPU runtimes directly. GGUF is a
runtime format, and quantization is a separate precision/size tradeoff. Prefer
the publisher's original released precision as the source for future conversions.
Neither a `.safetensors` extension nor this archive tool certifies original
precision, lineage, or compatibility with a particular converter/runtime.

## Requirements

- Python 3.9+; no additional Python packages required by this script.
- For downloads: `hf` supporting `models info --expand --format json` and
  `cache verify --local-dir --revision`. Authentication uses the CLI's existing
  login or `HF_TOKEN`; do not put credentials in recipes or command arguments.
- For NAS/backup copies: `rsync` (including the older macOS version).
- For `.tar.zst`: `zstd`. Uncompressed `.tar` needs only Python.

The implementation supports Linux/macOS without requiring systemd, GNU tar,
or a particular GPU. NAS and backup roots must already exist. Mount the intended
storage before running; an existing directory alone does not prove a NAS is mounted.

Run examples from `scripts/ai/`, or use the script's path from the checkout root.
Run `./archive-hf-model --help` for all options.

## Storage and immutability

Local storage defaults to `$XDG_DATA_HOME/hf-model-archives`, falling back to
`~/.local/share/hf-model-archives`. NAS defaults to `/mnt/ai-models`.
Override with `--local-root` / `HF_MODEL_DOWNLOAD_ROOT` and `--nas-root` /
`AI_MODELS_NAS_ROOT`. Choose a persistent disk with enough free space for the
source, staged copies, and any optional archive; `/tmp` is no longer the default.

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
selection of the same repository commit, supply a different `model_name`:

```sh
./archive-hf-model owner/repo selected-q4 \
  --include 'model-Q4_K_M.gguf' --include 'README.md' --include 'LICENSE*'
```

Auto layout routes GGUF-only weights to `inference/gguf`; source weights, mixed
repositories, and unknown selections use `source/huggingface`. `--layout` changes
routing, not filtering. GGUF layout rejects recognized source-format weights.

Old flat or mutable owner/model directories are not moved, deleted, or silently
adopted. Download the desired revision into a fresh snapshot to establish its
provenance. `--local-model-dir` can select a new exact download destination, or
an existing **sealed** snapshot for offline operations. Existing unmanaged
folders are rejected; a tar operation cannot reconstruct their original revision.

## Download and source checks

```sh
# Default: download, verify, copy to NAS, and save checksums
./archive-hf-model Qwen/Qwen3-8B

# Local snapshot only, resolving a branch/tag or full commit
./archive-hf-model Qwen/Qwen3-8B --revision main --download

# Require the structural source checks to pass without warnings
./archive-hf-model Qwen/Qwen3-8B --download --require-source-complete
```

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
`--require-source-complete` makes all assessment warnings fatal; some valid
non-Transformers repositories will need normal mode and manual review.

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

Offline stages require `--revision` with the **full commit SHA**, or derive it
from a sealed `--local-model-dir`. They never resolve `main` online.

```sh
./archive-hf-model Qwen/Qwen3-8B --revision FULL_COMMIT --sync

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
`.*.copy-partial` directories. Rerun with the same selection to resume. Publication
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

Paths in the recipe are relative to the recipe file unless absolute. The converter
commit must be a full lowercase SHA. `dependency_files` must be nonempty; use
`calibration_files: []` when no calibration was used. Otherwise list the data and
importance-matrix files to preserve. Only include non-secret files and commands.

```sh
./archive-hf-model Qwen/Qwen3-8B \
  --record-conversion /work/recipe.json --local-model-dir /work/outputs --sync

./archive-hf-model Qwen/Qwen3-8B --revision FULL_SOURCE_COMMIT \
  --conversion-name q4-k-m --verify
```

Import verifies the source snapshot, copies the existing GGUF outputs, bundles
and hashes dependency/calibration files and the source manifest, then seals a
separate conversion snapshot. It records commands and environment as
**user-reported**, never executes them, and does not attest that the reported
commands produced the outputs. Use a new conversion name if any output, recipe,
or input changes. Downloaded third-party GGUF provenance records its publisher's
revision; it does not invent a conversion recipe.

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
