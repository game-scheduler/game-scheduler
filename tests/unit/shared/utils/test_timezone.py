# Copyright 2025-2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""Tests for timezone utility functions."""

from datetime import UTC, datetime

from shared.utils.timezone import (
    from_iso_string,
    from_unix_timestamp,
    to_iso_string,
    to_unix_timestamp,
    to_utc,
    utcnow,
)


def test_utcnow():
    """Test utcnow returns current UTC datetime with timezone info."""
    now = utcnow()
    assert now.tzinfo == UTC
    assert isinstance(now, datetime)


def test_to_utc_naive_datetime():
    """Test converting naive datetime to UTC."""
    naive_dt = datetime(2025, 11, 15, 19, 0, 0)
    utc_dt = to_utc(naive_dt)

    assert utc_dt.tzinfo == UTC
    assert utc_dt.year == 2025
    assert utc_dt.month == 11
    assert utc_dt.day == 15
    assert utc_dt.hour == 19


def test_to_utc_aware_datetime():
    """Test converting timezone-aware datetime to UTC."""
    aware_dt = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)
    utc_dt = to_utc(aware_dt)

    assert utc_dt.tzinfo == UTC
    assert utc_dt == aware_dt


def test_to_unix_timestamp():
    """Test converting datetime to Unix timestamp."""
    dt = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)
    timestamp = to_unix_timestamp(dt)

    assert isinstance(timestamp, int)
    assert timestamp == 1763233200


def test_to_unix_timestamp_naive():
    """Test converting naive datetime to Unix timestamp."""
    dt = datetime(2025, 11, 15, 19, 0, 0)
    timestamp = to_unix_timestamp(dt)

    assert isinstance(timestamp, int)
    assert timestamp == 1763233200


def test_from_unix_timestamp():
    """Test converting Unix timestamp to datetime."""
    timestamp = 1763233200
    dt = from_unix_timestamp(timestamp)

    assert dt.tzinfo == UTC
    assert dt.year == 2025
    assert dt.month == 11
    assert dt.day == 15
    assert dt.hour == 19
    assert dt.minute == 0


def test_to_iso_string():
    """Test converting datetime to ISO 8601 string."""
    dt = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)
    iso_str = to_iso_string(dt)

    assert iso_str == "2025-11-15T19:00:00Z"


def test_to_iso_string_naive():
    """Test converting naive datetime to ISO 8601 string."""
    dt = datetime(2025, 11, 15, 19, 0, 0)
    iso_str = to_iso_string(dt)

    assert iso_str == "2025-11-15T19:00:00Z"


def test_from_iso_string_with_z():
    """Test parsing ISO 8601 string with Z suffix."""
    iso_str = "2025-11-15T19:00:00Z"
    dt = from_iso_string(iso_str)

    assert dt.tzinfo == UTC
    assert dt.year == 2025
    assert dt.month == 11
    assert dt.day == 15
    assert dt.hour == 19


def test_from_iso_string_with_offset():
    """Test parsing ISO 8601 string with UTC offset."""
    iso_str = "2025-11-15T19:00:00+00:00"
    dt = from_iso_string(iso_str)

    assert dt.tzinfo == UTC
    assert dt.year == 2025
    assert dt.month == 11
    assert dt.day == 15
    assert dt.hour == 19


def test_roundtrip_iso_string():
    """Test ISO string roundtrip conversion."""
    original_dt = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)
    iso_str = to_iso_string(original_dt)
    parsed_dt = from_iso_string(iso_str)

    assert parsed_dt == original_dt


def test_roundtrip_unix_timestamp():
    """Test Unix timestamp roundtrip conversion."""
    original_dt = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)
    timestamp = to_unix_timestamp(original_dt)
    parsed_dt = from_unix_timestamp(timestamp)

    assert parsed_dt == original_dt
