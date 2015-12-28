"to disable a plugin, add its bundle name to the following list
"let g:pathogen_disabled = []
"load pathogen and bundles
execute pathogen#infect()


set nocompatible                             "no need to be compatible with old vim
map <C-n> :NERDTreeToggle<CR>
autocmd! bufwritepost .vimrc source %        "Automatic reload of .vimrc when saving
filetype plugin indent on
set ts=4                                     "set indent to 4 spaces
set shiftwidth=4                             "set number of space characters inserted for indentation
set expandtab                                "use spaces, not tab characters
let mapleader = ","                          "set leader key to comma instead of \
let g:NERDTreeDirArrows=0                    "this sisables nertree's use of unicode charaters for better compatability.
set cursorline                               "highlight the current line. Disable if scrolling becomes laggy
set ignorecase                               "searches are case insensitive
set smartcase                                " ... unless they have at lease one capital
set hlsearch                                 "highlight searches. Type :noh to disable
set showmatch                                "briefly jump cursor to matching }, ] etc
set history=300                              "remember more than 20 searches/commands

"treat cursorline as line 0, helpful for motions
"if exists('+relativenumber')
"    set relativenumber
"end
set number                                   "show line numbers and length

"prevent cursor from jumping when joining
nnoremap J mzJ`z

" open new splits to the right an bottom. feels better
set splitbelow
set splitright

"better copy and paste
set pastetoggle=<F2>
set clipboard=unnamed


" wildmenu
set wildmenu
set wildmode=longest:list,full
"set wildignore=*.o,*.obj,~,*.pyc            "stuff to ignore when autocompleting
"set wildignore+=*DS_Store*


"easier moving of code blocks for better indentation
vnoremap < <gv
vnoremap > >gv

"enable mouse and backspace
set mouse=a                                  "on OSX press ALT and Click
set bs=2                                     "make backspace behave normally

"quick pairs in insert mode
imap <leader>' ''<ESC>i
imap <leader>" ""<ESC>i
imap <leader>( ()<ESC>i
imap <leader>[ []<ESC>i

"easier split navigations ex. ctrl J
nnoremap <C-J> <C-W><C-J>
nnoremap <C-K> <C-W><C-K>
nnoremap <C-L> <C-W><C-L>
nnoremap <C-H> <C-W><C-H>

"autocenter things
nmap G Gzz
nmap n nzz
nmap N Nzz
nmap } }zz
nmap { {zz
"some crazy voodoo ex: 20j - move 20 'real' lines up when wrapped
"nnoremap <expr> k (v:count == 0 ? 'gk' : 'k')
"nnoremap <expr> j (v:count == 0 ? 'gj' : 'j')

"unmap bad habits (arrow keys).
no <down> <Nop>
no <left> <Nop>
no <right> <Nop>
no <up> <Nop>
ino <down> <Nop>
ino <left> <Nop>
ino <right> <Nop>
ino <up> <Nop>

" move current line up/down while fixing indent
"nnoremap <Down> :m+<CR>==
"nnoremap <Up> :m-2<CR>==

"insert ruby hash rocket, Ctrl-L
imap <c-l> <space>=><space>



""""""""""""""""""""""
"   Colors/Theme     "
""""""""""""""""""""""

"show trailing whitespace
"insert BEFORE colorscheme command
autocmd ColorScheme * highlight ExtraWhitespace ctermbg=red guibg=red
au InsertLeave * match ExtraWhitespace /\s\+$/

syntax enable "formerly syntax on
set t_Co=256
"set background=dark
colorscheme apprentice

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

"vim airline configs
set laststatus=2


"have vim insert the standard 4spaces for .py files
"autocmd Filetype python setlocal expandtab tabstop=4 shiftwidth=4

"delete trailing whitespace
"http://wim.wikia.com/wiki/Remove_unwanted_spaces
function! RD_RemoveTrailingSpaces()
    " set mark to return to later
    normal m`
    " save user's search register
    let _lastsearch=@/
    " find any space/tab at ends of lines and remove
    " the 'e' suppresses error if none found
    %s/\s\+$//e
    "restore search register
    let @/=_lastsearch
    " jump back to mark we set
    normal ``
    echo "removed trailing spaces (if any)"
endfunction
nmap <leader>tw :call RD_RemoveTrailingSpaces()<CR>

" Punish those who use bad habits ;)
function! Evil()
    highlight ColorColumn ctermbg=red ctermfg=blue
    exec 'set colorcolumn=' . join(range(2,80,3), ',')
endfunction
no <down> :call Evil()<CR>
no <up> :call Evil()<CR>

"TODO wishlist
" read and env variable to
" configure vim with the 'kitchen sink' on desktop systems
" or load a minimal set for low cpu systems
" example:
" let myvar=$MYVAR  "get an env var
" if myvar == '1'
" call doSomething
" endif
