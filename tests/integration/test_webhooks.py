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


"""Integration tests for Discord webhook endpoint."""

import json
import os

import pytest
from nacl.signing import SigningKey

pytestmark = pytest.mark.integration

# Fixed keypair for integration tests matching env.int DISCORD_PUBLIC_KEY
INTEGRATION_TEST_PRIVATE_KEY = "4c480d86c13f3e142aca79d54cdd2a173eaf484cb4fd44e61790fa5386501b83"
INTEGRATION_TEST_PUBLIC_KEY = "bfdab846fefce17aaaa92860e42a70c61d2d40c95b1ebbcbe4087a505f66b8fe"


def create_valid_signature(body: bytes, timestamp: str, private_key: SigningKey) -> str:
    """Create valid Ed25519 signature for webhook request."""
    message = timestamp.encode() + body
    signature = private_key.sign(message).signature
    return signature.hex()


@pytest.fixture
def webhook_keypair():
    """Get fixed Ed25519 keypair for testing."""
    private_key = SigningKey(bytes.fromhex(INTEGRATION_TEST_PRIVATE_KEY))
    public_key = private_key.verify_key.encode().hex()
    return private_key, public_key


@pytest.fixture
def set_discord_public_key():
    """Verify DISCORD_PUBLIC_KEY environment variable is set correctly."""
    public_key = os.environ.get("DISCORD_PUBLIC_KEY")
    assert public_key == INTEGRATION_TEST_PUBLIC_KEY, (
        f"DISCORD_PUBLIC_KEY must be set to {INTEGRATION_TEST_PUBLIC_KEY} in env.int"
    )
    return public_key


@pytest.fixture
def ping_payload():
    """Discord PING webhook payload."""
    return {
        "version": 1,
        "application_id": "1234567890123456789",
        "type": 0,
    }


@pytest.fixture
def application_authorized_payload():
    """Discord APPLICATION_AUTHORIZED webhook payload."""
    return {
        "version": 1,
        "application_id": "1234567890123456789",
        "type": 1,
        "event": {
            "type": "APPLICATION_AUTHORIZED",
            "timestamp": "2024-10-18T14:42:53.064834",
            "data": {
                "integration_type": 0,
                "scopes": ["applications.commands"],
                "user": {"id": "9876543210987654321", "username": "testuser"},
                "guild": {"id": "1111222233334444555", "name": "Test Guild"},
            },
        },
    }


@pytest.mark.asyncio
async def test_webhook_ping_returns_not_implemented(
    async_client, webhook_keypair, set_discord_public_key, ping_payload
):
    """Webhook endpoint returns 204 for PING (Discord validation)."""
    private_key, _ = webhook_keypair
    body = json.dumps(ping_payload).encode()
    timestamp = "1634567890"

    signature = create_valid_signature(body, timestamp, private_key)

    response = await async_client.post(
        "/api/v1/webhooks/discord",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature-Ed25519": signature,
            "X-Signature-Timestamp": timestamp,
        },
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_webhook_application_authorized_returns_not_implemented(
    async_client,
    webhook_keypair,
    set_discord_public_key,
    application_authorized_payload,
):
    """Webhook endpoint returns 204 for APPLICATION_AUTHORIZED (guild install)."""
    private_key, _ = webhook_keypair
    body = json.dumps(application_authorized_payload).encode()
    timestamp = "1634567890"

    signature = create_valid_signature(body, timestamp, private_key)

    response = await async_client.post(
        "/api/v1/webhooks/discord",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature-Ed25519": signature,
            "X-Signature-Timestamp": timestamp,
        },
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_signature(
    async_client, set_discord_public_key, ping_payload
):
    """Webhook endpoint rejects requests with invalid signatures."""
    body = json.dumps(ping_payload).encode()
    timestamp = "1634567890"
    invalid_signature = "0" * 128

    response = await async_client.post(
        "/api/v1/webhooks/discord",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature-Ed25519": invalid_signature,
            "X-Signature-Timestamp": timestamp,
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid webhook signature"}


@pytest.mark.asyncio
async def test_webhook_requires_signature_headers(async_client, set_discord_public_key):
    """Webhook endpoint requires X-Signature headers."""
    body = json.dumps({"type": 0}).encode()

    response = await async_client.post(
        "/api/v1/webhooks/discord",
        content=body,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
