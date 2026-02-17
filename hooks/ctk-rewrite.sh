#!/bin/bash
# CTK auto-rewrite hook for Claude Code PreToolUse:Bash
# Transparently rewrites raw commands to their ctk equivalents.
# Outputs JSON with updatedInput to modify the command before execution.

# Guards: skip silently if dependencies missing
if ! command -v ctk &>/dev/null || ! command -v jq &>/dev/null; then
  exit 0
fi

set -euo pipefail

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$CMD" ]; then
  exit 0
fi

# Extract the first meaningful command (before pipes, &&, etc.)
FIRST_CMD="$CMD"

# Skip if already using ctk or rtk
case "$FIRST_CMD" in
  ctk\ *|*/ctk\ *|rtk\ *|*/rtk\ *) exit 0 ;;
esac

# Skip commands with heredocs
case "$FIRST_CMD" in
  *'<<'*) exit 0 ;;
esac

# Strip leading env var assignments for pattern matching
ENV_PREFIX=$(echo "$FIRST_CMD" | grep -oE '^([A-Za-z_][A-Za-z0-9_]*=[^ ]* +)+' || echo "")
if [ -n "$ENV_PREFIX" ]; then
  MATCH_CMD="${FIRST_CMD:${#ENV_PREFIX}}"
  CMD_BODY="${CMD:${#ENV_PREFIX}}"
else
  MATCH_CMD="$FIRST_CMD"
  CMD_BODY="$CMD"
fi

# Strip leading sudo (with optional flags)
SUDO_PREFIX=""
if echo "$MATCH_CMD" | grep -qE '^sudo([[:space:]]|$)'; then
  SUDO_PREFIX=$(echo "$MATCH_CMD" | grep -oE '^sudo([[:space:]]+-[A-Za-z]+([[:space:]]+[^[:space:]]+)?)*[[:space:]]+' || echo "")
  if [ -n "$SUDO_PREFIX" ]; then
    MATCH_CMD="${MATCH_CMD:${#SUDO_PREFIX}}"
    CMD_BODY="${CMD_BODY:${#SUDO_PREFIX}}"
  fi
fi

REWRITTEN=""

# --- Docker commands (including compose - HIGHEST PRIORITY) ---
if echo "$MATCH_CMD" | grep -qE '^docker[[:space:]]'; then
  # Docker compose - match all subcommands
  if echo "$MATCH_CMD" | grep -qE '^docker[[:space:]]+compose[[:space:]]'; then
    REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
  else
    DOCKER_SUBCMD=$(echo "$MATCH_CMD" | sed -E \
      -e 's/^docker[[:space:]]+//' \
      -e 's/(-H|--context|--config)[[:space:]]+[^[:space:]]+[[:space:]]*//g' \
      -e 's/--[a-z-]+=[^[:space:]]+[[:space:]]*//g' \
      -e 's/^[[:space:]]+//')
    case "$DOCKER_SUBCMD" in
      ps|ps\ *|images|images\ *|logs|logs\ *|run|run\ *|build|build\ *|exec|exec\ *|inspect|inspect\ *|cp|cp\ *)
        REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
        ;;
    esac
  fi

# --- Kubernetes ---
elif echo "$MATCH_CMD" | grep -qE '^kubectl[[:space:]]'; then
  KUBE_SUBCMD=$(echo "$MATCH_CMD" | sed -E \
    -e 's/^kubectl[[:space:]]+//' \
    -e 's/(--context|--kubeconfig|--namespace|-n)[[:space:]]+[^[:space:]]+[[:space:]]*//g' \
    -e 's/--[a-z-]+=[^[:space:]]+[[:space:]]*//g' \
    -e 's/^[[:space:]]+//')
  case "$KUBE_SUBCMD" in
    get|get\ *|logs|logs\ *|describe|describe\ *|apply|apply\ *|delete|delete\ *)
      REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
      ;;
  esac

# --- Git commands ---
elif echo "$MATCH_CMD" | grep -qE '^git[[:space:]]'; then
  GIT_SUBCMD=$(echo "$MATCH_CMD" | sed -E \
    -e 's/^git[[:space:]]+//' \
    -e 's/(-C|-c)[[:space:]]+[^[:space:]]+[[:space:]]*//g' \
    -e 's/--[a-z-]+=[^[:space:]]+[[:space:]]*//g' \
    -e 's/--(no-pager|no-optional-locks|bare|literal-pathspecs)[[:space:]]*//g' \
    -e 's/^[[:space:]]+//')
  case "$GIT_SUBCMD" in
    status|status\ *|diff|diff\ *|log|log\ *|add|add\ *|commit|commit\ *|push|push\ *|pull|pull\ *|branch|branch\ *|fetch|fetch\ *|stash|stash\ *|show|show\ *|merge|merge\ *|rebase|rebase\ *|checkout|checkout\ *)
      REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
      ;;
  esac

# --- GitHub CLI ---
elif echo "$MATCH_CMD" | grep -qE '^gh[[:space:]]+(pr|issue|run|api|release)([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"

# --- System commands (NEW - high priority) ---
elif echo "$MATCH_CMD" | grep -qE '^ps[[:space:]]+aux'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
elif echo "$MATCH_CMD" | grep -qE '^free([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
elif echo "$MATCH_CMD" | grep -qE '^date([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
elif echo "$MATCH_CMD" | grep -qE '^whoami([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"

# --- File operations ---
elif echo "$MATCH_CMD" | grep -qE '^cat[[:space:]]+'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}$(echo "$CMD_BODY" | sed 's/^cat /ctk read /')"
elif echo "$MATCH_CMD" | grep -qE '^(rg|grep)[[:space:]]+'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}$(echo "$CMD_BODY" | sed -E 's/^(rg|grep) /ctk grep /')"
elif echo "$MATCH_CMD" | grep -qE '^ls([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
elif echo "$MATCH_CMD" | grep -qE '^tree([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
elif echo "$MATCH_CMD" | grep -qE '^find[[:space:]]+'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
elif echo "$MATCH_CMD" | grep -qE '^diff[[:space:]]+'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
elif echo "$MATCH_CMD" | grep -qE '^du([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
elif echo "$MATCH_CMD" | grep -qE '^head[[:space:]]+'; then
  if echo "$MATCH_CMD" | grep -qE '^head[[:space:]]+-[0-9]+[[:space:]]+'; then
    LINES=$(echo "$MATCH_CMD" | sed -E 's/^head +-([0-9]+) +.+$/\1/')
    FILE=$(echo "$MATCH_CMD" | sed -E 's/^head +-[0-9]+ +(.+)$/\1/')
    REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk read $FILE --max-lines $LINES"
  elif echo "$MATCH_CMD" | grep -qE '^head[[:space:]]+--lines=[0-9]+[[:space:]]+'; then
    LINES=$(echo "$MATCH_CMD" | sed -E 's/^head +--lines=([0-9]+) +.+$/\1/')
    FILE=$(echo "$MATCH_CMD" | sed -E 's/^head +--lines=[0-9]+ +(.+)$/\1/')
    REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk read $FILE --max-lines $LINES"
  fi

# --- JS/TS tooling ---
elif echo "$MATCH_CMD" | grep -qE '^(pnpm[[:space:]]+)?(npx[[:space:]]+)?vitest([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}$(echo "$CMD_BODY" | sed -E 's/^(pnpm )?(npx )?vitest( run)?/ctk vitest/')"
elif echo "$MATCH_CMD" | grep -qE '^pnpm[[:space:]]+test([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk vitest"
elif echo "$MATCH_CMD" | grep -qE '^npm[[:space:]]+test([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk npm test"
elif echo "$MATCH_CMD" | grep -qE '^npm[[:space:]]+run[[:space:]]+'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}$(echo "$CMD_BODY" | sed 's/^npm run /ctk npm /')"
elif echo "$MATCH_CMD" | grep -qE '^(npx[[:space:]]+)?vue-tsc([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk tsc $(echo "$CMD_BODY" | sed -E 's/^(npx )?vue-tsc //')"
elif echo "$MATCH_CMD" | grep -qE '^pnpm[[:space:]]+tsc([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk tsc"
elif echo "$MATCH_CMD" | grep -qE '^(npx[[:space:]]+)?tsc([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}$(echo "$CMD_BODY" | sed -E 's/^(npx )?tsc/ctk tsc/')"
elif echo "$MATCH_CMD" | grep -qE '^pnpm[[:space:]]+lint([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk lint"
elif echo "$MATCH_CMD" | grep -qE '^(npx[[:space:]]+)?eslint([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}$(echo "$CMD_BODY" | sed -E 's/^(npx )?eslint/ctk lint/')"
elif echo "$MATCH_CMD" | grep -qE '^(npx[[:space:]]+)?prettier([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
elif echo "$MATCH_CMD" | grep -qE '^(npx[[:space:]]+)?playwright([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
elif echo "$MATCH_CMD" | grep -qE '^pnpm[[:space:]]+playwright([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
elif echo "$MATCH_CMD" | grep -qE '^(npx[[:space:]]+)?prisma([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"

# --- pnpm package management ---
elif echo "$MATCH_CMD" | grep -qE '^pnpm[[:space:]]+(list|ls|outdated)([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"

# --- Python tooling ---
elif echo "$MATCH_CMD" | grep -qE '^pytest([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
elif echo "$MATCH_CMD" | grep -qE '^python[[:space:]]+-m[[:space:]]+pytest([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}$(echo "$CMD_BODY" | sed 's/^python -m pytest/ctk pytest/')"
elif echo "$MATCH_CMD" | grep -qE '^ruff[[:space:]]+(check|format)([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
elif echo "$MATCH_CMD" | grep -qE '^pip[[:space:]]+(list|outdated|install|show)([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
elif echo "$MATCH_CMD" | grep -qE '^uv[[:space:]]+pip[[:space:]]+(list|outdated|install|show)([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}$(echo "$CMD_BODY" | sed 's/^uv pip /ctk pip /')"

# --- Cargo ---
elif echo "$MATCH_CMD" | grep -qE '^cargo[[:space:]]'; then
  CARGO_SUBCMD=$(echo "$MATCH_CMD" | sed -E 's/^cargo[[:space:]]+(\+[^[:space:]]+[[:space:]]+)?//')
  case "$CARGO_SUBCMD" in
    test|test\ *|build|build\ *|clippy|clippy\ *|check|check\ *|install|install\ *|fmt|fmt\ *)
      REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
      ;;
  esac

# --- Go tooling ---
elif echo "$MATCH_CMD" | grep -qE '^go[[:space:]]+test([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
elif echo "$MATCH_CMD" | grep -qE '^go[[:space:]]+build([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
elif echo "$MATCH_CMD" | grep -qE '^go[[:space:]]+vet([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
elif echo "$MATCH_CMD" | grep -qE '^golangci-lint([[:space:]]|$)'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"

# --- Network ---
elif echo "$MATCH_CMD" | grep -qE '^curl[[:space:]]+'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
elif echo "$MATCH_CMD" | grep -qE '^wget[[:space:]]+'; then
  REWRITTEN="${ENV_PREFIX}${SUDO_PREFIX}ctk ${CMD_BODY}"
fi

# If no rewrite needed, approve as-is
if [ -z "$REWRITTEN" ]; then
  exit 0
fi

# Build the updated tool_input with all original fields preserved
ORIGINAL_INPUT=$(echo "$INPUT" | jq -c '.tool_input')
UPDATED_INPUT=$(echo "$ORIGINAL_INPUT" | jq --arg cmd "$REWRITTEN" '.command = $cmd')

# Output the rewrite instruction
jq -n \
  --argjson updated "$UPDATED_INPUT" \
  '{
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "allow",
      "permissionDecisionReason": "CTK auto-rewrite",
      "updatedInput": $updated
    }
  }'
