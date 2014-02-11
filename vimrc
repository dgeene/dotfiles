

execute pathogen#infect()

""""""""""""""""""""""
"     General        "
""""""""""""""""""""""
set nocompatible

map <C-n> :NERDTreeToggle<CR>

"Automatic reload of .vimrc
autocmd! bufwritepost .vimrc source %

"better copy and paste
set pastetoggle=<F2>
set clipboard=unnamed

""""""""""""""""""""""
"     Events         "
""""""""""""""""""""""
filetype plugin indent on


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

""""""""""""""""""""""
"      Vim UI        "
""""""""""""""""""""""

"show line numbers and length
set number
"set tw=79 "width of document (used by gd)
"set nowrap "dont automatically wrap on load
"set fo-=t "dont automatically wrap text while typing

"highlight 80 char columns
"set colorcolumn=80 was ctermbg=233
highlight ColorColumn ctermbg=219
call matchadd('ColorColumn', '\%80v', 100)

"enable mouse and backspace
set mouse=a     "on OSX press ALT and Click
set bs=2 "make backspace behave normally

"easier moving of code blocks for better indentation
vnoremap < <gv 
vnoremap > >gv 

