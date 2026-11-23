#!/usr/bin/env bash
# install.sh - link dotfiles repository components into the user's home.
#
# Purpose:  Idempotent, non-destructive first-time (and repeat) setup.
# Requires: bash 3.2+, ln, readlink (macOS and Linux). Windows is not yet supported.
#
# Usage:
#   ./install.sh [--dry-run] [--with-shell] [--backup TARGET]... [--skip-conflicts]
#
# Options:
#   -n, --dry-run        Print the plan; change nothing.
#   --with-shell         Also append (or refresh) a marked block in ~/.zshenv and
#                        ~/.zshrc that sources shell/zshenv.sh and shell/init.zsh,
#                        and create machine-local templates
#                        $XDG_CONFIG_HOME/dotfiles/local.zshenv and local.zsh.
#                        Existing contents are kept; a timestamped backup is made
#                        first. Re-running replaces only the text between markers.
#                        Honors ZDOTDIR; DOTFILES_ZSHENV / DOTFILES_ZSHRC override
#                        the target paths (used for testing).
#   --backup TARGET      Move existing TARGET to TARGET.bak.<timestamp>, then link.
#                        Repeatable. Use after reviewing a dry run.
#   --skip-conflicts     Never prompt; skip and report conflicts.
#   -h, --help           Show this help.
#
# Links created (relative to this checkout):
#   bin/*                 -> $HOME/.local/bin/
#   config/nvim           -> $XDG_CONFIG_HOME/nvim
#   config/tmux           -> $XDG_CONFIG_HOME/tmux
#   config/wireplumber    -> $XDG_CONFIG_HOME/wireplumber (only if wireplumber is installed)
#
# Existing files are never replaced silently. Without a TTY, conflicts are
# skipped and reported (exit status 2). Interactive runs prompt per conflict.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"

DRY_RUN=0
WITH_SHELL=0
SKIP_CONFLICTS=0
BACKUP_TARGETS=""
n_ok=0 n_linked=0 n_backed=0 n_skipped=0

usage() { sed -n '2,/^$/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }
die() { echo "ERROR: $*" >&2; exit 1; }

while [ $# -gt 0 ]; do
    case "$1" in
        -n|--dry-run) DRY_RUN=1 ;;
        --with-shell) WITH_SHELL=1 ;;
        --skip-conflicts) SKIP_CONFLICTS=1 ;;
        --backup) [ $# -ge 2 ] || die "--backup requires a path"; BACKUP_TARGETS="$BACKUP_TARGETS
$2"; shift ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown option: $1 (see --help)" ;;
    esac
    shift
done

case "$(uname -s)" in
    Darwin|Linux) ;;
    *) die "unsupported OS '$(uname -s)'. Windows support is not implemented yet." ;;
esac

say() { printf '%s\n' "$*"; }

# Emit "source<TAB>destination" pairs for this machine.
plan() {
    local f name
    for f in "$REPO"/bin/*; do
        [ -e "$f" ] || [ -L "$f" ] || continue
        name="$(basename "$f")"
        printf '%s\t%s\n' "$f" "$HOME/.local/bin/$name"
    done
    printf '%s\t%s\n' "$REPO/config/nvim" "$XDG_CONFIG_HOME/nvim"
    printf '%s\t%s\n' "$REPO/config/tmux" "$XDG_CONFIG_HOME/tmux"
    if command -v wireplumber >/dev/null 2>&1; then
        printf '%s\t%s\n' "$REPO/config/wireplumber" "$XDG_CONFIG_HOME/wireplumber"
    fi
}

is_backup_target() {
    printf '%s\n' "$BACKUP_TARGETS" | grep -Fxq -- "$1"
}

describe_existing() {
    if [ -L "$1" ]; then
        echo "symlink -> $(readlink "$1")"
    elif [ -d "$1" ]; then
        echo "directory"
    else
        echo "file"
    fi
}

make_link() {
    mkdir -p "$(dirname "$2")"
    ln -s "$1" "$2"
}

backup_and_link() {
    local src="$1" dest="$2" bak
    bak="$dest.bak.$(date +%Y%m%d%H%M%S)"
    say "  BACKUP $dest -> $bak"
    if [ "$DRY_RUN" -eq 0 ]; then
        mv "$dest" "$bak"
        make_link "$src" "$dest"
    fi
    n_backed=$((n_backed + 1))
}

link_one() {
    local src="$1" dest="$2" answer
    if [ ! -e "$src" ] && [ ! -L "$src" ]; then
        say "  MISSING source $src (skipped)"
        n_skipped=$((n_skipped + 1))
        return
    fi

    if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then
        say "  ok       $dest"
        n_ok=$((n_ok + 1))
        return
    fi

    if [ ! -e "$dest" ] && [ ! -L "$dest" ]; then
        say "  LINK     $dest -> $src"
        if [ "$DRY_RUN" -eq 0 ]; then make_link "$src" "$dest"; fi
        n_linked=$((n_linked + 1))
        return
    fi

    # Conflict: something else already lives at dest.
    if is_backup_target "$dest"; then
        backup_and_link "$src" "$dest"
    elif [ "$DRY_RUN" -eq 0 ] && [ "$SKIP_CONFLICTS" -eq 0 ] && [ -t 0 ]; then
        printf '  CONFLICT %s (%s)\n    [s]kip or [b]ackup and replace? [s/b] ' "$dest" "$(describe_existing "$dest")"
        read -r answer
        case "$answer" in
            b|B) backup_and_link "$src" "$dest" ;;
            *) say "    skipped"; n_skipped=$((n_skipped + 1)) ;;
        esac
    else
        say "  CONFLICT $dest ($(describe_existing "$dest")) - skipped; rerun with --backup '$dest' to replace"
        n_skipped=$((n_skipped + 1))
    fi
}

say "Dotfiles repo: $REPO"
say "Host: $(uname -s) / $(uname -m)$([ "$DRY_RUN" -eq 1 ] && echo ' (dry run)')"
say ""

while IFS="$(printf '\t')" read -r src dest; do
    link_one "$src" "$dest"
done <<EOF
$(plan)
EOF

# Base XDG directories.
if [ "$DRY_RUN" -eq 0 ]; then
    mkdir -p "$HOME/.local/bin" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_STATE_HOME" "$XDG_CACHE_HOME"
fi

# Shell integration: marked blocks in existing rc files (never replaces the files).
BLOCK_BEGIN="# >>> dotfiles (managed by install.sh; safe to delete this block) >>>"
BLOCK_END="# <<< dotfiles <<<"

# DOTFILES default written into the rc blocks: $HOME-relative when possible.
case "$REPO" in
    "$HOME"/*) DOTFILES_REF="\$HOME/${REPO#"$HOME"/}" ;;
    *) DOTFILES_REF="$REPO" ;;
esac

# manage_block FILE ENTRY_SCRIPT: ensure FILE has exactly one managed block.
manage_block() {
    local file="$1" entry="$2" tmp block_text
    block_text="$BLOCK_BEGIN
export DOTFILES=\"\${DOTFILES:-$DOTFILES_REF}\"
[ -r \"\$DOTFILES/$entry\" ] && . \"\$DOTFILES/$entry\"
$BLOCK_END"
    tmp="$(mktemp "${TMPDIR:-/tmp}/dotfiles-install.XXXXXX")"
    if [ -f "$file" ] && grep -Fq -- "$BLOCK_BEGIN" "$file"; then
        # Replace the existing block in place.
        BLOCK_TEXT="$block_text" awk -v b="$BLOCK_BEGIN" -v e="$BLOCK_END" '
            $0 == b { print ENVIRON["BLOCK_TEXT"]; skip = 1; next }
            skip && $0 == e { skip = 0; next }
            !skip { print }' "$file" > "$tmp"
    else
        { [ -f "$file" ] && cat "$file"; printf '\n%s\n' "$block_text"; } > "$tmp"
    fi
    if [ -f "$file" ] && cmp -s "$file" "$tmp"; then
        say "  ok       $file (block up to date)"
        n_ok=$((n_ok + 1))
    elif [ "$DRY_RUN" -eq 1 ]; then
        say "  APPEND   $file (managed block -> $entry)"
    else
        if [ -f "$file" ]; then
            cp -p "$file" "$file.bak.$(date +%Y%m%d%H%M%S)"
        fi
        cat "$tmp" > "$file"   # preserves mode/owner of an existing file
        say "  UPDATED  $file (managed block -> $entry; backup kept)"
        n_linked=$((n_linked + 1))
    fi
    rm -f "$tmp"
}

ensure_local() {
    local file="$1" text="$2"
    [ -e "$file" ] && return 0
    if [ "$DRY_RUN" -eq 1 ]; then
        say "  CREATE   $file (empty template)"
    else
        mkdir -p "$(dirname "$file")"
        printf '%s\n' "$text" > "$file"
        say "  created  $file"
    fi
}

if [ "$WITH_SHELL" -eq 1 ]; then
    say ""
    say "Shell integration:"
    manage_block "${DOTFILES_ZSHENV:-${ZDOTDIR:-$HOME}/.zshenv}" "shell/zshenv.sh"
    manage_block "${DOTFILES_ZSHRC:-${ZDOTDIR:-$HOME}/.zshrc}" "shell/init.zsh"
    ensure_local "$XDG_CONFIG_HOME/dotfiles/local.zshenv" "# Machine-local, non-secret environment/PATH (read for every zsh). Not tracked by Git.
# Example: export JAVA_HOME=\"\$HOME/.jdk\"; path_prepend \"\$JAVA_HOME/bin\""
    ensure_local "$XDG_CONFIG_HOME/dotfiles/local.zsh" "# Machine-local, non-secret interactive zsh settings. Not tracked by Git.
# Example: alias work='source ~/.env_work'"
fi

say ""
say "Summary: $n_linked linked, $n_ok already correct, $n_backed backed up, $n_skipped skipped"

case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) say "NOTE: \$HOME/.local/bin is not on PATH. Add: export PATH=\"\$HOME/.local/bin:\$PATH\"" ;;
esac

[ "$n_skipped" -eq 0 ] || exit 2
