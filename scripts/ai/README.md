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

### Usage

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

# Sync an already-downloaded local model to the NAS and create checksums
./archive-hf-model Qwen/Qwen3-8B Qwen3-8B --sync --checksum

# Use a local model directory outside the default staging root
./archive-hf-model Qwen/Qwen3-8B Qwen3-8B \
    --local-model-dir ~/ai/downloads/Qwen3-8B \
    --sync \
    --checksum
```

If something fails halfway through, rerun it

rsync will avoid retransferring files that are already identical.

The --partial option also helps with interrupted transfers.

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
