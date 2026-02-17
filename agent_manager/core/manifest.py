"""Manifest system for tracking files written by agent-manager.

Each target directory gets a `.agent-manager/manifest` YAML file that
records which files were written, by which agents, and when the
directory was last synced.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from agent_manager.output import MessageType, VerbosityLevel, message

# Relative path under the target directory
MANIFEST_DIR = ".agent-manager"
MANIFEST_FILE = "manifest"


def _file_hash(path: Path) -> str:
    """Compute a SHA-256 hex digest for a file.

    Args:
        path: File to hash

    Returns:
        Hex digest string, or empty string if the file cannot be read
    """
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


# ------------------------------------------------------------------
# Data helpers
# ------------------------------------------------------------------
def _empty_manifest() -> dict[str, Any]:
    """Return an empty manifest structure."""
    return {"last_synced": None, "files": []}


def _manifest_path(base_directory: Path) -> Path:
    """Return the full path to the manifest file for a directory."""
    return base_directory / MANIFEST_DIR / MANIFEST_FILE


# ------------------------------------------------------------------
# Read / Write
# ------------------------------------------------------------------
def read_manifest(base_directory: Path) -> dict[str, Any]:
    """Read the manifest for *base_directory*.

    Returns an empty manifest if the file does not exist or is invalid.

    Args:
        base_directory: Target directory

    Returns:
        Manifest dictionary with ``last_synced`` and ``files`` keys
    """
    path = _manifest_path(base_directory)
    if not path.exists():
        return _empty_manifest()

    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            return _empty_manifest()
        data.setdefault("last_synced", None)
        data.setdefault("files", [])
        return data
    except Exception as exc:
        message(
            f"Warning: could not read manifest at {path}: {exc}",
            MessageType.WARNING,
            VerbosityLevel.ALWAYS,
        )
        return _empty_manifest()


def write_manifest(
    base_directory: Path,
    manifest: dict[str, Any],
) -> None:
    """Write *manifest* to disk under *base_directory*.

    Automatically updates ``last_synced`` to the current UTC time.

    Args:
        base_directory: Target directory
        manifest: Manifest dictionary
    """
    manifest["last_synced"] = (
        datetime.now(tz=UTC).isoformat(timespec="seconds")
    )

    path = _manifest_path(base_directory)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

    message(
        f"Manifest written to {path}",
        MessageType.DEBUG,
        VerbosityLevel.DEBUG,
    )


# ------------------------------------------------------------------
# Lookup helpers
# ------------------------------------------------------------------
def get_manifest_entry(
    manifest: dict[str, Any], file_name: str,
) -> dict[str, Any] | None:
    """Find a manifest entry by file name.

    Args:
        manifest: Manifest dictionary
        file_name: Relative file path (e.g. ``".cursor/rules/foo.md"``)

    Returns:
        The entry dict, or ``None`` if not found
    """
    for entry in manifest.get("files", []):
        if entry.get("name") == file_name:
            return entry
    return None


def is_managed(manifest: dict[str, Any], file_name: str) -> bool:
    """Return ``True`` if *file_name* is tracked in the manifest."""
    return get_manifest_entry(manifest, file_name) is not None


# ------------------------------------------------------------------
# Update helpers
# ------------------------------------------------------------------
def add_or_update_entry(
    manifest: dict[str, Any],
    file_name: str,
    agent_name: str,
    file_path: Path,
) -> None:
    """Add or update a manifest entry for a written file.

    If the file already exists in the manifest, the agent is added to
    its ``agents`` list (if not already present) and the hash is
    updated.  Otherwise a new entry is created.

    Args:
        manifest: Manifest dictionary (modified in place)
        file_name: Relative file path
        agent_name: Name of the agent that wrote the file
        file_path: Absolute path to compute hash from
    """
    entry = get_manifest_entry(manifest, file_name)
    new_hash = _file_hash(file_path)

    if entry is not None:
        if agent_name not in entry.get("agents", []):
            entry.setdefault("agents", []).append(agent_name)
        entry["hash"] = new_hash
    else:
        manifest.setdefault("files", []).append({
            "name": file_name,
            "agents": [agent_name],
            "hash": new_hash,
        })


def remove_agent_from_entry(
    manifest: dict[str, Any],
    file_name: str,
    agent_name: str,
) -> bool:
    """Remove an agent from a manifest entry.

    If the entry's ``agents`` list becomes empty after removal, the
    entry is removed from the manifest entirely.

    Args:
        manifest: Manifest dictionary (modified in place)
        file_name: Relative file path
        agent_name: Agent name to remove

    Returns:
        ``True`` if the entry was fully removed (agents empty),
        ``False`` if the agent was just removed from the list, or the
        entry/agent was not found.
    """
    entry = get_manifest_entry(manifest, file_name)
    if entry is None:
        return False

    agents = entry.get("agents", [])
    if agent_name in agents:
        agents.remove(agent_name)

    if not agents:
        manifest["files"] = [
            e for e in manifest["files"] if e.get("name") != file_name
        ]
        return True

    return False


# ------------------------------------------------------------------
# Cleanup
# ------------------------------------------------------------------
def cleanup_stale_files(
    base_directory: Path,
    manifest: dict[str, Any],
    agent_name: str,
    current_files: set[str],
) -> list[str]:
    """Remove files that an agent no longer produces.

    For each manifest entry that lists *agent_name*:
    - If the file is in *current_files*, do nothing (it's still active).
    - If the file is NOT in *current_files*, remove the agent from the
      entry. If no agents remain, delete the file from disk.

    Args:
        base_directory: Target directory
        manifest: Manifest dictionary (modified in place)
        agent_name: Agent being cleaned up
        current_files: Set of relative file paths the agent just wrote

    Returns:
        List of file paths that were deleted from disk
    """
    deleted: list[str] = []

    # Work on a copy of the files list since we mutate it
    for entry in list(manifest.get("files", [])):
        name = entry.get("name", "")
        agents = entry.get("agents", [])

        if agent_name not in agents:
            continue

        if name in current_files:
            continue

        # Agent no longer produces this file
        fully_removed = remove_agent_from_entry(manifest, name, agent_name)

        if fully_removed:
            file_path = base_directory / name
            if file_path.exists():
                try:
                    file_path.unlink()
                    deleted.append(name)
                    message(
                        f"  Deleted stale file: {name}",
                        MessageType.INFO,
                        VerbosityLevel.VERBOSE,
                    )
                except OSError as exc:
                    message(
                        f"  Could not delete {name}: {exc}",
                        MessageType.WARNING,
                        VerbosityLevel.ALWAYS,
                    )

    return deleted
