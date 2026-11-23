# shell/init.zsh - interactive zsh entry point, loaded from ~/.zshrc.
# Layers (each only if present): env -> portable aliases -> OS-specific -> functions
# -> machine-local ($XDG_CONFIG_HOME/dotfiles/local.zsh, not in Git).

: "${DOTFILES:=${${(%):-%x}:A:h:h}}"

. "$DOTFILES/shell/env.sh"

case "$(uname -s)" in
    Darwin) _dotfiles_host="$DOTFILES/shell/hosts/macos.sh" ;;
    Linux)  _dotfiles_host="$DOTFILES/shell/hosts/linux.sh" ;;
    *)      _dotfiles_host="" ;;
esac

for _dotfiles_file in \
    "$DOTFILES/shell/aliases.sh" \
    "$_dotfiles_host" \
    "$DOTFILES/shell/functions.sh" \
    "$XDG_CONFIG_HOME/dotfiles/local.zsh"
do
    if [ -n "$_dotfiles_file" ] && [ -r "$_dotfiles_file" ]; then
        . "$_dotfiles_file"
    fi
done
unset _dotfiles_host _dotfiles_file
