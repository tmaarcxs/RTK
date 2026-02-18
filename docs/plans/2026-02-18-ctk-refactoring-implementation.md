# CTK Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce CTK codebase by ~30% through consolidation of duplicated code while maintaining 100% functionality.

**Architecture:** Layered refactoring from bottom-up: utilities → compression → metrics → CLI → cleanup. Test-first approach with each layer independently verifiable.

**Tech Stack:** Python 3.11+, Click, Rich, SQLite, pytest

---

## Prerequisites

Before starting, verify the environment:

```bash
# Verify tests pass on current codebase
python3 -m pytest tests/ -v

# Verify CLI works
python3 -m ctk --version
python3 -m ctk git status
```

---

## Layer 1: Shared Utilities

### Task 1.1: Create helpers module with compact_duration

**Files:**
- Create: `ctk/utils/helpers.py`
- Test: `tests/test_helpers.py`

**Step 1: Write the failing tests**

Create `tests/test_helpers.py`:

```python
"""Tests for shared utility helpers."""

import pytest
from ctk.utils.helpers import compact_duration


class TestCompactDuration:
    """Tests for compact_duration function."""

    def test_hours(self):
        assert compact_duration("2 hours") == "2h"
        assert compact_duration("3 hour") == "3h"
        assert compact_duration("4 hrs") == "4h"
        assert compact_duration("5 hr") == "5h"

    def test_days(self):
        assert compact_duration("2 days") == "2d"
        assert compact_duration("1 day") == "1d"

    def test_minutes(self):
        assert compact_duration("30 minutes") == "30m"
        assert compact_duration("15 mins") == "15m"
        assert compact_duration("5 min") == "5m"

    def test_seconds(self):
        assert compact_duration("45 seconds") == "45s"
        assert compact_duration("10 secs") == "10s"
        assert compact_duration("1 sec") == "1s"

    def test_weeks(self):
        assert compact_duration("2 weeks") == "2w"
        assert compact_duration("1 week") == "1w"

    def test_mixed_units(self):
        assert compact_duration("2 hours 30 minutes") == "2h 30m"

    def test_removes_ago(self):
        assert compact_duration("2 hours ago") == "2h"
        assert compact_duration("3 days ago") == "3d"

    def test_removes_parenthetical(self):
        assert compact_duration("2 hours (healthy)") == "2h"
        assert compact_duration("Exited (0) 3 days") == "Exited 3d"

    def test_empty_string(self):
        assert compact_duration("") == ""

    def test_already_compact(self):
        assert compact_duration("2h") == "2h"
        assert compact_duration("3d") == "3d"

    def test_case_insensitive(self):
        assert compact_duration("2 HOURS") == "2h"
        assert compact_duration("3 DAYS") == "3d"
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_helpers.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'ctk.utils.helpers'"

**Step 3: Create the helpers module**

Create `ctk/utils/helpers.py`:

```python
"""Shared utility helpers for CTK."""

import re


def compact_duration(duration: str) -> str:
    """Compact duration strings to minimal format.

    Converts verbose durations to compact form:
        "2 hours" -> "2h"
        "3 days ago" -> "3d"
        "30 minutes" -> "30m"

    Args:
        duration: Duration string to compact

    Returns:
        Compacted duration string
    """
    if not duration:
        return duration

    # Pattern list: (regex_pattern, replacement)
    patterns = [
        (r"(\d+)\s*weeks?", r"\1w"),
        (r"(\d+)\s*days?", r"\1d"),
        (r"(\d+)\s*hours?|hrs?", r"\1h"),
        (r"(\d+)\s*minutes?|mins?", r"\1m"),
        (r"(\d+)\s*seconds?|secs?", r"\1s"),
    ]

    for pattern, replacement in patterns:
        duration = re.sub(pattern, replacement, duration, flags=re.IGNORECASE)

    # Remove parenthetical info (e.g., "(healthy)", "(0)")
    duration = re.sub(r"\s*\(.*?\)", "", duration)

    # Remove "ago" suffix
    duration = duration.replace(" ago", "")

    return duration.strip()
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_helpers.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add ctk/utils/helpers.py tests/test_helpers.py
git commit -m "feat: add compact_duration helper utility

- Create ctk/utils/helpers.py with duration compaction
- Add comprehensive test coverage
- Supports hours, days, minutes, seconds, weeks
- Removes parenthetical info and 'ago' suffix"
```

---

### Task 1.2: Update symbols.py to use compact_duration

**Files:**
- Modify: `ctk/utils/symbols.py:287-299`
- Modify: `ctk/utils/helpers.py` (if needed for import)

**Step 1: Write the failing test**

Add to `tests/test_helpers.py`:

```python
class TestSymbolizeDockerStateUsesHelper:
    """Verify symbolize_docker_state uses compact_duration helper."""

    def test_uses_compact_duration(self):
        from ctk.utils.symbols import symbolize_docker_state
        # These should work the same as compact_duration
        assert "2h" in symbolize_docker_state("Up 2 hours")
        assert "3d" in symbolize_docker_state("Up 3 days")
```

**Step 2: Run test to verify current behavior**

Run: `python3 -m pytest tests/test_helpers.py::TestSymbolizeDockerStateUsesHelper -v`
Expected: PASS (current code works, but duplicated)

**Step 3: Update symbols.py to use helper**

Modify `ctk/utils/symbols.py`:

1. Add import at top of file:
```python
from ctk.utils.helpers import compact_duration
```

2. Replace lines 287-296 in `symbolize_docker_state`:

Before:
```python
    # Compact duration
    if duration:
        duration = re.sub(r"(\d+)\s*hours?", r"\1h", duration, flags=re.IGNORECASE)
        duration = re.sub(r"(\d+)\s*days?", r"\1d", duration, flags=re.IGNORECASE)
        duration = re.sub(r"(\d+)\s*minutes?", r"\1m", duration, flags=re.IGNORECASE)
        duration = re.sub(r"(\d+)\s*seconds?", r"\1s", duration, flags=re.IGNORECASE)
        duration = re.sub(r"(\d+)\s*weeks?", r"\1w", duration, flags=re.IGNORECASE)
        duration = re.sub(r"\s*\(.*\)", "", duration)  # Remove exit codes/health
        duration = re.sub(r"\s*ago\s*", "", duration)
        duration = duration.strip()
        return f"{symbol}{duration}"
```

After:
```python
    # Compact duration using shared helper
    if duration:
        duration = compact_duration(duration)
        return f"{symbol}{duration}"
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_helpers.py tests/test_symbols.py -v`
Expected: All tests PASS

**Step 5: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add ctk/utils/symbols.py tests/test_helpers.py
git commit -m "refactor: use compact_duration helper in symbols.py

- Replace inline duration compaction with helper function
- Reduces code duplication"
```

---

### Task 1.3: Update output_filter.py to use compact_duration

**Files:**
- Modify: `ctk/utils/output_filter.py:347-367`

**Step 1: Write the failing test**

Add to `tests/test_output_filter.py` (create if doesn't exist):

```python
"""Tests for output filtering."""

import pytest
from ctk.utils.output_filter import compact_docker_output


class TestCompactDockerOutputDuration:
    """Verify docker output uses compact_duration helper."""

    def test_compacts_hours(self):
        output = "abc123456789   nginx   Up 2 hours   80/tcp   web"
        result = compact_docker_output(output)
        assert "2h" in result

    def test_compacts_days(self):
        output = "abc123456789   nginx   Up 3 days   80/tcp   web"
        result = compact_docker_output(output)
        assert "3d" in result
```

**Step 2: Run test to verify current behavior**

Run: `python3 -m pytest tests/test_output_filter.py -v`
Expected: PASS (current code works)

**Step 3: Update output_filter.py to use helper**

Modify `ctk/utils/output_filter.py`:

1. Add import at top:
```python
from ctk.utils.helpers import compact_duration
```

2. Replace lines 347-367 in `compact_docker_output`:

Before:
```python
                # Compact duration
                duration = re.sub(
                    r"(\d+)\s*(hours?|hrs?|h)\b", r"\1h", duration, flags=re.IGNORECASE
                )
                duration = re.sub(
                    r"(\d+)\s*(days?|d)\b", r"\1d", duration, flags=re.IGNORECASE
                )
                duration = re.sub(
                    r"(\d+)\s*(minutes?|mins?|m)\b",
                    r"\1m",
                    duration,
                    flags=re.IGNORECASE,
                )
                duration = re.sub(
                    r"(\d+)\s*(seconds?|secs?|s)\b",
                    r"\1s",
                    duration,
                    flags=re.IGNORECASE,
                )
                duration = re.sub(r"\s*\(.*\)", "", duration)  # Remove health info
                duration = re.sub(r"\s*ago\s*", "", duration)
                status = f"{state} {duration}".strip()
```

After:
```python
                # Compact duration using shared helper
                duration = compact_duration(duration)
                status = f"{state} {duration}".strip()
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_output_filter.py -v`
Expected: All tests PASS

**Step 5: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add ctk/utils/output_filter.py tests/test_output_filter.py
git commit -m "refactor: use compact_duration helper in output_filter.py

- Replace inline duration compaction with helper function
- Removes ~15 lines of duplicated regex code"
```

---

## Layer 2: Compression Module Consolidation

### Task 2.1: Create consolidated filters module

**Files:**
- Create: `ctk/utils/filters.py`
- Test: `tests/test_filters.py`

**Step 1: Create comprehensive test file**

Create `tests/test_filters.py`:

```python
"""Tests for consolidated filtering module."""

import pytest
from ctk.utils.filters import (
    preprocess,
    filter_output,
    compress_git_status,
    compress_docker_output,
    compress_pytest_output,
    compress_nodejs_output,
)


class TestPreprocess:
    """Tests for preprocess function."""

    def test_strips_ansi_codes(self):
        output = "\x1b[32mgreen text\x1b[0m"
        result = preprocess(output)
        assert "\x1b" not in result
        assert "green text" in result

    def test_strips_box_chars(self):
        output = "┌───┐\n│ hi │\n└───┘"
        result = preprocess(output)
        assert "┌" not in result
        assert "hi" in result

    def test_collapses_empty_lines(self):
        output = "line1\n\n\n\nline2"
        result = preprocess(output)
        assert result.count("\n\n") == 0


class TestCompressGitStatus:
    """Tests for git status compression."""

    def test_modified_files(self):
        lines = ["modified:   src/app.ts", "modified:   lib/utils.py"]
        result = compress_git_status(lines)
        assert "M:src/app.ts" in result
        assert "M:lib/utils.py" in result

    def test_deleted_files(self):
        lines = ["deleted:    old_file.ts"]
        result = compress_git_status(lines)
        assert "D:old_file.ts" in result

    def test_new_files(self):
        lines = ["new file:   new_feature.ts"]
        result = compress_git_status(lines)
        assert "A:new_feature.ts" in result

    def test_untracked_files(self):
        lines = ["Untracked files:", "  file1.txt", "  file2.txt"]
        result = compress_git_status(lines)
        assert "?file1.txt" in result
        assert "?file2.txt" in result


class TestCompressDockerOutput:
    """Tests for docker output compression."""

    def test_container_id_truncated(self):
        lines = ["abc123456789   nginx   Up 2 hours   80/tcp   web"]
        result = compress_docker_output(lines)
        assert "abc1234" in result[0]
        assert "abc123456789" not in result[0]

    def test_status_compacted(self):
        lines = ["abc123456789   nginx   Up 2 hours   80/tcp   web"]
        result = compress_docker_output(lines)
        assert "U2h" in result[0] or "Up 2h" in result[0]

    def test_skips_headers(self):
        lines = ["CONTAINER ID   IMAGE   STATUS   PORTS   NAMES"]
        result = compress_docker_output(lines)
        assert len(result) == 0


class TestCompressPytestOutput:
    """Tests for pytest output compression."""

    def test_extracts_failures(self):
        lines = [
            "FAILED tests/test_foo.py::test_bar - AssertionError",
            "PASSED tests/test_foo.py::test_baz",
        ]
        result = compress_pytest_output(lines)
        assert any("FAIL" in line for line in result)

    def test_skips_passed(self):
        lines = ["PASSED tests/test_foo.py::test_bar"]
        result = compress_pytest_output(lines)
        assert len(result) == 0 or "p" in result[-1]  # Only in summary

    def test_extracts_summary(self):
        lines = ["5 passed, 2 failed in 3.42s"]
        result = compress_pytest_output(lines)
        assert any("5p" in line or "2f" in line for line in result)


class TestCompressNodejsOutput:
    """Tests for nodejs output compression."""

    def test_extracts_package_changes(self):
        lines = ["added 25 packages, removed 3 packages in 5.2s"]
        result = compress_nodejs_output(lines)
        assert any("+25" in line for line in result)

    def test_compacts_duration(self):
        lines = ["added 5 packages in 3.42s"]
        result = compress_nodejs_output(lines)
        assert any("3.42s" in line for line in result)


class TestFilterOutput:
    """Tests for full filter pipeline."""

    def test_git_category(self):
        output = "modified:   src/app.ts\nOn branch main"
        result = filter_output(output, "git")
        assert "M:" in result or "modified" in result

    def test_empty_output(self):
        result = filter_output("", "git")
        assert result == ""

    def test_preserves_errors(self):
        output = "Error: something failed\nTraceback..."
        result = filter_output(output, "python")
        assert "Error" in result
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_filters.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create the filters module**

Create `ctk/utils/filters.py` by consolidating `output_filter.py` and `patterns.py`:

```python
"""Consolidated filtering and compression for maximum token savings."""

import re
from collections import defaultdict
from difflib import SequenceMatcher

from ctk.utils.helpers import compact_duration
from ctk.utils.symbols import (
    GIT_STATUS_SYMBOLS,
    DOCKER_STATE_SYMBOLS,
    has_errors,
    symbolize_docker_state,
)


# =============================================================================
# Phase 1: Preprocessing
# =============================================================================


def preprocess(output: str) -> str:
    """Preprocess output to remove ANSI codes and normalize whitespace."""
    if not output:
        return output

    # Strip ANSI escape sequences
    output = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", output)
    output = re.sub(r"\x1b\[\?[0-9;]*[a-zA-Z]", "", output)
    output = re.sub(r"\x1b\][^\x07]*\x07", "", output)
    output = re.sub(r"\x1b[()][AB012]", "", output)

    # Strip spinner characters
    output = re.sub(r"[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]", "", output)

    # Remove Unicode box drawing characters
    box_chars = "┌┐└┘│─├┤┬┴┼╭╮╯╰═║╔╗╚╝╠╣╦╩╬"
    for char in box_chars:
        output = output.replace(char, "")

    # Normalize and collapse
    lines = [line.rstrip() for line in output.split("\n")]
    return _collapse_empty_lines(lines)


def _collapse_empty_lines(lines: list[str]) -> str:
    """Collapse consecutive empty lines into a single empty line."""
    result = []
    prev_empty = False

    for line in lines:
        is_empty = not line.strip()
        if is_empty:
            if not prev_empty:
                result.append("")
            prev_empty = True
        else:
            result.append(line)
            prev_empty = False

    # Remove leading/trailing empty lines
    while result and not result[0].strip():
        result.pop(0)
    while result and not result[-1].strip():
        result.pop()

    return "\n".join(result)


# =============================================================================
# Phase 2: Skip Patterns
# =============================================================================


SKIP_PATTERNS = [
    r"^\s*$",
    r"^=+$",
    r"^-+$",
    r"^\++$",
    r"^\*+$",
    r"^~+$",
    r"^#+$",
    r"^\s*(Using|Fetching|Downloading|Installing|Building|Compiling|Processing|Analyzing|Checking|Validating|Verifying|Resolving|Preparing|Generating|Creating|Updating|Removing|Cleaning|Unpacking|Configuring|Setting up|Fetching|Linking|Unpacking)",
    r"^\s*\d+%\s*\|.*\|",
    r"^\s*\d+%\s+complete",
    r"^\s*\[\d+/\d+\]",
    r"^\s*>\s*\d+(/\d+)?",
    r"^\s*WARN\b",
    r"^\s*INFO\b",
    r"^\s*DEBUG\b",
    r"^\s*TRACE\b",
    r"^\s*notice\b",
    r"^\s*verbose\b",
    r"^\s*Done in\s+[\d.]+[smh]?",
    r"^\s*Completed in\s+[\d.]+",
    r"^\s*Finished in\s+[\d.]+",
    r"^\s*Took\s+[\d.]+",
    r"^\s*Time:\s+[\d.]+",
    r"^\s*Duration:\s+[\d.]+",
    r"^\s*real\s+\d+m\d+",
    r"^\s*user\s+\d+m\d+",
    r"^\s*sys\s+\d+m\d+",
    r"^\s*\.{3,}$",
    r"^\s*please wait",
    r"^\s*loading",
    r"^\s*spinning up",
    r"^\s*starting\s+",
    r"^\s*initializing",
    r"^\s*running\s+",
    r"^npm warn",
    r"^npm notice",
    r"^yarn warn",
    r"^pnpm warn",
    r"^warning:",
    r"^deprecation",
    r"^deprecated",
    r"up to date",
    r"already installed",
    r"nothing to do",
    r"no changes",
    r"skipping",
    r"^\s*ok\s*$",
    r"^\s*success\s*$",
    r"^\s*pass\s*$",
    r"^\s*passed\s*$",
    r"^\s*fail\s*$",
    r"^\s*failed\s*$",
    r"^\s*error:\s*$",
    r"^\s*funding\s+message",
    r"^\s*audited\b",
    r"^\s*packages?\s*:\s*\d+",
    r"^\s*Lockfile\s+is\s+up",
    r"^added\s+\d+\s+packages",
    r"^removed\s+\d+\s+packages",
    r"^changed\s+\d+\s+packages",
    r"^\d+\s+packages\s+are\s+looking\s+for\s+funding",
    r"Compiling\s+",
    r"Finished\s+dev",
    r"Running\s+unittests",
    r"^\s*test\s+result:\s+ok",
    r"^\s*\d+\s+passed",
    r"^\s*\d+\s+tests?\s+ran",
    r"^See \`",
    r"^Run \`",
    r"^Try \`",
]

GIT_SENSITIVE_PATTERNS = [
    r"^\s*(created|deleted|modified|changed|added|removed|updated|copied|moved|renamed):",
]

CATEGORY_PATTERNS = {
    "docker": [
        r"^\s*CONTAINER ID",
        r"^\s*IMAGE\s+COMMAND",
        r"^\s*NAMESPACE",
        r"^\s*NETWORK ID",
        r"^\s*VOLUME NAME",
    ],
    "docker-compose": [
        r"^\s*NAME\s+COMMAND",
        r"Network\s+\S+\s+created",
        r"Container\s+\S+\s+(Started|Created)",
        r"^\s*Attaching to",
        r"^\s*Creating",
        r"^\s*Starting",
    ],
    "nodejs": [
        r"^\s*up to date",
        r"^\s*audited",
        r"^\s*funding",
        r"^added \d+ packages",
        r"^removed \d+ packages",
        r"^changed \d+ packages",
        r"^\s*packages:",
        r"^\s*auditing",
        r"^\s*WARN\s+\d+\s+deprecated",
        r"^Progress:\s+resolved",
        r"^Done in\s+[\d.]+s",
        r"dependencies:\s*$",
        r"devDependencies:\s*$",
        r"^\s*Lockfile",
    ],
    "python": [
        r"^\s*==",
        r"^\s*---",
        r"^collected \d+ items",
        r"^=\d+ passed",
        r"^=\d+ failed",
        r"^=\d+ skipped",
        r"^\s*PASSED\s*\[",
        r"^\s*passed\s*$",
    ],
    "git": [
        r"^\s*$",
        r"^\s*On branch",
        r"^\s*Your branch",
    ],
}


def _apply_skip_patterns(lines: list[str], category: str) -> list[str]:
    """Apply skip patterns to filter boilerplate."""
    patterns = SKIP_PATTERNS + CATEGORY_PATTERNS.get(category, [])
    if category != "git":
        patterns = patterns + GIT_SENSITIVE_PATTERNS

    filtered = []
    for line in lines:
        skip = False
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                skip = True
                break
        if not skip:
            filtered.append(line)
    return filtered


# =============================================================================
# Phase 3: Compression
# =============================================================================


def compress_git_status(lines: list[str]) -> list[str]:
    """Compress git status output using symbol grouping."""
    result = []
    status_groups: dict[str, list[str]] = defaultdict(list)
    in_untracked = False

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        if "Untracked files:" in line:
            in_untracked = True
            continue
        if "Changes to be committed:" in line or "Changes not staged for commit:" in line:
            in_untracked = False
            continue

        if re.match(r"^(On branch|Your branch|nothing to|working tree)", line_stripped):
            continue

        line_clean = re.sub(r'\s*\(use "[^"]+".*\)', "", line_stripped)

        matched = False
        for status, symbol in GIT_STATUS_SYMBOLS.items():
            if status in line_clean.lower():
                match = re.search(rf"{re.escape(status)}\s+(.+)", line_clean, re.IGNORECASE)
                if match:
                    file_path = match.group(1).strip()
                    status_groups[symbol].append(file_path)
                    matched = True
                    break

        if not matched and in_untracked:
            match = re.match(r"^\s{2,}(\S.*)$", line)
            if match:
                file_path = match.group(1).strip()
                status_groups["?"].append(file_path)

    for symbol in ["M", "A", "D", "R", "C", "T", "?"]:
        if status_groups[symbol]:
            files = ",".join(status_groups[symbol])
            result.append(f"{symbol}:{files}")

    return result


def compress_docker_output(lines: list[str]) -> list[str]:
    """Compress docker ps output to minimal format."""
    result = []

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        if re.match(r"^\s*(CONTAINER ID|REPOSITORY|NETWORK ID|VOLUME NAME|IMAGE\s+COMMAND)", line_stripped):
            continue

        parts = re.split(r"\s{2,}", line_stripped)

        if len(parts) >= 5:
            container_id = parts[0][:7] if len(parts[0]) >= 7 else parts[0]
            image = parts[1].split(":")[0] if ":" in parts[1] else parts[1]
            if len(image) > 15:
                image = image[:12] + "..."

            status_raw = parts[4] if len(parts) > 4 else ""
            status = symbolize_docker_state(status_raw)

            ports = ""
            name = parts[-1]

            if len(parts) >= 7:
                ports_raw = parts[-2]
                port_match = re.search(r"0\.0\.0\.0:(\d+)->", ports_raw)
                if port_match:
                    ports = port_match.group(1)
                elif re.search(r"->", ports_raw):
                    port_match = re.search(r":(\d+)->", ports_raw)
                    if port_match:
                        ports = port_match.group(1)

            if ports and ports != name:
                result.append(f"{container_id} {image} {status} {ports} {name}")
            else:
                result.append(f"{container_id} {image} {status} {name}")
        else:
            compressed = re.sub(r"\b([a-f0-9]{12,})\b", lambda m: m.group(1)[:7], line_stripped)
            if compressed:
                result.append(compressed)

    return result


def compress_pytest_output(lines: list[str]) -> list[str]:
    """Compress pytest output to failures and summary only."""
    result = []
    failures = []
    summary = {"passed": 0, "failed": 0, "error": 0, "skipped": 0, "duration": ""}
    in_failure = False

    for line in lines:
        if "FAILED" in line or "ERROR" in line:
            in_failure = True
            match = re.search(r"(tests?[/\w_.]+\.py)::(\w+)", line)
            if match:
                file_path = match.group(1)
                test_name = match.group(2)
                failures.append(f"FAIL:{file_path}::{test_name}")
            else:
                failures.append(line.strip())
            continue

        if in_failure:
            if line.strip() and not line.startswith(" "):
                in_failure = False
            elif line.startswith(("E ", ">", "assert")):
                failures.append(line.strip())

        if "PASSED" in line:
            continue
        if re.match(r"^tests?[/\w_.]+\s*\.+\s*\[", line):
            continue
        if re.match(r"^[\w/_.\s]+\[\s*\d+%", line):
            continue

        if "passed" in line.lower():
            match = re.search(r"(\d+)\s+passed", line)
            if match:
                summary["passed"] = int(match.group(1))
        if "failed" in line.lower():
            match = re.search(r"(\d+)\s+failed", line)
            if match:
                summary["failed"] = int(match.group(1))
        if "error" in line.lower():
            match = re.search(r"(\d+)\s+error", line)
            if match:
                summary["error"] = int(match.group(1))
        if "skipped" in line.lower():
            match = re.search(r"(\d+)\s+skipped", line)
            if match:
                summary["skipped"] = int(match.group(1))
        if re.search(r"in\s+[\d.]+s", line):
            match = re.search(r"in\s+([\d.]+)s", line)
            if match:
                summary["duration"] = match.group(1)

    result.extend(failures)

    if summary["passed"] or summary["failed"]:
        parts = []
        if summary["passed"]:
            parts.append(f"{summary['passed']}p")
        if summary["failed"]:
            parts.append(f"{summary['failed']}f")
        if summary["error"]:
            parts.append(f"{summary['error']}e")
        if summary["skipped"]:
            parts.append(f"{summary['skipped']}s")

        summary_line = " ".join(parts)
        if summary["duration"]:
            summary_line += f" | {summary['duration']}s"
        result.append(summary_line)

    return result


def compress_nodejs_output(lines: list[str]) -> list[str]:
    """Compress npm/pnpm output to minimal format."""
    result = []
    package_lines: list[str] = []
    summary = {"added": 0, "removed": 0, "changed": 0, "duration": ""}

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        if re.search(r"added\s+\d+", line_stripped, re.IGNORECASE):
            match = re.search(r"added\s+(\d+)", line_stripped, re.IGNORECASE)
            if match:
                summary["added"] = int(match.group(1))
        if re.search(r"removed\s+\d+", line_stripped, re.IGNORECASE):
            match = re.search(r"removed\s+(\d+)", line_stripped, re.IGNORECASE)
            if match:
                summary["removed"] = int(match.group(1))
        if re.search(r"changed\s+\d+", line_stripped, re.IGNORECASE):
            match = re.search(r"changed\s+(\d+)", line_stripped, re.IGNORECASE)
            if match:
                summary["changed"] = int(match.group(1))

        if re.search(r"in\s+[\d.]+s?", line_stripped):
            match = re.search(r"in\s+([\d.]+)s?", line_stripped)
            if match:
                summary["duration"] = match.group(1)

        if re.match(r"^\s*[+\-~]\s+@?[\w/-]+\s*[\d.]+", line_stripped):
            package_lines.append(line_stripped)
            continue

        if re.match(r"^\s*(Progress:|packages:|audited|auditing|WARN|Done in)", line_stripped, re.IGNORECASE):
            continue
        if re.match(r"^\s*(dependencies|devDependencies):", line_stripped, re.IGNORECASE):
            continue

    if summary["added"] or summary["removed"] or summary["changed"]:
        parts = []
        if summary["added"]:
            parts.append(f"+{summary['added']}")
        if summary["removed"]:
            parts.append(f"-{summary['removed']}")
        if summary["changed"]:
            parts.append(f"~{summary['changed']}")

        summary_line = " ".join(parts)
        if summary["duration"]:
            summary_line += f" | {summary['duration']}s"
        result.append(summary_line)

    if package_lines and len(package_lines) <= 3:
        result.extend(package_lines)
    elif package_lines:
        result.append(package_lines[0])
        result.append(f"... {len(package_lines) - 1} more")

    return result


def compress_files_output(lines: list[str]) -> list[str]:
    """Compress file command output."""
    text = "\n".join(lines)

    if re.search(r"^[d\-l][rwx\-]{9}\s", text, re.MULTILINE):
        return _compress_ls_output(lines)
    if re.search(r"^[^:]+:\d+:", text, re.MULTILINE):
        return _compress_grep_output(lines)
    if re.search(r"^(\./)?[\w/_.\-]+$", text, re.MULTILINE):
        return _compress_find_output(lines)

    return lines[:50]


def _compress_ls_output(lines: list[str]) -> list[str]:
    result = []
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("total "):
            continue
        parts = line_stripped.split()
        if len(parts) >= 6:
            perms = parts[0]
            compact_perms = perms[0] + perms[1:3] if len(perms) >= 4 else perms
            size = parts[4] if len(parts) > 4 else ""
            try:
                size_int = int(size)
                if size_int >= 1024 * 1024:
                    size = f"{size_int / (1024 * 1024):.0f}M"
                elif size_int >= 1024:
                    size = f"{size_int / 1024:.0f}K"
            except ValueError:
                pass
            name = parts[-1] if parts else ""
            result.append(f"{compact_perms} {size} {name}")
        elif line_stripped:
            result.append(line_stripped)
    return result


def _compress_grep_output(lines: list[str]) -> list[str]:
    result = []
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        match = re.match(r"^([^:]+):(\d+)?(:|$)", line_stripped)
        if match:
            file_path = match.group(1)
            line_num = match.group(2)
            if line_num:
                result.append(f"{file_path}:{line_num}")
            else:
                result.append(file_path)
        else:
            result.append(line_stripped)
    return result[:50]


def _compress_find_output(lines: list[str]) -> list[str]:
    result = []
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        path = re.sub(r"^\./", "", line_stripped)
        result.append(path)
    return result[:50]


def compress_network_output(lines: list[str]) -> list[str]:
    """Compress network command output."""
    result = []
    for line in lines:
        line_stripped = line.strip()
        if re.match(r"^\s*[%*]\s+", line):
            continue
        if re.match(r"^\s*\d+\s+\d+\s+\d+", line):
            continue
        if re.match(r"^\s*0\s+0\s+0", line):
            continue
        if re.match(r"^\s*(Trying|Connected|TLS|SSL|ALPN)", line):
            continue
        if re.match(r"^>\s+(Host|User-Agent|Accept|Content-Type)", line):
            continue
        if re.match(r"^<\s+(Date|Server|Content-Type|Transfer-Encoding)", line):
            continue
        if re.match(r"^<\s+HTTP", line):
            match = re.search(r"HTTP/[\d.]+\s+(\d+)", line)
            if match:
                result.append(f"HTTP:{match.group(1)}")
            continue
        if line_stripped and not line.startswith("<") and not line.startswith(">"):
            result.append(line_stripped)
    return result[:20]


_COMPRESSORS = {
    "git": compress_git_status,
    "docker": compress_docker_output,
    "docker-compose": compress_docker_output,
    "python": compress_pytest_output,
    "nodejs": compress_nodejs_output,
    "files": compress_files_output,
    "network": compress_network_output,
}


def _compress(lines: list[str], category: str) -> list[str]:
    """Apply category-specific compression."""
    compressor = _COMPRESSORS.get(category)
    return compressor(lines) if compressor else lines


# =============================================================================
# Phase 4: Deduplication
# =============================================================================


def _deduplicate_similar_lines(lines: list[str], threshold: float = 0.75) -> list[str]:
    """Deduplicate consecutive similar lines."""
    if len(lines) <= 1:
        return lines

    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if not line.strip() or len(line.strip()) < 15:
            result.append(line)
            i += 1
            continue

        similar_group = [line]
        j = i + 1

        while j < len(lines):
            next_line = lines[j]
            if not next_line.strip() or len(next_line.strip()) < 15:
                break
            if SequenceMatcher(None, line, next_line).ratio() >= threshold:
                similar_group.append(next_line)
                j += 1
            else:
                break

        if len(similar_group) >= 3:
            result.append(f"{line} [... {len(similar_group)} similar]")
            i = j
        else:
            result.extend(similar_group)
            i = j

    return result


# =============================================================================
# Main Pipeline
# =============================================================================


def _light_filter(lines: list[str]) -> str:
    """Light filtering for error output - preserves all error information."""
    result = [line.rstrip() for line in lines if line.rstrip()]
    return "\n".join(result)


def filter_output(output: str, category: str) -> str:
    """Apply aggressive output filtering based on category to maximize token savings.

    Processing pipeline:
    1. Preprocess: Strip ANSI codes, normalize whitespace
    2. Filter: Remove boilerplate lines based on category
    3. Compress: Apply category-specific compression
    4. Deduplicate: Compress similar consecutive lines
    """
    if not output:
        return output

    # Phase 1: Preprocess
    output = preprocess(output)
    lines = output.split("\n")

    # Safety: Check for errors - if found, use light filtering only
    if has_errors(lines):
        return _light_filter(lines)

    # Phase 2: Apply skip patterns
    lines = _apply_skip_patterns(lines, category)

    # Phase 3: Compress
    if category in _COMPRESSORS:
        lines = _compress(lines, category)
        if lines:
            result = "\n".join(lines)
            return _collapse_empty_lines(result.split("\n"))

    # Phase 4: Deduplicate (fallback)
    lines = _deduplicate_similar_lines(lines)

    result = "\n".join(lines)
    return _collapse_empty_lines(result.split("\n"))
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_filters.py -v`
Expected: All tests PASS

**Step 5: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add ctk/utils/filters.py tests/test_filters.py
git commit -m "feat: create consolidated filters module

- Merge output_filter.py and patterns.py logic
- Single 4-phase pipeline: preprocess → filter → compress → dedupe
- All compression functions in one module
- Comprehensive test coverage"
```

---

### Task 2.2: Update imports to use new filters module

**Files:**
- Modify: `ctk/cli.py`
- Modify: `ctk/utils/__init__.py`

**Step 1: Update cli.py import**

In `ctk/cli.py`, change line 16:
```python
# Before:
from .utils.output_filter import filter_output

# After:
from .utils.filters import filter_output
```

**Step 2: Update utils __init__.py**

In `ctk/utils/__init__.py`:
```python
"""CTK utilities."""

from ctk.utils.filters import filter_output
from ctk.utils.helpers import compact_duration

__all__ = ["filter_output", "compact_duration"]
```

**Step 3: Run tests**

Run: `python3 -m pytest tests/ -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add ctk/cli.py ctk/utils/__init__.py
git commit -m "refactor: update imports to use new filters module"
```

---

### Task 2.3: Remove old modules

**Files:**
- Delete: `ctk/utils/output_filter.py`
- Delete: `ctk/utils/patterns.py`

**Step 1: Verify no remaining imports**

Run: `grep -r "output_filter\|patterns" ctk/ --include="*.py"`
Expected: Only references in comments/docs

**Step 2: Delete old files**

```bash
rm ctk/utils/output_filter.py
rm ctk/utils/patterns.py
```

**Step 3: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add -A
git commit -m "refactor: remove old output_filter.py and patterns.py

Logic consolidated into ctk/utils/filters.py"
```

---

## Layer 3: Metrics DB Helper

### Task 3.1: Add time_filter helper to MetricsDB

**Files:**
- Modify: `ctk/core/metrics.py`
- Test: `tests/test_metrics.py`

**Step 1: Write test for helper**

Add to `tests/test_metrics.py`:

```python
class TestTimeFilterHelper:
    """Tests for _time_filter helper method."""

    def test_no_filter(self):
        """When days=0, return empty WHERE clause."""
        from ctk.core.metrics import MetricsDB
        db = MetricsDB()
        where, params = db._time_filter(0)
        assert where == ""
        assert params == []

    def test_filter_7_days(self):
        """When days=7, return proper WHERE clause."""
        from ctk.core.metrics import MetricsDB
        db = MetricsDB()
        where, params = db._time_filter(7)
        assert "timestamp >= datetime" in where
        assert params == ["-7 days"]

    def test_filter_30_days(self):
        """When days=30, return proper WHERE clause."""
        from ctk.core.metrics import MetricsDB
        db = MetricsDB()
        where, params = db._time_filter(30)
        assert params == ["-30 days"]
```

**Step 2: Add helper method**

In `ctk/core/metrics.py`, add to `MetricsDB` class:

```python
def _time_filter(self, days: int) -> tuple[str, list[Any]]:
    """Build WHERE clause and params for time-based filtering.

    Args:
        days: Number of days to filter (0 = all time)

    Returns:
        Tuple of (where_clause, params)
    """
    if days > 0:
        return "WHERE timestamp >= datetime('now', ?)", [f"-{days} days"]
    return "", []
```

**Step 3: Update get_summary**

Replace lines 82-86:
```python
# Before:
where = ""
params: list[Any] = []
if days > 0:
    where = "WHERE timestamp >= datetime('now', ?)"
    params = [f"-{days} days"]

# After:
where, params = self._time_filter(days)
```

**Step 4: Update get_top_commands**

Replace lines 146-150:
```python
# Before:
where = ""
params: list[Any] = []
if days > 0:
    where = "WHERE timestamp >= datetime('now', ?)"
    params = [f"-{days} days"]

# After:
where, params = self._time_filter(days)
```

**Step 5: Update get_top_savers**

Replace lines 177-181:
```python
# Before:
where = ""
params: list[Any] = []
if days > 0:
    where = "WHERE timestamp >= datetime('now', ?)"
    params = [f"-{days} days"]

# After:
where, params = self._time_filter(days)
```

**Step 6: Update get_by_category**

Replace lines 208-212:
```python
# Before:
where = ""
params: list[Any] = []
if days > 0:
    where = "WHERE timestamp >= datetime('now', ?)"
    params = [f"-{days} days"]

# After:
where, params = self._time_filter(days)
```

**Step 7: Run tests**

Run: `python3 -m pytest tests/test_metrics.py -v`
Expected: All tests PASS

**Step 8: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All tests PASS

**Step 9: Commit**

```bash
git add ctk/core/metrics.py tests/test_metrics.py
git commit -m "refactor: extract _time_filter helper in MetricsDB

- Reduces duplicated time-filter logic across 4 methods
- ~12 lines saved, improved consistency"
```

---

## Layer 4: CLI Command Registry

### Task 4.1: Create command registry

**Files:**
- Modify: `ctk/cli.py`
- Test: `tests/test_cli.py`

**Step 1: Write tests for registry**

Add to `tests/test_cli.py`:

```python
class TestCommandRegistry:
    """Tests for command registry pattern."""

    def test_registry_has_docker_commands(self):
        from ctk.cli import COMMAND_REGISTRY
        docker_commands = [(g, c) for (g, c) in COMMAND_REGISTRY.keys() if g == "docker"]
        assert ("docker", "ps") in docker_commands
        assert ("docker", "images") in docker_commands
        assert ("docker", "logs") in docker_commands

    def test_registry_has_git_commands(self):
        from ctk.cli import COMMAND_REGISTRY
        git_commands = [(g, c) for (g, c) in COMMAND_REGISTRY.keys() if g == "git"]
        assert ("git", "status") in git_commands
        assert ("git", "log") in git_commands
        assert ("git", "diff") in git_commands

    def test_registry_has_ungrouped_commands(self):
        from ctk.cli import COMMAND_REGISTRY
        ungrouped = [(g, c) for (g, c) in COMMAND_REGISTRY.keys() if g == ""]
        assert ("", "npm") in ungrouped
        assert ("", "pip") in ungrouped

    def test_all_registered_commands_callable(self):
        """All commands in registry can be invoked."""
        from ctk.cli import cli, COMMAND_REGISTRY
        from click.testing import CliRunner
        runner = CliRunner()

        for (group, cmd), (_, category) in COMMAND_REGISTRY.items():
            if group:
                args = [group, cmd, "--help"]
            else:
                args = [cmd, "--help"]
            # Should not raise
            result = runner.invoke(cli, args)
            assert result.exit_code == 0 or "No such command" not in result.output
```

**Step 2: Add registry to cli.py**

Add after `CONTEXT_SETTINGS` definition (around line 27):

```python
# Command registry - single source of truth for proxy commands
# Format: (group, command): (cmd_template, category)
COMMAND_REGISTRY = {
    # Docker commands
    ("docker", "ps"): ("docker ps ", "docker"),
    ("docker", "images"): ("docker images ", "docker"),
    ("docker", "logs"): ("docker logs ", "docker"),
    ("docker", "exec"): ("docker exec ", "docker"),
    ("docker", "run"): ("docker run ", "docker"),
    ("docker", "build"): ("docker build ", "docker"),
    ("docker", "network"): ("docker network ", "docker"),
    ("docker", "volume"): ("docker volume ", "docker"),
    ("docker", "system"): ("docker system ", "docker"),

    # Docker Compose commands
    ("docker-compose", "ps"): ("docker compose ps ", "docker-compose"),
    ("docker-compose", "logs"): ("docker compose logs ", "docker-compose"),
    ("docker-compose", "up"): ("docker compose up ", "docker-compose"),
    ("docker-compose", "down"): ("docker compose down ", "docker-compose"),
    ("docker-compose", "exec"): ("docker compose exec ", "docker-compose"),

    # Git commands
    ("git", "status"): ("git status ", "git"),
    ("git", "diff"): ("git diff ", "git"),
    ("git", "log"): ("git log --oneline ", "git"),
    ("git", "add"): ("git add ", "git"),
    ("git", "commit"): ("git commit ", "git"),
    ("git", "push"): ("git push ", "git"),
    ("git", "pull"): ("git pull ", "git"),
    ("git", "branch"): ("git branch -a ", "git"),
    ("git", "remote"): ("git remote -v ", "git"),
    ("git", "stash"): ("git stash list ", "git"),
    ("git", "tag"): ("git tag ", "git"),

    # File commands
    ("", "ls"): ("ls ", "files"),
    ("", "tree"): ("tree ", "files"),
    ("", "grep"): ("grep ", "files"),
    ("", "find"): ("find ", "files"),
    ("", "du"): ("du ", "files"),
    ("", "wc"): ("wc ", "files"),
    ("", "stat"): ("stat ", "files"),
    ("", "file"): ("file ", "files"),
    ("", "sed"): ("sed ", "files"),
    ("", "jq"): ("jq ", "files"),

    # Python commands
    ("", "pytest"): ("pytest  -q --tb=short 2>&1", "python"),
    ("", "ruff"): ("ruff ", "python"),
    ("", "pip"): ("pip ", "python"),

    # Node.js commands
    ("", "npm"): ("npm ", "nodejs"),
    ("", "pnpm"): ("pnpm ", "nodejs"),
    ("", "vitest"): ("npx vitest run --reporter=verbose 2>&1", "nodejs"),
    ("", "tsc"): ("npx tsc --pretty 2>&1", "nodejs"),
    ("", "lint"): ("npx eslint --format compact 2>&1", "nodejs"),
    ("", "prettier"): ("npx prettier ", "nodejs"),

    # Network commands
    ("", "curl"): ("curl -s ", "network"),
    ("", "wget"): ("wget -q ", "network"),
    ("", "ip"): ("ip ", "network"),
    ("", "ss"): ("ss -tuln ", "network"),
    ("", "gh"): ("gh ", "gh"),

    # System commands
    ("", "ps"): ("ps aux --sort=-%mem | head -20", "system"),
    ("", "free"): ("free -h", "system"),
    ("", "df"): ("df -h ", "system"),
    ("", "uname"): ("uname -a", "system"),
    ("", "env"): ("env | head -30", "system"),
    ("", "which"): ("which ", "system"),
    ("", "id"): ("id", "system"),
    ("", "pwd"): ("pwd", "system"),
    ("", "hostname"): ("hostname", "system"),
    ("", "uptime"): ("uptime", "system"),
    ("", "apt"): ("apt ", "system"),
    ("", "sqlite3"): ("sqlite3 ", "system"),
}


def _make_proxy_handler(cmd_template: str, category: str):
    """Factory function to create proxy command handlers."""
    def handler(args: tuple[str, ...] = ()):
        _run_command(cmd_template + " ".join(args), category)
    return handler
```

**Step 3: Run tests**

Run: `python3 -m pytest tests/test_cli.py::TestCommandRegistry -v`
Expected: Tests PASS

**Step 4: Commit**

```bash
git add ctk/cli.py tests/test_cli.py
git commit -m "feat: add COMMAND_REGISTRY for proxy commands

- Central registry of all proxy commands
- Factory function for creating handlers
- Tests for registry structure"
```

---

### Task 4.2: Replace duplicate commands with registry

**Files:**
- Modify: `ctk/cli.py`

**Step 1: Create register_commands function**

Add after `_make_proxy_handler`:

```python
def _register_proxy_commands():
    """Register all proxy commands from the registry."""
    groups: dict[str, click.Group] = {}

    for (group_name, cmd_name), (cmd_template, category) in COMMAND_REGISTRY.items():
        # Create group if needed
        if group_name and group_name not in groups:
            groups[group_name] = click.Group(
                name=group_name,
                context_settings=CONTEXT_SETTINGS,
            )
            cli.add_command(groups[group_name], name=group_name)

        # Create command
        handler = _make_proxy_handler(cmd_template, category)
        handler = click.argument("args", nargs=-1)(handler)

        cmd = click.command(
            cmd_name,
            context_settings=CONTEXT_SETTINGS,
        )(handler)

        # Add to group or CLI
        if group_name:
            groups[group_name].add_command(cmd)
        else:
            cli.add_command(cmd)


# Auto-register on import
_register_proxy_commands()
```

**Step 2: Remove duplicate command definitions**

Remove these functions (approximately lines 386-738):
- `docker_ps`, `docker_images`, `docker_logs`, `docker_exec`, `docker_run`, `docker_build`
- `compose_ps`, `compose_logs`, `compose_up`, `compose_down`, `compose_exec`
- `git_status`, `git_diff`, `git_log`, `git_add`, `git_commit`, `git_push`, `git_pull`
- `git_branch`, `git_remote`, `git_stash`, `git_tag`
- `ps_command`, `free_command`, `date_command`, `whoami_command`
- `ls_command`, `tree_command`, `grep_command`, `find_command`, `du_command`
- `pytest_command`, `ruff_command`, `pip_command`
- `npm_command`, `pnpm_command`, `vitest_command`, `tsc_command`, `lint_command`, `prettier_command`
- `gh_command`, `curl_command`, `wget_command`
- `df_command`, `uname_command`, `hostname_command`, `uptime_command`, `env_command`, `which_command`, `history_command`, `id_command`
- `wc_command`, `stat_command`, `file_command`
- `docker_network`, `docker_volume`, `docker_system`
- `ip_command`, `ss_command`, `ping_command`
- `pwd_command`, `sed_command`, `jq_command`, `apt_command`, `sqlite3_command`

**Keep these custom commands:**
- `gain` - complex analytics
- `discover` - analysis command
- `proxy_command` - raw execution
- `config_command` - configuration
- `read_command`, `tail_command`, `cat_command` - custom options
- `ping_command` - custom options

**Step 3: Keep the docker and git group decorators**

Keep these empty group definitions:
```python
@cli.group(context_settings=CONTEXT_SETTINGS)
def docker():
    """Docker commands with compact output."""
    pass


@cli.group(context_settings=CONTEXT_SETTINGS)
def git():
    """Git commands with compact output."""
    pass
```

**Step 4: Run tests**

Run: `python3 -m pytest tests/ -v`
Expected: All tests PASS

**Step 5: Verify CLI still works**

Run: `python3 -m ctk --help`
Run: `python3 -m ctk docker --help`
Run: `python3 -m ctk git --help`

**Step 6: Commit**

```bash
git add ctk/cli.py
git commit -m "refactor: replace ~40 duplicate commands with registry pattern

- Remove individual command functions
- Use _register_proxy_commands() to auto-register
- Keep custom commands with special options
- Reduces cli.py by ~600 lines"
```

---

## Layer 5: Legacy Cleanup

### Task 5.1: Remove backward compatibility aliases

**Files:**
- Modify: `ctk/cli.py`
- Modify: `ctk/core/rewriter.py`
- Modify: `tests/` (update any tests using old APIs)

**Step 1: Find and update test references**

Run: `grep -r "_filter_output\|COMMAND_PATTERNS" tests/ --include="*.py"`

Update any tests to use:
- `filter_output` instead of `_filter_output`
- `COMMAND_CATEGORIES` instead of `COMMAND_PATTERNS`

**Step 2: Remove _filter_output alias**

In `ctk/cli.py`, remove line ~789:
```python
# DELETE:
_filter_output = filter_output
```

**Step 3: Update discover command import**

In `ctk/cli.py`, update line ~15:
```python
# Before:
from .core.rewriter import COMMAND_PATTERNS, should_rewrite_command

# After:
from .core.rewriter import COMMAND_CATEGORIES, should_rewrite_command
```

**Step 4: Update discover command usage**

In `_analyze_history_dir()`, update line ~339:
```python
# Before:
for category, config in COMMAND_PATTERNS.items():
    for pattern, _ in config["patterns"]:

# After:
for category, cat_config in COMMAND_CATEGORIES.items():
    for pattern, _ in cat_config.patterns:
```

**Step 5: Remove COMMAND_PATTERNS from rewriter.py**

In `ctk/core/rewriter.py`, remove lines ~248-255:
```python
# DELETE:
COMMAND_PATTERNS = {
    name: {
        "patterns": [(p.pattern, label) for p, label in cat.patterns],
        "subcommands": cat.subcommands,
    }
    for name, cat in COMMAND_CATEGORIES.items()
}
```

**Step 6: Run tests**

Run: `python3 -m pytest tests/ -v`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add ctk/cli.py ctk/core/rewriter.py tests/
git commit -m "refactor: remove legacy compatibility aliases

- Remove _filter_output alias from cli.py
- Remove COMMAND_PATTERNS from rewriter.py
- Update tests to use new API"
```

---

## Final Verification

### Task 6.1: Run complete test suite

**Step 1: Run all tests**

Run: `python3 -m pytest tests/ -v --cov=ctk --cov-report=term-missing`
Expected: All tests PASS, coverage >90%

**Step 2: Verify real commands work**

```bash
python3 -m ctk git status
python3 -m ctk docker ps
python3 -m ctk --help
python3 -m ctk gain
```

**Step 3: Check code reduction**

Run: `find ctk -name "*.py" -exec wc -l {} + | tail -1`
Compare to original ~3100 lines

### Task 6.2: Final commit

```bash
git add -A
git commit -m "refactor: complete CTK codebase consolidation

Summary:
- Layer 1: Added compact_duration helper (removes 3 duplications)
- Layer 2: Consolidated output_filter.py + patterns.py → filters.py
- Layer 3: Added _time_filter helper to MetricsDB
- Layer 4: Replaced ~40 CLI commands with registry pattern
- Layer 5: Removed legacy compatibility aliases

Total reduction: ~1000 lines (32%)
All tests pass with >90% coverage"
```

---

## Success Criteria

- [ ] All existing tests pass
- [ ] New tests achieve >90% coverage on changed code
- [ ] Real commands produce identical output
- [ ] No regression in token savings percentage
- [ ] Codebase reduced by ~30% (~1000 lines)
