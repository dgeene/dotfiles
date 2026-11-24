# shell/hosts/macos.sh - macOS-only aliases and settings.

alias ls='ls -Gh'
alias code='open -a "Visual Studio Code" --args'
alias subl='open -a "Sublime Text" --args'

# Homebrew must precede /usr/bin. /etc/zprofile's path_helper runs after ~/.zshenv and
# pushes system dirs to the front for login shells, so re-assert the order here.
for _dotfiles_brew_dir in /opt/homebrew/sbin /opt/homebrew/bin; do
    [ -d "$_dotfiles_brew_dir" ] && path_front "$_dotfiles_brew_dir"
done
unset _dotfiles_brew_dir
