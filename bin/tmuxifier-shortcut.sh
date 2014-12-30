# Credit to /u/nath_schwarz for this awesome script
# tmux new-session || attach-session
# usage (when aliased to 't') $ t <session-name>
# Checks if the given name is a tmuxifier layout, if so it attaches to it or creates it.
#   If not a tmuxifier layout it creates a new session with the given name.
#   Creates a nested session if no name specified and currently in an existing session.
#   Creates a normal session if no name specified with tmux numbering.
tmux-attach-or-new() {
    if [[ -n "$1" ]]; then
        if [[ -n "$(tmuxifier list-sessions | grep $1)" ]]; then
            tmuxifier load-session "$1"
        else
            tmux -2 new-session -s "$1" || tmux -2 attach-session -t "$1" || tmux -2 switch-client -t "$1"
        fi
    elif [[ -n "$TMUX" ]]; then
        TMUX=""
        tmux -2 new-session -s n"$RANDOM"
    elif [[ ! $(tmux list-sessions) =~ main ]]; then
        i3-msg 'rename workspace to "1: main"'
        tmux -2 new-session -s main
    else
        tmux -2 new-session
    fi
}
