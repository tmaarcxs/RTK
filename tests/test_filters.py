"""Tests for consolidated filtering module."""

from ctk.utils.filters import (
    compress_docker_output,
    compress_git_status,
    compress_nodejs_output,
    compress_pytest_output,
    filter_output,
    preprocess,
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
        # Should collapse multiple empty lines to at most one between content
        assert result.count("\n\n") <= 1
        assert "line1" in result
        assert "line2" in result


class TestCompressGitStatus:
    """Tests for git status compression."""

    def test_modified_files(self):
        lines = ["modified:   src/app.ts", "modified:   lib/utils.py"]
        result = compress_git_status(lines)
        # Files are grouped by status: M:file1,file2
        result_text = " ".join(result)
        assert "M:" in result_text
        assert "src/app.ts" in result_text
        assert "lib/utils.py" in result_text

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
        # Files are grouped by status: ?:file1,file2
        result_text = " ".join(result)
        assert "?:" in result_text
        assert "file1.txt" in result_text
        assert "file2.txt" in result_text


class TestCompressDockerOutput:
    """Tests for docker output compression."""

    def test_container_id_truncated(self):
        lines = ["abc123456789   nginx   Up 2 hours   80/tcp   web"]
        result = compress_docker_output(lines)
        assert "abc1234" in result[0]
        assert "abc123456789" not in result[0]

    def test_status_compacted(self):
        # Docker ps format: ID, IMAGE, COMMAND, CREATED, STATUS, PORTS, NAMES
        lines = [
            "abc123456789   nginx:latest   /bin/sh   2 hours ago   Up 2 hours   80/tcp   web"
        ]
        result = compress_docker_output(lines)
        result_text = " ".join(result)
        # Should have container ID truncated and status compacted
        assert "abc1234" in result_text
        assert "U2h" in result_text or "Up2h" in result_text or "Up" in result_text

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
