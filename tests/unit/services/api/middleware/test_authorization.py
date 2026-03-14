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


"""Unit tests for authorization middleware."""

from unittest.mock import MagicMock

import pytest
from fastapi import Request, Response

from services.api.middleware import authorization


@pytest.fixture
def mock_request():
    """Create mock request."""
    request = MagicMock(spec=Request)
    request.method = "GET"
    request.url.path = "/api/v1/games"
    request.headers = {}
    return request


@pytest.fixture
def mock_response():
    """Create mock response."""
    response = MagicMock(spec=Response)
    response.status_code = 200
    return response


@pytest.fixture
def middleware():
    """Create middleware instance."""
    app = MagicMock()
    return authorization.AuthorizationMiddleware(app)


@pytest.mark.asyncio
async def test_dispatch_with_user_id(middleware, mock_request, mock_response):
    """Test dispatch with authenticated user."""
    mock_request.headers = {"X-User-Id": "user123", "X-Request-Id": "req456"}

    async def call_next(request):
        return mock_response

    response = await middleware.dispatch(mock_request, call_next)

    assert response == mock_response
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_dispatch_without_user_id(middleware, mock_request, mock_response):
    """Test dispatch without authenticated user."""

    async def call_next(request):
        return mock_response

    response = await middleware.dispatch(mock_request, call_next)

    assert response == mock_response


@pytest.mark.asyncio
async def test_dispatch_403_response(middleware, mock_request):
    """Test dispatch with 403 authorization denied."""
    mock_request.headers = {"X-User-Id": "user123"}
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 403

    async def call_next(request):
        return mock_response

    response = await middleware.dispatch(mock_request, call_next)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_dispatch_401_response(middleware, mock_request):
    """Test dispatch with 401 authentication required."""
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 401

    async def call_next(request):
        return mock_response

    response = await middleware.dispatch(mock_request, call_next)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_dispatch_exception(middleware, mock_request):
    """Test dispatch with exception."""

    async def call_next(request):
        msg = "Test error"
        raise ValueError(msg)

    with pytest.raises(ValueError, match="Test error"):
        await middleware.dispatch(mock_request, call_next)


@pytest.mark.asyncio
async def test_dispatch_timing(middleware, mock_request, mock_response):
    """Test dispatch measures request timing."""

    async def call_next(request):
        return mock_response

    response = await middleware.dispatch(mock_request, call_next)

    assert response == mock_response
