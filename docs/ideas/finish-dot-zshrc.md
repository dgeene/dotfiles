# Finish dot-zshrc and dot-zprofile

Status: proposed
Last reviewed: 2026-11-23

## Goal

Make the repository's zsh configuration complete enough to replace a machine's
existing `~/.zshrc` (and optionally `~/.zprofile`), so the append-only stop-gap
can be retired machine by machine. Machines range over macOS, Ubuntu, and Arch
Linux (Windows later).

## Current behavior

* `install.sh --with-shell` does not replace anything. It appends one managed
  block (between `# >>> dotfiles ... >>>` and `# <<< dotfiles <<<`) to
  `~/.zshenv` and `~/.zshrc`. The blocks source `shell/zshenv.sh` and
  `shell/init.zsh`. It also creates `$XDG_CONFIG_HOME/dotfiles/local.zshenv` and
  `local.zsh` templates. See [install.sh](../../install.sh).
* Layered loading today: `shell/env.sh` (XDG defaults, `path_prepend`/`path_append`,
  `~/.local/bin`) -> `shell/aliases.sh` -> `shell/hosts/{macos,linux}.sh` ->
  `shell/functions.sh` -> `local.zsh`.
* [shell/dot-zshrc](../../shell/dot-zshrc) and [shell/dot-zprofile](../../shell/dot-zprofile)
  are unfinished and unused by `install.sh`. They were written for one specific
  Linux machine. Known problems (recheck before relying on them):
  * `dot-zshrc` sources `$XDG_CONFIG_HOME/shell/alias`, which nothing creates.
  * `dot-zprofile` hard-codes `EDITOR=nvim`, sets `ZDOTDIR=$XDG_CONFIG_HOME/zsh`
    (so zsh would look for `~/.config/zsh/.zshrc`, which nothing links), and
    exports XDG variables without the `:-` defaults, and omits `XDG_STATE_HOME`.
  * `HISTFILE` is placed under `$XDG_CACHE_HOME`; `XDG_STATE_HOME` is the
    conventional place, and cache may be cleared.
  * The fzf line is commented out; no completion (`compinit`) is enabled;
    the keybinding section is empty.
  * `HISTCONTROL` is a bash variable; zsh uses `setopt hist_ignore_dups` /
    `hist_ignore_space`.
* Real machines often already have tool initialization in their rc files
  (conda, pyenv, Homebrew, etc.) that must not be lost. Machine-specific
  toolchain paths belong in the local files, not the repo.
* Related: [shell/env.sh](../../shell/env.sh), [shell/init.zsh](../../shell/init.zsh),
  [shell/zshenv.sh](../../shell/zshenv.sh), [shell/hosts/](../../shell/hosts).

## Proposed changes

Agent recommendations (not yet agreed unless noted):

1. **Fold dot-zshrc into the layers rather than replacing them.** Move the
   portable options (setopt, history, prompt, colors) into a new
   `shell/zshrc.d/` or directly into `shell/init.zsh`, so one code path serves
   both the append stop-gap and a full replacement. Keep `dot-zshrc` only if a
   standalone file is still wanted; otherwise delete it once superseded.
2. **Fix history:** use `$XDG_STATE_HOME/zsh/history`, create the directory,
   and use zsh options in place of `HISTCONTROL`.
3. **Add completion** (`autoload -Uz compinit && compinit`, with a cache under
   `$XDG_CACHE_HOME/zsh`) guarded so it runs once and tolerates missing dirs.
4. **Make optional integrations capability-checked:** fzf (`command -v fzf`),
   zoxide/direnv if present, tmux helpers.
5. **Replacement mode for `install.sh`** (flag name not decided, for example
   `--replace-zshrc`): back up the existing file, show a diff of what would be
   lost (excluding value contents of environment exports), refuse unless the
   user confirms, and keep the managed-block mode as the default.
6. **Decide on ZDOTDIR.** Either drop it (keep `~/.zshrc` in `$HOME`, simplest
   and what the managed block assumes) or adopt `~/.config/zsh` consistently and
   have `install.sh` link it. `dot-zprofile` should then be reduced to what is
   truly login-only, or removed.
7. **Add a bash entry point** if any machine uses bash as its login shell
   (`shell/init.bash`), reusing the same layers.

## Scope

Included: zsh option, history, completion, prompt, and integration setup in the
shared layers; a safe replacement mode in `install.sh`; documentation in
`README.md` and the setup skill.

Deferred: Windows/PowerShell profile, a plugin manager, SOPS-managed shell
secrets, relocating credentials out of rc files (a separate task, see
[Move shell credentials into SOPS](sops-shell-secrets.md)).

## Constraints

* Never replace an existing rc file silently; preserve user data and idempotency
  ([AGENTS.md](../../AGENTS.md)).
* Must work on macOS (BSD userland, Apple zsh) and Linux (GNU userland); check
  capabilities with `command -v`, not hostnames.
* No secrets or machine-specific paths in the repo; no hard-coded home
  directories.
* `~/.zshenv` runs for every zsh (scripts, cron): keep it free of output and
  aliases.
* Existing machines' rc files may contain credentials; tooling must not print
  or copy their contents.

## Acceptance criteria

* On a clean macOS or Linux account, `./install.sh --with-shell` (or the chosen
  replacement mode) gives a working interactive zsh: completion, history under
  XDG state, portable and OS-specific aliases, and the repo functions.
* On an existing machine, nothing is lost: the original file is backed up and a
  diff is shown before any replacement.
* `zsh -ic exit` prints nothing and exits 0 on both OS families, with and
  without optional tools installed.
* Re-running the installer changes nothing.
* No `dot-*` file references a path that nothing creates.

## Validation

* Run `install.sh` against a throwaway `HOME`/`ZDOTDIR` (use `DOTFILES_ZSHRC` and
  `DOTFILES_ZSHENV` overrides because some sandboxes block files named `.zshrc`).
* `zsh -n` syntax check and `zsh -ic 'exit'` with stderr captured.
* Test: missing fzf, missing local files, existing populated rc file, stale
  managed block, second run.
* Verify on at least one macOS and one Linux machine (Ubuntu and Arch).

## Open questions

* Keep `dot-zshrc` as a standalone file, or fully fold it into `init.zsh`?
  (Recommended: fold in.)
* Use `ZDOTDIR` or keep rc files in `$HOME`? (Recommended: keep in `$HOME`.)
* Which prompt, if any, belongs in shared config versus local files?
* Do any machines use bash as their login shell?
* Does the replacement mode need to exist at all, or is the managed block good
  enough permanently? (User has said replacement is a goal "eventually", not yet.)

## Implementation outcome

Not implemented.
