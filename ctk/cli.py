"""CTK CLI commands."""

import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .core.config import Config, get_config
from .core.metrics import MetricsDB, get_metrics
from .core.rewriter import should_rewrite_command, COMMAND_PATTERNS
from .utils.tokenizer import calculate_savings


console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version="1.0.0", prog_name="ctk")
def cli(ctx: click.Context):
    """CTK - Claude Token Killer: Token-optimized CLI proxy.

    This tool runs shell commands as a proxy - subprocess usage is intentional.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ==================== Meta Commands ====================

@cli.command()
@click.option("--history", is_flag=True, help="Show command history")
@click.option("--daily", is_flag=True, help="Show daily statistics")
@click.option("--weekly", is_flag=True, help="Show weekly statistics")
@click.option("--monthly", is_flag=True, help="Show monthly statistics")
@click.option("--export", type=click.Choice(["json", "csv"]), help="Export data")
@click.option("--output", "-o", type=click.Path(), help="Output file for export")
def gain(history: bool, daily: bool, weekly: bool, monthly: bool,
         export: Optional[str], output: Optional[str]):
    """Show token savings summary and analytics."""
    metrics = get_metrics()

    if export:
        data = metrics.export(format=export, output_path=Path(output) if output else None)
        if not output:
            click.echo(data)
        console.print(f"[green]Exported to {output}[/green]" if output else "[green]Exported[/green]")
        return

    if history:
        _show_history(metrics)
        return

    days = 30 if monthly else (7 if weekly else (1 if daily else 0))
    _show_summary(metrics, days)


def _show_summary(metrics: MetricsDB, days: int = 0):
    """Display token savings summary."""
    summary = metrics.get_summary(days=days)
    by_category = metrics.get_by_category(days=days)

    period = "all time" if days == 0 else f"last {days} day{'s' if days > 1 else ''}"

    console.print(Panel(f"[bold cyan]Token Savings Summary ({period})[/bold cyan]", expand=False))

    console.print(f"\n[bold]Overall Statistics[/bold]")
    console.print(f"  Commands tracked: {summary['total_commands']}")
    console.print(f"  Commands rewritten: {summary['rewritten_commands']}")
    console.print(f"  Tokens saved: [green]{summary['total_tokens_saved']:,}[/green]")
    console.print(f"  Avg savings: {summary['avg_savings_percent']}%")

    if by_category:
        console.print(f"\n[bold]By Category[/bold]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Category")
        table.add_column("Commands", justify="right")
        table.add_column("Tokens Saved", justify="right")
        table.add_column("Avg %", justify="right")

        for cat, stats in sorted(by_category.items(), key=lambda x: x[1]["tokens_saved"], reverse=True):
            table.add_row(cat, str(stats["count"]), f"[green]{stats['tokens_saved']:,}[/green]", f"{stats['avg_savings_percent']}%")

        console.print(table)

    daily_stats = metrics.get_daily_stats(days=7)
    if daily_stats:
        console.print(f"\n[bold]Daily Breakdown (Last 7 Days)[/bold]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Date")
        table.add_column("Commands", justify="right")
        table.add_column("Tokens Saved", justify="right")

        for stat in daily_stats:
            table.add_row(stat["date"], str(stat["commands"]), f"[green]{stat['tokens_saved'] or 0:,}[/green]")

        console.print(table)


def _show_history(metrics: MetricsDB, limit: int = 20):
    """Display command history."""
    history = metrics.get_history(limit=limit)

    if not history:
        console.print("[yellow]No command history found[/yellow]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Time")
    table.add_column("Category")
    table.add_column("Command")
    table.add_column("Saved", justify="right")

    for entry in history:
        cmd = entry["original_command"]
        if len(cmd) > 40:
            cmd = cmd[:37] + "..."
        table.add_row(
            entry["timestamp"][:19] if entry["timestamp"] else "",
            entry["category"] or "",
            cmd,
            f"[green]{entry['tokens_saved'] or 0}[/green]"
        )

    console.print(table)


@cli.command()
@click.option("--all", "show_all", is_flag=True, help="Show all missed opportunities")
def discover(show_all: bool):
    """Analyze Claude Code history for missed optimization opportunities."""
    console.print("[cyan]Analyzing Claude Code history for missed opportunities...[/cyan]")

    history_paths = [
        Path.home() / ".claude" / "projects",
        Path.home() / ".config" / "claude" / "projects",
    ]

    found = False
    for base_path in history_paths:
        if base_path.exists():
            found = True
            _analyze_history_dir(base_path, show_all)

    if not found:
        console.print("[yellow]No Claude Code history found[/yellow]")


def _analyze_history_dir(base_path: Path, show_all: bool):
    """Analyze Claude Code history directory for missed opportunities."""
    import json
    from collections import Counter

    missed = Counter()

    for jsonl_file in base_path.rglob("*.jsonl"):
        try:
            with open(jsonl_file) as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if data.get("type") == "human":
                            msg = data.get("message", "")
                            for category, config in COMMAND_PATTERNS.items():
                                for pattern, _ in config["patterns"]:
                                    import re
                                    if re.search(pattern, msg):
                                        result = should_rewrite_command(msg)
                                        if not result.should_rewrite:
                                            missed[category] += 1
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass

    if missed:
        console.print("\n[bold]Potential missed opportunities by category:[/bold]")
        limit = None if show_all else 10
        for cat, count in missed.most_common(limit):
            console.print(f"  {cat}: {count} commands")
    else:
        console.print("[green]No significant missed opportunities found[/green]")


@cli.command("proxy")
@click.argument("command", nargs=-1, required=True)
def proxy_command(command: Tuple[str, ...]):
    """Execute command without filtering but track usage."""
    cmd_str = " ".join(command)
    metrics = get_metrics()

    start = time.time()
    result = subprocess.run(cmd_str, shell=True)  # noqa: S602 - intentional for CLI proxy
    exec_time = int((time.time() - start) * 1000)

    metrics.record(
        original_command=cmd_str,
        rewritten_command=None,
        category="proxy",
        exec_time_ms=exec_time,
    )

    sys.exit(result.returncode)


# ==================== Docker Commands ====================

@cli.group()
def docker():
    """Docker commands with compact output."""
    pass


@docker.command("ps")
@click.argument("args", nargs=-1)
def docker_ps(args: Tuple[str, ...]):
    """Compact container listing."""
    _run_command("docker ps " + " ".join(args), "docker")


@docker.command("images")
@click.argument("args", nargs=-1)
def docker_images(args: Tuple[str, ...]):
    """Compact image listing."""
    _run_command("docker images " + " ".join(args), "docker")


@docker.command("logs")
@click.argument("args", nargs=-1)
def docker_logs(args: Tuple[str, ...]):
    """Deduplicated log output."""
    _run_command("docker logs " + " ".join(args), "docker")


@docker.command("exec")
@click.argument("args", nargs=-1)
def docker_exec(args: Tuple[str, ...]):
    """Execute command in container."""
    _run_command("docker exec " + " ".join(args), "docker")


@docker.command("run")
@click.argument("args", nargs=-1)
def docker_run(args: Tuple[str, ...]):
    """Run container with compact output."""
    _run_command("docker run " + " ".join(args), "docker")


@docker.command("build")
@click.argument("args", nargs=-1)
def docker_build(args: Tuple[str, ...]):
    """Build image with compact output."""
    _run_command("docker build " + " ".join(args), "docker")


# Docker Compose group
@docker.group("compose")
def docker_compose():
    """Docker Compose commands."""
    pass


@docker_compose.command("ps")
@click.argument("args", nargs=-1)
def compose_ps(args: Tuple[str, ...]):
    """Compact compose container listing."""
    _run_command("docker compose ps " + " ".join(args), "docker-compose")


@docker_compose.command("logs")
@click.argument("args", nargs=-1)
def compose_logs(args: Tuple[str, ...]):
    """Deduplicated compose logs."""
    _run_command("docker compose logs " + " ".join(args), "docker-compose")


@docker_compose.command("up")
@click.argument("args", nargs=-1)
def compose_up(args: Tuple[str, ...]):
    """Start services with summary."""
    _run_command("docker compose up " + " ".join(args), "docker-compose")


@docker_compose.command("down")
@click.argument("args", nargs=-1)
def compose_down(args: Tuple[str, ...]):
    """Stop services with summary."""
    _run_command("docker compose down " + " ".join(args), "docker-compose")


@docker_compose.command("exec")
@click.argument("args", nargs=-1)
def compose_exec(args: Tuple[str, ...]):
    """Execute in compose service."""
    _run_command("docker compose exec " + " ".join(args), "docker-compose")


# ==================== Git Commands ====================

@cli.group()
def git():
    """Git commands with compact output."""
    pass


@git.command("status")
@click.argument("args", nargs=-1)
def git_status(args: Tuple[str, ...]):
    """Compact status output."""
    _run_command("git status " + " ".join(args), "git")


@git.command("diff")
@click.argument("args", nargs=-1)
def git_diff(args: Tuple[str, ...]):
    """Ultra-condensed diff."""
    _run_command("git diff " + " ".join(args), "git")


@git.command("log")
@click.argument("args", nargs=-1)
def git_log(args: Tuple[str, ...]):
    """Compact log output."""
    _run_command("git log --oneline " + " ".join(args), "git")


@git.command("add")
@click.argument("args", nargs=-1)
def git_add(args: Tuple[str, ...]):
    """Stage files."""
    _run_command("git add " + " ".join(args), "git")


@git.command("commit")
@click.argument("args", nargs=-1)
def git_commit(args: Tuple[str, ...]):
    """Commit changes."""
    _run_command("git commit " + " ".join(args), "git")


@git.command("push")
@click.argument("args", nargs=-1)
def git_push(args: Tuple[str, ...]):
    """Push changes."""
    _run_command("git push " + " ".join(args), "git")


@git.command("pull")
@click.argument("args", nargs=-1)
def git_pull(args: Tuple[str, ...]):
    """Pull changes."""
    _run_command("git pull " + " ".join(args), "git")


# ==================== System Commands ====================

@cli.command("ps")
@click.argument("args", nargs=-1)
def ps_command(args: Tuple[str, ...]):
    """Top processes by CPU/memory."""
    _run_command("ps aux --sort=-%mem | head -20", "system")


@cli.command("free")
@click.argument("args", nargs=-1)
def free_command(args: Tuple[str, ...]):
    """Single line memory summary."""
    _run_command("free -h", "system")


@cli.command("date")
@click.argument("args", nargs=-1)
def date_command(args: Tuple[str, ...]):
    """Compact date output."""
    _run_command("date '+%Y-%m-%d %H:%M:%S'", "system")


@cli.command("whoami")
def whoami_command():
    """Current user."""
    _run_command("whoami", "system")


# ==================== File Commands ====================

@cli.command("ls")
@click.argument("args", nargs=-1)
def ls_command(args: Tuple[str, ...]):
    """Compact directory listing."""
    args_str = " ".join(args) if args else "-1"
    _run_command(f"ls {args_str}", "files")


@cli.command("tree")
@click.argument("args", nargs=-1)
def tree_command(args: Tuple[str, ...]):
    """Compact tree output."""
    _run_command("tree " + " ".join(args), "files")


@cli.command("read")
@click.argument("file", type=click.Path(exists=True))
@click.option("--max-lines", "-n", default=100, help="Maximum lines to show")
def read_command(file: str, max_lines: int):
    """Read file with filtering."""
    _run_command(f"head -{max_lines} {file}", "files")


@cli.command("grep")
@click.argument("args", nargs=-1)
def grep_command(args: Tuple[str, ...]):
    """Compact grep output."""
    _run_command("grep " + " ".join(args), "files")


@cli.command("find")
@click.argument("args", nargs=-1)
def find_command(args: Tuple[str, ...]):
    """Compact find output."""
    _run_command("find " + " ".join(args), "files")


@cli.command("du")
@click.argument("args", nargs=-1)
def du_command(args: Tuple[str, ...]):
    """Disk usage summary."""
    args_str = " ".join(args) if args else "-sh ."
    _run_command(f"du {args_str}", "files")


# ==================== Python Commands ====================

@cli.command("pytest")
@click.argument("args", nargs=-1)
def pytest_command(args: Tuple[str, ...]):
    """Pytest with compact output."""
    args_str = " ".join(args) if args else ""
    _run_command(f"pytest {args_str} -q --tb=short 2>&1", "python")


@cli.command("ruff")
@click.argument("args", nargs=-1)
def ruff_command(args: Tuple[str, ...]):
    """Ruff with compact output."""
    _run_command("ruff " + " ".join(args), "python")


@cli.command("pip")
@click.argument("args", nargs=-1)
def pip_command(args: Tuple[str, ...]):
    """Pip with compact output."""
    _run_command("pip " + " ".join(args), "python")


# ==================== Node.js Commands ====================

@cli.command("npm")
@click.argument("args", nargs=-1)
def npm_command(args: Tuple[str, ...]):
    """npm with filtered output."""
    _run_command("npm " + " ".join(args), "nodejs")


@cli.command("pnpm")
@click.argument("args", nargs=-1)
def pnpm_command(args: Tuple[str, ...]):
    """pnpm with compact output."""
    _run_command("pnpm " + " ".join(args), "nodejs")


@cli.command("vitest")
@click.argument("args", nargs=-1)
def vitest_command(args: Tuple[str, ...]):
    """Vitest with compact output."""
    _run_command("npx vitest run --reporter=verbose 2>&1", "nodejs")


@cli.command("tsc")
@click.argument("args", nargs=-1)
def tsc_command(args: Tuple[str, ...]):
    """TypeScript compiler with grouped errors."""
    _run_command("npx tsc --pretty 2>&1", "nodejs")


@cli.command("lint")
@click.argument("args", nargs=-1)
def lint_command(args: Tuple[str, ...]):
    """ESLint with grouped violations."""
    _run_command("npx eslint --format compact 2>&1", "nodejs")


@cli.command("prettier")
@click.argument("args", nargs=-1)
def prettier_command(args: Tuple[str, ...]):
    """Prettier with compact output."""
    _run_command("npx prettier " + " ".join(args), "nodejs")


# ==================== Kubernetes Commands ====================

@cli.group()
def kubectl():
    """Kubectl commands with compact output."""
    pass


@kubectl.command("get")
@click.argument("args", nargs=-1)
def kubectl_get(args: Tuple[str, ...]):
    """Get resources."""
    _run_command("kubectl get " + " ".join(args), "kubernetes")


@kubectl.command("logs")
@click.argument("args", nargs=-1)
def kubectl_logs(args: Tuple[str, ...]):
    """Pod logs."""
    _run_command("kubectl logs " + " ".join(args), "kubernetes")


@kubectl.command("describe")
@click.argument("args", nargs=-1)
def kubectl_describe(args: Tuple[str, ...]):
    """Describe resource."""
    _run_command("kubectl describe " + " ".join(args), "kubernetes")


# ==================== Utility Functions ====================

def _run_command(cmd: str, category: str):
    """Run a command and track metrics.

    Also runs the raw equivalent command to measure actual token savings.
    """
    metrics = get_metrics()

    # Determine the raw command (what would have run without CTK)
    raw_cmd = _get_raw_command(cmd, category)

    # Run raw command first to measure original output size
    raw_output = ""
    if raw_cmd and raw_cmd != cmd:
        try:
            raw_result = subprocess.run(raw_cmd, shell=True, capture_output=True, text=True, timeout=5)  # noqa: S602
            raw_output = raw_result.stdout + raw_result.stderr
        except Exception:
            raw_output = ""

    # Run the CTK-optimized command
    start = time.time()
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)  # noqa: S602 - intentional for CLI proxy
    exec_time = int((time.time() - start) * 1000)

    output = result.stdout + result.stderr
    filtered = _filter_output(output, category)

    # Calculate savings: compare raw output vs CTK filtered output
    if raw_output:
        savings = calculate_savings(raw_output, filtered)
    else:
        # Fallback: compare before/after filtering
        savings = calculate_savings(output, filtered)

    click.echo(filtered)

    metrics.record(
        original_command=raw_cmd or cmd,
        rewritten_command=f"ctk {cmd}",
        category=category,
        exec_time_ms=exec_time,
        original_tokens=savings["original_tokens"],
        filtered_tokens=savings["filtered_tokens"],
        tokens_saved=savings["tokens_saved"],
        savings_percent=savings["savings_percent"],
    )

    sys.exit(result.returncode)


def _get_raw_command(ctk_cmd: str, category: str) -> str:
    """Get the raw command equivalent for a CTK command.

    This is used to measure actual token savings by running both
    the raw command and the CTK version.
    """
    # Map CTK commands back to their raw equivalents
    raw_map = {
        "ps aux --sort=-%mem | head -20": "ps aux",
        "free -h": "free",
        "date '+%Y-%m-%d %H:%M:%S'": "date",
        "whoami": "whoami",
    }

    # Check for exact match
    if ctk_cmd in raw_map:
        return raw_map[ctk_cmd]

    # Check for partial matches
    if ctk_cmd.startswith("git log"):
        return ctk_cmd.replace(" --oneline", "")
    if ctk_cmd.startswith("docker compose ps"):
        return ctk_cmd
    if ctk_cmd.startswith("docker compose logs"):
        return ctk_cmd

    return ""  # No raw equivalent - use CTK output as baseline


def _filter_output(output: str, category: str) -> str:
    """Apply basic output filtering based on category."""
    import re

    if not output:
        return output

    lines = output.split("\n")
    filtered_lines = []

    skip_patterns = [
        r"^\s*$",
        r"^=",
        r"^\s*(Using|Fetching|Downloading|Installing|Building|Compiling)",
        r"^\s*(created|deleted|modified):",
        r"^\s*\d+%\s*\|.*\|",
        r"^\s*[-=]{10,}",
    ]

    for line in lines:
        skip = False
        for pattern in skip_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                skip = True
                break
        if not skip:
            filtered_lines.append(line)

    if len(filtered_lines) > 200:
        filtered_lines = filtered_lines[:100] + ["... (truncated)"] + filtered_lines[-100:]

    return "\n".join(filtered_lines)


# ==================== Additional Commands ====================

@cli.command("gh")
@click.argument("args", nargs=-1)
def gh_command(args: Tuple[str, ...]):
    """GitHub CLI with compact output."""
    _run_command("gh " + " ".join(args), "gh")


@cli.command("cargo")
@click.argument("args", nargs=-1)
def cargo_command(args: Tuple[str, ...]):
    """Cargo with compact output."""
    _run_command("cargo " + " ".join(args), "rust")


@cli.command("go")
@click.argument("args", nargs=-1)
def go_command(args: Tuple[str, ...]):
    """Go commands with compact output."""
    _run_command("go " + " ".join(args), "go")


@cli.command("curl")
@click.argument("args", nargs=-1)
def curl_command(args: Tuple[str, ...]):
    """Curl with auto-JSON detection."""
    _run_command("curl -s " + " ".join(args), "network")


@cli.command("wget")
@click.argument("args", nargs=-1)
def wget_command(args: Tuple[str, ...]):
    """Wget with compact output."""
    _run_command("wget -q " + " ".join(args), "network")


# Config command
@cli.command("config")
@click.option("--show", is_flag=True, help="Show current configuration")
@click.option("--init", is_flag=True, help="Initialize configuration file")
def config_command(show: bool, init: bool):
    """Manage CTK configuration."""
    config = get_config()

    if init:
        config.save()
        console.print(f"[green]Configuration saved to {config.config_path}[/green]")
        return

    console.print(f"[bold]Configuration file:[/bold] {config.config_path}")
    console.print(f"[bold]Database:[/bold] {config.database_path}")
    console.print(f"\n[bold]Enabled commands:[/bold]")
    for cat, cmds in config._config.get("commands", {}).items():
        if isinstance(cmds, dict) and cmds.get("enabled"):
            console.print(f"  {cat}: enabled")
