#!/usr/bin/env bash
# SessionStart hook for CTK plugin
# Ensures CTK is properly set up and ready to use

set -euo pipefail

# Determine plugin root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Check if ctk binary exists
CTK_BIN="$HOME/.local/bin/ctk"
CTK_LIB="$HOME/.local/lib/ctk"

# Install CTK if not present or if plugin was updated
if [ ! -f "$CTK_BIN" ] || [ "$PLUGIN_ROOT/ctk/cli.py" -nt "$CTK_LIB/ctk/cli.py" ]; then
    # Create directories
    mkdir -p "$HOME/.local/bin"
    mkdir -p "$CTK_LIB/ctk/core"
    mkdir -p "$CTK_LIB/ctk/utils"
    mkdir -p "$HOME/.local/share/ctk"
    mkdir -p "$HOME/.config/ctk"

    # Copy Python package
    cp -r "$PLUGIN_ROOT/ctk/"*.py "$CTK_LIB/ctk/" 2>/dev/null || true
    cp -r "$PLUGIN_ROOT/ctk/core/"*.py "$CTK_LIB/ctk/core/" 2>/dev/null || true
    cp -r "$PLUGIN_ROOT/ctk/utils/"*.py "$CTK_LIB/ctk/utils/" 2>/dev/null || true

    # Create wrapper script
    cat > "$CTK_BIN" << 'WRAPPER'
#!/bin/bash
export PYTHONPATH="$HOME/.local/lib/ctk:$PYTHONPATH"
exec python3 -m ctk "$@"
WRAPPER
    chmod +x "$CTK_BIN"

    # Initialize database
    cd "$CTK_LIB" && python3 -c "
import sys
sys.path.insert(0, '.')
from ctk.core.metrics import MetricsDB
from ctk.core.config import get_config
MetricsDB()
get_config().save()
" 2>/dev/null || true
fi

# Copy hook script to ensure it's up to date
cp "$PLUGIN_ROOT/hooks/ctk-rewrite.sh" "$HOME/.claude/hooks/ctk-rewrite.sh" 2>/dev/null || true
chmod +x "$HOME/.claude/hooks/ctk-rewrite.sh" 2>/dev/null || true

# Output nothing - silent startup
exit 0
