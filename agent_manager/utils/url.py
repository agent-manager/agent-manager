"""File URL utilities for agent-manager."""

from pathlib import Path


def is_file_url(url: str) -> bool:
    """Check if a URL is a file:// URL or a plain filesystem path.

    Args:
        url: The URL to check

    Returns:
        True if it's a file:// URL or plain path, False otherwise
    """
    # Reject URLs with leading/trailing whitespace
    if url != url.strip():
        return False

    # Explicit file:// protocol
    if url.startswith("file://"):
        return True

    # Plain absolute path (Unix-style)
    if url.startswith("/"):
        return True

    # Home directory path
    if url.startswith("~"):
        return True

    # Relative paths
    if url.startswith("./") or url.startswith("../"):
        return True

    # Current or parent directory
    return bool(url == "." or url == "..")


def resolve_file_path(url: str) -> Path:
    """Resolve a file:// URL to an absolute path.

    Args:
        url: The file:// URL to resolve (or plain path)

    Returns:
        Resolved absolute Path
    """
    path_str = url[7:] if url.startswith("file://") else url
    return Path(path_str).expanduser().resolve()
