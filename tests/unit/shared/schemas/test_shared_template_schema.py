# Copyright 2026 Bret McKee
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


"""Tests for template schema description length constraints."""

import pytest
from pydantic import ValidationError

from shared.schemas.template import TemplateCreateRequest, TemplateUpdateRequest
from shared.utils.limits import MAX_DESCRIPTION_LENGTH

VALID_GUILD_ID = "00000000-0000-0000-0000-000000000001"
VALID_CHANNEL_ID = "00000000-0000-0000-0000-000000000002"


class TestTemplateCreateRequestDescriptionLimit:
    """Tests for TemplateCreateRequest description max_length=MAX_DESCRIPTION_LENGTH."""

    def test_description_at_limit_accepted(self):
        """Test that a 2,000-character description is accepted."""
        req = TemplateCreateRequest(
            guild_id=VALID_GUILD_ID,
            name="My Template",
            channel_id=VALID_CHANNEL_ID,
            description="A" * MAX_DESCRIPTION_LENGTH,
        )
        assert len(req.description) == MAX_DESCRIPTION_LENGTH

    def test_description_over_limit_rejected(self):
        """Test that a 2,001-character description is rejected."""
        with pytest.raises(ValidationError):
            TemplateCreateRequest(
                guild_id=VALID_GUILD_ID,
                name="My Template",
                channel_id=VALID_CHANNEL_ID,
                description="A" * (MAX_DESCRIPTION_LENGTH + 1),
            )

    def test_none_description_accepted(self):
        """Test that None description is accepted."""
        req = TemplateCreateRequest(
            guild_id=VALID_GUILD_ID,
            name="My Template",
            channel_id=VALID_CHANNEL_ID,
        )
        assert req.description is None


class TestTemplateUpdateRequestDescriptionLimit:
    """Tests for TemplateUpdateRequest description max_length=MAX_DESCRIPTION_LENGTH."""

    def test_description_at_limit_accepted(self):
        """Test that a 2,000-character description is accepted."""
        req = TemplateUpdateRequest(description="A" * MAX_DESCRIPTION_LENGTH)
        assert len(req.description) == MAX_DESCRIPTION_LENGTH

    def test_description_over_limit_rejected(self):
        """Test that a 2,001-character description is rejected."""
        with pytest.raises(ValidationError):
            TemplateUpdateRequest(description="A" * (MAX_DESCRIPTION_LENGTH + 1))

    def test_none_description_accepted(self):
        """Test that None description is accepted."""
        req = TemplateUpdateRequest(description=None)
        assert req.description is None
