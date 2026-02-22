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


"""Unit tests for Discord webhook endpoint edge cases."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from services.api.routes.webhooks import _get_event_publisher, discord_webhook
from shared.messaging.events import Event, EventType


@pytest.fixture
def mock_publisher():
    """Mock EventPublisher for webhook tests."""
    publisher = AsyncMock()
    publisher.publish = AsyncMock()
    return publisher


@pytest.mark.asyncio
async def test_webhook_ping_returns_204(mock_publisher):
    """PING webhook (type=0) returns 204 No Content."""
    payload = {"version": 1, "application_id": "123456", "type": 0}
    validated_body = json.dumps(payload).encode()

    response = await discord_webhook(validated_body, mock_publisher)

    assert response.status_code == 204
    assert response.body == b""


@pytest.mark.asyncio
async def test_webhook_application_authorized_guild_install_returns_204(mock_publisher):
    """APPLICATION_AUTHORIZED with guild install (type=0) returns 204."""
    payload = {
        "version": 1,
        "application_id": "123456",
        "type": 1,
        "event": {
            "type": "APPLICATION_AUTHORIZED",
            "timestamp": "2024-10-18T14:42:53.064834",
            "data": {
                "integration_type": 0,
                "scopes": ["applications.commands"],
                "user": {"id": "user123", "username": "testuser"},
                "guild": {"id": "guild123", "name": "Test Guild"},
            },
        },
    }
    validated_body = json.dumps(payload).encode()

    response = await discord_webhook(validated_body, mock_publisher)

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_webhook_application_authorized_user_install_returns_204(mock_publisher):
    """APPLICATION_AUTHORIZED with user install (type=1) returns 204."""
    payload = {
        "version": 1,
        "application_id": "123456",
        "type": 1,
        "event": {
            "type": "APPLICATION_AUTHORIZED",
            "timestamp": "2024-10-18T14:42:53.064834",
            "data": {
                "integration_type": 1,
                "scopes": ["applications.commands"],
                "user": {"id": "user123", "username": "testuser"},
            },
        },
    }
    validated_body = json.dumps(payload).encode()

    response = await discord_webhook(validated_body, mock_publisher)

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_webhook_application_authorized_missing_guild_returns_204(mock_publisher):
    """APPLICATION_AUTHORIZED with missing guild field still returns 204."""
    payload = {
        "version": 1,
        "application_id": "123456",
        "type": 1,
        "event": {
            "type": "APPLICATION_AUTHORIZED",
            "timestamp": "2024-10-18T14:42:53.064834",
            "data": {
                "integration_type": 0,
                "scopes": ["applications.commands"],
                "user": {"id": "user123", "username": "testuser"},
            },
        },
    }
    validated_body = json.dumps(payload).encode()

    response = await discord_webhook(validated_body, mock_publisher)

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_webhook_application_authorized_empty_guild_returns_204(mock_publisher):
    """APPLICATION_AUTHORIZED with empty guild object returns 204."""
    payload = {
        "version": 1,
        "application_id": "123456",
        "type": 1,
        "event": {
            "type": "APPLICATION_AUTHORIZED",
            "timestamp": "2024-10-18T14:42:53.064834",
            "data": {
                "integration_type": 0,
                "scopes": ["applications.commands"],
                "user": {"id": "user123", "username": "testuser"},
                "guild": {},
            },
        },
    }
    validated_body = json.dumps(payload).encode()

    response = await discord_webhook(validated_body, mock_publisher)

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_webhook_unknown_event_type_returns_204(mock_publisher):
    """Unknown event type in type=1 webhook returns 204."""
    payload = {
        "version": 1,
        "application_id": "123456",
        "type": 1,
        "event": {
            "type": "UNKNOWN_EVENT_TYPE",
            "timestamp": "2024-10-18T14:42:53.064834",
            "data": {},
        },
    }
    validated_body = json.dumps(payload).encode()

    response = await discord_webhook(validated_body, mock_publisher)

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_webhook_missing_event_field_returns_204(mock_publisher):
    """Type=1 webhook with missing event field returns 204."""
    payload = {"version": 1, "application_id": "123456", "type": 1}
    validated_body = json.dumps(payload).encode()

    response = await discord_webhook(validated_body, mock_publisher)

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_webhook_unknown_type_returns_204(mock_publisher):
    """Webhook with unknown type returns 204."""
    payload = {"version": 1, "application_id": "123456", "type": 99}
    validated_body = json.dumps(payload).encode()

    response = await discord_webhook(validated_body, mock_publisher)

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_webhook_missing_type_field_returns_204(mock_publisher):
    """Webhook with missing type field returns 204."""
    payload = {"version": 1, "application_id": "123456"}
    validated_body = json.dumps(payload).encode()

    response = await discord_webhook(validated_body, mock_publisher)

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_webhook_application_authorized_missing_integration_type(mock_publisher):
    """APPLICATION_AUTHORIZED with missing integration_type returns 204."""
    payload = {
        "version": 1,
        "application_id": "123456",
        "type": 1,
        "event": {
            "type": "APPLICATION_AUTHORIZED",
            "timestamp": "2024-10-18T14:42:53.064834",
            "data": {
                "scopes": ["applications.commands"],
                "user": {"id": "user123", "username": "testuser"},
            },
        },
    }
    validated_body = json.dumps(payload).encode()

    response = await discord_webhook(validated_body, mock_publisher)

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_webhook_application_authorized_missing_data(mock_publisher):
    """APPLICATION_AUTHORIZED with missing data field returns 204."""
    payload = {
        "version": 1,
        "application_id": "123456",
        "type": 1,
        "event": {
            "type": "APPLICATION_AUTHORIZED",
            "timestamp": "2024-10-18T14:42:53.064834",
        },
    }
    validated_body = json.dumps(payload).encode()

    response = await discord_webhook(validated_body, mock_publisher)

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_webhook_idempotency_multiple_same_guild(mock_publisher):
    """Multiple webhooks for the same guild all return 204 (idempotent)."""
    payload = {
        "version": 1,
        "application_id": "123456",
        "type": 1,
        "event": {
            "type": "APPLICATION_AUTHORIZED",
            "timestamp": "2024-10-18T14:42:53.064834",
            "data": {
                "integration_type": 0,
                "scopes": ["applications.commands"],
                "user": {"id": "user123", "username": "testuser"},
                "guild": {"id": "guild123", "name": "Test Guild"},
            },
        },
    }
    validated_body = json.dumps(payload).encode()

    for _ in range(3):
        response = await discord_webhook(validated_body, mock_publisher)
        assert response.status_code == 204


@pytest.mark.asyncio
async def test_webhook_publishes_guild_sync_event_for_guild_install(mock_publisher):
    """APPLICATION_AUTHORIZED with guild install publishes GUILD_SYNC_REQUESTED event."""
    payload = {
        "version": 1,
        "application_id": "123456",
        "type": 1,
        "event": {
            "type": "APPLICATION_AUTHORIZED",
            "timestamp": "2024-10-18T14:42:53.064834",
            "data": {
                "integration_type": 0,
                "scopes": ["applications.commands"],
                "user": {"id": "user123", "username": "testuser"},
                "guild": {"id": "guild123", "name": "Test Guild"},
            },
        },
    }
    validated_body = json.dumps(payload).encode()

    response = await discord_webhook(validated_body, mock_publisher)

    assert response.status_code == 204
    mock_publisher.publish.assert_called_once()

    call_args = mock_publisher.publish.call_args
    published_event = call_args[0][0]

    assert isinstance(published_event, Event)
    assert published_event.event_type == EventType.GUILD_SYNC_REQUESTED
    assert published_event.data == {}


@pytest.mark.asyncio
async def test_webhook_does_not_publish_for_user_install(mock_publisher):
    """APPLICATION_AUTHORIZED with user install (type=1) does not publish event."""
    payload = {
        "version": 1,
        "application_id": "123456",
        "type": 1,
        "event": {
            "type": "APPLICATION_AUTHORIZED",
            "timestamp": "2024-10-18T14:42:53.064834",
            "data": {
                "integration_type": 1,
                "scopes": ["applications.commands"],
                "user": {"id": "user123", "username": "testuser"},
            },
        },
    }
    validated_body = json.dumps(payload).encode()

    response = await discord_webhook(validated_body, mock_publisher)

    assert response.status_code == 204
    mock_publisher.publish.assert_not_called()


@pytest.mark.asyncio
async def test_webhook_returns_204_even_if_publish_fails(mock_publisher):
    """Webhook returns 204 even if RabbitMQ publish fails."""
    mock_publisher.publish.side_effect = Exception("RabbitMQ connection failed")

    payload = {
        "version": 1,
        "application_id": "123456",
        "type": 1,
        "event": {
            "type": "APPLICATION_AUTHORIZED",
            "timestamp": "2024-10-18T14:42:53.064834",
            "data": {
                "integration_type": 0,
                "scopes": ["applications.commands"],
                "user": {"id": "user123", "username": "testuser"},
                "guild": {"id": "guild123", "name": "Test Guild"},
            },
        },
    }
    validated_body = json.dumps(payload).encode()

    response = await discord_webhook(validated_body, mock_publisher)

    assert response.status_code == 204
    mock_publisher.publish.assert_called_once()


@pytest.mark.asyncio
async def test_get_event_publisher_dependency():
    """Test EventPublisher dependency lifecycle management."""
    with patch("services.api.routes.webhooks.EventPublisher") as mock_publisher_class:
        mock_publisher = AsyncMock()
        mock_publisher_class.return_value = mock_publisher

        async for publisher in _get_event_publisher():
            assert publisher == mock_publisher
            mock_publisher.connect.assert_called_once()

        mock_publisher.close.assert_called_once()
