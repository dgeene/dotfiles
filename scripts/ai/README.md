# AI Scripts

## Archiving Models
There's also an important wrinkle here.

A Hugging Face download is not necessarily an Ollama model.

For example, you might have:
```text
config.json
tokenizer.json
tokenizer_config.json
generation_config.json
model-00001-of-00008.safetensors
model-00002-of-00008.safetensors
...
```
That's a Hugging Face model repository.

Ollama generally wants a model packaged/imported through its own model format/Modelfile workflow. LM Studio can work much more directly with certain Hugging Face formats, particularly GGUF.

### Download workflow
This gives you a local staging area so that a partially failed download doesn't leave your NAS full of half-downloaded models.

```text
Hugging Face
     │
     ▼
~/ai/downloads/
     │
     │ rsync
     ▼
NAS:/mnt/ai-models/huggingface/
     │
     ├── checksum
     │
     └── optional archive
```

### Recommended archive layout

```text
/mnt/ai-models/
├── README.md
├── huggingface/
│   ├── Qwen/
│   │   ├── Qwen3-30B-A3B/
│   │   └── Qwen3-8B/
│   │
│   ├── meta-llama/
│   │   └── Llama-3.3-70B-Instruct/
│   │
│   └── mistralai/
│       └── Mistral-Small-3.1-24B-Instruct/
│
├── gguf/
│   ├── Qwen/
│   ├── Llama/
│   └── Mistral/
│
├── ollama/
│   └── manifests/
│
├── archives/
│   ├── huggingface/
│   └── gguf/
│
└── checksums/
    ├── huggingface/
    └── gguf/
```

Use the top-level directories by purpose:

```text
huggingface/   upstream-style Hugging Face repository mirrors
gguf/          curated runtime-ready GGUF files for local inference engines
ollama/        Ollama-specific manifests, blobs, or imports
archives/      compressed or cold-storage copies
checksums/     checksum manifests for stored models and artifacts
```

A GGUF file may originally come from a Hugging Face repository, but it can still
be useful to keep a separate `gguf/` area for hand-picked files intended to be
loaded directly by LM Studio, llama.cpp, or similar tools. As a rule of thumb,
store full Hub repository downloads under `huggingface/`; store selected,
runtime-ready `.gguf` artifacts under `gguf/`.

### Model format compatibility

Hugging Face is a hosting platform and repository layout, not a single runtime
format. A model stored under `huggingface/` may still contain files meant for
different engines.

Check the files before trying to load a model from the NAS:

```shell
find /mnt/ai-models/huggingface/<org>/<model> -maxdepth 2 -type f
```

Common patterns:

```text
config.json
tokenizer.json
model-00001-of-00004.safetensors
model.safetensors.index.json
```

This is usually a Hugging Face Transformers-style model. It is most likely to
work with Python/server runtimes such as Transformers, vLLM, Text Generation
Inference, or other engines that explicitly support Hugging Face model
directories and safetensors.

```text
model.gguf
model-Q4_K_M.gguf
model-Q6_K.gguf
```

This is a GGUF model. It is most likely to work with llama.cpp-style runtimes
such as LM Studio, llama.cpp, and many local desktop LLM tools.

`hf download` does not automatically separate safetensors models from GGUF
models. It downloads files from the requested Hub repository. Use `--include`
or `--exclude` when you only want one format:

```shell
# Download only GGUF files from a repository
./archive-hf-model <org>/<repo> <model-name> --include "*.gguf"

# Exclude GGUF files from a mixed repository
./archive-hf-model <org>/<repo> <model-name> --exclude "*.gguf"
```

Before moving or converting a model, check the target engine's documentation.
Format support is engine-specific, and being hosted on Hugging Face does not
mean every local model engine can load it directly.

### Usage

Downloads automatically create `archive-provenance/download-<unique-id>.json`
inside the model directory. These records are included in NAS syncs and tar
archives. Downloading requires Python 3.9+ and an `hf` CLI supporting
`hf models info --expand --format json`; authentication uses the CLI's normal
login or `HF_TOKEN`. Archive and sync stages still work offline.

Each record contains the repository URL, requested revision, resolved commit,
commit-pinned file URLs, UTC download start/completion times, file sizes and
locally computed SHA-256 hashes. The download itself is pinned to that commit.
Hashing reads each selected file in full and can take time for large models.
Times describe the current successful download invocation, including cache
reuse, rather than claiming to know when cached bytes were first downloaded.

Per-file format information distinguishes `quantized_gguf` (quantization label
recognized in the filename), `gguf` (quantization unknown), and
`source_format_weights` (such as safetensors or PyTorch weights). Classification
is based on filenames, not tensor inspection: source-format weights can also
be quantized, adapters, or derivatives. The model card's declared base model
and base-model relation are saved when available, without claiming verified
lineage. GGUF's embedded metadata stays in the original file.

Records cover only repository files selected by that invocation, not cache
files or unrelated files already in the directory. Earlier records are retained;
their hashes describe earlier downloads and may differ from files subsequently
updated in place. Failed downloads do not publish a new record. Existing
downloads need a successful `--download` run to gain provenance; `--archive`
alone cannot reconstruct their original download date or revision.

For a single quantization plus its model card:

```shell
./archive-hf-model \
  mradermacher/Hermes-3-Llama-3.1-70B-Uncensored-i1-GGUF \
  Hermes-3-70B-i1-Q4_K_S \
  --include 'Hermes-3-Llama-3.1-70B-Uncensored.i1-Q4_K_S.gguf' \
  --include 'README.md' \
  --download --archive
```

```shell
./archive-hf-model Qwen/Qwen3-8B Qwen3-8B
# saves to
# /mnt/ai-models/huggingface/Qwen/Qwen3-8B/
```

Run only selected stages by passing one or more stage flags. If no stage flags
are passed, the command runs the full download, sync, and checksum workflow.
For private or gated models, set `HF_TOKEN` in the environment before running
the download stage.

```shell
# Download only
./archive-hf-model Qwen/Qwen3-8B Qwen3-8B --download

# Download with one worker to avoid saturating the connection
./archive-hf-model Qwen/Qwen3-8B Qwen3-8B --download --limit

# Sync an already-downloaded local model to the NAS and create checksums
./archive-hf-model Qwen/Qwen3-8B Qwen3-8B --sync --checksum

# Create a local tar archive and checksum for manual copying
./archive-hf-model Qwen/Qwen3-8B Qwen3-8B --archive

# Download, then create a local tar archive and checksum
./archive-hf-model Qwen/Qwen3-8B Qwen3-8B --download --archive

# Use a local model directory outside the default staging root
./archive-hf-model Qwen/Qwen3-8B Qwen3-8B \
    --local-model-dir ~/ai/downloads/Qwen3-8B \
    --sync \
    --checksum
```

If something fails halfway through, rerun it

rsync will avoid retransferring files that are already identical.

The --partial option also helps with interrupted transfers.

For manual copying, the archive stage writes a local `.tar.zst` next to the
local model directory by default, plus a matching `.sha256` file:

```text
/tmp/hf-model-downloads/Qwen3-8B.tar.zst
/tmp/hf-model-downloads/Qwen3-8B.tar.zst.sha256
```

Copy both files to the NAS, then verify the archive from the directory that
contains both files:

```shell
sha256sum -c Qwen3-8B.tar.zst.sha256
```

Verifying the entire model
```shell
cd /mnt/ai-models/huggingface/Qwen/Qwen3-8B
sha256sum -c \
    /mnt/ai-models/checksums/huggingface/Qwen/Qwen3-8B.sha256
```

For models you don't expect to use for a while, you could archive them:
```shell
tar --zstd -cvf \
    /mnt/ai-models/archives/huggingface/Qwen3-8B.tar.zst \
    -C /mnt/ai-models/huggingface/Qwen \
    Qwen3-8B
```
Then potentially remove the directory after verifying the archive.

To inspect an archive without extracting it:
```shell
tar --zstd -tf Qwen3-8B.tar.zst
```

And restore:
```shell
tar --zstd -xvf Qwen3-8B.tar.zst \
    -C /mnt/ai-models/huggingface/Qwen
```
