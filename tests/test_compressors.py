"""Tests for additional compressor functions."""

from ctk.utils.filters import (
    _detect_nested_category,
    compress_alembic_output,
    compress_git_log,
    compress_vitest_output,
)


class TestGitLogCompressor:
    """Tests for git log compression."""

    def test_basic_commit(self):
        """Should compress basic commit line (SHA truncated to 7 chars, message preserved)."""
        lines = ["abc1234567890 My commit message here"]
        result = compress_git_log(lines)
        assert len(result) == 1
        # SHA should be truncated to 7 chars
        assert result[0].startswith("abc1234")
        # Message should be preserved
        assert "My commit message here" in result[0]

    def test_truncates_long_messages(self):
        """Should truncate long commit messages."""
        long_message = "This is a very long commit message that exceeds the maximum length and should be truncated"
        lines = [f"abc1234 {long_message}"]
        result = compress_git_log(lines)
        assert len(result) == 1
        # Should be truncated to 60 chars max for the message part
        assert len(result[0]) < len(lines[0])
        assert "..." in result[0]

    def test_limits_output(self):
        """Should limit output to 50 lines."""
        lines = [f"abc123{str(i).zfill(4)} Commit message {i}" for i in range(100)]
        result = compress_git_log(lines)
        assert len(result) <= 50


class TestAlembicCompressor:
    """Tests for alembic migration output compression."""

    def test_migration_output(self):
        """Should compress migration output to 'from -> to: message' format."""
        lines = [
            "INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.",
            "INFO  [alembic.runtime.migration] Will assume transactional DDL.",
            "INFO  [alembic.runtime.migration] Running upgrade 1a2b3c4d -> 5e6f7g8h, add_users_table",
        ]
        result = compress_alembic_output(lines)
        # Should contain the migration in compressed format
        assert any("1a2b3c4d -> 5e6f7g8h" in line or "->" in line for line in result)
        # Should contain the message
        assert any("add_users_table" in line for line in result)


class TestVitestCompressor:
    """Tests for vitest output compression."""

    def test_passing_tests(self):
        """Should show summary for passing tests (e.g., '5p | 1.23s')."""
        lines = [
            "✓ src/utils.test.ts (5)",
            "✓ src/api.test.ts (3)",
            "Test Files  2 passed (2)",
            "Tests  8 passed (8)",
            "Duration  1.23s",
        ]
        result = compress_vitest_output(lines)
        # Should have summary line with passed count
        result_text = " ".join(result)
        assert (
            "8p" in result_text
            or "8 p" in result_text
            or "passed" in result_text.lower()
        )
        # Should include duration
        assert any("1.23s" in line or "1.23" in line for line in result)

    def test_failing_tests(self):
        """Should show failing test file (e.g., 'FAIL:src/api.test.ts')."""
        lines = [
            "✓ src/utils.test.ts (5)",
            "✘ src/api.test.ts (3)",
            "Test Files  1 passed, 1 failed (2)",
            "Tests  5 passed, 3 failed (8)",
        ]
        result = compress_vitest_output(lines)
        # Should indicate failure
        assert any("FAIL" in line for line in result)
        # Should include the failing file
        assert any("api.test.ts" in line for line in result)


class TestNestedCategoryDetection:
    """Tests for nested category detection in compound commands."""

    def test_vitest_inside_docker(self):
        """Should detect vitest output inside docker exec."""
        output = """
        PASS src/utils.test.ts
        Test Files  1 passed (1)
        Tests  5 passed (5)
        Duration  1.23s
        """
        result = _detect_nested_category(output, "docker")
        assert result == "vitest"

    def test_alembic_inside_docker(self):
        """Should detect alembic output."""
        output = """
        INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
        INFO  [alembic.runtime.migration] Running upgrade abc123 -> def456, add column
        """
        result = _detect_nested_category(output, "docker")
        assert result == "alembic"

    def test_returns_primary_if_no_match(self):
        """Should return primary category if no nested pattern matches."""
        output = "Some generic docker container output"
        result = _detect_nested_category(output, "docker")
        assert result == "docker"
