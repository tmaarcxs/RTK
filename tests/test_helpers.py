"""Tests for shared utility helpers."""

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


class TestSymbolizeDockerStateUsesHelper:
    """Verify symbolize_docker_state uses compact_duration helper."""

    def test_uses_compact_duration(self):
        from ctk.utils.symbols import symbolize_docker_state

        # These should work the same as compact_duration
        assert "2h" in symbolize_docker_state("Up 2 hours")
        assert "3d" in symbolize_docker_state("Up 3 days")

    def test_removes_parenthetical(self):
        from ctk.utils.symbols import symbolize_docker_state

        # Exited with exit code should be compacted
        result = symbolize_docker_state("Exited (0) 3 days ago")
        assert "3d" in result
        assert "(0)" not in result

    def test_exited_state(self):
        from ctk.utils.symbols import symbolize_docker_state

        result = symbolize_docker_state("Exited (1) 2 hours ago")
        assert result.startswith("X")
        assert "2h" in result
