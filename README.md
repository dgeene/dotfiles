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

NOTE!!!: do not run makesymlinks.sh because it installs zsh and oh_my_zsh. I don't use zsh

vimrc examples from:https://www.youtube.com/watch?v=YhqsjUUHj6g


## Git submodules
We can use gitmodules as a way of keeping our repo clean. We can include a reference to third part code without actually storing it in our own repo.
After the repo has been cloned run:
```bash
$ cd dotfiles
~/dotfiles$ git submodule init
~/dotfiles$ git submodule update
```
This will clone vim/bundle submodules.
Now symlink the following config files to the root of the home directory.
```bash
ln -s ~/dotfiles/vim ~/.vim
ln -s ~/dotfiles/vimrc ~/.vimrc
```


To add more vim plugins as submodules:
```bash
~/dotfiles$ git submodule add <https://path/to/submodule/repo.git> <path/to/designated/directory>
```

Using ctrlp as an example,
```bash
~/dotfiles$ git submodule add https://github.com/kien/ctrlp.vim.git vim/bundle/ctrlp.vim
```

If you do a git status you will notice it modified the gitmodules file and added a new file.
```bash
Changes to be committed:
  (use "git reset HEAD <file>..." to unstage)

    modified:   .gitmodules
    new file:   vim/bundle/rust.vim
```
This new file is ok as git is adding a reference to the file.

It is safe to commit these.

```bash
~/dotfiles$ git commit -m "added ctrlp vim plugin"
~/dotfiles$ git push
```

Just make sure.. Pay attention to whether or not the github repo is a folder or a file. The designated directory will matter.


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
