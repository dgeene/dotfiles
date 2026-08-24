# Dev2 development environment
session_root $PWD

if initialize_session "dev2"; then
    # load a defined window layout
    load_window "dev2"
fi

finalize_and_go_to_session
