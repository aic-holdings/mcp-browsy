"""
Platform utilities for Chrome/browser detection.

Handles cross-platform detection of:
- Chrome executable paths
- Default user profile directories
- Browser process detection
"""

import os
import shutil
import sys
from pathlib import Path
from typing import Optional


def get_platform() -> str:
    """Return the current operating system: 'mac', 'linux', or 'windows'."""
    if sys.platform.startswith("darwin"):
        return "mac"
    elif sys.platform.startswith("win"):
        return "windows"
    return "linux"


def find_chrome_executable() -> Optional[str]:
    """
    Find the Chrome/Chromium executable path based on the platform.

    Returns the first found executable, checking common installation paths
    before falling back to PATH lookup.
    """
    plat = get_platform()

    if plat == "mac":
        paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]
    elif plat == "windows":
        # Expand environment variables for Windows paths
        paths = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        ]
    else:  # linux
        paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium",
            "/usr/bin/brave-browser",
            "/usr/bin/microsoft-edge",
        ]

    # Check explicit paths first
    for path in paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path

    # Fallback to PATH lookup
    for name in ["google-chrome", "google-chrome-stable", "chrome", "chromium", "chromium-browser"]:
        path = shutil.which(name)
        if path:
            return path

    return None


def find_default_profile_dir() -> Optional[str]:
    """
    Find the default Chrome user data directory.

    Returns None if the directory doesn't exist.
    """
    plat = get_platform()
    home = Path.home()

    if plat == "mac":
        candidates = [
            home / "Library/Application Support/Google/Chrome",
            home / "Library/Application Support/Chromium",
        ]
    elif plat == "windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidates = [
                Path(local_app_data) / "Google" / "Chrome" / "User Data",
                Path(local_app_data) / "Chromium" / "User Data",
            ]
        else:
            return None
    else:  # linux
        candidates = [
            home / ".config" / "google-chrome",
            home / ".config" / "chromium",
        ]

    for path in candidates:
        if path.exists():
            return str(path)

    return None


def is_profile_locked(profile_dir: str) -> bool:
    """
    Check if a Chrome profile is locked (Chrome is running with this profile).

    Chrome creates a 'SingletonLock' file or 'lockfile' when running.
    """
    profile_path = Path(profile_dir)

    # Different lock file names by platform
    lock_files = [
        profile_path / "SingletonLock",
        profile_path / "SingletonSocket",
        profile_path / "lockfile",
    ]

    for lock_file in lock_files:
        if lock_file.exists():
            return True

    return False


def get_temp_profile_dir() -> str:
    """Create and return a temporary profile directory."""
    import tempfile
    return tempfile.mkdtemp(prefix="mcp-browsy-profile-")
