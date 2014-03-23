
"load pathogen and bundles
execute pathogen#infect()


set nocompatible                             "no need to be compatible with old vim
map <C-n> :NERDTreeToggle<CR>
autocmd! bufwritepost .vimrc source %        "Automatic reload of .vimrc when saving
filetype plugin indent on
set ts=2                                     "set indent to 2 spaces
set shiftwidth=2                             "set number of space characters inserted for indentation
set expandtab                                "use spaces, not tab characters
set number                                   "show line numbers and length
let mapleader = ","                          "set leader key to comma instead of \

"better copy and paste
set pastetoggle=<F2>
set clipboard=unnamed

"easier moving of code blocks for better indentation
vnoremap < <gv
vnoremap > >gv

"enable mouse and backspace
set mouse=a                                  "on OSX press ALT and Click
set bs=2                                     "make backspace behave normally



""""""""""""""""""""""
"   Colors/Theme     "
""""""""""""""""""""""

"show trailing whitespace
"insert BEFORE colorscheme command
autocmd ColorScheme * highlight ExtraWhitespace ctermbg=red guibg=red
au InsertLeave * match ExtraWhitespace /\s\+$/

syntax enable "formerly syntax on
set t_Co=256
colorscheme monokai

"highlight 80 char columns
"set colorcolumn=80 was ctermbg=233
highlight ColorColumn ctermbg=219
call matchadd('ColorColumn', '\%80v', 100)



""""""""""""""""""""""
"      Misc          "
""""""""""""""""""""""

"set tw=79 "width of document (used by gd)
"set nowrap "dont automatically wrap on load
"set fo-=t "dont automatically wrap text while typing







