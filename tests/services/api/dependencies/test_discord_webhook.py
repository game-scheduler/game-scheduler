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


"""Tests for Discord webhook signature validation."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from nacl.signing import SigningKey

from services.api.dependencies.discord_webhook import validate_discord_webhook


@pytest.fixture
def test_keypair():
    """Generate test Ed25519 keypair for signature validation."""
    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key
    return {
        "signing_key": signing_key,
        "verify_key": verify_key,
        "public_key_hex": verify_key.encode().hex(),
    }


@pytest.fixture
def mock_request():
    """Create mock FastAPI Request object."""
    request = MagicMock()
    request.body = AsyncMock()
    return request


def create_valid_signature(signing_key, timestamp: str, body: bytes) -> str:
    """Helper to create valid Discord webhook signature."""
    message = timestamp.encode() + body
    signed = signing_key.sign(message)
    return signed.signature.hex()


@pytest.mark.asyncio
async def test_valid_signature_returns_body(mock_request, test_keypair, monkeypatch):
    """Valid Ed25519 signature should return request body."""
    body = json.dumps({"type": 0, "data": "test"}).encode()
    timestamp = "1234567890"

    mock_request.body.return_value = body
    signature = create_valid_signature(test_keypair["signing_key"], timestamp, body)

    monkeypatch.setenv("DISCORD_PUBLIC_KEY", test_keypair["public_key_hex"])

    result = await validate_discord_webhook(
        request=mock_request,
        x_signature_ed25519=signature,
        x_signature_timestamp=timestamp,
    )

    assert result == body


@pytest.mark.asyncio
async def test_invalid_signature_raises_401(mock_request, test_keypair, monkeypatch):
    """Invalid signature should raise HTTPException with 401 status."""
    body = json.dumps({"type": 0, "data": "test"}).encode()
    timestamp = "1234567890"
    invalid_signature = "0" * 128

    mock_request.body.return_value = body
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", test_keypair["public_key_hex"])

    with pytest.raises(HTTPException) as exc_info:
        await validate_discord_webhook(
            request=mock_request,
            x_signature_ed25519=invalid_signature,
            x_signature_timestamp=timestamp,
        )

    assert exc_info.value.status_code == 401
    assert "Invalid webhook signature" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_wrong_public_key_raises_401(mock_request, test_keypair, monkeypatch):
    """Signature valid for different key should raise 401."""
    body = json.dumps({"type": 0, "data": "test"}).encode()
    timestamp = "1234567890"

    mock_request.body.return_value = body
    signature = create_valid_signature(test_keypair["signing_key"], timestamp, body)

    wrong_keypair = SigningKey.generate()
    wrong_public_key_hex = wrong_keypair.verify_key.encode().hex()
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", wrong_public_key_hex)

    with pytest.raises(HTTPException) as exc_info:
        await validate_discord_webhook(
            request=mock_request,
            x_signature_ed25519=signature,
            x_signature_timestamp=timestamp,
        )

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_malformed_signature_raises_401(mock_request, test_keypair, monkeypatch):
    """Malformed signature hex string should raise 401."""
    body = json.dumps({"type": 0, "data": "test"}).encode()
    timestamp = "1234567890"
    malformed_signature = "not_valid_hex"

    mock_request.body.return_value = body
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", test_keypair["public_key_hex"])

    with pytest.raises(HTTPException) as exc_info:
        await validate_discord_webhook(
            request=mock_request,
            x_signature_ed25519=malformed_signature,
            x_signature_timestamp=timestamp,
        )

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_empty_body_validates_correctly(mock_request, test_keypair, monkeypatch):
    """Empty body should validate correctly with valid signature."""
    body = b""
    timestamp = "1234567890"

    mock_request.body.return_value = body
    signature = create_valid_signature(test_keypair["signing_key"], timestamp, body)
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", test_keypair["public_key_hex"])

    result = await validate_discord_webhook(
        request=mock_request,
        x_signature_ed25519=signature,
        x_signature_timestamp=timestamp,
    )

    assert result == body


@pytest.mark.asyncio
async def test_large_body_validates_correctly(mock_request, test_keypair, monkeypatch):
    """Large body (10KB) should validate correctly."""
    body = json.dumps({"data": "x" * 10000}).encode()
    timestamp = "1234567890"

    mock_request.body.return_value = body
    signature = create_valid_signature(test_keypair["signing_key"], timestamp, body)
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", test_keypair["public_key_hex"])

    result = await validate_discord_webhook(
        request=mock_request,
        x_signature_ed25519=signature,
        x_signature_timestamp=timestamp,
    )

    assert result == body


@pytest.mark.asyncio
async def test_missing_public_key_raises_500(mock_request, test_keypair, monkeypatch):
    """Missing DISCORD_PUBLIC_KEY environment variable should raise 500."""
    body = json.dumps({"type": 0}).encode()
    timestamp = "1234567890"

    mock_request.body.return_value = body
    signature = create_valid_signature(test_keypair["signing_key"], timestamp, body)
    monkeypatch.delenv("DISCORD_PUBLIC_KEY", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        await validate_discord_webhook(
            request=mock_request,
            x_signature_ed25519=signature,
            x_signature_timestamp=timestamp,
        )

    assert exc_info.value.status_code == 500
    assert "not configured" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_invalid_public_key_format_raises_401(mock_request, test_keypair, monkeypatch):
    """Invalid public key hex format should raise 401."""
    body = json.dumps({"type": 0}).encode()
    timestamp = "1234567890"

    mock_request.body.return_value = body
    signature = create_valid_signature(test_keypair["signing_key"], timestamp, body)
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", "not_valid_hex")

    with pytest.raises(HTTPException) as exc_info:
        await validate_discord_webhook(
            request=mock_request,
            x_signature_ed25519=signature,
            x_signature_timestamp=timestamp,
        )

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_wrong_timestamp_raises_401(mock_request, test_keypair, monkeypatch):
    """Signature with wrong timestamp should raise 401."""
    body = json.dumps({"type": 0}).encode()
    correct_timestamp = "1234567890"
    wrong_timestamp = "9999999999"

    mock_request.body.return_value = body
    signature = create_valid_signature(test_keypair["signing_key"], correct_timestamp, body)
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", test_keypair["public_key_hex"])

    with pytest.raises(HTTPException) as exc_info:
        await validate_discord_webhook(
            request=mock_request,
            x_signature_ed25519=signature,
            x_signature_timestamp=wrong_timestamp,
        )

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_signature_too_short_raises_401(mock_request, test_keypair, monkeypatch):
    """Signature that is too short should raise 401."""
    body = json.dumps({"type": 0}).encode()
    timestamp = "1234567890"
    short_signature = "abc123"

    mock_request.body.return_value = body
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", test_keypair["public_key_hex"])

    with pytest.raises(HTTPException) as exc_info:
        await validate_discord_webhook(
            request=mock_request,
            x_signature_ed25519=short_signature,
            x_signature_timestamp=timestamp,
        )

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_unicode_body_validates_correctly(mock_request, test_keypair, monkeypatch):
    """Body with Unicode characters should validate correctly."""
    body = json.dumps({"message": "Hello 世界 🌍"}).encode("utf-8")
    timestamp = "1234567890"

    mock_request.body.return_value = body
    signature = create_valid_signature(test_keypair["signing_key"], timestamp, body)
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", test_keypair["public_key_hex"])

    result = await validate_discord_webhook(
        request=mock_request,
        x_signature_ed25519=signature,
        x_signature_timestamp=timestamp,
    )

    assert result == body
