
"load pathogen and bundles
execute pathogen#infect()


set nocompatible                             "no need to be compatible with old vim
map <C-n> :NERDTreeToggle<CR>
autocmd! bufwritepost .vimrc source %        "Automatic reload of .vimrc when saving
filetype plugin indent on
set ts=4                                     "set indent to 4 spaces
set shiftwidth=4                             "set number of space characters inserted for indentation
set expandtab                                "use spaces, not tab characters
set number                                   "show line numbers and length
let mapleader = ","                          "set leader key to comma instead of \
let g:NERDTreeDirArrows=0                    "this sisables nertree's use of unicode charaters. search cannot enter child dir's

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

"ctrlp config
let g:ctrlp_map = '<leader>f'
let g:ctrlp_max_height = 30

"have vim insert the standard 4spaces for .py files
"autocmd Filetype python setlocal expandtab tabstop=4 shiftwidth=4



