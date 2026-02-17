#!/bin/bash
# CTK Installation Script
# Uninstalls RTK and installs CTK

set -e

CTK_DIR="$HOME/.local/lib/ctk"
CTK_BIN="$HOME/.local/bin/ctk"
CTK_HOOK="$HOME/.claude/hooks/ctk-rewrite.sh"
RTK_HOOK="$HOME/.claude/hooks/rtk-rewrite.sh"
SETTINGS_FILE="$HOME/.claude/settings.json"
RTK_DATA="$HOME/.local/share/rtk/history.db"
CTK_DATA="$HOME/.local/share/ctk"

echo "🚀 CTK (Claude Token Killer) Installer"
echo "======================================"
echo

# Check dependencies
echo "Checking dependencies..."
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 is required but not found"
    exit 1
fi

if ! python3 -c "import click" 2>/dev/null; then
    echo "📦 Installing click, rich, pyyaml..."
    pip3 install click rich pyyaml --quiet
fi

if ! command -v jq &>/dev/null; then
    echo "❌ jq is required but not found. Please install jq first."
    exit 1
fi

echo "✅ Dependencies satisfied"
echo

# Step 1: Uninstall RTK hook
echo "Step 1: Removing RTK hook..."
if [ -f "$RTK_HOOK" ]; then
    rm -f "$RTK_HOOK"
    echo "  Removed $RTK_HOOK"
else
    echo "  RTK hook not found (already removed or never installed)"
fi

# Step 2: Update settings.json to remove RTK hook and add CTK hook
echo "Step 2: Updating Claude Code settings..."
if [ -f "$SETTINGS_FILE" ]; then
    # Create backup
    cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak.ctk"
    echo "  Backup created at $SETTINGS_FILE.bak.ctk"

    # Remove rtk-rewrite.sh from hooks
    jq 'del(.hooks.PreToolUse[].hooks[] | select(.command | endswith("rtk-rewrite.sh")))' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
    echo "  Removed RTK hook from settings"

    # Add CTK hook using Python (more reliable for nested arrays)
    python3 - "$SETTINGS_FILE" << 'PYEOF'
import json
import sys

settings_file = sys.argv[1]

with open(settings_file) as f:
    settings = json.load(f)

# Ensure hooks structure exists
if "hooks" not in settings:
    settings["hooks"] = {}
if "PreToolUse" not in settings["hooks"]:
    settings["hooks"]["PreToolUse"] = []

# Find Bash matcher or create it
bash_matcher = None
for matcher in settings["hooks"]["PreToolUse"]:
    if matcher.get("matcher") == "Bash":
        bash_matcher = matcher
        break

if not bash_matcher:
    bash_matcher = {"matcher": "Bash", "hooks": []}
    settings["hooks"]["PreToolUse"].append(bash_matcher)

if "hooks" not in bash_matcher:
    bash_matcher["hooks"] = []

# Add CTK hook at the beginning if not present
ctk_hook = {"type": "command", "command": "/root/.claude/hooks/ctk-rewrite.sh"}
ctk_hook_exists = any(
    h.get("command", "").endswith("ctk-rewrite.sh")
    for h in bash_matcher["hooks"]
)

if not ctk_hook_exists:
    bash_matcher["hooks"].insert(0, ctk_hook)

with open(settings_file, "w") as f:
    json.dump(settings, f, indent=2)

print("  Added CTK hook to settings")
PYEOF
fi

# Step 3: Create directories
echo "Step 3: Creating directories..."
mkdir -p "$CTK_DATA"
mkdir -p "$HOME/.config/ctk"
mkdir -p "$HOME/.local/bin"
echo "  Created $CTK_DATA"
echo "  Created $HOME/.config/ctk"

# Step 4: Create the ctk executable wrapper
echo "Step 4: Creating CTK executable..."
cat > "$CTK_BIN" << 'EXECEOF'
#!/bin/bash
# CTK executable wrapper - runs the Python module
exec python3 -m ctk "$@"
EXECEOF
chmod +x "$CTK_BIN"
echo "  Created $CTK_BIN"

# Step 5: Verify hook script
echo "Step 5: Verifying hook script..."
if [ -f "$CTK_HOOK" ]; then
    chmod +x "$CTK_HOOK"
    echo "  Hook script ready at $CTK_HOOK"
else
    echo "  ❌ Hook script not found at $CTK_HOOK"
    exit 1
fi

# Step 6: Initialize database and create default config
echo "Step 6: Initializing metrics database..."
cd "$HOME/.local/lib/ctk"
python3 -c "
import sys
sys.path.insert(0, '.')
from ctk.core.metrics import MetricsDB
from ctk.core.config import get_config
MetricsDB()
config = get_config()
config.save()
print('  Database initialized')
print('  Config file created at ~/.config/ctk/config.yaml')
" 2>&1 || echo "  (Database will be created on first use)"

# Step 7: Migrate RTK data (optional)
echo
echo "Step 7: Checking for RTK data to migrate..."
if [ -f "$RTK_DATA" ]; then
    echo "  Found RTK history database at $RTK_DATA"
    read -p "  Migrate RTK history to CTK? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd "$HOME/.local/lib/ctk"
        python3 -c "
import sys
sys.path.insert(0, '.')
from ctk.core.metrics import MetricsDB
from pathlib import Path
metrics = MetricsDB()
migrated = metrics.migrate_from_rtk(Path('$RTK_DATA'))
print(f'  Migrated {migrated} records from RTK')
" 2>&1 || echo "  Migration will occur on first use"
    fi
else
    echo "  No RTK data to migrate"
fi

echo
echo "======================================"
echo "✅ CTK installation complete!"
echo
echo "Usage:"
echo "  ctk --help            # Show all commands"
echo "  ctk gain              # Show token savings"
echo "  ctk gain --history    # Show command history"
echo "  ctk gain --weekly     # Weekly statistics"
echo "  ctk discover          # Find missed opportunities"
echo "  ctk docker compose ps # Compact docker compose output"
echo "  ctk git status        # Compact git status"
echo
echo "The hook will automatically rewrite commands like:"
echo "  docker compose ps  ->  ctk docker compose ps"
echo "  git status         ->  ctk git status"
echo
echo "⚠️  Restart Claude Code for the hook to take effect."
