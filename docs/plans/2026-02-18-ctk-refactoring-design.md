# CTK Refactoring Design

**Date:** 2026-02-18
**Goal:** Maximum code reduction with full test coverage and real command verification

## Summary

Refactor CTK to eliminate ~1000 lines of duplicated code while maintaining 100% functionality.

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| `cli.py` | ~1050 lines | ~450 lines | 57% |
| `output_filter.py` + `patterns.py` | ~1420 lines | ~1020 lines | 28% |
| Total Python | ~3100 lines | ~2100 lines | 32% |

## Approach: Layered Refactoring

Refactor in layers from bottom-up, ensuring each layer is tested before moving up.

## Layer 1: Shared Utilities

Create `ctk/utils/helpers.py` for shared utility functions.

### `compact_duration()`

Single function to replace 3 duplicated implementations:

```python
def compact_duration(duration: str) -> str:
    """Compact duration strings to minimal format.

    "2 hours" -> "2h", "3 days ago" -> "3d"
    """
    patterns = [
        (r"(\d+)\s*weeks?", r"\1w"),
        (r"(\d+)\s*days?", r"\1d"),
        (r"(\d+)\s*hours?|hrs?", r"\1h"),
        (r"(\d+)\s*minutes?|mins?", r"\1m"),
        (r"(\d+)\s*seconds?|secs?", r"\1s"),
    ]
    for pattern, replacement in patterns:
        duration = re.sub(pattern, replacement, duration, flags=re.IGNORECASE)
    return re.sub(r"\s*\(.*\)", "", duration).replace(" ago", "")
```

**Files changed:**
- Create `ctk/utils/helpers.py`
- Update `symbols.py:289-295` to use `compact_duration()`
- Update `output_filter.py:347-364` to use `compact_duration()`

## Layer 2: Compression Module Consolidation

Merge `output_filter.py` and `patterns.py` into single module.

### New Structure

```
ctk/utils/
├── helpers.py      # Shared utilities (from Layer 1)
├── symbols.py      # Symbol dictionaries (unchanged)
├── filters.py      # Combined filtering + compression (new)
└── tokenizer.py    # Token estimation (unchanged)
```

### Consolidation Map

| Current Function | Action |
|-----------------|--------|
| `output_filter.py::compact_git_status()` | Remove - use `compress_git_status()` |
| `output_filter.py::compact_docker_output()` | Remove - use `compress_docker_output()` |
| `output_filter.py::compact_pytest_output()` | Merge into `compress_pytest_output()` |
| `output_filter.py::compact_nodejs_output()` | Merge into `compress_nodejs_output()` |
| `patterns.py::compress_*` | Keep as primary implementations |

### Single Pipeline

```python
def filter_output(output: str, category: str) -> str:
    """4-phase filtering pipeline."""
    # Phase 1: Preprocess (strip ANSI, normalize)
    output = preprocess(output)

    # Phase 2: Skip patterns (remove boilerplate)
    lines = apply_skip_patterns(output, category)

    # Phase 3: Compress (category-specific)
    lines = compress(lines, category)

    # Phase 4: Deduplicate (similar lines)
    return deduplicate(lines)
```

## Layer 3: Metrics DB Helper

Extract repeated time-filter pattern into helper method.

### Before (repeated 4 times)

```python
where = ""
params = []
if days > 0:
    where = "WHERE timestamp >= datetime('now', ?)"
    params = [f"-{days} days"]
```

### After

```python
def _time_filter(self, days: int) -> tuple[str, list[Any]]:
    """Build WHERE clause and params for time-based filtering."""
    if days > 0:
        return "WHERE timestamp >= datetime('now', ?)", [f"-{days} days"]
    return "", []
```

**Methods updated:**
- `get_summary()`
- `get_top_commands()`
- `get_top_savers()`
- `get_by_category()`

## Layer 4: CLI Command Registry

Replace ~40 duplicate command functions with registry pattern.

### Registry Structure

```python
COMMAND_REGISTRY = {
    # (group, command): (cmd_template, category)
    ("docker", "ps"): ("docker ps ", "docker"),
    ("docker", "images"): ("docker images ", "docker"),
    ("git", "status"): ("git status ", "git"),
    ("git", "log"): ("git log --oneline ", "git"),
    ("", "npm"): ("npm ", "nodejs"),
    # ... ~40 total commands
}

def register_commands():
    """Auto-register all commands from registry."""
    # Dynamic command generation
```

### Special Cases (keep as explicit functions)

- `gain` - complex analytics command
- `discover` - analysis command
- `proxy` - raw execution
- `config` - configuration management
- `read`, `tail`, `cat`, `ping`, `history`, `env` - custom options

## Layer 5: Legacy Cleanup

### Removals

1. **`cli.py:789`** - Remove `_filter_output` alias
2. **`rewriter.py:248-255`** - Remove `COMMAND_PATTERNS` legacy dict
3. **`filters.py`** - Remove `postprocess_output()` after consolidation

## Test Strategy

### Test-First Approach

For each layer:
1. Write comprehensive tests for current behavior
2. Run tests to establish baseline
3. Refactor code
4. Ensure tests still pass
5. Add new tests for new code paths

### Test Files

| Layer | Test File | Coverage |
|-------|-----------|----------|
| 1 | `tests/test_helpers.py` | Duration compaction |
| 2 | `tests/test_filters.py` | Compression functions, pipeline |
| 3 | `tests/test_metrics.py` | Time filtering, queries |
| 4 | `tests/test_cli.py` | Registry, command execution |
| 5 | `tests/test_legacy.py` | Ensure clean API |

### Integration Tests

- Real `git status` execution
- Real `docker ps` execution (if docker available)
- Compare filtered vs unfiltered output tokens

## Execution Order

1. **Layer 1** - Shared utilities (low risk)
2. **Layer 2** - Compression consolidation (medium risk)
3. **Layer 3** - Metrics helper (low risk)
4. **Layer 4** - CLI registry (high risk, high reward)
5. **Layer 5** - Legacy cleanup (low risk)

## Rollback Strategy

Each layer is committed independently. If issues arise:
1. Revert specific layer commit
2. Previous layers remain intact and functional
3. Can pause between layers

## Success Criteria

- [ ] All existing tests pass
- [ ] New tests achieve >90% coverage on changed code
- [ ] Real commands produce identical output (verified manually)
- [ ] No regression in token savings percentage
- [ ] Codebase reduced by ~30%
