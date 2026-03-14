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


"""Tests for base model utilities."""

from datetime import UTC, datetime

from shared.models.base import generate_uuid, utc_now


def test_utc_now_returns_timezone_naive_datetime():
    """Verify utc_now returns timezone-naive datetime in UTC."""
    now = utc_now()

    assert isinstance(now, datetime)
    assert now.tzinfo is None

    # Verify it's reasonably close to current time
    utc_aware_now = datetime.now(UTC)
    diff = abs((utc_aware_now.replace(tzinfo=None) - now).total_seconds())
    assert diff < 1.0


def test_utc_now_consistent_timing():
    """Verify multiple calls to utc_now are consistent."""
    time1 = utc_now()
    time2 = utc_now()

    assert time1.tzinfo is None
    assert time2.tzinfo is None
    assert time2 >= time1


def test_generate_uuid_returns_string():
    """Verify generate_uuid returns a valid UUID string."""
    uuid = generate_uuid()

    assert isinstance(uuid, str)
    assert len(uuid) == 36
    assert uuid.count("-") == 4


def test_generate_uuid_unique():
    """Verify generate_uuid returns unique values."""
    uuid1 = generate_uuid()
    uuid2 = generate_uuid()

    assert uuid1 != uuid2
