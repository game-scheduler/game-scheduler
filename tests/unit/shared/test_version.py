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


"""Tests for version information module."""

from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

from shared.version import API_VERSION, get_api_version, get_git_version


class TestGetGitVersion:
    """Tests for get_git_version function."""

    def test_returns_version_from_package_metadata(self):
        """Should return version from importlib.metadata.version when package is installed."""
        with patch("shared.version.version") as mock_version:
            mock_version.return_value = "1.2.3"

            result = get_git_version()

            assert result == "1.2.3"
            mock_version.assert_called_once_with("Game_Scheduler")

    def test_falls_back_to_env_var_when_package_not_found(self, monkeypatch):
        """Should use GIT_VERSION environment variable when package not installed."""
        monkeypatch.setenv("GIT_VERSION", "0.0.1.dev478+gd128f6a")

        with patch("shared.version.version") as mock_version:
            mock_version.side_effect = PackageNotFoundError()

            result = get_git_version()

            assert result == "0.0.1.dev478+gd128f6a"

    def test_returns_dev_unknown_when_no_version_available(self, monkeypatch):
        """Should return 'dev-unknown' when neither package nor env var is available."""
        monkeypatch.delenv("GIT_VERSION", raising=False)

        with patch("shared.version.version") as mock_version:
            mock_version.side_effect = PackageNotFoundError()

            result = get_git_version()

            assert result == "dev-unknown"

    def test_handles_empty_env_var(self, monkeypatch):
        """Should fall back to 'dev-unknown' when GIT_VERSION is empty string."""
        monkeypatch.setenv("GIT_VERSION", "")

        with patch("shared.version.version") as mock_version:
            mock_version.side_effect = PackageNotFoundError()

            result = get_git_version()

            assert result == "dev-unknown"

    def test_preserves_setuptools_scm_format(self):
        """Should preserve setuptools-scm version format with dev and commit hash."""
        test_versions = [
            "1.0.0",
            "1.0.1.dev5+gd128f6a",
            "1.0.1.dev5+gd128f6a.d20251227",
            "0.0.1.dev478+gd128f6a",
        ]

        for test_version in test_versions:
            with patch("shared.version.version") as mock_version:
                mock_version.return_value = test_version

                result = get_git_version()

                assert result == test_version


class TestGetApiVersion:
    """Tests for get_api_version function."""

    def test_returns_api_version_constant(self):
        """Should return the API_VERSION constant value."""
        result = get_api_version()

        assert result == API_VERSION

    def test_api_version_is_semantic_version(self):
        """API version should follow semantic versioning format."""
        result = get_api_version()

        # Basic semantic version validation (major.minor.patch)
        parts = result.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_api_version_constant_matches_function(self):
        """The function should return exactly what the constant contains."""
        assert get_api_version() == API_VERSION
        assert API_VERSION == "1.0.0"


class TestVersionModuleIntegration:
    """Integration tests for version module behavior."""

    def test_version_functions_do_not_raise_exceptions(self):
        """Both version functions should never raise exceptions."""
        # These should not raise even in unusual circumstances
        git_version = get_git_version()
        api_version = get_api_version()

        assert isinstance(git_version, str)
        assert isinstance(api_version, str)
        assert len(git_version) > 0
        assert len(api_version) > 0

    def test_version_priority_order(self, monkeypatch):
        """Should follow priority: package metadata > env var > fallback."""
        monkeypatch.setenv("GIT_VERSION", "env-version")

        # Priority 1: Package metadata
        with patch("shared.version.version") as mock_version:
            mock_version.return_value = "package-version"
            assert get_git_version() == "package-version"

        # Priority 2: Environment variable (when package not found)
        with patch("shared.version.version") as mock_version:
            mock_version.side_effect = PackageNotFoundError()
            assert get_git_version() == "env-version"

        # Priority 3: Fallback (when neither available)
        monkeypatch.delenv("GIT_VERSION", raising=False)
        with patch("shared.version.version") as mock_version:
            mock_version.side_effect = PackageNotFoundError()
            assert get_git_version() == "dev-unknown"
