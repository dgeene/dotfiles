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
symlinks="vim vimrc tmux.conf tmux-layouts"

main () {

    echo "installing our favorite packages..."
    sleep 1
    #apt-get -y install vim tmux git



    echo "Creating symlinks for $symlinks. Will backup old ones."
    #[[ -d $olddir ]] || mkdir $olddir
    for link in $symlinks; do
        #mv ~/.$link $olddir
        echo "Creating symlink for $link"
        #ln -s $dir/$file ~/.$file
    done

    echo "sourcing our functions from scripts/e"
    echo -e '/n/nsource $HOME/dotfiles/scripts/functions' >> ~/.bashrc

    echo "Pulling git submodules"
    sleep 1
    #git submodule init
    #git submodule update

    echo "Installing tmuxifier"
    sleep 1
    git clone https://github.com/jimeh/tmuxifier.git ~/.tmuxifier
    echo -e "\n\n### For Tmuxifier ###" >> ~/.bashrc
    echo -e 'export PATH="$HOME/.tmuxifier/bin:$PATH"' >> ~/.bashrc
    echo -e 'export TMUXIFIER_LAYOUT_PATH="$HOME/.tmux-layouts' >> ~/.bashrc
    echo -e 'export TMUXIFIER_TMUX_OPTS="-2"' >> ~/.bashrc
    echo -e 'eval "$(tmuxifier init -)"' >> ~/.bashrc


}


main
