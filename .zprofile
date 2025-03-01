#!/bin/sh
# read first
# env vars to be set on login, zsh settings in ~/.zshrc


# default programs
export EDITOR="nvim"
#export TERM="st"
#export TERMINAL="st"

# follow XDG base dir specification
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_CACHE_HOME="$HOME/.cache"

# bootstrap .zshrc to ~/.config/zsh/.zshrc, any other zsh config files can reside here
export ZDOTDIR="$XDG_CONFIG_HOME/zsh"


# moving other files and vars
