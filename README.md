dotfiles
========

Dave's Dotfiles


Used the example from: http://blog.smalleycreative.com/tutorials/using-git-and-github-to-manage-your-dotfiles/
to sync my dotfiles

NOTE!!!: do not run makesymlinks.sh because it installs zsh and oh_my_zsh. I don't use zsh

vimrc examples from:https://www.youtube.com/watch?v=YhqsjUUHj6g

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
Using ctrlp as an example,
```bash
~/dotfiles$ git submodule add https://github.com/kien/ctrlp.vim.git vim/bundle/ctrlp.vim
~/dotfiles$ git commit -m "added ctrlp vim plugin"
~/dotfiles$ git push
```


## Notes about TMUX
Since tmux doesnt run in 256 mode by default it is best to force it using an alias in either .bashrc or .profile.
For whatever reason it is not enabled in .tmux.conf even though it is there.
Put this line in either .bashrc or .profile or both:
alias tmux="TERM=screen-256color-bce tmux"

## Tmuxifier
Define the custom layouts path for tmuxifier in .profile or .bashrc so we can sync our custom layouts.
First make a symlink to `~/.tmux-layouts` from `~/dotfiles/tmux-layouts`
Then in either .profile or .bash
```bash
export TMUXIFIER_LAYOUT_PATH="$HOME/.tmux-layouts"
```
Add an extra argument in .profile to force tmuxifier to start tmux in 256 color mode.
