# Dotfiles

Model downloads are organized into source and GGUF inference directories,
with repository provenance and SHA-256 hashes
using [archive-hf-model](scripts/ai/README.md#usage).

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
