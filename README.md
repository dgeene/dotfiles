dotfiles
========

Dave's Dotfiles


Used the example from: http://blog.smalleycreative.com/tutorials/using-git-and-github-to-manage-your-dotfiles/
to sync my dotfiles

NOTE!!!: do not run makesymlinks.sh because it installs zsh and oh_my_zsh. I don't fully understand those tools yet.

vimrc examples from:https://www.youtube.com/watch?v=YhqsjUUHj6g

After the repo has been cloned run:
```bash
$ cd dotfiles
~/dotfiles$ git submodule init
~/dotfiles$ git submodule update
```
This will clone vim/bundle submodules.
Now symlink the config files to the root of the home directory.


To add more vim plugins as submodules:
Using ctrlp as an example,
```bash
~/dotfiles$ git submodule add https://github.com/kien/ctrlp.vim.git vim/bundle/ctrlp.vim
~/dotfiles$ git commit -m "added ctrlp vim plugin"
~/dotfiles$ git push
```
