# shell/env.sh - portable environment: XDG defaults and PATH helpers.
# Sourced from zsh/bash. Must stay quiet, fast, and idempotent (safe to source twice).
# Toolchain paths (Java, Android, pyenv, conda...) belong in machine-local files,
# not here: $XDG_CONFIG_HOME/dotfiles/local.zshenv or local.zsh.

export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"

# path_prepend DIR / path_append DIR: add DIR to PATH once, only if not already present.
path_prepend() {
    case ":$PATH:" in *":$1:"*) ;; *) PATH="$1${PATH:+:$PATH}" ;; esac
    export PATH
}
path_append() {
    case ":$PATH:" in *":$1:"*) ;; *) PATH="${PATH:+$PATH:}$1" ;; esac
    export PATH
}

# path_front DIR: put DIR at the very front of PATH, removing any earlier occurrence.
# Use when something (e.g. macOS path_helper) reorders PATH after startup files ran.
# Requires bash or zsh.
path_front() {
    local p=":$PATH:"
    while [[ "$p" == *":$1:"* ]]; do p="${p/":$1:"/:}"; done
    p="${p#:}"; p="${p%:}"
    PATH="$1${p:+:$p}"
    export PATH
}

path_prepend "$HOME/.local/bin"
