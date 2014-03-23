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
$ git submodule init
$ git submodule update 
```
This will clone vim/bundle submodules
