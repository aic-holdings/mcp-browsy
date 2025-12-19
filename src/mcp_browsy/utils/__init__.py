"""
Utility modules for mcp-browsy.
"""

from .platform import (
    find_chrome_executable,
    find_default_profile_dir,
    is_profile_locked,
    get_temp_profile_dir,
)

__all__ = [
    "find_chrome_executable",
    "find_default_profile_dir",
    "is_profile_locked",
    "get_temp_profile_dir",
]
