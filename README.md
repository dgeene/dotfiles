dotfiles
========
Dave's Dotfiles

The goal is to get a system up and running in as little time as possible. This repository will grow as I learn. I am constantly installing linux on something.

## Home Directory Setup
~/bin - for compiled binaries. Usually from outside sources and that I do not want synced.
~/bin/src - source files
~/dotfiles - Where dotfiles that need to be synced to the cloud will live.
~/dotfiles/scripts - Shellscripts and other utilities will live.


Used the example from: http://blog.smalleycreative.com/tutorials/using-git-and-github-to-manage-your-dotfiles/
to sync my dotfiles


vimrc examples from:https://www.youtube.com/watch?v=YhqsjUUHj6g




## Notes about TMUX
Since tmux doesnt run in 256 mode by default it is best to force it using an alias in either .bashrc or .profile.
For whatever reason it is not enabled in .tmux.conf even though it is there.
Put this line in either .bashrc or .profile or both:
alias tmux="TERM=screen-256color-bce tmux"
Also if using putty or mtputty, enable utf-8 mode so we don't get funny characters to denote pane splits. To do that open
the regular putty.exe go to Window > Translation > Remote character set. From the dropwdown select UTF-8. Save this session
and you should be able to load it in mtputty.

## Tmuxifier
Define the custom layouts path for tmuxifier in .profile or .bashrc so we can sync our custom layouts.
First make a symlink to `~/.tmux-layouts` from `~/dotfiles/tmux-layouts`
Then in either .profile or .bash
```bash
eval "$(tmuxifier init -)"
export TMUXIFIER_LAYOUT_PATH="$HOME/.tmux-layouts"
```
Then on the next line we can pass args to tmux itself. In this case force tmux to start in 256 color mode.
```bash
export TMUXIFIER_TMUX_OPTS="-2"
```
