"""Tests for platform utilities - Chrome detection and profile management.

These tests run without needing Chrome and verify the platform detection logic.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

from mcp_browsy.utils.platform import (
    find_chrome_executable,
    find_default_profile_dir,
    is_profile_locked,
    get_temp_profile_dir,
)


class TestFindChromeExecutable:
    """Test Chrome executable detection."""

    def test_returns_string_or_none(self):
        """Should return a string path or None."""
        result = find_chrome_executable()
        assert result is None or isinstance(result, str)

    def test_executable_exists_if_found(self):
        """If a path is returned, it should exist."""
        result = find_chrome_executable()
        if result:
            assert os.path.exists(result), f"Chrome path doesn't exist: {result}"

    def test_executable_is_file(self):
        """If a path is returned, it should be a file (or app on macOS)."""
        result = find_chrome_executable()
        if result:
            # On macOS, it might be an .app bundle
            if sys.platform == "darwin":
                assert os.path.exists(result)
            else:
                assert os.path.isfile(result), f"Chrome path is not a file: {result}"


class TestFindDefaultProfileDir:
    """Test Chrome profile directory detection."""

    def test_returns_string_or_none(self):
        """Should return a string path or None."""
        result = find_default_profile_dir()
        assert result is None or isinstance(result, str)

    def test_is_directory_if_exists(self):
        """If returned and exists, should be a directory."""
        result = find_default_profile_dir()
        if result and os.path.exists(result):
            assert os.path.isdir(result), f"Profile path is not a directory: {result}"


class TestIsProfileLocked:
    """Test Chrome profile lock detection."""

    def test_nonexistent_dir_not_locked(self):
        """A nonexistent directory should not be considered locked."""
        result = is_profile_locked("/nonexistent/path/that/does/not/exist")
        assert result is False

    def test_empty_dir_not_locked(self):
        """An empty directory should not be considered locked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = is_profile_locked(tmpdir)
            assert result is False

    def test_dir_with_lock_file_is_locked(self):
        """A directory with SingletonLock should be considered locked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock lock file
            lock_file = Path(tmpdir) / "SingletonLock"
            lock_file.touch()
            result = is_profile_locked(tmpdir)
            assert result is True


class TestGetTempProfileDir:
    """Test temporary profile directory creation."""

    def test_returns_string(self):
        """Should return a string path."""
        result = get_temp_profile_dir()
        assert isinstance(result, str)

    def test_path_is_valid(self):
        """Should return a valid path string."""
        result = get_temp_profile_dir()
        # Just verify it's a reasonable path
        assert len(result) > 0
        assert "mcp-browsy" in result

    def test_returns_different_paths(self):
        """Multiple calls should return different paths."""
        path1 = get_temp_profile_dir()
        path2 = get_temp_profile_dir()
        # They should be different (unique temp dirs)
        assert path1 != path2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
