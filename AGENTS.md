# AGENTS.md

## Purpose

This repository is a personal cross-platform dotfiles, shell configuration, and automation toolkit.

It is intended to bootstrap and maintain Linux and macOS machines used for development, homelab administration, infrastructure automation, AI/model workflows, storage management, Docker, Proxmox, and general system administration.

The repository is the **source of truth for portable, non-secret personal tooling and configuration**.

Agents working in this repository should preserve the separation between:

1. Repository source files
2. Installed user commands
3. XDG configuration/data/state
4. Machine-specific configuration
5. Secrets

Do not collapse these concerns into a single directory.

---

## Repository Layout

The expected repository structure is:

```text
~/src/dotfiles/
│
├── AGENTS.md
├── README.md
├── install.sh
├── bootstrap.sh
│
├── bin/
│   ├── model-archive
│   ├── model-restore
│   └── ...
│
├── scripts/
│   ├── ai/
│   ├── docker/
│   ├── homelab/
│   ├── storage/
│   └── system/
│
├── shell/
│   ├── env.sh
│   ├── aliases.sh
│   ├── functions.sh
│   └── hosts/
│       ├── macos.sh
│       └── linux.sh
│
├── config/
│   ├── git/
│   ├── zsh/
│   └── ...
│
└── ...
```

### `AGENTS.md`

Instructions and architectural context for AI coding/automation agents.

Agents should read this file before making changes to the repository.

### `README.md`

Human-facing documentation.

Keep it concise and focused on:

* What the repository is
* Supported operating systems
* Initial setup
* Common commands
* How to add a new script
* How machine-specific configuration works

Detailed agent behavior belongs in `AGENTS.md`, not `README.md`.

### `install.sh`

Installs or links repository components into the user's home directory.

It should be:

* Idempotent
* Safe to run repeatedly
* Non-destructive by default
* Explicit when replacing existing files
* Suitable for both fresh machines and existing machines

Do not overwrite existing user configuration without an explicit mechanism for doing so.

### `bootstrap.sh`

Performs higher-level machine setup.

Bootstrap may:

* Detect operating system
* Detect architecture
* Detect host role
* Install prerequisite packages
* Configure XDG directories
* Install/link repository commands
* Configure shell integration
* Enable optional components

Bootstrap should call smaller, reusable scripts rather than becoming one enormous shell script.

---

# Command Layout

## `bin/`

`bin/` contains commands intended to be directly available in the user's shell.

Anything in this directory should be executable and have a stable command-line interface.

Examples:

```text
bin/model-archive
bin/model-restore
bin/disk-health
bin/docker-backup
```

These commands should generally be symlinked into:

```text
$HOME/.local/bin/
```

The repository itself should **not** normally be added directly to `$PATH`.

Expected PATH configuration:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

---

## `scripts/`

`scripts/` contains the implementation of automation that is organized by purpose.

Recommended categories:

```text
scripts/
├── ai/
├── docker/
├── homelab/
├── storage/
└── system/
```

Use `scripts/` when a script needs organizational grouping or is not necessarily intended to be directly exposed as a command.

When a script becomes a commonly used user command, expose it through `bin/`.

For example:

```text
scripts/ai/archive-hf-model
        ↓
bin/model-archive
        ↓
~/.local/bin/model-archive
```

Prefer a symlink or thin wrapper rather than maintaining two independent copies.

---

# XDG Directory Policy

Follow the XDG Base Directory Specification wherever practical.

Preferred locations:

```text
$XDG_CONFIG_HOME
    default: ~/.config

$XDG_DATA_HOME
    default: ~/.local/share

$XDG_STATE_HOME
    default: ~/.local/state

$XDG_CACHE_HOME
    default: ~/.cache

$HOME/.local/bin
    user-installed executables
```

If an environment variable is not already defined, shell configuration may establish the standard defaults:

```bash
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
```

Do not create unnecessary hidden directories directly under `$HOME`.

Prefer:

```text
~/.config/my-tool/
~/.local/share/my-tool/
~/.local/state/my-tool/
~/.cache/my-tool/
```

over:

```text
~/.my-tool/
```

unless the application itself requires the latter.

---

# Repository Location

The preferred checkout location is:

```text
$HOME/src/dotfiles
```

Do not assume the username or absolute home directory.

Use:

```bash
$HOME/src/dotfiles
```

rather than:

```text
/home/bill/src/dotfiles
```

This is important because the repository is intended to work across multiple machines and users.

---

# Multi-Host Design

This repository must support multiple machines without requiring separate repositories.

Examples of supported environments include:

* macOS workstation
* macOS Mac mini
* Ubuntu workstation
* Ubuntu server
* Proxmox VM
* Homelab server
* Other Linux systems

Do not create separate copies of the repository for each host unless there is a compelling reason.

Prefer:

```text
common configuration
        +
OS-specific configuration
        +
host-role configuration
        +
optional machine-local configuration
```

---

# Host Detection

Scripts should be able to determine at least:

```bash
uname -s
uname -m
```

Use those values for OS and architecture detection.

Examples:

```text
Darwin / arm64
Darwin / x86_64
Linux / x86_64
Linux / aarch64
```

Do not assume:

* Intel CPU
* AMD CPU
* ARM CPU
* `/bin/bash` exists
* `/bin/zsh` exists
* Homebrew exists
* `apt` exists
* `systemd` exists

Check for capabilities before using them.

---

# Host-Specific Configuration

Host-specific behavior should be isolated rather than scattered throughout every script.

Recommended structure:

```text
shell/
└── hosts/
    ├── macos.sh
    └── linux.sh
```

If host roles become sufficiently complex, additional structure may be introduced:

```text
hosts/
├── common/
├── macos/
├── linux/
├── workstation/
├── server/
└── homelab/
```

Do not introduce this additional complexity until it is actually needed.

Prefer capability detection over hostname detection.

For example, prefer:

```bash
if command -v docker >/dev/null 2>&1; then
    ...
fi
```

over:

```bash
if [[ "$HOSTNAME" == "my-epyc-server" ]]; then
    ...
fi
```

When behavior truly must be host-specific, use an explicit host/role configuration mechanism.

---

# Machine-Local Configuration

Machine-specific configuration should not normally be committed to Git.

Use XDG configuration for local overrides.

For example:

```text
~/.config/dotfiles/
└── local.sh
```

or:

```text
~/.config/shell/
└── env.local.sh
```

Common configuration can source the local configuration if it exists:

```bash
if [[ -f "$XDG_CONFIG_HOME/shell/env.local.sh" ]]; then
    source "$XDG_CONFIG_HOME/shell/env.local.sh"
fi
```

Local configuration may contain:

* Host-specific paths
* Local usernames
* Local network addresses
* Device identifiers
* Optional feature flags
* Non-secret machine-specific settings

It must not be committed unless explicitly intended to be public and portable.

---

# Secrets

Never commit secrets to this repository.

This includes:

* API tokens
* Passwords
* SSH private keys
* Cloud credentials
* Tailscale authentication keys
* Cloudflare tokens
* AWS credentials
* GitHub tokens
* Private certificates
* Provisioning profiles
* Signing credentials
* Database passwords

Do not create a fake secret and commit it merely as an example.

Use one of:

* Environment variables
* Local XDG configuration
* SOPS
* A password manager
* The operating system's credential/keychain facility

If secrets are required for a workflow, document the expected variable name or secret path without committing the secret itself.

Example:

```bash
export CLOUDFLARE_API_TOKEN="..."
```

may be documented as an example, but the real value must never appear in Git.

---

# SOPS

SOPS may be used for encrypted configuration when configuration needs to be version controlled.

Encrypted files are acceptable in Git.

Plaintext decrypted secrets are not.

Agents must not:

* Commit decrypted SOPS files
* Print secret values to logs
* Include secrets in command output unnecessarily
* Store temporary decrypted secrets in the repository

Prefer short-lived temporary files or process/environment mechanisms where appropriate.

---

# Shell Script Standards

Shell scripts should generally use:

```bash
#!/usr/bin/env bash
set -euo pipefail
```

when Bash is required.

Do not assume Bash when POSIX shell is sufficient.

Use:

```bash
#!/bin/sh
```

for scripts that genuinely require only POSIX shell behavior.

Prefer:

```bash
command -v docker >/dev/null 2>&1
```

for command detection.

Avoid:

```bash
which docker
```

Prefer clear error messages:

```bash
echo "ERROR: docker is required but was not found" >&2
exit 1
```

Scripts should fail safely.

Never silently delete, overwrite, format, or destroy data.

---

# Idempotency

Bootstrap and installation operations should be idempotent.

Running:

```bash
./bootstrap.sh
```

twice should not corrupt the machine or create duplicate configuration.

Scripts should safely handle:

* Existing directories
* Existing symlinks
* Existing configuration
* Already-installed packages
* Existing PATH entries
* Already-created users or groups
* Already-running services

Use explicit checks before modifying existing resources.

---

# Symlink Policy

Prefer symlinks for files that should remain under Git control.

For example:

```text
~/.local/bin/model-archive
    -> ~/src/dotfiles/bin/model-archive
```

Before replacing an existing file:

1. Determine whether it is a symlink.
2. Determine where it points.
3. Do not destroy user data automatically.
4. Back up or require explicit confirmation when necessary.

Never blindly run:

```bash
rm -rf "$HOME/.config"
```

or similarly destructive operations.

---

# Package Managers

Use the native package manager for the detected operating system.

Examples:

```text
macOS
    Homebrew

Debian/Ubuntu
    apt

Arch
    pacman

Fedora/RHEL
    dnf
```

Do not assume a package manager exists.

Check first and provide a useful error when a prerequisite cannot be installed automatically.

For development tools that have multiple installation mechanisms, prefer the mechanism already used by the host.

---

# Python

Python automation should avoid modifying the system Python installation.

Prefer:

* `pyenv`
* virtual environments
* `uv`
* Poetry

depending on the project requirements.

Do not use:

```bash
sudo pip install ...
```

Do not install Python packages globally unless there is a deliberate system-level requirement.

Scripts that are intended to be standalone CLI tools should clearly document their Python requirements.

---

# Docker

Docker workflows should prefer Docker Compose when practical.

Do not silently replace Docker Compose with Podman or Kubernetes.

The repository may support alternative container runtimes in the future, but existing Docker/Compose workflows should remain functional unless explicitly being migrated.

---

# AI / Model Tooling

AI-related scripts may manage:

* Hugging Face models
* Ollama
* LM Studio
* Model archives
* Model metadata
* Local inference infrastructure

Large model files must **not** be committed to this repository.

The repository should contain:

* Scripts
* Configuration
* Metadata
* Documentation
* Checksums/manifests where useful

Large model artifacts should live in appropriate storage such as:

* NAS
* Object storage
* Dedicated model storage
* Local model cache

For example:

```text
Repository:
    scripts/ai/model-archive

Working storage:
    ~/models/

Long-term archive:
    NAS/model-archive/
```

Scripts should not assume that model storage is local to the machine.

---

# Homelab Safety

Homelab automation may interact with:

* Proxmox
* Unraid
* Docker
* NAS storage
* SSH
* Network services
* Tailscale
* Backup systems

Treat destructive storage operations as high risk.

Commands involving:

```text
rm
mkfs
fdisk
parted
zpool
zfs destroy
lvremove
wipefs
dd
docker system prune
```

or equivalent destructive operations require extra care.

Never infer a disk device from assumptions such as:

```text
/dev/sda is always the data disk
```

Prefer explicit device identification using:

```bash
lsblk
blkid
udevadm
smartctl
```

and require confirmation for destructive operations.

---

# Backup Safety

A script named `backup` should never assume that copying data somewhere means the backup is valid.

Where practical:

1. Verify source paths.
2. Verify destination paths.
3. Preserve file metadata when appropriate.
4. Check exit codes.
5. Report failures.
6. Provide a summary.
7. Avoid deleting the source unless explicitly requested.
8. Consider checksums or verification for important archives.

For NAS and Proxmox workflows, document whether the operation is:

* Copy
* Snapshot
* Backup
* Replication
* Archive

These are not interchangeable.

---

# Git Practices

Keep commits focused.

Examples:

```text
feat: add Hugging Face model archiver
fix: handle missing smartctl
feat: add macOS host configuration
docs: document model archive workflow
refactor: consolidate XDG environment setup
```

Do not commit:

* Secrets
* Temporary files
* Logs
* Model files
* Build artifacts
* Virtual environments
* OS-specific junk files

Before committing changes, inspect:

```bash
git status
git diff
git diff --cached
```

Do not automatically commit changes unless explicitly instructed.

---

# Adding a New Script

When adding a new automation script:

1. Determine whether it belongs in `scripts/<category>/`.
2. Use `bin/` only if it should become a user-facing command.
3. Make the script executable.
4. Add usage/help information.
5. Validate arguments.
6. Fail with useful error messages.
7. Avoid hard-coded home directories.
8. Avoid hard-coded hostnames.
9. Avoid hard-coded network addresses when practical.
10. Consider macOS/Linux compatibility.
11. Document external dependencies.
12. Update `README.md` when the new command is generally useful.

Example:

```text
scripts/storage/disk-health
bin/disk-health
```

The implementation should live in one place.

---

# Adding Configuration

Before adding configuration, determine whether it is:

### Global

Applies to all supported machines.

Place it in the common configuration.

### OS-specific

Applies to macOS or Linux.

Place it in the appropriate OS-specific configuration.

### Role-specific

Applies to a class of machines such as workstation/server/homelab.

Place it in a role-specific configuration.

### Machine-specific

Applies to only one machine.

Keep it outside Git under XDG local configuration.

### Secret

Never store plaintext in Git.

Use SOPS, environment variables, or a credential store.

---

# Portability

Do not assume that the repository will always run on the current machine.

When writing automation, consider:

```text
OS
CPU architecture
shell
package manager
filesystem
available commands
user permissions
systemd/launchd
Docker availability
network availability
```

Prefer feature detection to assumptions.

Avoid hard-coded:

```text
/home/<username>
/Users/<username>
/dev/sdX
hostname
IP addresses
interface names
```

Use:

```bash
$HOME
uname
command -v
id
getent
sysctl
```

or platform-appropriate equivalents.

---

# Agent Workflow

Before modifying the repository:

1. Read `AGENTS.md`.
2. Inspect the repository structure.
3. Inspect relevant existing scripts.
4. Determine the target OS and architecture.
5. Check whether the requested functionality already exists.
6. Reuse existing functions and conventions where possible.
7. Avoid introducing a new dependency when an existing tool solves the problem.
8. Make the smallest coherent change.
9. Test the change.
10. Show what files changed and how the change was validated.

Do not rewrite unrelated files.

Do not reorganize the repository merely for aesthetic reasons.

Do not introduce a framework when a small shell or Python script is sufficient.

---

# Bootstrap Workflow

When an agent is asked to bootstrap a new machine:

## Phase 1: Discovery

Determine:

```bash
uname -s
uname -m
echo "$SHELL"
echo "$HOME"
```

Check for important tools:

```bash
git
curl
wget
zsh
bash
python3
ssh
docker
```

Determine the package manager and available privileges.

Do not make changes yet if the machine's identity or target role is unclear.

## Phase 2: Repository

Clone or locate:

```text
$HOME/src/dotfiles
```

Read:

```text
AGENTS.md
README.md
```

before executing repository-provided automation.

## Phase 3: Base Environment

Establish:

```text
~/.local/bin
~/.config
~/.local/share
~/.local/state
~/.cache
```

without deleting existing content.

Ensure:

```bash
$HOME/.local/bin
```

is available in the user's PATH.

## Phase 4: Configuration

Install common shell configuration.

Then apply:

```text
OS-specific configuration
        ↓
role-specific configuration
        ↓
machine-local configuration
```

Do not overwrite existing user configuration without a safe migration/backup strategy.

## Phase 5: Tools

Install only the tools required for the requested machine role.

Do not install the entire contents of the repository on every machine.

For example, a minimal server does not necessarily need:

* GUI tools
* macOS tools
* iOS development tools
* desktop utilities
* AI model tooling

## Phase 6: Verification

Verify:

```bash
command -v <important-command>
```

Check shell configuration.

Check symlinks.

Check Git status.

Confirm that no unexpected files were modified.

Report any steps that require manual intervention.

---

# Agent Decision Rules

When uncertain, follow these priorities:

1. Preserve user data.
2. Preserve existing configuration.
3. Preserve portability.
4. Preserve idempotency.
5. Prefer existing repository conventions.
6. Prefer simple solutions.
7. Avoid unnecessary dependencies.
8. Never expose or commit secrets.
9. Never perform destructive operations without explicit intent.
10. Ask for clarification when an ambiguous operation could affect data or infrastructure.

---

# Documentation Expectations

Scripts that are likely to be used interactively should support:

```bash
command --help
```

or:

```bash
command -h
```

Document:

* Purpose
* Requirements
* Usage
* Important options
* Examples
* Side effects
* Files/directories affected

Documentation should describe behavior rather than merely restating implementation.

---

# Future Extensions

The repository may eventually add:

```text
ansible/
    playbooks/
    roles/

hosts/
    macos/
    linux/
    server/
    workstation/

sops/
    common/
    hosts/

tests/
```

Do not introduce these directories until there is a concrete need.

The repository should remain useful as a lightweight personal automation repository before growing into a complete configuration-management system.

---

# Guiding Principle

This repository should behave like a **portable personal operating environment** rather than a collection of random scripts.

Keep:

```text
source
configuration
commands
machine-specific state
secrets
large data
```

separate.

Prefer small, composable, idempotent automation that can safely be reused across multiple machines.
