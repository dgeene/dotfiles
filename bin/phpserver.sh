# start a PHP server from a directory, optionally specify a port
# Requires PHP 5.4.0+
# TODO improve the script to use fallbacks for aquiring ip address
#       make it compatable w/ more systems
# TODO what type of shell syntax is this? Looks like it was made for mac,
#       adapt it for other unixes
function phpserver() {
    local port="${1:-4000}";
    local ip=$(ipconfig getifaddr en1);
    sleep 1 && open "http://${ip}:${port}/" & #open wont work on headless
    php -S "${ip}:${port}";
}
