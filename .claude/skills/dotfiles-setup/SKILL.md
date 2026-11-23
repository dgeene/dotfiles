---
name: dotfiles-setup
description: First-time or repeat setup of this dotfiles repo on the current machine. Symlinks bin/ commands into ~/.local/bin, links configs into ~/.config, creates the local override file, and checks dependencies. Use when the user asks to set up, install, bootstrap, or repair the dotfiles on this machine.
---

# Dotfiles setup

Follow `AGENTS.md` (symlink policy, idempotency, no destructive actions). The logic lives in `install.sh` at the repo root; do not reimplement it here.

## Steps

1. **Discover.** Run `uname -s`, `uname -m`, `echo "$HOME"`. If the OS is not Darwin or Linux, stop and tell the user Windows is not supported yet (no `install.ps1`).
2. **Dependencies.** Run `scripts/system/check-deps`. Report what is missing. Offer to install missing tools with the detected package manager, but only install after the user confirms.
3. **Dry run.** Run `./install.sh --dry-run` from the repo root and show the plan. Ask whether to include shell integration (`--with-shell`). It never replaces `~/.zshrc` or `~/.zshenv`: it appends one marked block to each (backup first) that loads `shell/zshenv.sh` and `shell/init.zsh`, and creates `local.zshenv`/`local.zsh` templates under `$XDG_CONFIG_HOME/dotfiles/`. Default to no. These rc files may hold plaintext credentials: never print or copy their contents; mask values if you must inspect them.
4. **Conflicts.** For every `CONFLICT` line, ask the user (one question per target) whether to skip or back up and replace. Show what exists there (`ls -l`). Never replace anything without an answer.
5. **Apply.** Run `./install.sh` with the same flags, adding `--backup <target>` for each target the user approved replacing and `--skip-conflicts`. Exit status 2 means some conflicts were skipped; that is fine if the user chose to skip them.
6. **Verify.** Check `command -v` for each command in `bin/`, check `~/.local/bin` is on PATH (tell the user how to add it to their shell config if not; do not edit their rc files without asking), run `git status` in the repo to confirm nothing changed, and list any manual steps remaining.

## Notes

- Re-running is safe: correct links are reported as `ok`.
- Machine-specific settings go in `$XDG_CONFIG_HOME/dotfiles/local.zshenv` (env/PATH, read by every zsh) or `local.zsh` (interactive), never in Git. Toolchain paths (Java, Android, pyenv, conda) belong there.
- `shell/dot-zshrc` and `shell/dot-zprofile` are an unfinished future full replacement; setup does not use them.
- Writes to `.zshrc`/`.zshenv` may be blocked by the sandbox; if so, tell the user and have them run `! ./install.sh --with-shell` themselves.
- Do not print or commit secrets.
