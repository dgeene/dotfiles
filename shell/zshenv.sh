# shell/zshenv.sh - loaded from ~/.zshenv, which zsh reads for EVERY invocation
# (scripts, cron, ssh commands). Keep it minimal: environment and PATH only.
# No aliases, no prompts, no output.

. "${DOTFILES:?}/shell/env.sh"

if [ -r "$XDG_CONFIG_HOME/dotfiles/local.zshenv" ]; then
    . "$XDG_CONFIG_HOME/dotfiles/local.zshenv"
fi
