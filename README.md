# Dotfiles

Model archives preserve immutable repository revisions, verified NAS/backup
copies, and separate GGUF conversions with reproducible recipe records using
[archive-hf-model](scripts/ai/README.md). Optional tar archives include content
verification and restore guidance, with compression available via
`--compression zstd` (default: uncompressed). The guide also explains how to assess
GPU compatibility and inference memory requirements. Existing model directories
are left in place.

Machine specific configurations

To avoid turning a .zshrc into a giant pile of conditionals...

```text
shell/
├── env.sh
├── aliases.sh
├── functions.sh
└── hosts/
    ├── macos.sh
    ├── linux.sh
    └── server.sh
```

Then
```shell
case "$(uname -s)" in
    Darwin)
        source "$DOTFILES/shell/hosts/macos.sh"
        ;;
    Linux)
        source "$DOTFILES/shell/hosts/linux.sh"
        ;;
esac
```
