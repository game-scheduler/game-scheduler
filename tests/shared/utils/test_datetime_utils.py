# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""Unit tests for datetime formatting utilities."""

from datetime import UTC, datetime

from shared.utils import datetime_utils


def test_format_datetime_as_utc_basic():
    """Test basic datetime formatting with Z suffix."""
    dt = datetime(2025, 12, 20, 15, 30, 45)
    result = datetime_utils.format_datetime_as_utc(dt)
    assert result == "2025-12-20T15:30:45Z"


def test_format_datetime_as_utc_midnight():
    """Test midnight UTC is not offset (critical bug fix verification)."""
    dt = datetime(2025, 11, 27, 0, 15, 0)
    result = datetime_utils.format_datetime_as_utc(dt)
    assert result == "2025-11-27T00:15:00Z"


def test_format_datetime_as_utc_end_of_day():
    """Test end of day formatting."""
    dt = datetime(2025, 12, 31, 23, 59, 59)
    result = datetime_utils.format_datetime_as_utc(dt)
    assert result == "2025-12-31T23:59:59Z"


def test_format_datetime_as_utc_various_times():
    """Test various times are consistently formatted."""
    test_cases = [
        (datetime(2025, 11, 27, 0, 0, 0), "2025-11-27T00:00:00Z"),
        (datetime(2025, 11, 27, 6, 30, 0), "2025-11-27T06:30:00Z"),
        (datetime(2025, 11, 27, 12, 0, 0), "2025-11-27T12:00:00Z"),
        (datetime(2025, 11, 27, 18, 45, 0), "2025-11-27T18:45:00Z"),
        (datetime(2025, 11, 27, 23, 59, 59), "2025-11-27T23:59:59Z"),
    ]

    for dt, expected in test_cases:
        result = datetime_utils.format_datetime_as_utc(dt)
        assert result == expected, f"Failed for {dt}"


def test_format_datetime_as_utc_parseable():
    """Test that output can be parsed back correctly."""
    dt = datetime(2025, 11, 27, 0, 15, 0)
    result = datetime_utils.format_datetime_as_utc(dt)

    # Verify the formatted string can be parsed back
    parsed_dt = datetime.fromisoformat(result.replace("Z", "+00:00"))
    assert parsed_dt.hour == 0
    assert parsed_dt.minute == 15

    # Verify Unix timestamp is correct
    computed_unix = int(parsed_dt.timestamp())
    expected_unix = int(datetime(2025, 11, 27, 0, 15, 0, tzinfo=UTC).timestamp())
    assert computed_unix == expected_unix


def test_format_datetime_as_utc_always_has_z_suffix():
    """Verify all formatted datetimes end with 'Z'."""
    test_datetimes = [
        datetime(2025, 1, 1, 0, 0, 0),
        datetime(2025, 6, 15, 12, 30, 45),
        datetime(2025, 12, 31, 23, 59, 59),
    ]

    for dt in test_datetimes:
        result = datetime_utils.format_datetime_as_utc(dt)
        assert result.endswith("Z"), f"Missing Z suffix for {dt}"
        assert "+00:00" not in result, f"Should not have +00:00 for {dt}"
