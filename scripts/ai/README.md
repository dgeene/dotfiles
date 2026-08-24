# AI Scripts

## Archiving Models

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