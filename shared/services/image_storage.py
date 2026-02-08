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


"""
Image storage service with content-hash deduplication.

Provides functions for storing and releasing images with automatic reference
counting and deduplication based on SHA256 content hash.
"""

import hashlib
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.game_image import GameImage

logger = logging.getLogger(__name__)


async def store_image(db: AsyncSession, image_data: bytes, mime_type: str) -> UUID:
    """
    Store image with automatic deduplication via SHA256 hash.

    If an image with the same content already exists, increments its
    reference count and returns the existing image ID. Otherwise, creates
    a new image with reference_count=1.

    Does not commit. Caller must commit transaction.

    Args:
        db: Database session
        image_data: Raw image bytes
        mime_type: MIME type (e.g., "image/png", "image/jpeg")

    Returns:
        Image ID (UUID) - existing or newly created
    """
    content_hash = hashlib.sha256(image_data).hexdigest()
    logger.info(
        "store_image called: hash=%s... mime=%s size=%s",
        content_hash[:8],
        mime_type,
        len(image_data),
    )

    stmt = select(GameImage).where(GameImage.content_hash == content_hash).with_for_update()
    result = await db.execute(stmt)
    existing_image = result.scalar_one_or_none()

    if existing_image:
        old_count = existing_image.reference_count
        existing_image.reference_count += 1
        await db.flush()
        logger.info(
            "store_image: Found existing image %s, refs %s -> %s",
            existing_image.id,
            old_count,
            existing_image.reference_count,
        )
        return existing_image.id

    new_image = GameImage(
        content_hash=content_hash,
        image_data=image_data,
        mime_type=mime_type,
        reference_count=1,
    )
    db.add(new_image)
    await db.flush()
    logger.info("store_image: Created new image %s, refs=1", new_image.id)
    return new_image.id


async def release_image(db: AsyncSession, image_id: UUID | None) -> None:
    """
    Decrement reference count, delete image if count reaches zero.

    Does not commit. Caller must commit transaction.

    Args:
        db: Database session
        image_id: Image ID to release, or None (no-op)
    """
    if not image_id:
        logger.info("release_image: Called with None, no-op")
        return

    logger.info("release_image: Called for image %s", image_id)

    stmt = select(GameImage).where(GameImage.id == image_id).with_for_update()
    result = await db.execute(stmt)
    image = result.scalar_one_or_none()

    if not image:
        logger.warning("release_image: Image %s not found", image_id)
        return

    old_count = image.reference_count
    image.reference_count -= 1

    if image.reference_count <= 0:
        await db.delete(image)
        logger.info("release_image: Image %s refs %s -> 0, deleted", image_id, old_count)
    else:
        logger.info(
            "release_image: Image %s refs %s -> %s",
            image_id,
            old_count,
            image.reference_count,
        )

    await db.flush()
