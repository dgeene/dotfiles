#!/bin/bash
# Script to prep my environment on a newly installed system
# Designed for debian/ubuntu systems


# TODO
# After pulling repo down
# 1. git submodule init and update
# 2. create symlinks for
#   vim
#   vimrc
#   tmux-layouts
#   tmux.conf
#   bin
#
#
# ideas for bashrc
# 1. use an amber color for non-local bash sessions


#TODO put sudo check here
# If we're on a server and we don't have sudo privileges
# then do a best effort bootstrapping

cat << SetupMessage


This script is meant to be run on a fresh install of a debian/ubuntu system.
--Apt Installs--
tmux
vim
--Git Repos--
tmuxifier


SetupMessage


dir=~/dotfiles
olddir=~/old_dotfiles
symlinks="vim vimrc tmux.conf"

main () {

    echo "installing our favorite packages..."
    sleep 1
    #apt-get -y install vim tmux git

    echo "Creating symlinks for $symlinks"
    for link in $symlinks; do
        echo "$link"
    done


}


main
