# A generic development environment
# Set window root path. Default is `$session_root`.
# Must be called before `new_window`.
#window_root "~/Projects/dev"

# Create new window. If no argument is given, window name will be based on
# layout file name.
new_window "dev1"

# Split window into panes.
split_v 20
split_h 50

# Set active pane.
select_pane 0
