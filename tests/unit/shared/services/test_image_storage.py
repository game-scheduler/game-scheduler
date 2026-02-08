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


"""Unit tests for image_storage module."""

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.game_image import GameImage
from shared.services import image_storage


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession."""
    session = MagicMock(spec=AsyncSession)
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.mark.asyncio
async def test_store_image_new_image(mock_session):
    """Test storing a new image creates a GameImage record."""
    image_data = b"test image data"
    mime_type = "image/png"
    expected_hash = hashlib.sha256(image_data).hexdigest()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def capture_flush():
        added_image = mock_session.add.call_args[0][0]
        added_image.id = UUID("00000000-0000-0000-0000-000000000001")

    mock_session.flush = AsyncMock(side_effect=capture_flush)

    result = await image_storage.store_image(mock_session, image_data, mime_type)

    assert isinstance(result, UUID)
    mock_session.add.assert_called_once()
    added_image = mock_session.add.call_args[0][0]
    assert isinstance(added_image, GameImage)
    assert added_image.content_hash == expected_hash
    assert added_image.image_data == image_data
    assert added_image.mime_type == mime_type
    assert added_image.reference_count == 1
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_store_image_existing_image(mock_session):
    """Test storing an existing image increments reference count."""
    image_data = b"test image data"
    mime_type = "image/png"
    expected_hash = hashlib.sha256(image_data).hexdigest()

    existing_image = MagicMock(spec=GameImage)
    existing_image.id = UUID("00000000-0000-0000-0000-000000000001")
    existing_image.content_hash = expected_hash
    existing_image.reference_count = 1

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=existing_image)
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await image_storage.store_image(mock_session, image_data, mime_type)

    assert result == existing_image.id
    assert existing_image.reference_count == 2
    mock_session.add.assert_not_called()
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_store_image_computes_correct_hash(mock_session):
    """Test that store_image computes the correct SHA256 hash."""
    image_data = b"specific test data"
    mime_type = "image/jpeg"
    expected_hash = hashlib.sha256(image_data).hexdigest()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def capture_flush():
        added_image = mock_session.add.call_args[0][0]
        added_image.id = UUID("00000000-0000-0000-0000-000000000002")

    mock_session.flush = AsyncMock(side_effect=capture_flush)

    result = await image_storage.store_image(mock_session, image_data, mime_type)

    assert isinstance(result, UUID)
    added_image = mock_session.add.call_args[0][0]
    assert added_image.content_hash == expected_hash


@pytest.mark.asyncio
async def test_release_image_with_none(mock_session):
    """Test releasing a None image_id does nothing."""
    await image_storage.release_image(mock_session, None)

    mock_session.execute.assert_not_called()
    mock_session.flush.assert_not_called()


@pytest.mark.asyncio
async def test_release_image_nonexistent(mock_session):
    """Test releasing a nonexistent image logs warning and does nothing."""
    image_id = UUID("00000000-0000-0000-0000-000000000001")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("shared.services.image_storage.logger") as mock_logger:
        await image_storage.release_image(mock_session, image_id)

        mock_logger.warning.assert_called_once()
        assert "not found" in mock_logger.warning.call_args[0][0]


@pytest.mark.asyncio
async def test_release_image_decrements_reference_count(mock_session):
    """Test releasing an image decrements reference count."""
    image_id = UUID("00000000-0000-0000-0000-000000000001")
    image = MagicMock(spec=GameImage)
    image.id = image_id
    image.content_hash = "test_hash"
    image.reference_count = 2

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=image)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.delete = AsyncMock()

    await image_storage.release_image(mock_session, image_id)

    assert image.reference_count == 1
    mock_session.delete.assert_not_called()
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_release_image_deletes_when_count_reaches_zero(mock_session):
    """Test releasing an image deletes it when reference count reaches zero."""
    image_id = UUID("00000000-0000-0000-0000-000000000001")
    image = MagicMock(spec=GameImage)
    image.id = image_id
    image.content_hash = "test_hash"
    image.reference_count = 1

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=image)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.delete = AsyncMock()

    await image_storage.release_image(mock_session, image_id)

    assert image.reference_count == 0
    mock_session.delete.assert_called_once_with(image)
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_release_image_handles_negative_count(mock_session):
    """Test releasing an image with already zero count logs warning."""
    image_id = UUID("00000000-0000-0000-0000-000000000001")
    image = MagicMock(spec=GameImage)
    image.id = image_id
    image.content_hash = "test_hash"
    image.reference_count = 0

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=image)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.delete = AsyncMock()

    with patch("shared.services.image_storage.logger") as mock_logger:
        await image_storage.release_image(mock_session, image_id)

        assert image.reference_count == -1
        mock_logger.info.assert_called()
        assert "deleted" in str(mock_logger.info.call_args)


@pytest.mark.asyncio
async def test_store_image_uses_correct_query(mock_session):
    """Test that store_image executes the correct SQL query."""
    image_data = b"test data"
    mime_type = "image/png"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=mock_result)

    await image_storage.store_image(mock_session, image_data, mime_type)

    mock_session.execute.assert_called_once()
    call_args = mock_session.execute.call_args[0][0]
    assert str(call_args).lower().count("select") == 1
    assert "game_images" in str(call_args).lower()


@pytest.mark.asyncio
async def test_release_image_uses_correct_query(mock_session):
    """Test that release_image executes the correct SQL query."""
    image_id = UUID("00000000-0000-0000-0000-000000000001")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=mock_result)

    await image_storage.release_image(mock_session, image_id)

    mock_session.execute.assert_called_once()
    call_args = mock_session.execute.call_args[0][0]
    assert str(call_args).lower().count("select") == 1
    assert "game_images" in str(call_args).lower()
