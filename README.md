# CTK - Claude Token Killer

**Token-optimized CLI proxy for Claude Code** - Save 60-90% on dev operations by automatically filtering and compacting command output.

## Features

- **Automatic command rewriting** via Claude Code hooks
- **Docker Compose support** (160+ uses identified as critical)
- **System commands**: `ps aux`, `free`, `date`, `whoami`
- **Git commands**: `status`, `diff`, `log`, etc.
- **File operations**: `ls`, `tree`, `grep`, `find`, `du`
- **All major tooling**: npm, pnpm, pytest, cargo, go, kubectl, gh CLI
- **Metrics tracking**: Token savings analytics with export

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/ctk.git
cd ctk

# Run the installer
./bin/install-ctk.sh
```

The installer will:
1. Install Python dependencies (click, rich, pyyaml)
2. Create the CTK binary at `~/.local/bin/ctk`
3. Install the Claude Code hook at `~/.claude/hooks/ctk-rewrite.sh`
4. Update Claude Code settings to use the hook

## Usage

### Meta Commands (always use ctk directly)

```bash
ctk gain              # Show token savings analytics
ctk gain --history    # Show command usage history with savings
ctk gain --weekly     # Weekly statistics
ctk gain --export json # Export data to JSON
ctk discover          # Analyze Claude Code history for missed opportunities
ctk proxy <cmd>       # Execute raw command without filtering (for debugging)
```

### Hook-Based Usage

All other commands are automatically rewritten by the Claude Code hook.

Example: `git status` -> `ctk git status` (transparent, 0 tokens overhead)

The hook automatically rewrites these commands:

| Category | Commands |
|----------|----------|
| **Docker** | `docker compose ps/logs/up/down/exec`, `docker ps/images/logs` |
| **Git** | `status`, `diff`, `log`, `add`, `commit`, `push`, `pull` |
| **System** | `ps aux`, `free`, `date`, `whoami` |
| **Files** | `ls`, `tree`, `cat`->`read`, `grep`, `find`, `du` |
| **Python** | `pytest`, `ruff`, `pip` |
| **Node.js** | `npm`, `pnpm`, `vitest`, `tsc`, `eslint`->`lint`, `prettier` |
| **Rust** | `cargo test/build/clippy/check` |
| **Go** | `go test/build/vet`, `golangci-lint` |
| **Kubernetes** | `kubectl get/logs/describe` |
| **GitHub** | `gh pr/issue/run/api/release` |
| **Network** | `curl`, `wget` |

## How It Works

1. **Hook intercepts Bash commands** before execution
2. **Rewrites commands** to use CTK (e.g., `docker compose ps` -> `ctk docker compose ps`)
3. **CTK runs the command** and filters the output
4. **Token savings are tracked** in SQLite database

## Token Savings

CTK saves tokens by:

1. **Pre-truncation**: Commands like `ps aux` are limited to top 20 processes
2. **Filtering**: Removes empty lines, progress bars, boilerplate
3. **Compact formats**: Git uses `--oneline`, docker uses table format
4. **Smart defaults**: All commands optimized for minimal output

## Configuration

Configuration file: `~/.config/ctk/config.yaml`

```yaml
version: 1
enabled: true
commands:
  docker:
    enabled: true
    compose: true
  git:
    enabled: true
  # ... etc
display:
  color: true
  compact: true
  max_lines: 100
metrics:
  enabled: true
```

## Data Storage

- **Metrics database**: `~/.local/share/ctk/metrics.db` (SQLite)
- **Configuration**: `~/.config/ctk/config.yaml`
- **Binary**: `~/.local/bin/ctk`
- **Hook**: `~/.claude/hooks/ctk-rewrite.sh`

## Migrating from RTK

The installer automatically:
1. Removes the old RTK hook from Claude Code settings
2. Optionally migrates RTK history to CTK metrics database

## Requirements

- Python 3.8+
- click
- rich
- pyyaml
- jq (for the hook script)

## License

MIT
