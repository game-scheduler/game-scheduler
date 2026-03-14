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


"""Tests for API version endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from services.api.app import create_app


@pytest.fixture
def client():
    """Create test client for API."""
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint with version information."""

    def test_health_returns_200(self, client):
        """Health endpoint should return 200 OK."""
        response = client.get("/health")

        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client):
        """Health endpoint should include 'healthy' status."""
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"

    def test_health_includes_service_name(self, client):
        """Health endpoint should identify service as 'api'."""
        response = client.get("/health")
        data = response.json()

        assert data["service"] == "api"

    def test_health_includes_version_object(self, client):
        """Health endpoint should include version object with git and api versions."""
        response = client.get("/health")
        data = response.json()

        assert "version" in data
        assert isinstance(data["version"], dict)
        assert "git" in data["version"]
        assert "api" in data["version"]

    def test_health_git_version_is_string(self, client):
        """Git version should be a non-empty string."""
        response = client.get("/health")
        data = response.json()

        git_version = data["version"]["git"]
        assert isinstance(git_version, str)
        assert len(git_version) > 0

    def test_health_api_version_is_string(self, client):
        """API version should be a non-empty string."""
        response = client.get("/health")
        data = response.json()

        api_version = data["version"]["api"]
        assert isinstance(api_version, str)
        assert len(api_version) > 0

    def test_health_uses_version_functions(self, client):
        """Health endpoint should call version functions to get version info."""
        with (
            patch("services.api.app.get_git_version") as mock_git,
            patch("services.api.app.get_api_version") as mock_api,
        ):
            mock_git.return_value = "test-git-version"
            mock_api.return_value = "test-api-version"

            response = client.get("/health")
            data = response.json()

            assert data["version"]["git"] == "test-git-version"
            assert data["version"]["api"] == "test-api-version"
            mock_git.assert_called()
            mock_api.assert_called()


class TestVersionEndpoint:
    """Tests for /api/v1/version endpoint."""

    def test_version_returns_200(self, client):
        """Version endpoint should return 200 OK."""
        response = client.get("/api/v1/version")

        assert response.status_code == 200

    def test_version_returns_json(self, client):
        """Version endpoint should return JSON response."""
        response = client.get("/api/v1/version")

        assert response.headers["content-type"] == "application/json"

    def test_version_includes_service_name(self, client):
        """Version endpoint should identify service as 'api'."""
        response = client.get("/api/v1/version")
        data = response.json()

        assert data["service"] == "api"

    def test_version_includes_git_version(self, client):
        """Version endpoint should include git_version field."""
        response = client.get("/api/v1/version")
        data = response.json()

        assert "git_version" in data
        assert isinstance(data["git_version"], str)
        assert len(data["git_version"]) > 0

    def test_version_includes_api_version(self, client):
        """Version endpoint should include api_version field."""
        response = client.get("/api/v1/version")
        data = response.json()

        assert "api_version" in data
        assert isinstance(data["api_version"], str)
        assert len(data["api_version"]) > 0

    def test_version_includes_api_prefix(self, client):
        """Version endpoint should include api_prefix field."""
        response = client.get("/api/v1/version")
        data = response.json()

        assert "api_prefix" in data
        assert data["api_prefix"] == "/api/v1"

    def test_version_response_structure(self, client):
        """Version endpoint should return expected structure."""
        response = client.get("/api/v1/version")
        data = response.json()

        expected_keys = {"service", "git_version", "api_version", "api_prefix"}
        assert set(data.keys()) == expected_keys

    def test_version_uses_version_functions(self, client):
        """Version endpoint should call version functions to get version info."""
        with (
            patch("services.api.app.get_git_version") as mock_git,
            patch("services.api.app.get_api_version") as mock_api,
        ):
            mock_git.return_value = "mocked-git-123"
            mock_api.return_value = "2.0.0"

            response = client.get("/api/v1/version")
            data = response.json()

            assert data["git_version"] == "mocked-git-123"
            assert data["api_version"] == "2.0.0"
            mock_git.assert_called()
            mock_api.assert_called()

    def test_version_api_version_semantic_format(self, client):
        """API version should follow semantic versioning format."""
        response = client.get("/api/v1/version")
        data = response.json()

        api_version = data["api_version"]
        parts = api_version.split(".")

        # Should have exactly 3 parts (major.minor.patch)
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)


class TestVersionIntegration:
    """Integration tests for version information across endpoints."""

    def test_health_and_version_return_same_versions(self, client):
        """Health and version endpoints should return consistent version info."""
        health_response = client.get("/health")
        version_response = client.get("/api/v1/version")

        health_data = health_response.json()
        version_data = version_response.json()

        assert health_data["version"]["git"] == version_data["git_version"]
        assert health_data["version"]["api"] == version_data["api_version"]

    def test_fastapi_app_version_matches_api_version(self, client):
        """FastAPI app version should match the API version from endpoint."""
        version_response = client.get("/api/v1/version")
        version_data = version_response.json()

        # Check OpenAPI schema version
        openapi_response = client.get("/openapi.json")
        openapi_data = openapi_response.json()

        assert openapi_data["info"]["version"] == version_data["api_version"]
