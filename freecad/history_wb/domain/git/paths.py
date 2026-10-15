# File responsibility: Resolve filesystem aliases for repository-relative paths
# and normalize Git paths across operating systems while preserving their spelling.
"""Git path normalization helpers."""

from os.path import realpath, relpath
from pathlib import PurePosixPath


def to_git_path(path: str) -> str:
    """Convert OS path separators to Git's POSIX-style separators."""
    return path.replace("\\", "/")


def relative_git_path(path: str, root: str) -> str:
    """Resolve filesystem aliases and return a repository-relative Git path."""
    return to_git_path(relpath(realpath(path), realpath(root)))


def git_path_name(path: str) -> str:
    """Return final path component from an OS or Git-style path."""
    return PurePosixPath(to_git_path(path).rstrip("/")).name


def is_fcstd_path(path: str) -> bool:
    """Return True when path has a FreeCAD document extension."""
    return path.lower().endswith(".fcstd")
