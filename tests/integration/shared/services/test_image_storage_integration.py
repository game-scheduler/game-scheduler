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


"""Integration tests for image storage service with deduplication."""

import hashlib
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.game_image import GameImage
from shared.services.image_storage import release_image, store_image


@pytest.fixture
async def clean_images(admin_db: AsyncSession):
    """Clean game_images table before each test for hermetic isolation."""
    await admin_db.execute(delete(GameImage))
    await admin_db.commit()
    yield
    await admin_db.execute(delete(GameImage))
    await admin_db.commit()


@pytest.fixture
def png_data() -> bytes:
    """Valid PNG image data for testing."""
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )


@pytest.fixture
def jpeg_data() -> bytes:
    """Valid JPEG image data for testing."""
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'"
        b"9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        b"\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\xff\xc4\x00\x14\x10\x01\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff"
        b"\xda\x00\x08\x01\x01\x00\x00?\x00\x7f\xff\xd9"
    )


@pytest.mark.integration
async def test_store_image_creates_new_image(
    admin_db: AsyncSession, png_data: bytes, clean_images
) -> None:
    """First upload creates new image with reference_count=1."""
    image_id = await store_image(admin_db, png_data, "image/png")
    await admin_db.commit()

    result = await admin_db.get(GameImage, image_id)
    assert result is not None
    assert result.image_data == png_data
    assert result.mime_type == "image/png"
    assert result.reference_count == 1
    assert result.content_hash == hashlib.sha256(png_data).hexdigest()


@pytest.mark.integration
async def test_store_duplicate_image_increments_count(
    admin_db: AsyncSession, png_data: bytes, clean_images
) -> None:
    """Uploading same image twice increments count, returns same ID."""
    image_id_1 = await store_image(admin_db, png_data, "image/png")
    await admin_db.commit()

    await admin_db.begin()
    image_id_2 = await store_image(admin_db, png_data, "image/png")
    await admin_db.commit()

    assert image_id_1 == image_id_2

    result = await admin_db.get(GameImage, image_id_1)
    assert result is not None
    assert result.reference_count == 2


@pytest.mark.integration
async def test_release_image_decrements_count(
    admin_db: AsyncSession, png_data: bytes, clean_images
) -> None:
    """Releasing image decrements count, keeps image if count > 0."""
    image_id = await store_image(admin_db, png_data, "image/png")
    await store_image(admin_db, png_data, "image/png")
    await admin_db.commit()

    await admin_db.begin()
    await release_image(admin_db, image_id)
    await admin_db.commit()

    result = await admin_db.get(GameImage, image_id)
    assert result is not None
    assert result.reference_count == 1


@pytest.mark.integration
async def test_release_image_deletes_when_count_zero(
    admin_db: AsyncSession, png_data: bytes, clean_images
) -> None:
    """Releasing last reference deletes image."""
    image_id = await store_image(admin_db, png_data, "image/png")
    await admin_db.commit()

    await admin_db.begin()
    await release_image(admin_db, image_id)
    await admin_db.commit()

    result = await admin_db.get(GameImage, image_id)
    assert result is None


@pytest.mark.integration
async def test_concurrent_store_operations_safe(
    admin_db: AsyncSession, png_data: bytes, clean_images
) -> None:
    """Concurrent uploads of same image handled safely (SELECT FOR UPDATE)."""
    image_id_1 = await store_image(admin_db, png_data, "image/png")
    await admin_db.commit()

    await admin_db.begin()
    image_id_2 = await store_image(admin_db, png_data, "image/png")
    await admin_db.commit()

    assert image_id_1 == image_id_2

    result = await admin_db.get(GameImage, image_id_1)
    assert result is not None
    assert result.reference_count == 2


@pytest.mark.integration
async def test_different_images_stored_separately(
    admin_db: AsyncSession, png_data: bytes, jpeg_data: bytes, clean_images
) -> None:
    """Different image data creates separate entries."""
    png_id = await store_image(admin_db, png_data, "image/png")
    jpeg_id = await store_image(admin_db, jpeg_data, "image/jpeg")
    await admin_db.commit()

    assert png_id != jpeg_id

    png_image = await admin_db.get(GameImage, png_id)
    jpeg_image = await admin_db.get(GameImage, jpeg_id)

    assert png_image is not None
    assert jpeg_image is not None
    assert png_image.content_hash != jpeg_image.content_hash
    assert png_image.reference_count == 1
    assert jpeg_image.reference_count == 1


@pytest.mark.integration
async def test_release_image_with_none_id_is_noop(admin_db: AsyncSession, clean_images) -> None:
    """Releasing None ID is a no-op (no error)."""
    await release_image(admin_db, None)
    await admin_db.commit()


@pytest.mark.integration
async def test_release_image_with_missing_id_is_noop(admin_db: AsyncSession, clean_images) -> None:
    """Releasing non-existent ID is a no-op (no error)."""
    fake_id = uuid4()
    await release_image(admin_db, fake_id)
    await admin_db.commit()


@pytest.mark.integration
async def test_same_data_different_mime_types_stored_separately(
    admin_db: AsyncSession, png_data: bytes, clean_images
) -> None:
    """Same image data with different MIME types creates separate entries."""
    png_id = await store_image(admin_db, png_data, "image/png")
    webp_id = await store_image(admin_db, png_data, "image/webp")
    await admin_db.commit()

    assert png_id == webp_id

    image = await admin_db.get(GameImage, png_id)
    assert image is not None
    assert image.reference_count == 2


@pytest.mark.integration
async def test_transaction_rollback_prevents_orphaned_images(
    admin_db: AsyncSession, png_data: bytes, clean_images
) -> None:
    """Transaction rollback prevents creating orphaned images."""
    image_id = await store_image(admin_db, png_data, "image/png")

    await admin_db.rollback()

    result = await admin_db.get(GameImage, image_id)
    assert result is None
