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


"""Unit tests for image validation in game routes."""

import io

import pytest
from fastapi import HTTPException, UploadFile

from services.api.routes.games import _validate_image_upload


def create_mock_upload_file(content: bytes, content_type: str) -> UploadFile:
    """Create mock UploadFile for testing."""
    file_obj = io.BytesIO(content)
    # UploadFile uses SpooledTemporaryFile, but accepts headers for content_type
    upload_file = UploadFile(
        filename="test.png",
        file=file_obj,
        headers={"content-type": content_type},
    )
    return upload_file


@pytest.mark.asyncio
async def test_validate_image_upload_valid_png():
    """Test validation accepts valid PNG file."""
    content = b"fake_png_data_under_5mb"
    upload_file = create_mock_upload_file(content, "image/png")

    # Should not raise exception
    await _validate_image_upload(upload_file, "thumbnail")

    # Verify file pointer was reset
    assert upload_file.file.tell() == 0


@pytest.mark.asyncio
async def test_validate_image_upload_valid_jpeg():
    """Test validation accepts valid JPEG file."""
    content = b"fake_jpeg_data"
    upload_file = create_mock_upload_file(content, "image/jpeg")

    # Should not raise exception
    await _validate_image_upload(upload_file, "thumbnail")


@pytest.mark.asyncio
async def test_validate_image_upload_valid_gif():
    """Test validation accepts valid GIF file."""
    content = b"fake_gif_data"
    upload_file = create_mock_upload_file(content, "image/gif")

    # Should not raise exception
    await _validate_image_upload(upload_file, "thumbnail")


@pytest.mark.asyncio
async def test_validate_image_upload_valid_webp():
    """Test validation accepts valid WebP file."""
    content = b"fake_webp_data"
    upload_file = create_mock_upload_file(content, "image/webp")

    # Should not raise exception
    await _validate_image_upload(upload_file, "thumbnail")


@pytest.mark.asyncio
async def test_validate_image_upload_invalid_type():
    """Test validation rejects invalid file type."""
    content = b"fake_pdf_data"
    upload_file = create_mock_upload_file(content, "application/pdf")

    with pytest.raises(HTTPException) as exc_info:
        await _validate_image_upload(upload_file, "thumbnail")

    assert exc_info.value.status_code == 400
    assert "thumbnail must be PNG, JPEG, GIF, or WebP" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_image_upload_file_too_large():
    """Test validation rejects file exceeding 5MB limit."""
    # Create file larger than 5MB
    content = b"x" * (5 * 1024 * 1024 + 1)
    upload_file = create_mock_upload_file(content, "image/png")

    with pytest.raises(HTTPException) as exc_info:
        await _validate_image_upload(upload_file, "thumbnail")

    assert exc_info.value.status_code == 400
    assert "thumbnail must be less than 5MB" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_image_upload_exactly_5mb():
    """Test validation accepts file exactly at 5MB limit."""
    # Create file exactly 5MB
    content = b"x" * (5 * 1024 * 1024)
    upload_file = create_mock_upload_file(content, "image/png")

    # Should not raise exception
    await _validate_image_upload(upload_file, "image")


@pytest.mark.asyncio
async def test_validate_image_upload_custom_field_name():
    """Test error messages use provided field name."""
    content = b"fake_pdf_data"
    upload_file = create_mock_upload_file(content, "application/pdf")

    with pytest.raises(HTTPException) as exc_info:
        await _validate_image_upload(upload_file, "banner")

    assert "banner must be PNG, JPEG, GIF, or WebP" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_image_upload_empty_file():
    """Test validation accepts empty file (0 bytes)."""
    content = b""
    upload_file = create_mock_upload_file(content, "image/png")

    # Should not raise exception
    await _validate_image_upload(upload_file, "thumbnail")
