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


"""Unit tests for image validation in game routes."""

import io

import pytest
from fastapi import HTTPException, UploadFile

from services.api.routes.games import _validate_image_upload


def create_mock_upload_file(content: bytes, content_type: str) -> UploadFile:
    """Create mock UploadFile for testing."""
    file_obj = io.BytesIO(content)
    # UploadFile uses SpooledTemporaryFile, but accepts headers for content_type
    return UploadFile(
        filename="test.png",
        file=file_obj,
        headers={"content-type": content_type},
    )


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
