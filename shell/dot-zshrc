#!/bin/sh
# parsed second



# source global shell alias and variales files
[ -f "$XDG_CONFIG_HOME/shell/alias" ] && source "$XDG_CONFIG_HOME/shell/alias"

# load modules
#zmodload zsh/complist
#autoload -U compinit && compinit
autoload -U colors && colors
#autoload -U tetris



# completion options




# main options
setopt append_history inc_append_history share_history # better history
# on exit history appends rather than oeverwrite; history appends as cmds are executed; history shared across sesions
setopt auto_menu menu_complete # autocomplete first menu match
setopt autocd
setopt auto_param_slash # when dir is completed add a /
setopt no_case_glob no_case_match # make autocomplete case insensitive
setopt globdots # include dotfiles
setopt extended_glob # match ~ # ^
setopt interactive_comments # allow comments in the shell
unsetopt prompt_sp # dont autoclean blank lines


# history opts
HISTSIZE=1000000
SAVEHIST=1000000
HISTFILE="$XDG_CACHE_HOME/zsh_history" # move histfile to cache
HISTCONTROL=ignoreboth # consecutive duplicate commands and cms with space are not saved


# fzf setup
#source <(fzf --zsh) # allow fzf history widget


# keybindings to view a list type zle -l also set -o


# setup prompt
