"""Command rewriting engine for CTK."""

import re
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class RewriteResult:
    """Result of a command rewrite operation."""

    original: str
    rewritten: Optional[str]
    category: str
    should_rewrite: bool


# Command patterns organized by category
COMMAND_PATTERNS = {
    # Docker commands
    "docker": {
        "patterns": [
            (r"^docker\s+compose\s+", "docker compose"),
            (r"^docker\s+ps", "docker ps"),
            (r"^docker\s+images", "docker images"),
            (r"^docker\s+logs", "docker logs"),
            (r"^docker\s+run", "docker run"),
            (r"^docker\s+build", "docker build"),
            (r"^docker\s+exec", "docker exec"),
            (r"^docker\s+inspect", "docker inspect"),
            (r"^docker\s+cp", "docker cp"),
        ],
        "subcommands": ["compose", "ps", "images", "logs", "run", "build", "exec", "inspect", "cp"],
    },
    # Git commands
    "git": {
        "patterns": [
            (r"^git\s+", "git"),
        ],
        "subcommands": [
            "status", "diff", "log", "add", "commit", "push", "pull",
            "branch", "fetch", "stash", "show", "merge", "rebase", "checkout",
        ],
    },
    # GitHub CLI
    "gh": {
        "patterns": [
            (r"^gh\s+pr", "gh pr"),
            (r"^gh\s+issue", "gh issue"),
            (r"^gh\s+run", "gh run"),
            (r"^gh\s+api", "gh api"),
            (r"^gh\s+release", "gh release"),
        ],
        "subcommands": ["pr", "issue", "run", "api", "release"],
    },
    # Kubernetes
    "kubectl": {
        "patterns": [
            (r"^kubectl\s+", "kubectl"),
        ],
        "subcommands": ["get", "logs", "describe", "apply", "delete", "create"],
    },
    # File operations
    "files": {
        "patterns": [
            (r"^ls(\s|$)", "ls"),
            (r"^tree(\s|$)", "tree"),
            (r"^cat\s+", "read"),
            (r"^rg\s+", "grep"),
            (r"^grep\s+", "grep"),
            (r"^find\s+", "find"),
            (r"^diff\s+", "diff"),
            (r"^head\s+", "head"),
            (r"^du(\s|$)", "du"),
            (r"^rm(\s|$)", "rm"),
            (r"^ln(\s|$)", "ln"),
            (r"^mv(\s|$)", "mv"),
            (r"^stat\s+", "stat"),
        ],
        "subcommands": None,  # Direct commands
    },
    # System commands
    "system": {
        "patterns": [
            (r"^ps\s+", "ps"),
            (r"^free(\s|$)", "free"),
            (r"^date(\s|$)", "date"),
            (r"^whoami(\s|$)", "whoami"),
            (r"^uname(\s|$)", "uname"),
            (r"^dpkg\s+", "dpkg"),
            (r"^apt(\s|$)", "apt"),
            (r"^pkill\s+", "pkill"),
            (r"^top(\s|$)", "top"),
            (r"^htop(\s|$)", "htop"),
        ],
        "subcommands": None,
    },
    # Python tooling
    "python": {
        "patterns": [
            (r"^pytest(\s|$)", "pytest"),
            (r"^python\s+-m\s+pytest", "pytest"),
            (r"^ruff\s+", "ruff"),
            (r"^pip\s+", "pip"),
            (r"^uv\s+pip\s+", "pip"),
        ],
        "subcommands": None,
    },
    # Node.js tooling
    "nodejs": {
        "patterns": [
            (r"^pnpm\s+test", "vitest"),
            (r"^pnpm\s+tsc", "tsc"),
            (r"^pnpm\s+lint", "lint"),
            (r"^pnpm\s+playwright", "playwright"),
            (r"^pnpm\s+(list|ls|outdated)", "pnpm"),
            (r"^npm\s+test", "npm test"),
            (r"^npm\s+run\s+", "npm"),
            (r"^(npx\s+)?vitest", "vitest"),
            (r"^(npx\s+)?vue-tsc", "tsc"),
            (r"^(npx\s+)?tsc", "tsc"),
            (r"^(npx\s+)?eslint", "lint"),
            (r"^(npx\s+)?prettier", "prettier"),
            (r"^(npx\s+)?playwright", "playwright"),
            (r"^(npx\s+)?prisma", "prisma"),
        ],
        "subcommands": None,
    },
    # Rust tooling
    "rust": {
        "patterns": [
            (r"^cargo\s+", "cargo"),
        ],
        "subcommands": ["test", "build", "clippy", "check", "install", "fmt"],
    },
    # Go tooling
    "go": {
        "patterns": [
            (r"^go\s+test", "go test"),
            (r"^go\s+build", "go build"),
            (r"^go\s+vet", "go vet"),
            (r"^golangci-lint", "golangci-lint"),
        ],
        "subcommands": None,
    },
    # Network
    "network": {
        "patterns": [
            (r"^curl\s+", "curl"),
            (r"^wget\s+", "wget"),
        ],
        "subcommands": None,
    },
}


def extract_prefix(cmd: str) -> Tuple[str, str]:
    """Extract environment variable prefix and sudo prefix from command.

    Returns: (prefix_to_preserve, command_body)
    """
    prefix = ""
    remaining = cmd

    # Extract env vars at the start
    env_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*=[^\s]*\s+)+", remaining)
    if env_match:
        prefix += env_match.group(0)
        remaining = remaining[len(env_match.group(0)):]

    # Extract sudo with optional flags
    sudo_match = re.match(r"^sudo(\s+-[A-Za-z]+(\s+[^\s]+)?)?\s+", remaining)
    if sudo_match:
        prefix += sudo_match.group(0)
        remaining = remaining[len(sudo_match.group(0)):]

    return prefix, remaining


def extract_git_subcommand(cmd: str) -> Optional[str]:
    """Extract git subcommand, stripping flags like -C, -c, etc."""
    # Remove git prefix
    cmd = re.sub(r"^git\s+", "", cmd)
    # Remove -C, -c options with their values
    cmd = re.sub(r"(-C|-c)\s+[^\s]+\s*", "", cmd)
    # Remove other --option=value patterns
    cmd = re.sub(r"--[a-z-]+=[^\s]+\s*", "", cmd)
    # Remove standalone flags
    cmd = re.sub(r"--(no-pager|no-optional-locks|bare|literal-pathspecs)\s*", "", cmd)
    # Get the subcommand
    cmd = cmd.strip()
    parts = cmd.split()
    return parts[0] if parts else None


def extract_docker_subcommand(cmd: str) -> Optional[str]:
    """Extract docker subcommand, stripping flags like -H, --context, etc."""
    # Remove docker prefix
    cmd = re.sub(r"^docker\s+", "", cmd)
    # Check if it's compose
    if cmd.startswith("compose"):
        return "compose"
    # Remove -H, --context, --config options with their values
    cmd = re.sub(r"(-H|--context|--config)\s+[^\s]+\s*", "", cmd)
    # Remove other --option=value patterns
    cmd = re.sub(r"--[a-z-]+=[^\s]+\s*", "", cmd)
    # Get the subcommand
    cmd = cmd.strip()
    parts = cmd.split()
    return parts[0] if parts else None


def extract_kubectl_subcommand(cmd: str) -> Optional[str]:
    """Extract kubectl subcommand, stripping flags like --context, -n, etc."""
    cmd = re.sub(r"^kubectl\s+", "", cmd)
    cmd = re.sub(r"(--context|--kubeconfig|--namespace|-n)\s+[^\s]+\s*", "", cmd)
    cmd = re.sub(r"--[a-z-]+=[^\s]+\s*", "", cmd)
    cmd = cmd.strip()
    parts = cmd.split()
    return parts[0] if parts else None


def extract_cargo_subcommand(cmd: str) -> Optional[str]:
    """Extract cargo subcommand, handling +toolchain prefix."""
    cmd = re.sub(r"^cargo\s+(\+[^\s]+\s+)?", "", cmd)
    cmd = cmd.strip()
    parts = cmd.split()
    return parts[0] if parts else None


def should_rewrite_command(cmd: str) -> RewriteResult:
    """Determine if a command should be rewritten and how.

    Args:
        cmd: The command string to analyze

    Returns:
        RewriteResult with rewrite information
    """
    if not cmd or cmd.startswith("ctk ") or cmd.startswith("rtk "):
        return RewriteResult(cmd, None, "none", False)

    # Skip heredocs
    if "<<" in cmd:
        return RewriteResult(cmd, None, "none", False)

    prefix, cmd_body = extract_prefix(cmd)

    for category, config in COMMAND_PATTERNS.items():
        for pattern, _ in config["patterns"]:
            if re.search(pattern, cmd_body):
                # Check if there are subcommands to validate
                subcommands = config.get("subcommands")

                if subcommands:
                    extracted = None
                    if category == "git":
                        extracted = extract_git_subcommand(cmd_body)
                    elif category == "docker":
                        extracted = extract_docker_subcommand(cmd_body)
                    elif category == "kubectl":
                        extracted = extract_kubectl_subcommand(cmd_body)
                    elif category == "rust":
                        extracted = extract_cargo_subcommand(cmd_body)
                    elif category == "gh":
                        parts = cmd_body.split()
                        if len(parts) > 1:
                            extracted = parts[1]

                    # If we have subcommands, check if extracted is valid
                    if extracted and extracted in subcommands:
                        rewritten = f"{prefix}ctk {cmd_body}"
                        return RewriteResult(cmd, rewritten, category, True)
                    elif extracted is None:
                        # Pattern matched but no specific subcommand required
                        rewritten = f"{prefix}ctk {cmd_body}"
                        return RewriteResult(cmd, rewritten, category, True)
                else:
                    # No subcommand validation needed
                    rewritten = f"{prefix}ctk {cmd_body}"
                    return RewriteResult(cmd, rewritten, category, True)

    return RewriteResult(cmd, None, "none", False)


def rewrite_command(cmd: str) -> Optional[str]:
    """Simple function to just return the rewritten command or None.

    Args:
        cmd: The command string to rewrite

    Returns:
        Rewritten command string or None if no rewrite needed
    """
    result = should_rewrite_command(cmd)
    return result.rewritten


# Categories for grouping in metrics
def get_command_category(cmd: str) -> str:
    """Get the category for a command without rewriting."""
    result = should_rewrite_command(cmd)
    return result.category
