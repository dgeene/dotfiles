# Move shell credentials into SOPS

Status: proposed
Last reviewed: 2026-11-23

## Goal

Stop keeping plaintext credentials in shell startup files. Store them encrypted
(SOPS) so they can be version controlled safely, and load them only where and
when needed, on macOS and Linux machines.

## Current behavior

* On at least one machine, `~/.zshenv` exports many credentials in plaintext:
  API tokens, webhook URLs, service account passwords, and CI/automation
  keys, mixed with non-secret values (usernames, URLs, node names).
  Because `~/.zshenv` is read by every zsh, these reach the environment of every
  zsh process, including scripts, cron jobs, and child processes, and anything
  that logs its environment.
* The repository does not manage secrets. `install.sh --with-shell` appends
  managed blocks and `local.zshenv`/`local.zsh` templates, but nothing here
  handles secrets ([install.sh](../../install.sh), [shell/](../../shell)).
* [AGENTS.md](../../AGENTS.md) already permits SOPS-encrypted files in Git and
  forbids committing decrypted files or printing secret values.
* Recheck before implementing: which tools are installed (`sops`, `age`), and
  whether other rc files (`~/.zshrc`, `~/.zprofile`, sourced env files) also
  contain secrets.

## Proposed changes

Agent recommendations; none are agreed unless stated:

1. **Inventory by name only.** Record variable names (never values) in a local,
   uncommitted worksheet, classified as secret / non-secret / unknown. Non-secret
   items (usernames, hostnames, IDs) may stay in `local.zshenv`.
2. **Use SOPS with `age` keys.** Keep an encrypted dotenv file in the repo
   (for example `secrets/<scope>.env.sops`, with a `.sops.yaml` creation rule).
   The private `age` key lives outside the repo
   (`$XDG_CONFIG_HOME/sops/age/keys.txt`, mode 600) or in the OS keychain.
3. **Load lazily rather than globally (recommended).** Provide a command, for
   example `with-secrets <command>` or `secrets-shell`, that decrypts to the
   environment of one process (no file on disk) and runs the command. Avoid
   exporting secrets from `~/.zshenv`. Name and location not decided;
   likely `scripts/system/` exposed through `bin/`.
4. **Optional eager loading** for variables a workflow truly needs in every shell:
   a function the user calls (`load-secrets`) that exports for the current
   session only. Not run automatically.
5. **Per-machine subsets.** Separate encrypted files per scope (for example
   shared, work, home) so each machine decrypts only what it needs; a machine's
   `age` key is a recipient only of the scopes it should read.
6. **Guardrails:** `.gitignore` entries for decrypted output, and a pre-commit
   check that rejects files containing plaintext secret-looking assignments or
   unencrypted files under `secrets/`.
7. **Migration steps for each machine:** encrypt, verify the loader reproduces the
   needed variables, then remove the plaintext lines from the rc file (with a
   backup stored outside the repo), then open a new shell and re-verify.
8. **Rotation:** treat values that lived in plaintext on disk as exposed; list
   which to rotate and in which order (user decision per credential).

## Scope

Included: a SOPS/age workflow, loader command, per-scope files, guardrails,
migration procedure, documentation, and updates to the setup skill to
include a secrets step.

Deferred: Windows support, keychain-only alternatives (1Password, macOS
keychain) as an optional backend, secret rotation automation, CI usage.

## Constraints

* Never commit plaintext or decrypted secrets, never write them to the repo,
  never print values in logs or command output ([AGENTS.md](../../AGENTS.md)).
* Prefer environment/pipe-based decryption over temporary files; if a temp file is
  unavoidable, use mode 600 in a private directory and delete it.
* Work on macOS and Linux (`sops` and `age` are available through Homebrew, apt,
  and pacman, but check with `command -v` and give a clear error).
* Idempotent, non-destructive setup; do not modify rc files without a backup.
* The tooling must not read, echo, or copy values from existing rc files; use
  name-only inspection (for example mask everything after `=`).
* The encrypted file in a public repo still reveals variable names; decide whether
  names themselves are sensitive.

## Acceptance criteria

* No credential values remain in `~/.zshenv`, `~/.zshrc`, or other startup files
  on a migrated machine; non-secret values still load.
* A command that needs a credential works through the loader on a migrated
  machine, and the credential is absent from a fresh shell's environment
  unless the user explicitly loaded it.
* A machine without the right `age` key cannot decrypt a scope it is not a
  recipient of, and the loader says so clearly.
* The repository contains only encrypted secret files; the pre-commit check fails
  on a plaintext test fixture.
* Re-running setup changes nothing.

## Validation

* Use synthetic fake secrets and a throwaway `age` key in a temporary `HOME`;
  never real values.
* Test: round trip encrypt, decrypt, loader exec, missing key, wrong key, missing
  `sops`, an edited encrypted file, and the pre-commit rejection path.
* Confirm with `env`-style checks (names only) that nothing leaks into the
  parent shell after `with-secrets` exits.
* Verify on one macOS and one Linux machine.

## Open questions

* Lazy per-command loading (recommended, safer) or eager session loading
  (closest to today's behavior)? Or both?
* `age` key storage: file under `$XDG_CONFIG_HOME` or OS keychain?
* Which credentials need to be present in every interactive shell, if any?
* Which credentials should be rotated, and when?
* How are `age` keys distributed to a new Ubuntu or Arch machine
  (copy over SSH, password manager)?
* Are variable names sensitive enough to avoid committing them?

## Implementation outcome

Not implemented. Related: [Finish dot-zshrc and dot-zprofile](finish-dot-zshrc.md).
