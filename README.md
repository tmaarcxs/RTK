# CTK - Claude Token Killer

**Token-optimized CLI proxy for Claude Code** - Save 60-90% on dev operations by automatically filtering and compacting command output.

## Installation

### As a Claude Code Plugin (Recommended)

```bash
# Install directly from GitHub
claude plugin install https://github.com/tmaarcxs/CTK.git
```

That's it! The plugin will:
- Auto-install on first session start
- Register the command rewriting hook
- Work transparently for all supported commands

### Manual Installation

```bash
# Clone and run installer
git clone https://github.com/tmaarcxs/CTK.git
cd CTK
./bin/install-ctk.sh
```

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

### Automatic Command Rewriting

All supported commands are automatically rewritten by the hook:

| Raw Command | Rewritten To |
|-------------|--------------|
| `git status` | `ctk git status` |
| `docker compose ps` | `ctk docker compose ps` |
| `ps aux` | `ctk ps` |
| `npm test` | `ctk npm test` |

## Supported Commands

| Category | Commands |
|----------|----------|
| **Docker** | `compose ps/logs/up/down/exec`, `ps`, `images`, `logs`, `network`, `volume`, `system` |
| **Git** | `status`, `diff`, `log`, `add`, `commit`, `push`, `pull`, `branch`, `remote`, `stash`, `tag` |
| **System** | `ps aux`, `free`, `df`, `date`, `whoami`, `uname`, `hostname`, `uptime`, `env`, `which`, `history`, `id` |
| **Files** | `ls`, `tree`, `cat`→`read`, `grep`, `find`, `du`, `tail`, `wc`, `stat`, `file` |
| **Python** | `pytest`, `ruff`, `pip` |
| **Node.js** | `npm`, `pnpm`, `vitest`, `tsc`, `eslint`→`lint`, `prettier` |
| **Network** | `curl`, `wget`, `ip`, `ss`, `ping` |

## How It Works

1. **Hook intercepts Bash commands** before execution
2. **Rewrites commands** to use CTK (e.g., `docker compose ps` -> `ctk docker compose ps`)
3. **CTK runs the command** and filters output (removes boilerplate, progress bars, noise)
4. **Token savings are tracked** in SQLite database

## Token Savings

CTK saves tokens by:

1. **Filtering boilerplate**: Removes progress bars, timing info, warnings, deprecation notices
2. **Category-specific patterns**: Docker headers, npm noise, pytest separators
3. **No truncation of useful data**: Savings come from removing noise, not cutting results

Example savings:
- `docker logs`: ~2,440 tokens (39%)
- `ps aux`: ~4,531 tokens (10%)

## Configuration

Config file: `~/.config/ctk/config.yaml`

```yaml
version: 1
enabled: true
commands:
  docker:
    enabled: true
    compose: true
  git:
    enabled: true
```

## Data Storage

- **Metrics database**: `~/.local/share/ctk/metrics.db` (SQLite)
- **Configuration**: `~/.config/ctk/config.yaml`
- **Binary**: `~/.local/bin/ctk`

## Requirements

- Python 3.8+
- click, rich, pyyaml (auto-installed)
- jq (for the hook script)

## License

MIT
