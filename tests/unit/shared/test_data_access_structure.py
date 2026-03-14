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


"""Tests for data_access module structure.

Verifies that the guild-scoped query wrapper module structure is correctly set up
and can be imported. This is the foundation test for Task 1.1.
"""

import shared.data_access
import shared.data_access.guild_queries
from shared.data_access import guild_queries


def test_data_access_module_imports():
    """Verify data_access module and submodules can be imported."""
    assert hasattr(shared.data_access, "guild_queries")
    assert shared.data_access.guild_queries.__doc__ is not None


def test_guild_queries_module_structure():
    """Verify guild_queries module has correct structure and documentation."""
    assert guild_queries.__name__ == "shared.data_access.guild_queries"
    assert "guild isolation" in guild_queries.__doc__.lower()
    assert "required guild_id" in guild_queries.__doc__.lower()
